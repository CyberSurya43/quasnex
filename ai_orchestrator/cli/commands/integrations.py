"""Configure integrations without requiring a model provider."""

from pathlib import Path

from ...integrations import CONFIG_NAME, IntegrationError, initialize_integrations, load_integrations
from ...skills import list_skills
from ..ui import console


def handle_integrations(action: str, project_dir: Path | None) -> None:
    root = (project_dir or Path.cwd()).resolve()
    try:
        if action == "init":
            path = initialize_integrations(root)
            console.print(f"Created {path}", markup=False)
            console.print("Edit the server settings and set enabled to true. Put skills in .quasnex/skills/ or add paths to skills.")
            return
        config = load_integrations(root)
        console.print(f"Configuration: {root / CONFIG_NAME}", markup=False)
        for name, server in config.mcpServers.items():
            console.print(f"  MCP {name}: {server.transport}, {'enabled' if server.enabled else 'disabled'}", markup=False)
        if not config.mcpServers:
            console.print("No MCP servers configured. Run quasnex integrations init.")
        console.print("Skills: " + ", ".join(list_skills(root)), markup=False)
    except FileExistsError:
        console.print(f"{CONFIG_NAME} already exists; edit it to update your integrations.", markup=False)
    except (IntegrationError, OSError) as exc:
        console.print(f"Error: {exc}", markup=False)
        raise SystemExit(1) from exc
