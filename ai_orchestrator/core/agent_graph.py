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

import sqlite3
from pathlib import Path
from typing import Callable, Iterable

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph

from ..agent_tools import build_all_tools
from ..llm import ModelRegistry
from ..tools.senior_dev import get_agent_instructions
from . import context as ctx_store

ToolCallHook = Callable[[str, dict], None]


def _checkpointer(project_dir: Path | None):
    if project_dir is None:
        return MemorySaver()
    state_dir = project_dir / ".orchestrator"
    state_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(state_dir / "chat_state.sqlite"), check_same_thread=False)
    return SqliteSaver(conn)


def _system_prompt(project_dir: Path | None, persona: str | None) -> str:
    parts = [persona or get_agent_instructions("codex")]
    if project_dir is not None:
        context_block = ctx_store.inject_context_block(project_dir)
        if context_block:
            parts.append(context_block)
    return "\n".join(parts)


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

    def send(self, message: str, on_tool_call: ToolCallHook | None = None) -> str:
        """Send a message, run the tool-use loop, and return the final assistant text."""
        config = {"configurable": {"thread_id": self._thread_id()}, "recursion_limit": 50}
        final_text = ""
        seen = 0
        for step in self._graph.stream(
            {"messages": [("user", message)]}, config, stream_mode="values"
        ):
            messages: list[BaseMessage] = step.get("messages", [])
            for msg in messages[seen:]:
                if isinstance(msg, AIMessage) and msg.content:
                    final_text = msg.content if isinstance(msg.content, str) else str(msg.content)
                if isinstance(msg, AIMessage) and msg.tool_calls and on_tool_call:
                    for call in msg.tool_calls:
                        on_tool_call(call["name"], call.get("args", {}))
            seen = len(messages)
        return final_text or "(no response)"

    def list_tools(self) -> list[str]:
        return [t.name for t in self._tools]
