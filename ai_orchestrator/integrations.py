"""Project-local MCP and external skill configuration, read afresh on each use."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .config.loader import _read_env_file

CONFIG_NAME = ".quasnex.json"


class IntegrationError(ValueError):
    """A user-correctable configuration error with no credential values."""


class MCPServer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    transport: Literal["stdio", "streamable-http", "sse"] = "stdio"
    enabled: bool = True
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    cwd: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    timeout: float = Field(default=30, gt=0, le=600)

    @model_validator(mode="after")
    def validate_transport(self):
        if self.transport == "stdio":
            if not self.command or self.url or self.headers:
                raise ValueError("stdio requires command and does not accept url/headers")
        elif not self.url or self.command or self.args or self.cwd or self.env:
            raise ValueError("HTTP/SSE requires url and does not accept process settings")
        return self


class Integrations(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    mcpServers: dict[str, MCPServer] = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)


def load_integrations(root: Path) -> Integrations:
    path = root / CONFIG_NAME
    if not path.exists():
        return Integrations()
    try:
        config = Integrations.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, ValidationError) as exc:
        # Pydantic errors can contain raw input, including credentials.
        raise IntegrationError(f"Invalid {CONFIG_NAME}; check its JSON and integration fields.") from exc
    if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name) for name in config.mcpServers):
        raise IntegrationError("MCP server names must use 1–64 letters, numbers, underscores or hyphens.")
    return config


def resolve_path(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return (root / path).resolve() if not path.is_absolute() else path.resolve()


def resolve_server(root: Path, name: str) -> MCPServer:
    config = load_integrations(root)
    if name not in config.mcpServers:
        raise IntegrationError(f"Unknown MCP server {name!r}; inspect list_mcp_servers first.")
    server = config.mcpServers[name]
    if not server.enabled:
        raise IntegrationError(f"MCP server {name!r} is disabled in {CONFIG_NAME}.")
    variables = {**os.environ, **_read_env_file(root)}

    def expand(value: str) -> str:
        def replace(match: re.Match) -> str:
            key = match.group(1)
            if not variables.get(key):
                raise IntegrationError(f"Missing environment variable {key} for MCP server {name!r}.")
            return variables[key]
        return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", replace, value)

    data = server.model_dump()
    for key in ("command", "cwd", "url"):
        if data[key] is not None:
            data[key] = expand(data[key])
    data["args"] = [expand(arg) for arg in data["args"]]
    for key in ("env", "headers"):
        data[key] = {k: expand(v) for k, v in data[key].items()}
    resolved = MCPServer.model_validate(data)
    if resolved.url:
        url = urlsplit(resolved.url)
        if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password:
            raise IntegrationError("MCP URLs must be HTTP(S); put authentication in headers.")
    return resolved


EXAMPLE_CONFIG = {
    "mcpServers": {
        "local-tools": {
            "transport": "stdio", "enabled": False,
            "command": "python", "args": ["/absolute/path/to/mcp_server.py"],
        },
        "remote-tools": {
            "transport": "streamable-http", "enabled": False,
            "url": "https://your-server.example/mcp",
            "headers": {"Authorization": "Bearer ${MCP_API_TOKEN}"},
            "timeout": 30,
        },
    },
    "skills": [],
}


def initialize_integrations(root: Path) -> Path:
    path = root / CONFIG_NAME
    # Exclusive creation keeps existing settings intact.
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(EXAMPLE_CONFIG, indent=2) + "\n")
    return path
