"""Tools available to the coding agent: filesystem, shell, web (knowledge gateway), scaffolding."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool

from . import fs_tools, kg_tools, memory_tools, scaffold_tools, shell_tools, skill_tools, web_tools
from .confirm import confirm, set_confirmation_sink
from .tool_context import ToolContext

__all__ = ["build_all_tools", "confirm", "set_confirmation_sink"]


def build_all_tools(workspace_root: Path, project_dir: Path | None = None) -> list[BaseTool]:
    """Assemble the full toolset for a workspace.

    ``workspace_root`` scopes file/shell tools (usually the project's workspace/
    directory). ``project_dir`` scopes the scaffolding and memory tools (usually
    the project's root, so persistent memory and sibling-project scaffolding work).
    """
    tools: list[BaseTool] = []
    context = ToolContext()
    tools.extend(kg_tools.build_tools(workspace_root, project_dir, context))
    tools.extend(fs_tools.build_tools(workspace_root, context))
    tools.extend(shell_tools.build_tools(workspace_root))
    tools.extend(web_tools.build_tools())
    tools.extend(scaffold_tools.build_tools(project_dir or workspace_root))
    tools.extend(memory_tools.build_tools(project_dir))
    tools.extend(skill_tools.build_tools())
    return tools
