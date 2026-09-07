"""On-demand MCP tools with bounded, independently closed client sessions."""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from datetime import timedelta
import json
import os
from pathlib import Path

from langchain_core.tools import BaseTool, tool

from ..integrations import IntegrationError, MCPServer, load_integrations, resolve_path, resolve_server
from .confirm import confirm


async def _request(root: Path, server: MCPServer, name: str | None, arguments: dict) -> dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamable_http_client
    import httpx

    async with asyncio.timeout(server.timeout), AsyncExitStack() as stack:
        if server.transport == "stdio":
            params = StdioServerParameters(
                command=server.command, args=server.args, env=server.env,
                cwd=str(resolve_path(root, server.cwd or ".")),
            )
            # Server stderr may contain credentials; keep it out of chat/logs.
            errlog = stack.enter_context(open(os.devnull, "w"))
            streams = await stack.enter_async_context(stdio_client(params, errlog=errlog))
        elif server.transport == "sse":
            streams = await stack.enter_async_context(sse_client(
                server.url, headers=server.headers,
                timeout=server.timeout, sse_read_timeout=server.timeout,
            ))
        else:
            client = await stack.enter_async_context(httpx.AsyncClient(
                headers=server.headers, timeout=server.timeout,
            ))
            streams = await stack.enter_async_context(streamable_http_client(server.url, http_client=client))
        session = await stack.enter_async_context(ClientSession(
            streams[0], streams[1], read_timeout_seconds=timedelta(seconds=server.timeout),
        ))
        await session.initialize()
        if name is not None:
            result = await session.call_tool(name, arguments)
            return result.model_dump(mode="json", by_alias=True, exclude_none=True)
        tools, cursor, seen = [], None, set()
        while True:
            page = await session.list_tools(cursor=cursor)
            tools.extend(item.model_dump(mode="json", by_alias=True, exclude_none=True) for item in page.tools)
            cursor = page.nextCursor
            if not cursor:
                return {"tools": tools}
            if cursor in seen:
                raise IntegrationError("MCP server returned a repeated pagination cursor.")
            seen.add(cursor)


def request(root: Path, server_name: str, name: str | None = None, arguments: dict | None = None) -> str:
    """Confirm on the caller's thread, then connect; never replay failed calls."""
    try:
        server = resolve_server(root, server_name)
        operation = f"call {name}" if name else "list tools"
        if not confirm("MCP connection", f"Server: {server_name}\nOperation: {operation}\n"
                       f"Arguments: {json.dumps(arguments or {}, ensure_ascii=False)}"):
            return "Declined by user: MCP operation was not run."
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            result = asyncio.run(_request(root, server, name, arguments or {}))
        else:
            # A sync LangChain tool may also be invoked by an async caller.
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(lambda: asyncio.run(_request(root, server, name, arguments or {}))).result()
        return json.dumps(result, ensure_ascii=False)
    except ImportError:
        return 'Error: MCP support is not installed. Run python -m pip install "quasnex[mcp]" (or -e ".[mcp]" from the source checkout).'
    except IntegrationError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        # Transport errors can embed authorization headers or token-bearing URLs.
        return (f"Error: MCP request failed ({type(exc).__name__}). Check the server command/URL, "
                "credentials and timeout. A failed tool call may have executed; inspect its effects before retrying.")


def build_tools(root: Path) -> list[BaseTool]:
    @tool
    def list_mcp_servers() -> str:
        """List configured MCP server names, transports and enabled flags without connecting."""
        try:
            return json.dumps({name: {"transport": server.transport, "enabled": server.enabled}
                               for name, server in load_integrations(root).mcpServers.items()})
        except IntegrationError as exc:
            return f"Error: {exc}"

    @tool
    def list_mcp_tools(server: str) -> str:
        """Connect to a configured MCP server and discover tool names, descriptions and JSON input schemas."""
        return request(root, server)

    @tool
    def call_mcp_tool(server: str, name: str, arguments: dict) -> str:
        """Call an external MCP tool using the input schema from list_mcp_tools. Requires confirmation.

        Results include content, structuredContent when provided, and isError.
        Each request uses a fresh session; session-local state is not retained.
        """
        return request(root, server, name, arguments)

    return [list_mcp_servers, list_mcp_tools, call_mcp_tool]
