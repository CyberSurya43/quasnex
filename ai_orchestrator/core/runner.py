from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json

from ..config import AgentConfig, ModelRoute, StageConfig, load_config
from .. import knowledge_graph as kg
from . import context as ctx_store
from .agent_graph import CodingAgent, HardStopError
from ..llm import ModelRegistry
from ..skills import load_skill
from ..tools.senior_dev import get_rules_for_stage, DevelopmentTools

_STAGE_SKILL_KEYWORDS = (
    ("deploy", "deploy"),
    ("test", "test"),
    ("intake", "plan"),
    ("architecture", "plan"),
)

_ROLE_STAGE_KEYWORDS = (
    ("deployment", ("deploy", "release", "container", "docker")),
    ("testing", ("test", "quality", "verification", "verify")),
    ("debugging", ("debug", "fix", "failure", "bug")),
    ("planner", ("intake", "architecture", "plan")),
    ("repository_search", ("repository", "repo search", "context", "knowledge graph")),
    ("coding", ("frontend", "backend", "integration", "build", "code")),
    ("documentation", ("doc", "handoff", "api-contract", "contract")),
)


def _matching_skill(stage_name: str) -> str | None:
    lowered = stage_name.lower()
    for keyword, skill_name in _STAGE_SKILL_KEYWORDS:
        if keyword in lowered:
            return skill_name
    return "build"  # frontend/backend/integration stages all write code


def model_role_for_stage(stage: StageConfig) -> str:
    """Pick the model capability role for a pipeline stage."""
    identity = f"{stage.name} {stage.title}".lower()
    for role, keywords in _ROLE_STAGE_KEYWORDS:
        if any(keyword in identity for keyword in keywords):
            return role

    objective = stage.objective.lower()
    for role, keywords in _ROLE_STAGE_KEYWORDS:
        if any(keyword in objective for keyword in keywords):
            return role
    return "coding"


class Orchestrator:
    """Plans and runs the multi-stage build pipeline defined in orchestrator.toml.

    Each stage is executed by the same tool-using LangGraph agent (see
    ``core.agent_graph.CodingAgent``), adopting the stage's configured persona
    and reading/writing real files in the project workspace. If the active
    model provider fails, it falls back to the other configured provider.
    """

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir.resolve()
        self.config = load_config(self.project_dir)
        self.registry = ModelRegistry(self.project_dir)

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
        kg.build_or_update(self.config.workspace, self.project_dir)
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
            result = self._run_stage(stage, task_file, execute)
            results.append(result)
        self._write_state(run_dir, "executed" if execute else "dry_run", results)
        return results

    def write_task(self, run_dir: Path, stage: StageConfig) -> Path:
        agent = self.config.agents[stage.agent]
        task_file = run_dir / "tasks" / f"{stage.name}.md"

        content = self._task_markdown(stage, agent.role)
        content += "\n" + self._add_professional_guidelines(stage)
        skill_name = _matching_skill(stage.name)
        if skill_name:
            content += f"\n---\n## Skill: {skill_name}\n\n{load_skill(skill_name)}\n"
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
                "- Each stage is executed by the same tool-using coding agent, adopting the",
                "  stage's persona (see [agents.<id>].role in orchestrator.toml).",
                "- The agent reads its stage task file, then uses its filesystem/shell tools",
                "  to do the work directly in the workspace.",
                "- File writes and shell commands require interactive confirmation.",
                "- Each stage writes completion notes into `.orchestrator/notes/<stage>.md`.",
                "- If the active model provider errors out, the run falls back to the other",
                "  configured role candidate and resumes from the same task file.",
                "- Shared context is maintained in `.orchestrator/context.json`.",
            ]
        )
        handoff.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return handoff

    # ------------------------------------------------------------------
    # Stage execution
    # ------------------------------------------------------------------

    def _run_stage(
        self,
        stage: StageConfig,
        task_file: Path,
        execute: bool,
    ) -> dict[str, object]:
        agent = self.config.agents[stage.agent]
        result: dict[str, object] = {
            "stage": stage.name,
            "agent": stage.agent,
            "task_file": str(task_file),
            "executed": execute,
            "model_used": None,
            "success": None,
        }

        if not execute:
            return result

        model_role = model_role_for_stage(stage)
        model_order = self._model_order(model_role, agent)
        task_prompt = task_file.read_text(encoding="utf-8")

        for route in model_order:
            try:
                self.registry.switch(route.provider, route.model)
                coding_agent = CodingAgent(
                    self.registry,
                    workspace_root=self.config.workspace,
                    project_dir=self.project_dir,
                    persona=agent.role,
                )
                coding_agent.send(task_prompt)
                result["model_used"] = route.label
                result["success"] = True
                ctx_store.record_stage_complete(
                    self.project_dir, stage.name, stage.agent, route.label
                )
                return result
            except HardStopError:
                # Hard-stops are policy decisions (too many retries, permission
                # denied, etc.) — re-raise immediately.  Provider fallback would
                # just repeat the same outcome with a different model.
                raise
            except Exception as exc:
                reason = str(exc)
                print(
                    f"  [fallback] model {route.label!r} failed for stage {stage.name!r} "
                    f"({reason}). Trying next model..."
                )
                ctx_store.record_stage_failure(
                    self.project_dir, stage.name, stage.agent, route.label, reason
                )

        result["success"] = False
        result["model_used"] = "none"
        print(f"  [ERROR] All models failed for stage {stage.name!r}. Manual intervention required.")
        return result

    def _provider_order(self, agent: AgentConfig) -> list[str]:
        """Preferred provider first (if configured/available), then the rest."""
        available = list(self.registry.env_config.providers)
        if agent.provider and agent.provider in available:
            return [agent.provider] + [p for p in available if p != agent.provider]
        return available

    def _model_order(self, role: str, agent: AgentConfig) -> list[ModelRoute]:
        """Preferred role candidates first, then any remaining configured models."""
        routes = list(self.registry.role_candidates(role))

        seen = {(route.provider, route.model) for route in routes}
        for provider_name in self._provider_order(agent):
            for model_name in self.registry.env_config.providers[provider_name].models:
                key = (provider_name, model_name)
                if key in seen:
                    continue
                seen.add(key)
                routes.append(ModelRoute(provider_name, model_name))
        return routes

    def _add_professional_guidelines(self, stage: StageConfig) -> str:
        lines = ["", "---", "## Professional Development Guidelines", ""]

        stage_rules = get_rules_for_stage(stage.name)
        lines.append(stage_rules)
        lines.append("")

        if "test" in stage.name.lower():
            lines.append("### Testing Checklist")
            for item in DevelopmentTools.get_testing_checklist():
                lines.append(f"- [ ] {item}")
            lines.append("")

        if "deploy" in stage.name.lower():
            lines.append("### Deployment Checklist")
            for item in DevelopmentTools.get_deployment_checklist():
                lines.append(f"- [ ] {item}")
            lines.append("")

        lines.append("### Security Checklist")
        for item in DevelopmentTools.get_security_checklist():
            lines.append(f"- [ ] {item}")
        lines.append("")

        lines.append("### Code Review Checklist")
        for item in DevelopmentTools.get_code_review_checklist():
            lines.append(f"- [ ] {item}")
        lines.append("")

        return "\n".join(lines)

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
            f"Model role: `{model_role_for_stage(stage)}`",
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
