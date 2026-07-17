"""Lightweight project knowledge graph + context resolver.

Indexes files, their functions/classes, and import edges into
``.orchestrator/knowledge_graph.json``, then lets the agent map a bug/feature
description straight to candidate files (``resolver.resolve``) instead of
exploring blind. Rebuilds incrementally (unchanged files are reused) so it's
cheap to refresh before every use — this is how it stays in sync as the
project's architecture or code changes.
"""

from .builder import build_graph
from .resolver import format_results, resolve
from .store import build_or_update, load_graph, save_graph

__all__ = [
    "build_graph",
    "build_or_update",
    "load_graph",
    "save_graph",
    "resolve",
    "format_results",
]
