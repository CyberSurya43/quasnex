"""Lets the agent pull a step-by-step methodology into context on demand."""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from ..skills import list_skills, load_skill


def build_tools() -> list[BaseTool]:
    @tool
    def load_skill_instructions(name: str) -> str:
        """Load detailed step-by-step instructions for a development skill.

        Available skills: plan, build, test, deploy, debug. Call this before
        starting a non-trivial task of that kind (e.g. call load_skill_instructions('test')
        before running/writing tests) so you follow the project's expected methodology.
        """
        return load_skill(name)

    return [load_skill_instructions]


__all__ = ["build_tools", "list_skills"]
