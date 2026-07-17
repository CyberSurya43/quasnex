"""Persistent project memory, distinct from the per-thread chat history.

Backed by the existing shared-context store (``.orchestrator/context.json``),
so facts saved here are visible to every future chat session and every
pipeline stage for this project — not just the current conversation.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool, tool


def build_tools(project_dir: Path | None) -> list[BaseTool]:
    @tool
    def remember(key: str, value: str) -> str:
        """Save a fact/preference/decision that should persist across chat sessions
        and pipeline runs for this project (e.g. "database=postgres", "style_guide=airbnb").
        Use this for anything worth not re-explaining next time.
        """
        if project_dir is None:
            return "Error: no project directory is active — nothing to attach this memory to"
        from ..core import context as ctx_store

        ctx_store.set_user_preference(project_dir, key, value)
        return f"Remembered: {key} = {value}"

    @tool
    def recall() -> str:
        """List everything currently remembered about this project (preferences,
        completed stages, past failures)."""
        if project_dir is None:
            return "No project directory is active — nothing has been remembered"
        from ..core import context as ctx_store

        block = ctx_store.inject_context_block(project_dir)
        return block or "Nothing remembered yet"

    return [remember, recall]
