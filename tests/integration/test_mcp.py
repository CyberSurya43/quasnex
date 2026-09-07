"""Real MCP round trips; skipped when the optional MCP extra is not installed."""

import asyncio
import json
import sys
import socket
import subprocess
import time

import pytest

pytest.importorskip("mcp")

from ai_orchestrator.agent_tools import mcp_tools
from ai_orchestrator.agent_tools.confirm import set_confirmation_sink
from ai_orchestrator.integrations import MCPServer


@pytest.fixture
def local_server(tmp_path):
    source = tmp_path / "server.py"
    source.write_text('''from mcp.server.fastmcp import FastMCP
server = FastMCP("Quasnex test")
@server.tool()
def add(a: int, b: int) -> int:
    return a + b
@server.tool()
def fail() -> str:
    raise ValueError("deliberate tool failure")
@server.tool()
async def slow() -> str:
    import asyncio
    await asyncio.sleep(10)
    return "done"
server.run()
''')
    (tmp_path / ".quasnex.json").write_text(json.dumps({"mcpServers": {
        "local": {"command": sys.executable, "args": [str(source)], "timeout": 10},
    }}))
    set_confirmation_sink(lambda *_: True)
    yield tmp_path
    set_confirmation_sink(None)


def test_real_stdio_discovery_call_and_server_error(local_server):
    tools = {item.name: item for item in mcp_tools.build_tools(local_server)}
    discovered = json.loads(tools["list_mcp_tools"].invoke({"server": "local"}))
    add = next(item for item in discovered["tools"] if item["name"] == "add")
    assert set(add["inputSchema"]["required"]) == {"a", "b"}
    result = json.loads(tools["call_mcp_tool"].invoke({
        "server": "local", "name": "add", "arguments": {"a": 2, "b": 3},
    }))
    assert result["isError"] is False
    assert result["content"][0]["text"] == "5"
    failed = json.loads(mcp_tools.request(local_server, "local", "fail", {}))
    assert failed["isError"] is True


def test_stdio_timeout_returns_error(local_server):
    path = local_server / ".quasnex.json"
    config = json.loads(path.read_text())
    config["mcpServers"]["local"]["timeout"] = 2
    path.write_text(json.dumps(config))
    result = mcp_tools.request(local_server, "local", "slow", {})
    assert result.startswith("Error: MCP request failed")


def test_real_streamable_http_round_trip(tmp_path, monkeypatch):
    import httpx
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("HTTP test", stateless_http=True, json_response=True)

    @server.tool()
    def echo(message: str) -> str:
        return message

    app = server.streamable_http_app()
    received_headers = []

    async def recording_app(scope, receive, send):
        received_headers.append(dict(scope["headers"]))
        await app(scope, receive, send)

    original_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(
        transport=httpx.ASGITransport(app=recording_app), **kwargs,
    ))
    config = MCPServer(transport="streamable-http", url="http://localhost:8000/mcp",
                       headers={"Authorization": "Bearer test-token"})

    async def exercise():
        async with server.session_manager.run():
            discovered = await mcp_tools._request(tmp_path, config, None, {})
            result = await mcp_tools._request(tmp_path, config, "echo", {"message": "hello Quasnex"})
            return discovered, result

    discovered, result = asyncio.run(exercise())
    assert discovered["tools"][0]["name"] == "echo"
    assert result["content"][0]["text"] == "hello Quasnex"
    assert all(headers[b"authorization"] == b"Bearer test-token" for headers in received_headers)


def test_real_legacy_sse_round_trip(tmp_path):
    # Bind a local test server only; no external service or credentials required.
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    source = tmp_path / "sse_server.py"
    source.write_text('''import sys
from mcp.server.fastmcp import FastMCP
server = FastMCP("SSE test", host="127.0.0.1", port=int(sys.argv[1]))
@server.tool()
def echo(message: str) -> str:
    return message
server.run(transport="sse")
''')
    process = subprocess.Popen([sys.executable, str(source), str(port)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 10
        while True:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.2):
                    break
            except OSError:
                if process.poll() is not None or time.monotonic() > deadline:
                    pytest.fail("Local SSE test server did not start")
                time.sleep(.05)
        config = MCPServer(transport="sse", url=f"http://127.0.0.1:{port}/sse", timeout=5)
        discovered = asyncio.run(mcp_tools._request(tmp_path, config, None, {}))
        result = asyncio.run(mcp_tools._request(tmp_path, config, "echo", {"message": "SSE works"}))
        assert discovered["tools"][0]["name"] == "echo"
        assert result["content"][0]["text"] == "SSE works"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
