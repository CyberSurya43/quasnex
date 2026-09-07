"""Skills: reusable step-by-step methodologies for plan/build/test/deploy/debug.

Unlike ``tools/senior_dev.py`` (broad standards injected into every system
prompt), skills are pulled in on demand — either explicitly via the
``load_skill`` tool, or by the chat REPL's ``/plan`` ``/build`` ``/test``
``/deploy`` ``/debug`` slash commands — so a small model isn't carrying every
methodology in context all the time, only the one relevant to the task at hand.
"""

from __future__ import annotations

from pathlib import Path
import re

from ..integrations import IntegrationError, load_integrations, resolve_path

_SKILLS_DIR = Path(__file__).resolve().parent

SKILL_NAMES = ("plan", "build", "test", "deploy", "debug")


def skill_files(root: Path | None = None) -> dict[str, Path]:
    """Find bundled skills plus project and configured external skill folders."""
    files = {name: _SKILLS_DIR / f"{name}.md" for name in SKILL_NAMES}
    if root is None:
        return files
    sources = [root / ".quasnex" / "skills"]
    for value in load_integrations(root).skills:
        path = resolve_path(root, value)
        if not path.exists():
            raise IntegrationError(f"Configured skill path does not exist: {path}")
        sources.append(path)
    for source in sources:
        if source.is_file():
            candidates = [source]
        elif (source / "SKILL.md").is_file():
            candidates = [source / "SKILL.md"]
        elif source.is_dir():
            candidates = sorted(set(source.glob("*.md")) | set(source.glob("*/SKILL.md")))
        else:
            continue
        for path in candidates:
            name = path.parent.name if path.name == "SKILL.md" else path.stem
            name = name.lower()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
                raise IntegrationError(f"Invalid skill name {name!r}; use letters, numbers, hyphens or underscores.")
            if name in files and files[name].resolve() != path.resolve():
                raise IntegrationError(f"Duplicate skill {name!r}; rename the external file or folder.")
            files[name] = path.resolve()
    return files


def list_skills(root: Path | None = None) -> tuple[str, ...]:
    return tuple(skill_files(root))


def load_skill(name: str, root: Path | None = None) -> str:
    """Return the full instructions for a skill, or an error message if unknown."""
    name = name.strip().lower()
    try:
        files = skill_files(root)
        if name not in files:
            return f"Error: unknown skill {name!r}. Available: {', '.join(files)}"
        path = files[name]
        text = path.read_text(encoding="utf-8")
        if name not in SKILL_NAMES:
            text = f"Skill: {name}\nSource: {path}\nRelative resources are under: {path.parent}\n\n{text}"
        return text
    except (IntegrationError, OSError, UnicodeError) as exc:
        return f"Error loading skill: {exc}"


def read_skill_resource(name: str, relative_path: str, root: Path) -> str:
    """Read companion text files, confined to the selected skill directory."""
    try:
        files = skill_files(root)
        if name not in files:
            return f"Error: unknown skill {name!r}."
        directory = files[name].parent.resolve()
        target = (directory / relative_path).resolve()
        if not target.is_relative_to(directory):
            return "Error: resource must be inside the skill directory."
        if target.stat().st_size > 100_000:
            return "Error: skill resource exceeds 100 KB."
        return target.read_text(encoding="utf-8")
    except (IntegrationError, OSError, UnicodeError) as exc:
        return f"Error reading skill resource: {exc}"


__all__ = ["list_skills", "load_skill", "SKILL_NAMES"]
