"""Lets the agent pull a step-by-step methodology into context on demand."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool, tool

from ..skills import list_skills, load_skill, read_skill_resource
from ..integrations import IntegrationError


def build_tools(root: Path | None = None) -> list[BaseTool]:
    @tool
    def list_available_skills() -> str:
        """List built-in and external development skills. Inspect before build/debug tasks."""
        try:
            return ", ".join(list_skills(root))
        except IntegrationError as exc:
            return f"Error: {exc}"

    @tool
    def load_skill_instructions(name: str) -> str:
        """Load detailed step-by-step instructions for a development skill.

        Use list_available_skills to discover bundled and external skills. Call this before
        starting a non-trivial task of that kind (e.g. call load_skill_instructions('test')
        before running/writing tests) so you follow the project's expected methodology.
        """
        return load_skill(name, root)

    @tool
    def load_skill_resource(name: str, relative_path: str) -> str:
        """Read a skill's companion text file, such as references/api.md or scripts/check.py.

        Paths are relative to the skill directory. This only reads; it does not execute scripts.
        """
        return read_skill_resource(name, relative_path, root or Path.cwd())

    return [list_available_skills, load_skill_instructions, load_skill_resource]


__all__ = ["build_tools", "list_skills"]
