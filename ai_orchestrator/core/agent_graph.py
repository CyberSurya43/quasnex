"""LangGraph tool-using coding agent.

Wraps ``langgraph.prebuilt.create_react_agent`` with:
- the active model from ``ModelRegistry`` (rebuildable when the user switches models),
- the filesystem/shell/web/scaffolding tools from ``agent_tools``,
- a system prompt built from the existing professional-guidelines text and shared
  project context (``tools.senior_dev`` / ``core.context``),
- a SQLite-backed checkpointer so conversation state survives across chat sessions,
  scoped per project directory.
"""

from __future__ import annotations

import json
import sqlite3
import re
from pathlib import Path
from typing import Any, Callable, Iterable

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph

from ..agent_tools import build_all_tools
from .. import knowledge_graph as kg
from ..llm import ModelRegistry
from ..tools.senior_dev import get_agent_instructions
from . import context as ctx_store

ToolCallHook = Callable[[str, dict], None]
_MAX_EDIT_TOOL_CALLS_PER_TURN = 8
_MAX_TOOL_CALLS_PER_TURN = 25
_MAX_RAW_TOOL_CALLS_PER_TURN = 3
_TOOL_HARD_STOP_MARKERS = (
    "HARD STOP:",
    "permission required",
)


class HardStopError(RuntimeError):
    """Raised when a tool emits a HARD STOP or permission-required signal.

    Unlike generic RuntimeError, this should NOT trigger provider fallback —
    it means a deliberate policy decision was reached (too many retries, user
    denied permission, etc.) and further model attempts would repeat the same
    outcome.
    """


_KG_CONTEXT_RE = re.compile(
    r"\b("
    r"add|api|bug|build|change|code|component|create|creating|debug|deploy|"
    r"documentation|error|failure|fetch|file|fix|folder|implement|issue|loader|"
    r"modify|read|refactor|remove|repository|search|test|update|verify|write"
    r")\b",
    re.IGNORECASE,
)


def _checkpointer(project_dir: Path | None):
    if project_dir is None:
        return MemorySaver()
    state_dir = project_dir / ".orchestrator"
    state_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(state_dir / "chat_state.sqlite"), check_same_thread=False)
    return SqliteSaver(conn)


def _system_prompt(project_dir: Path | None, persona: str | None) -> str:
    parts = [persona or get_agent_instructions("codex")]
    parts.append(
        "## Tool Workflow\n"
        "- KG-first rule: before reading files, listing folders, globbing, or searching code "
        "for any repository task, use the injected knowledge graph resolver context or call "
        "`resolve_issue(description)` yourself.\n"
        "- Read the highest-ranked KG files first. Use `project_tree`, `list_dir`, "
        "`search_code`, or `glob_files` only after KG context is present or clearly empty.\n"
        "- Once you identify the target file, make the smallest needed edit, then run a focused "
        "verification command when available."
    )
    if project_dir is not None:
        context_block = ctx_store.inject_context_block(project_dir)
        if context_block:
            parts.append(context_block)
    return "\n".join(parts)


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped


def _parse_raw_tool_call(text: str) -> tuple[str, dict[str, Any]] | None:
    """Parse local-model JSON tool-call text emitted outside LangChain tool calling."""
    candidate = _strip_json_fence(text)
    if not (candidate.startswith("{") and candidate.endswith("}")):
        return None
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None

    name = payload.get("name") or payload.get("tool")
    args = payload.get("arguments", payload.get("args", {}))
    if not isinstance(name, str) or not name:
        return None
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return None
    return name, args


