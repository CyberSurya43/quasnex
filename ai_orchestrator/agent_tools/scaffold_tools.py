"""Project scaffolding tool — lets the agent create a new orchestrator project."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool, tool

from .. import knowledge_graph as kg
from ..scaffolding import init_project


def build_tools(base_dir: Path) -> list[BaseTool]:
    base_dir = base_dir.resolve()

    @tool
    def scaffold_project(target_dir: str, name: str) -> str:
        """Create a new AI-orchestrator project (orchestrator.toml, workspace/, .env.example)
        at a path relative to the current directory.
        """
        target = (base_dir / target_dir).resolve()
        try:
            init_project(target, name)
        except FileExistsError as exc:
            return f"Error: {exc}"
        kg.build_or_update(target / "workspace", target)
        return f"Created project {name!r} at {target}"

    return [scaffold_project]
