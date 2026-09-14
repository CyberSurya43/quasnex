from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock

from ai_orchestrator import knowledge_graph as kg
from ai_orchestrator.config import ModelRoute
from ai_orchestrator.cli.commands import chat
from ai_orchestrator.llm import RoutingDecision


class _DummyRegistry:
    switched_roles: list[str] = []
    switched_models: list[tuple[str, str]] = []
    reload_count = 0

    def __init__(self, project_dir: Path | None = None):
        self.project_dir = project_dir
        self.active = ("dummy", "model")

    def current(self) -> tuple[str, str]:
        return self.active

    def switch_role(self, role: str) -> tuple[str, str]:
        self.switched_roles.append(role)
        self.active = ("dummy", "model")
        return self.active

    def role_candidates(self, role: str) -> tuple[ModelRoute, ...]:
        return (ModelRoute("dummy", "model"),)

    def switch(self, provider_name: str, model_name: str | None = None) -> tuple[str, str]:
        self.active = (provider_name, model_name or "model")
        self.switched_models.append(self.active)
        return self.active

    def switch_thinking_model(self, provider_name: str, model_name: str) -> tuple[str, str]:
        return self.switch(provider_name, model_name)

    def reset_thinking_model(self) -> tuple[str, str]:
        return self.switch_role("planner")

    def reload_env(self) -> dict[str, tuple[str, ...]]:
        type(self).reload_count += 1
        return self.list_available()

    def planner_model(self) -> ModelRoute:
        return ModelRoute("dummy", "model")

    def list_visible_models(self) -> dict[str, tuple[str, ...]]:
        return {"dummy": ("model",)}

    def list_available(self) -> dict[str, tuple[str, ...]]:
        return {
            "dummy": ("model",),
            "openrouter": ("openrouter/auto", "provider/coding-model"),
        }


class _DummyAgent:
    sent_messages: list[str] = []

    def __init__(self, *args, **kwargs):
        self.last_verification = None

    def rebuild(self) -> None:
        pass

    def send(self, message: str, *args, **kwargs) -> str:
        self.sent_messages.append(message)
        return f"response {len(self.sent_messages)}"


class ChatKnowledgeGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        _DummyRegistry.switched_roles = []
        _DummyRegistry.switched_models = []
        _DummyRegistry.reload_count = 0
        _DummyAgent.sent_messages = []

    def test_plain_chat_kg_rebuild_is_available_to_kg_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "app.py").write_text("import helpers\n\ndef main():\n    pass\n", encoding="utf-8")
            (workspace / "helpers.py").write_text("def help_me():\n    pass\n", encoding="utf-8")

            with patch.object(chat, "ModelRegistry", _DummyRegistry), patch.object(
                chat, "CodingAgent", _DummyAgent
            ), patch("ai_orchestrator.cli.commands.chat.Path.cwd", return_value=workspace):
                session = chat.ChatSession()

                should_exit = session._handle_command("/kg rebuild")
                status_should_exit = session._handle_command("/kg")

            self.assertFalse(should_exit)
            self.assertFalse(status_should_exit)
            graph = kg.load_graph(workspace)
            self.assertIsNotNone(graph)
            self.assertEqual(len(graph["files"]), 2)

    def test_plan_command_runs_full_capability_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with patch.object(chat, "ModelRegistry", _DummyRegistry), patch.object(
                chat, "CodingAgent", _DummyAgent
            ), patch("ai_orchestrator.cli.commands.chat.Path.cwd", return_value=workspace):
                session = chat.ChatSession()
                should_exit = session._handle_command("/plan add auth")

            self.assertFalse(should_exit)
            self.assertEqual(
                _DummyRegistry.switched_roles,
                ["planner", "planner", "coding", "testing"],
            )
            self.assertEqual(len(_DummyAgent.sent_messages), 3)

    def test_plain_create_request_runs_full_capability_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with patch.object(chat, "ModelRegistry", _DummyRegistry), patch.object(
                chat, "CodingAgent", _DummyAgent
            ), patch("ai_orchestrator.cli.commands.chat.Path.cwd", return_value=workspace):
                session = chat.ChatSession()

                if session._should_run_workflow("create a good looking loader for all the api fetch"):
                    session._run_plan_workflow("create a good looking loader for all the api fetch")

            self.assertEqual(
                _DummyRegistry.switched_roles,
                ["planner", "planner", "coding", "testing"],
            )
            self.assertEqual(len(_DummyAgent.sent_messages), 3)
            self.assertTrue(
                all("Before reading files, folders, or code" in msg for msg in _DummyAgent.sent_messages)
            )

    def test_plain_question_does_not_run_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with patch.object(chat, "ModelRegistry", _DummyRegistry), patch.object(
                chat, "CodingAgent", _DummyAgent
            ), patch("ai_orchestrator.cli.commands.chat.Path.cwd", return_value=workspace):
                session = chat.ChatSession()

            self.assertFalse(session._should_run_workflow("how does api fetching work?"))

    def test_model_command_lists_only_the_thinking_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with patch.object(chat, "ModelRegistry", _DummyRegistry), patch.object(
                chat, "CodingAgent", _DummyAgent
            ), patch("ai_orchestrator.cli.commands.chat.Path.cwd", return_value=workspace), patch.object(
                chat.console, "input", return_value="1"
            ):
                session = chat.ChatSession()
                session.registry.list_available = Mock(
                    side_effect=AssertionError("worker inventory must stay internal")
                )
                should_exit = session._handle_command("/model")

            self.assertFalse(should_exit)
            self.assertEqual(session.registry.current(), ("dummy", "model"))

    def test_providers_command_lists_providers_without_worker_model_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with patch.object(chat, "ModelRegistry", _DummyRegistry), patch.object(
                chat, "CodingAgent", _DummyAgent
            ), patch("ai_orchestrator.cli.commands.chat.Path.cwd", return_value=workspace):
                session = chat.ChatSession()
                with chat.console.capture() as capture:
                    should_exit = session._handle_command("/providers")

            output = capture.get()
            self.assertFalse(should_exit)
            self.assertIn("dummy", output)
            self.assertIn("openrouter", output)
            self.assertNotIn("provider/coding-model", output)

    def test_model_reload_refreshes_env_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with patch.object(chat, "ModelRegistry", _DummyRegistry), patch.object(
                chat, "CodingAgent", _DummyAgent
            ), patch("ai_orchestrator.cli.commands.chat.Path.cwd", return_value=workspace):
                session = chat.ChatSession()
                should_exit = session._handle_command("/model reload")

            self.assertFalse(should_exit)
            self.assertEqual(_DummyRegistry.reload_count, 1)

    def test_plain_chat_preserves_interactively_selected_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with patch.object(chat, "ModelRegistry", _DummyRegistry), patch.object(
                chat, "CodingAgent", _DummyAgent
            ), patch("ai_orchestrator.cli.commands.chat.Path.cwd", return_value=workspace):
                session = chat.ChatSession()
                session.registry.switch("openrouter", "openrouter/auto")
                session._send("hello", preserve_active=True)

            self.assertEqual(session.registry.current(), ("openrouter", "openrouter/auto"))

    def test_automatic_routing_uses_planner_selected_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with patch.object(chat, "ModelRegistry", _DummyRegistry), patch.object(
                chat, "CodingAgent", _DummyAgent
            ), patch("ai_orchestrator.cli.commands.chat.Path.cwd", return_value=workspace):
                session = chat.ChatSession()
                session.router.route = Mock(
                    return_value=RoutingDecision(
                        role="documentation",
                        route=ModelRoute("openrouter", "openrouter/auto"),
                        domain="documentation",
                        complexity="low",
                        workload="light",
                        execution_mode="direct",
                        reason="Best fit for a concise explanation.",
                    )
                )
                session._dispatch_query("Explain the public API")

            session.router.route.assert_called_once_with("Explain the public API")
            self.assertEqual(session.registry.current(), ("openrouter", "openrouter/auto"))
            self.assertEqual(_DummyAgent.sent_messages, ["Explain the public API"])

    def test_worker_model_cannot_be_selected_with_model_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with patch.object(chat, "ModelRegistry", _DummyRegistry), patch.object(
                chat, "CodingAgent", _DummyAgent
            ), patch("ai_orchestrator.cli.commands.chat.Path.cwd", return_value=workspace):
                session = chat.ChatSession()
                should_exit = session._handle_command("/model openrouter openrouter/auto")

            self.assertFalse(should_exit)
            self.assertEqual(session.registry.current(), ("dummy", "model"))

    def test_workflow_execution_uses_planner_selected_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with patch.object(chat, "ModelRegistry", _DummyRegistry), patch.object(
                chat, "CodingAgent", _DummyAgent
            ), patch("ai_orchestrator.cli.commands.chat.Path.cwd", return_value=workspace):
                session = chat.ChatSession()
                session.router.route = Mock(
                    return_value=RoutingDecision(
                        role="debugging",
                        route=ModelRoute("openrouter", "provider/coding-model"),
                        domain="backend",
                        complexity="high",
                        workload="heavy",
                        execution_mode="workflow",
                        reason="Specialist model fits the failure.",
                    )
                )
                session._dispatch_query("Fix the intermittent backend failure")

            self.assertEqual(len(_DummyAgent.sent_messages), 3)
            self.assertIn(
                ("openrouter", "provider/coding-model"),
                _DummyRegistry.switched_models,
            )

    def test_permission_hard_stop_is_not_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with patch.object(chat, "ModelRegistry", _DummyRegistry), patch.object(
                chat, "CodingAgent", _DummyAgent
            ), patch("ai_orchestrator.cli.commands.chat.Path.cwd", return_value=workspace):
                session = chat.ChatSession()

            self.assertTrue(
                session._is_non_retryable_error(
                    RuntimeError("HARD STOP: permission required. User approval is required.")
                )
            )
            self.assertTrue(
                session._is_non_retryable_error(
                    RuntimeError("Stopped tool loop: edit_file was called too many times")
                )
            )
            self.assertFalse(session._is_non_retryable_error(RuntimeError("provider timed out")))


if __name__ == "__main__":
    unittest.main()
