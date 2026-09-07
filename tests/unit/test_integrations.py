import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ai_orchestrator.agent_tools import build_all_tools, mcp_tools
from ai_orchestrator.agent_tools.confirm import set_confirmation_sink
from ai_orchestrator.integrations import IntegrationError, initialize_integrations, load_integrations, resolve_server
from ai_orchestrator.skills import list_skills, load_skill, read_skill_resource


def write_config(root, config):
    (root / ".quasnex.json").write_text(json.dumps(config))


def test_initialize_preserves_existing_config(tmp_path):
    path = initialize_integrations(tmp_path)
    original = path.read_text()
    with pytest.raises(FileExistsError):
        initialize_integrations(tmp_path)
    assert path.read_text() == original
    assert all(not server.enabled for server in load_integrations(tmp_path).mcpServers.values())


def test_credentials_resolve_from_env_without_exposing_them(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_TOKEN", "process-secret")
    (tmp_path / ".env").write_text("MCP_TOKEN=file-secret\n")
    write_config(tmp_path, {"mcpServers": {"docs": {
        "transport": "streamable-http", "url": "https://example.com/mcp",
        "headers": {"Authorization": "Bearer ${MCP_TOKEN}"},
    }}})
    assert resolve_server(tmp_path, "docs").headers["Authorization"] == "Bearer file-secret"
    listed = mcp_tools.build_tools(tmp_path)[0].invoke({})
    assert "secret" not in listed and "Authorization" not in listed
    (tmp_path / ".env").unlink()
    monkeypatch.delenv("MCP_TOKEN")
    with pytest.raises(IntegrationError, match="Missing environment variable MCP_TOKEN"):
        resolve_server(tmp_path, "docs")


@pytest.mark.parametrize("config", [
    {"mcpServers": {"bad": {"transport": "wrong", "headers": {"Authorization": "secret"}}}},
    {"skills": "not-a-list"},
    {"mcpServers": {"bad": {"command": "python", "timeout": -1}}},
    {"mcpServers": {"bad": {"transport": "sse", "command": "python", "url": "https://example.com"}}},
])
def test_invalid_config_is_safe(tmp_path, config):
    write_config(tmp_path, config)
    with pytest.raises(IntegrationError) as error:
        load_integrations(tmp_path)
    assert "secret" not in str(error.value)


def test_external_skills_and_resources_are_available_to_agent(tmp_path):
    skill = tmp_path / ".quasnex/skills/api-debug"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: api-debug\n---\nCheck API logs. Read references.md.")
    (skill / "references.md").write_text("Run the focused API tests.")
    assert "api-debug" in list_skills(tmp_path)
    assert "Check API logs" in load_skill("api-debug", tmp_path)
    assert read_skill_resource("api-debug", "references.md", tmp_path) == "Run the focused API tests."
    assert read_skill_resource("api-debug", "../../../../.env", tmp_path).startswith("Error")
    outside = tmp_path / "outside.txt"
    outside.write_text("private")
    (skill / "escape.txt").symlink_to(outside)
    assert read_skill_resource("api-debug", "escape.txt", tmp_path).startswith("Error")
    tools = {tool.name: tool for tool in build_all_tools(tmp_path)}
    assert "api-debug" in tools["list_available_skills"].invoke({})
    assert "Check API logs" in tools["load_skill_instructions"].invoke({"name": "api-debug"})
    assert {"list_mcp_servers", "list_mcp_tools", "call_mcp_tool"} <= tools.keys()


def test_external_directory_and_duplicate_names(tmp_path):
    external = tmp_path / "shared-skills"
    external.mkdir()
    (external / "frontend.md").write_text("Build frontend components.")
    write_config(tmp_path, {"skills": [str(external)]})
    assert "frontend" in list_skills(tmp_path)
    (external / "build.md").write_text("Shadow a bundled skill")
    with pytest.raises(IntegrationError, match="Duplicate skill"):
        list_skills(tmp_path)


def test_denied_and_disabled_mcp_never_connect(tmp_path):
    write_config(tmp_path, {"mcpServers": {"local": {"command": "python"}}})
    try:
        set_confirmation_sink(lambda *_: False)
        with patch.object(mcp_tools, "_request") as request:
            assert "Declined" in mcp_tools.request(tmp_path, "local", "write", {})
            request.assert_not_called()
        write_config(tmp_path, {"mcpServers": {"local": {"command": "python", "enabled": False}}})
        assert "disabled" in mcp_tools.request(tmp_path, "local")
    finally:
        set_confirmation_sink(None)


def test_chat_custom_skill_dispatch(tmp_path):
    from ai_orchestrator.cli.commands.chat import ChatSession
    skill = tmp_path / ".quasnex/skills/api-debug"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("Inspect failing endpoints.")
    session = ChatSession.__new__(ChatSession)
    session.project_dir = None
    session.workspace_root = tmp_path
    session._send = Mock()
    assert session._handle_command("/skill api-debug fix the login error") is False
    message, role = session._send.call_args.args
    assert "Inspect failing endpoints" in message and "fix the login error" in message
    assert role == "coding"
