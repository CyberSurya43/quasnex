from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ai_orchestrator import knowledge_graph as kg
from ai_orchestrator.config import ModelRoute
from ai_orchestrator.cli.commands import chat


class _DummyRegistry:
    switched_roles: list[str] = []

    def __init__(self, project_dir: Path | None = None):
        self.project_dir = project_dir

    def current(self) -> tuple[str, str]:
        return ("dummy", "model")

    def switch_role(self, role: str) -> tuple[str, str]:
        self.switched_roles.append(role)
        return ("dummy", "model")

    def role_candidates(self, role: str) -> tuple[ModelRoute, ...]:
        return (ModelRoute("dummy", "model"),)

    def switch(self, provider_name: str, model_name: str | None = None) -> tuple[str, str]:
        return (provider_name, model_name or "model")

    def planner_model(self) -> ModelRoute:
        return ModelRoute("dummy", "model")

    def list_visible_models(self) -> dict[str, tuple[str, ...]]:
        return {"dummy": ("model",)}


class _DummyAgent:
    sent_messages: list[str] = []

    def __init__(self, *args, **kwargs):
        pass

    def rebuild(self) -> None:
        pass

    def send(self, message: str, *args, **kwargs) -> str:
        self.sent_messages.append(message)
        return f"response {len(self.sent_messages)}"


class ChatKnowledgeGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        _DummyRegistry.switched_roles = []
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
