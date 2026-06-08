"""Shared context store — persisted as .orchestrator/context.json.

All agents read and write through this so every model (Gemini, Codex, Qwen)
shares the same project state, user preferences, and progress history.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json


_CONTEXT_FILE = ".orchestrator/context.json"


def _path(project_dir: Path) -> Path:
    return project_dir / _CONTEXT_FILE


def load(project_dir: Path) -> dict:
    p = _path(project_dir)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def save(project_dir: Path, context: dict) -> None:
    p = _path(project_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(context, indent=2), encoding="utf-8")


def record_stage_complete(project_dir: Path, stage: str, agent: str, model: str) -> None:
    ctx = load(project_dir)
    ctx.setdefault("completed_stages", []).append(
        {
            "stage": stage,
            "agent": agent,
            "model_used": model,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    save(project_dir, ctx)


def record_stage_failure(project_dir: Path, stage: str, agent: str, model: str, reason: str) -> None:
    ctx = load(project_dir)
    ctx.setdefault("failures", []).append(
        {
            "stage": stage,
            "agent": agent,
            "model_attempted": model,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    save(project_dir, ctx)


def set_user_preference(project_dir: Path, key: str, value: object) -> None:
    ctx = load(project_dir)
    ctx.setdefault("user_preferences", {})[key] = value
    save(project_dir, ctx)


def inject_context_block(project_dir: Path) -> str:
    """Return a markdown block that can be appended to every task file."""
    ctx = load(project_dir)
    if not ctx:
        return ""

    lines = [
        "",
        "---",
        "## Shared Project Context",
        "",
        "This block is auto-injected so all agents share the same project state.",
        "",
    ]

    prefs = ctx.get("user_preferences", {})
    if prefs:
        lines.append("### User Preferences")
        lines.extend(f"- {k}: {v}" for k, v in prefs.items())
        lines.append("")

    done = ctx.get("completed_stages", [])
    if done:
        lines.append("### Completed Stages")
        for entry in done:
            lines.append(
                f"- `{entry['stage']}` completed by {entry['agent']} "
                f"(model: {entry['model_used']}) at {entry['timestamp']}"
            )
        lines.append("")

    failures = ctx.get("failures", [])
    if failures:
        lines.append("### Known Failures / Fallbacks")
        for entry in failures:
            lines.append(
                f"- `{entry['stage']}` — {entry['agent']} / {entry['model_attempted']} "
                f"failed: {entry['reason']}"
            )
        lines.append("")

    notes_dir = project_dir / ".orchestrator" / "notes"
    if notes_dir.exists():
        note_files = sorted(notes_dir.glob("*.md"))
        if note_files:
            lines.append("### Agent Completion Notes")
            for nf in note_files:
                lines.append(f"#### {nf.stem}")
                lines.extend(nf.read_text(encoding="utf-8").splitlines())
                lines.append("")

    return "\n".join(lines) + "\n"