class CodingAgent:
    """A tool-using LangGraph agent bound to a project workspace and active model."""

    def __init__(
        self,
        registry: ModelRegistry,
        workspace_root: Path,
        project_dir: Path | None = None,
        persona: str | None = None,
    ):
        self.registry = registry
        self.workspace_root = workspace_root
        self.project_dir = project_dir
        self.persona = persona
        self._checkpointer = _checkpointer(project_dir)
        self._tools = build_all_tools(workspace_root, project_dir)
        self._tools_by_name = {tool.name: tool for tool in self._tools}
        self._thread_suffix = 0
        self._graph: CompiledStateGraph = self._build()

    def _build(self) -> CompiledStateGraph:
        from langgraph.prebuilt import create_react_agent

        return create_react_agent(
            self.registry.chat_model(),
            self._tools,
            prompt=_system_prompt(self.project_dir, self.persona),
            checkpointer=self._checkpointer,
        )

    def rebuild(self) -> None:
        """Rebuild the graph against the currently active model (call after switching)."""
        self._graph = self._build()

    def _thread_id(self) -> str:
        base = str(self.project_dir.resolve()) if self.project_dir else "global"
        return f"{base}#{self._thread_suffix}"

    def clear_history(self) -> None:
        """Start a fresh conversation thread (previous history stays in the checkpoint db)."""
        self._thread_suffix += 1

    def _message_with_kg_context(self, message: str) -> str:
        """Pre-resolve repository requests locally before the LLM sees them."""
        if not _KG_CONTEXT_RE.search(message):
            return message

        store_dir = self.project_dir or self.workspace_root
        graph = kg.build_or_update(self.workspace_root, store_dir)
        results = kg.resolve(message, graph, top_k=8)
        formatted = kg.format_results(results) if results else (
            "No strong KG matches. Use search_code/glob_files as a fallback, "
            "and keep the search narrowly scoped."
        )

        return (
            "Knowledge graph context resolver results for this request "
            "(computed locally, no LLM call):\n"
            f"{formatted}\n\n"
            "KG-FIRST INSTRUCTION: use these files as the first places to inspect. "
            "Only fall back to project_tree/list_dir/search_code/glob_files if the KG "
            "results are empty or clearly wrong.\n\n"
            f"User request:\n{message}"
        )

    def send(
        self,
        message: str,
        on_tool_call: ToolCallHook | None = None,
        recursion_limit: int = 40,
        raw_tool_depth: int = 0,
    ) -> str:
        """Send a message, run the tool-use loop, and return the final assistant text."""
        config = {"configurable": {"thread_id": self._thread_id()}, "recursion_limit": recursion_limit}
        message = self._message_with_kg_context(message)
        final_text = ""
        seen = 0
        edit_tool_calls = 0
        total_tool_calls = 0
        for step in self._graph.stream(
            {"messages": [("user", message)]}, config, stream_mode="values"
        ):
            messages: list[BaseMessage] = step.get("messages", [])
            for msg in messages[seen:]:
                if isinstance(msg, AIMessage) and msg.content:
                    final_text = msg.content if isinstance(msg.content, str) else str(msg.content)
                if isinstance(msg, ToolMessage):
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    if any(marker in content for marker in _TOOL_HARD_STOP_MARKERS):
                        # Hard-stop signals are policy decisions, not transient
                        # failures — raise HardStopError so the runner does NOT
                        # attempt provider fallback.
                        raise HardStopError(content)
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for call in msg.tool_calls:
                        total_tool_calls += 1
                        if call["name"] == "edit_file":
                            edit_tool_calls += 1
                            if edit_tool_calls > _MAX_EDIT_TOOL_CALLS_PER_TURN:
                                raise HardStopError(
                                    "Stopped tool loop: edit_file was called too many times in one turn. "
                                    "Re-read the exact target lines and continue in a fresh request."
                                )
                        if total_tool_calls > _MAX_TOOL_CALLS_PER_TURN:
                            raise HardStopError(
                                "Stopped tool loop: too many tool calls in one turn. "
                                "Summarize progress and continue with a narrower request."
                            )
                        if on_tool_call:
                            on_tool_call(call["name"], call.get("args", {}))
            seen = len(messages)
        if final_text:
            raw_tool_call = _parse_raw_tool_call(final_text)
            if raw_tool_call is not None:
                if raw_tool_depth >= _MAX_RAW_TOOL_CALLS_PER_TURN:
                    raise HardStopError(
                        "Stopped tool loop: model emitted too many raw JSON tool calls. "
                        "Continue with a narrower request or switch to a model with proper tool calling."
                    )
                tool_name, args = raw_tool_call
                tool_result = self._run_raw_tool_call(tool_name, args, on_tool_call)
                followup = (
                    f"The model emitted a raw JSON tool call, so it was executed locally.\n\n"
                    f"Tool: {tool_name}\n"
                    f"Arguments: {args}\n"
                    f"Result:\n{tool_result}\n\n"
                    "Continue from this tool result. Do not repeat the same raw JSON tool call; "
                    "answer the user or choose the next necessary tool."
                )
                return self.send(
                    followup,
                    on_tool_call=on_tool_call,
                    recursion_limit=recursion_limit,
                    raw_tool_depth=raw_tool_depth + 1,
                )
        return final_text or "(no response)"

    def _run_raw_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        on_tool_call: ToolCallHook | None,
    ) -> str:
        tool = self._tools_by_name.get(tool_name)
        if tool is None:
            return (
                f"Error: unknown tool {tool_name!r}. Available tools: "
                f"{', '.join(sorted(self._tools_by_name))}"
            )
        if on_tool_call:
            on_tool_call(tool_name, args)
        result = tool.invoke(args)
        result_text = result if isinstance(result, str) else str(result)
        if any(marker in result_text for marker in _TOOL_HARD_STOP_MARKERS):
            raise RuntimeError(result_text)
        return result_text

    def list_tools(self) -> list[str]:
        return [t.name for t in self._tools]
