from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class AgentConfig:
    name: str
    role: str
    command: str


@dataclass(frozen=True)
class StageConfig:
    name: str
    agent: str
    title: str
    objective: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    acceptance: tuple[str, ...]


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    workspace: Path
    stack: dict[str, str]
    agents: dict[str, AgentConfig]
    stages: tuple[StageConfig, ...]


def load_config(project_dir: Path) -> ProjectConfig:
    config_path = project_dir / "orchestrator.toml"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing orchestrator config: {config_path}")

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    agents_data = data.get("agents", {})
    stages_data = data.get("stages", [])

    if not project.get("name"):
        raise ValueError("orchestrator.toml must define [project].name")
    if not stages_data:
        raise ValueError("orchestrator.toml must define at least one [[stages]] entry")

    agents = {
        key: AgentConfig(
            name=value.get("name", key),
            role=value.get("role", ""),
            command=value.get("command", ""),
        )
        for key, value in agents_data.items()
    }
    if not agents:
        raise ValueError("orchestrator.toml must define at least one [agents.<id>] entry")

    stages: list[StageConfig] = []
    for raw_stage in stages_data:
        stage = StageConfig(
            name=_required(raw_stage, "name"),
            agent=_required(raw_stage, "agent"),
            title=_required(raw_stage, "title"),
            objective=_required(raw_stage, "objective"),
            inputs=tuple(raw_stage.get("inputs", [])),
            outputs=tuple(raw_stage.get("outputs", [])),
            acceptance=tuple(raw_stage.get("acceptance", [])),
        )
        if stage.agent not in agents:
            raise ValueError(f"Stage {stage.name!r} references unknown agent {stage.agent!r}")
        stages.append(stage)

    workspace = project_dir / project.get("workspace", "workspace")
    return ProjectConfig(
        name=project["name"],
        workspace=workspace,
        stack=dict(data.get("stack", {})),
        agents=agents,
        stages=tuple(stages),
    )


def _required(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Stage entry must define {key!r}")
    return value
