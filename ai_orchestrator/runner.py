from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import shlex
import subprocess

from .config import AgentConfig, ProjectConfig, StageConfig, load_config
from . import context as ctx_store


_MAX_RETRIES_PER_MODEL = 1


class Orchestrator:
    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir.resolve()
        self.config = load_config(self.project_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
            result = self._run_stage(stage, task_file, run_dir, execute)
            results.append(result)
        self._write_state(run_dir, "executed" if execute else "dry_run", results)
        return results

    def write_task(self, run_dir: Path, stage: StageConfig) -> Path:
        agent = self.config.agents[stage.agent]
        task_file = run_dir / "tasks" / f"{stage.name}.md"
        content = self._task_markdown(stage, agent.role)
        content += ctx_store.inject_context_block(self.project_dir)
        task_file.write_text(content, encoding="utf-8")
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
                "- Frontend (UI/UX) is owned by Gemini. Fallback: Qwen local model.",
                "- Backend, testing, deployment, and release are owned by Codex. Fallback: Qwen local model.",
                "- If a primary model fails (credit exhaustion, timeout, API error), the fallback model",
                "  resumes from the same task file without human intervention.",
                "- Shared context is maintained in `.orchestrator/context.json` across all models.",
            ]
        )
        handoff.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return handoff

    def render_command(self, stage: StageConfig, task_file: Path, run_dir: Path) -> str:
        agent = self.config.agents[stage.agent]
        return self._render(agent.command, stage, task_file, run_dir)

    # ------------------------------------------------------------------
    # Fallback execution
    # ------------------------------------------------------------------

    def _run_stage(
        self,
        stage: StageConfig,
        task_file: Path,
        run_dir: Path,
        execute: bool,
    ) -> dict[str, object]:
        agent = self.config.agents[stage.agent]
        result: dict[str, object] = {
            "stage": stage.name,
            "agent": stage.agent,
            "task_file": str(task_file),
            "executed": execute,
            "returncode": None,
            "model_used": None,
        }

        if not execute:
            command = self.render_command(stage, task_file, run_dir)
            result["command"] = command
            return result

        # Build ordered list: primary model first, then fallbacks
        model_commands = self._model_command_sequence(agent, stage, task_file, run_dir)

        for model_key, command in model_commands:
            result["command"] = command
            returncode = self._execute(command)
            if returncode == 0:
                result["returncode"] = returncode
                result["model_used"] = model_key
                ctx_store.record_stage_complete(self.project_dir, stage.name, stage.agent, model_key)
                return result
            else:
                reason = f"exit code {returncode}"
                print(
                    f"  [fallback] {model_key} failed for stage {stage.name!r} ({reason})."
                    f" Trying next model..."
                )
                ctx_store.record_stage_failure(
                    self.project_dir, stage.name, stage.agent, model_key, reason
                )

        # All models exhausted
        result["returncode"] = -1
        result["model_used"] = "none"
        print(f"  [ERROR] All models failed for stage {stage.name!r}. Manual intervention required.")
        return result

    def _model_command_sequence(
        self,
        agent: AgentConfig,
        stage: StageConfig,
        task_file: Path,
        run_dir: Path,
    ) -> list[tuple[str, str]]:
        """Return [(model_key, rendered_command), ...] in priority order."""
        sequence: list[tuple[str, str]] = []

        # Primary command
        if agent.command:
            sequence.append(("primary", self._render(agent.command, stage, task_file, run_dir)))

        # Fallback models
        if agent.fallback:
            for model_key in agent.fallback.models:
                cmd_template = agent.fallback.commands.get(model_key, "")
                if cmd_template:
                    sequence.append(
                        (model_key, self._render(cmd_template, stage, task_file, run_dir))
                    )

        return sequence

    def _execute(self, command: str) -> int:
        completed = subprocess.run(
            shlex.split(command),
            cwd=self.config.workspace,
            check=False,
            text=True,
        )
        return completed.returncode

    def _render(self, template: str, stage: StageConfig, task_file: Path, run_dir: Path) -> str:
        return template.format(
            task_file=str(task_file),
            workspace=str(self.config.workspace),
            stage=stage.name,
            run_dir=str(run_dir),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _selected_stages(self, stage_name: str | None) -> tuple[StageConfig, ...]:
        if stage_name is None:
            return self.config.stages
        matches = tuple(s for s in self.config.stages if s.name == stage_name)
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
