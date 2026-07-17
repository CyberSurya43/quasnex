"""Skills: reusable step-by-step methodologies for plan/build/test/deploy/debug.

Unlike ``tools/senior_dev.py`` (broad standards injected into every system
prompt), skills are pulled in on demand — either explicitly via the
``load_skill`` tool, or by the chat REPL's ``/plan`` ``/build`` ``/test``
``/deploy`` ``/debug`` slash commands — so a small model isn't carrying every
methodology in context all the time, only the one relevant to the task at hand.
"""

from __future__ import annotations

from pathlib import Path

_SKILLS_DIR = Path(__file__).resolve().parent

SKILL_NAMES = ("plan", "build", "test", "deploy", "debug")


def list_skills() -> tuple[str, ...]:
    return SKILL_NAMES


def load_skill(name: str) -> str:
    """Return the full instructions for a skill, or an error message if unknown."""
    name = name.strip().lower()
    if name not in SKILL_NAMES:
        return f"Error: unknown skill {name!r}. Available: {', '.join(SKILL_NAMES)}"
    return (_SKILLS_DIR / f"{name}.md").read_text(encoding="utf-8")


__all__ = ["list_skills", "load_skill", "SKILL_NAMES"]
