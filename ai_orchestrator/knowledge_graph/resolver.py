"""Context resolver: map a natural-language issue/task description to the most
likely-relevant files and symbols in the knowledge graph.

This is the "point the model at the right place before it starts digging"
piece — a cheap keyword/symbol scorer, not a semantic search. It's meant to
narrow down a handful of candidates for the agent to then actually read with
``read_file``/``search_code``, not to replace those tools.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_STOPWORDS = {
    "the", "a", "an", "is", "are", "to", "of", "in", "on", "for", "and", "or",
    "it", "this", "that", "when", "with", "not", "does", "do", "why", "how",
    "tries", "manual", "manually", "should", "need", "needs", "done",
}
_SPLIT_RE = re.compile(r"[^A-Za-z0-9]+")
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _tokenize(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in _SPLIT_RE.split(text):
        if not raw:
            continue
        for part in _CAMEL_RE.sub(" ", raw).split():
            part = part.lower()
            if len(part) > 2 and part not in _STOPWORDS:
                tokens.add(part)
    return tokens


def resolve(query: str, graph: dict[str, Any], top_k: int = 8) -> list[dict[str, Any]]:
    """Score every indexed file against the query tokens. Returns the top_k
    files with score > 0, each with the symbols that matched and why.
    """
    tokens = _tokenize(query)
    if not tokens:
        return []

    results: list[dict[str, Any]] = []
    for rel_path, entry in graph.get("files", {}).items():
        score = 0
        matched: list[str] = []
        reasons: list[str] = []

        path_tokens = _tokenize(rel_path)
        overlap = tokens & path_tokens
        if overlap:
            score += 2 * len(overlap)
            reasons.append(f"path matches: {', '.join(sorted(overlap))}")

        for symbol in entry.get("functions", []) + entry.get("classes", []):
            symbol_tokens = _tokenize(symbol)
            if tokens & symbol_tokens or symbol.lower() in tokens:
                score += 3
                matched.append(symbol)

        term_hits = tokens & set(entry.get("terms", {}))
        if term_hits:
            weighted_hits = sorted(
                term_hits,
                key=lambda term: entry.get("terms", {}).get(term, 0),
                reverse=True,
            )
            score += sum(min(entry.get("terms", {}).get(term, 0), 5) for term in term_hits)
            reasons.append(f"content terms: {', '.join(weighted_hits[:6])}")

        for module in entry.get("imports", []):
            module_tokens = _tokenize(module)
            if tokens & module_tokens:
                score += 1
                reasons.append(f"imports {module}")

        if score > 0:
            results.append(
                {
                    "file": rel_path,
                    "score": score,
                    "matched_symbols": sorted(set(matched))[:15],
                    "reasons": reasons[:3],
                }
            )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def format_results(results: list[dict[str, Any]]) -> str:
    if not results:
        return (
            "No strong matches in the knowledge graph for that description. "
            "Fall back to search_code/glob_files to locate the relevant code."
        )
    lines = []
    for r in results:
        line = f"- {r['file']} (score {r['score']})"
        if r["matched_symbols"]:
            line += f" — symbols: {', '.join(r['matched_symbols'])}"
        if r["reasons"]:
            line += f" [{'; '.join(r['reasons'])}]"
        lines.append(line)
    return "\n".join(lines)
