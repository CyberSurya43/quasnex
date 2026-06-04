from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import shlex
import subprocess

from .config import ProjectConfig, StageConfig, load_config


class Orchestrator:
    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir.resolve()
        self.config = load_config(self.project_dir)

    def create_run(self) -> Path:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = self.project_dir / ".orchestrator" / "runs" / run_id
        (run_dir / "tasks").mkdir(parents=True, exist_ok=True)
        (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        self._write_state(run_dir, "created")
        return run_dir

    def plan(self, run_dir: Path | None = None) -> Path:
        run_dir = run_dir or self.create_run()
        for stage in self.config.stages:
            self.write_task(run_dir, stage)
        self.write_handoff(run_dir)
        self._write_state(run_dir, "planned")
        return run_dir

    def run(self, stage_name: str | None, execute: bool) -> list[dict[str, object]]:
        run_dir = self.plan()
        stages = self._selected_stages(stage_name)
        results = []
        for stage in stages:
            task_file = self.write_task(run_dir, stage)
            command = self.render_command(stage, task_file, run_dir)
            result = {
                "stage": stage.name,
                "agent": stage.agent,
                "task_file": str(task_file),
                "command": command,
                "executed": execute,
                "returncode": None,
            }
            if execute:
                completed = subprocess.run(
                    shlex.split(command),
                    cwd=self.config.workspace,
                    check=False,
                    text=True,
                )
                result["returncode"] = completed.returncode
            results.append(result)
        self._write_state(run_dir, "executed" if execute else "dry_run", results)
        return results

    def write_task(self, run_dir: Path, stage: StageConfig) -> Path:
        agent = self.config.agents[stage.agent]
        task_file = run_dir / "tasks" / f"{stage.name}.md"
        task_file.write_text(self._task_markdown(stage, agent.role), encoding="utf-8")
        return task_file

    def write_handoff(self, run_dir: Path) -> Path:
        handoff = run_dir / "handoff.md"
        lines = [
            f"# {self.config.name} Build Handoff",
            "",
            f"Workspace: `{self.config.workspace}`",
            "",
            "## Stage Order",
            "",
        ]
        for index, stage in enumerate(self.config.stages, start=1):
            lines.append(f"{index}. `{stage.name}` -> `{stage.agent}`: {stage.title}")
        lines.extend(
            [
                "",
                "## Operating Rules",
                "",
                "- Each agent reads its stage task file before making changes.",
                "- Each agent writes completed work notes into `.orchestrator/notes/<stage>.md`.",
                "- Frontend changes are owned by Gemini unless a later Codex stage is integrating or testing.",
                "- Backend, test, deployment, and release changes are owned by Codex.",
            ]
        )
        handoff.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return handoff

    def render_command(self, stage: StageConfig, task_file: Path, run_dir: Path) -> str:
        agent = self.config.agents[stage.agent]
        if not agent.command:
            raise ValueError(f"Agent {stage.agent!r} has no command configured")
        return agent.command.format(
            task_file=str(task_file),
            workspace=str(self.config.workspace),
            stage=stage.name,
            run_dir=str(run_dir),
        )

    def _selected_stages(self, stage_name: str | None) -> tuple[StageConfig, ...]:
        if stage_name is None:
            return self.config.stages
        matches = tuple(stage for stage in self.config.stages if stage.name == stage_name)
        if not matches:
            raise ValueError(f"Unknown stage {stage_name!r}")
        return matches

    def _task_markdown(self, stage: StageConfig, agent_role: str) -> str:
        lines = [
            f"# {stage.title}",
            "",
            f"Project: `{self.config.name}`",
            f"Workspace: `{self.config.workspace}`",
            f"Stage: `{stage.name}`",
            "",
            "## Agent Role",
            "",
            agent_role,
            "",
            "## Objective",
            "",
            stage.objective,
            "",
            "## Stack",
            "",
        ]
        if self.config.stack:
            lines.extend(f"- {key}: {value}" for key, value in self.config.stack.items())
        else:
            lines.append("- Not specified")
        lines.extend(["", "## Inputs", ""])
        lines.extend(f"- {item}" for item in stage.inputs) if stage.inputs else lines.append("- None")
        lines.extend(["", "## Required Outputs", ""])
        lines.extend(f"- {item}" for item in stage.outputs) if stage.outputs else lines.append("- None")
        lines.extend(["", "## Acceptance Criteria", ""])
        lines.extend(f"- {item}" for item in stage.acceptance) if stage.acceptance else lines.append("- None")
        lines.extend(
            [
                "",
                "## Completion Notes",
                "",
                f"Write notes to `.orchestrator/notes/{stage.name}.md` with files changed, commands run, and blockers.",
            ]
        )
        return "\n".join(lines) + "\n"

    def _write_state(
        self,
        run_dir: Path,
        status: str,
        results: list[dict[str, object]] | None = None,
    ) -> None:
        state = {
            "project": self.config.name,
            "status": status,
            "workspace": str(self.config.workspace),
            "stages": [asdict(stage) for stage in self.config.stages],
            "results": results or [],
        }
        (run_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
