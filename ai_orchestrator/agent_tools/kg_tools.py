"""Knowledge-graph tools: index the project once, then point the model at the
right files for a given issue instead of exploring blind.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool, tool

from .. import knowledge_graph as kg


def build_tools(workspace_root: Path, project_dir: Path | None) -> list[BaseTool]:
    @tool
    def build_knowledge_graph() -> str:
        """(Re)index the project into a knowledge graph of files, functions/classes,
        and import relationships. Call this once when you start working in an
        existing/unfamiliar project, before exploring file-by-file. Safe to call
        again later — unchanged files are reused, so re-indexing is cheap.
        """
        graph = kg.build_or_update(workspace_root, project_dir)
        return (
            f"Indexed {len(graph['files'])} files and {len(graph['edges'])} import edges. "
            "Use resolve_issue(description) to find where a reported problem likely lives."
        )

    @tool
    def resolve_issue(description: str, top_k: int = 8) -> str:
        """Given a bug report or feature description, use the knowledge graph to
        point at the most likely-relevant files and symbols before reading code
        blindly. Refreshes the graph first (cheap — only changed files are
        re-parsed), so it reflects the current state of the code.
        """
        graph = kg.build_or_update(workspace_root, project_dir)
        results = kg.resolve(description, graph, top_k=top_k)
        return kg.format_results(results)

    @tool
    def kg_stats() -> str:
        """Show a summary of the current knowledge graph (files indexed, symbol
        counts, when it was last built)."""
        graph = kg.load_graph(project_dir) if project_dir else None
        if not graph:
            return "No knowledge graph built yet. Call build_knowledge_graph() first."
        files = graph.get("files", {})
        n_functions = sum(len(f.get("functions", [])) for f in files.values())
        n_classes = sum(len(f.get("classes", [])) for f in files.values())
        return (
            f"{len(files)} files indexed, {n_functions} functions, {n_classes} classes, "
            f"{len(graph.get('edges', []))} import edges."
        )

    return [build_knowledge_graph, resolve_issue, kg_stats]
