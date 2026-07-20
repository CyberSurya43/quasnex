"""Lightweight, dependency-free project knowledge graph.

Inspired by tools like GitNexus (which uses tree-sitter + a native graph DB to
index a codebase for AI agents) but scoped down to something that runs
anywhere Python does: no native bindings, no graph database. It walks the
workspace, extracts symbols (functions/classes) and import edges per file
using ``ast`` for Python and light regex heuristics for other languages, and
caches the result as JSON. Re-running only re-parses files whose mtime/size
changed, so it stays cheap to call often.
"""

from __future__ import annotations

import ast
from collections import Counter
import re
import time
from pathlib import Path
from typing import Any

_IGNORE_DIRS = {
    ".git", ".orchestrator", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", "dist", "build", ".next", ".cache", "egg-info",
}
_LANGUAGE_BY_EXT = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".go": "go", ".java": "java",
    ".rb": "ruby", ".php": "php", ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp",
    ".cs": "csharp", ".rs": "rust", ".kt": "kotlin", ".swift": "swift",
}
_MAX_FILES = 4000
_MAX_FILE_BYTES = 300_000
_MAX_TERMS = 300

_GENERIC_FUNC_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)|"
    r"^\s*(?:public|private|protected|static|func|def|fn)\s+([A-Za-z_$][\w$]*)\s*\(|"
    r"^\s*(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(",
    re.MULTILINE,
)
_GENERIC_CLASS_RE = re.compile(
    r"^\s*(?:export\s+)?(?:public\s+)?(?:class|interface|struct)\s+([A-Za-z_$][\w$]*)",
    re.MULTILINE,
)
_GENERIC_IMPORT_RE = re.compile(
    r"""^\s*(?:import\s+.*?from\s+['"]([^'"]+)['"]|"""
    r"""import\s+['"]([^'"]+)['"]|"""
    r"""require\(\s*['"]([^'"]+)['"]\s*\)|"""
    r"""#include\s+["<]([^">]+)[">])""",
    re.MULTILINE,
)
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_TERM_STOPWORDS = {
    "the", "and", "for", "from", "with", "this", "that", "then", "than", "else",
    "const", "let", "var", "function", "return", "import", "export", "class",
    "public", "private", "protected", "static", "true", "false", "null", "none",
    "undefined", "async", "await", "type", "interface",
}


def _is_ignored(rel: Path) -> bool:
    return any(part in _IGNORE_DIRS for part in rel.parts)


def _extract_python(text: str) -> tuple[list[str], list[str], list[str]]:
    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return functions, classes, imports

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append("." * node.level + node.module)
    return functions, classes, imports


def _extract_generic(text: str) -> tuple[list[str], list[str], list[str]]:
    functions = [m for group in _GENERIC_FUNC_RE.findall(text) for m in group if m]
    classes = _GENERIC_CLASS_RE.findall(text)
    imports = [m for group in _GENERIC_IMPORT_RE.findall(text) for m in group if m]
    return functions, classes, imports


def _extract_symbols(text: str, language: str | None) -> tuple[list[str], list[str], list[str]]:
    if language == "python":
        return _extract_python(text)
    if language is not None:
        return _extract_generic(text)
    return [], [], []


def _tokens(text: str) -> list[str]:
    terms: list[str] = []
    for raw in _TOKEN_RE.findall(text):
        for part in _CAMEL_RE.sub(" ", raw).replace("_", " ").split():
            part = part.lower()
            if len(part) > 2 and part not in _TERM_STOPWORDS:
                terms.append(part)
    return terms


def _term_counts(rel: Path, text: str, functions: list[str], classes: list[str], imports: list[str]) -> dict[str, int]:
    """Build a small local lexical index for fuzzy KG resolution.

    This intentionally stays simple and dependency-free: no LLM calls, no
    embeddings, just capped token counts from path, symbols, imports, and file
    text. It gives the resolver enough signal for UI strings and attributes
    such as "due date picker" even when there is no matching symbol name.
    """
    counter: Counter[str] = Counter()
    counter.update(_tokens(str(rel)))
    counter.update(_tokens(" ".join(functions + classes + imports)))
    counter.update(_tokens(text))
    return dict(counter.most_common(_MAX_TERMS))


def _resolve_import_targets(module: str, all_files: list[str]) -> list[str]:
    """Best-effort match of an import string to an indexed file, by stem name."""
    stem = module.lstrip(".").split("/")[-1].split(".")[-1]
    if not stem:
        return []
    targets = []
    for rel in all_files:
        name = Path(rel).stem
        if name == stem or name == "index" and Path(rel).parent.name == stem:
            targets.append(rel)
    return targets[:5]


def build_graph(workspace_root: Path, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """Walk workspace_root and build/update the knowledge graph.

    Files whose mtime+size match the previous graph are reused as-is instead
    of being re-parsed, so repeated calls (e.g. before every resolve_issue)
    stay cheap.
    """
    workspace_root = workspace_root.resolve()
    prev_files: dict[str, Any] = (previous or {}).get("files", {})

    files: dict[str, Any] = {}
    scanned = 0
    for path in sorted(workspace_root.rglob("*")):
        if scanned >= _MAX_FILES:
            break
        if not path.is_file():
            continue
        rel = path.relative_to(workspace_root)
        if _is_ignored(rel):
            continue
        ext = path.suffix.lower()
        language = _LANGUAGE_BY_EXT.get(ext)
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_size > _MAX_FILE_BYTES:
            continue

        rel_str = str(rel)
        scanned += 1
        cached = prev_files.get(rel_str)
        if (
            cached
            and cached.get("mtime") == stat.st_mtime
            and cached.get("size") == stat.st_size
            and "terms" in cached
        ):
            files[rel_str] = cached
            continue

        functions: list[str] = []
        classes: list[str] = []
        imports: list[str] = []
        text = ""
        if language:
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                text = ""
            functions, classes, imports = _extract_symbols(text, language)

        files[rel_str] = {
            "language": language,
            "mtime": stat.st_mtime,
            "size": stat.st_size,
            "functions": sorted(set(functions))[:100],
            "classes": sorted(set(classes))[:100],
            "imports": sorted(set(imports))[:100],
            "terms": _term_counts(rel, text, functions, classes, imports),
        }

    all_paths = list(files.keys())
    edges: list[dict[str, str]] = []
    for rel_str, entry in files.items():
        for module in entry.get("imports", []):
            for target in _resolve_import_targets(module, all_paths):
                if target != rel_str:
                    edges.append({"from": rel_str, "to": target, "type": "imports"})

    return {
        "generated_at": time.time(),
        "root": str(workspace_root),
        "files": files,
        "edges": edges,
    }
