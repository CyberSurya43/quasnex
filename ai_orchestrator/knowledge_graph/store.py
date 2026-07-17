"""Persistence for the project knowledge graph: ``.orchestrator/knowledge_graph.json``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .builder import build_graph

_KG_FILE = ".orchestrator/knowledge_graph.json"


def _path(project_dir: Path) -> Path:
    return project_dir / _KG_FILE


def load_graph(project_dir: Path) -> dict[str, Any] | None:
    p = _path(project_dir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_graph(project_dir: Path, graph: dict[str, Any]) -> None:
    p = _path(project_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(graph, indent=2), encoding="utf-8")


def build_or_update(workspace_root: Path, project_dir: Path | None) -> dict[str, Any]:
    """Build the graph, incrementally reusing unchanged files from any cached
    graph, and persist it (when a project_dir is available). This is cheap
    enough to call before every resolve — unchanged files are never re-parsed.
    """
    previous = load_graph(project_dir) if project_dir else None
    graph = build_graph(workspace_root, previous)
    if project_dir:
        save_graph(project_dir, graph)
    return graph
