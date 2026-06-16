from pathlib import Path
import json
import tempfile
import unittest

from ai_orchestrator.core import Orchestrator
from ai_orchestrator.scaffolding import init_project
from ai_orchestrator.core import context as ctx_store


class OrchestratorTests(unittest.TestCase):
    def test_init_and_plan_generates_stage_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "app"
            init_project(project_dir, "sample-app")

            run_dir = Orchestrator(project_dir).plan()

            self.assertTrue((project_dir / "orchestrator.toml").exists())
            self.assertTrue((run_dir / "handoff.md").exists())
            task_file = run_dir / "tasks" / "10_frontend_gemini.md"
            self.assertTrue(task_file.exists())
            self.assertIn("sample-app", task_file.read_text(encoding="utf-8"))

    def test_command_render_uses_configured_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "app"
            init_project(project_dir, "sample-app")
            orchestrator = Orchestrator(project_dir)
            run_dir = orchestrator.plan()
            stage = orchestrator.config.stages[1]  # 10_frontend_gemini
            task_file = run_dir / "tasks" / f"{stage.name}.md"

            command = orchestrator.render_command(stage, task_file, run_dir)

            # Check that the command contains the expected parts (may have env vars prepended)
            self.assertIn("gemini --prompt-file ", command)
            self.assertIn(str(task_file), command)

    def test_fallback_group_loaded_for_frontend_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "app"
            init_project(project_dir, "sample-app")
            orchestrator = Orchestrator(project_dir)

            agent = orchestrator.config.agents["gemini_frontend"]
            self.assertIsNotNone(agent.fallback, "gemini_frontend must have a fallback group")
            self.assertIn("qwen_local", agent.fallback.models)

    def test_fallback_group_loaded_for_engineering_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "app"
            init_project(project_dir, "sample-app")
            orchestrator = Orchestrator(project_dir)

            agent = orchestrator.config.agents["codex_engineering"]
            self.assertIsNotNone(agent.fallback, "codex_engineering must have a fallback group")
            self.assertIn("qwen_local", agent.fallback.models)

    def test_shared_context_appended_to_task_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "app"
            init_project(project_dir, "sample-app")
            ctx_store.set_user_preference(project_dir, "theme", "dark")

            run_dir = Orchestrator(project_dir).plan()
            task_file = run_dir / "tasks" / "10_frontend_gemini.md"
            content = task_file.read_text(encoding="utf-8")

            self.assertIn("Shared Project Context", content)
            self.assertIn("theme", content)

    def test_context_records_stage_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "app"
            init_project(project_dir, "sample-app")
            ctx_store.record_stage_complete(project_dir, "00_intake_architecture", "codex_engineering", "codex")

            data = ctx_store.load(project_dir)
            self.assertEqual(len(data["completed_stages"]), 1)
            self.assertEqual(data["completed_stages"][0]["stage"], "00_intake_architecture")
            self.assertEqual(data["completed_stages"][0]["model_used"], "codex")

    def test_context_records_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "app"
            init_project(project_dir, "sample-app")
            ctx_store.record_stage_failure(
                project_dir, "10_frontend_gemini", "gemini_frontend", "gemini", "credit exhausted"
            )

            data = ctx_store.load(project_dir)
            self.assertEqual(len(data["failures"]), 1)
            self.assertEqual(data["failures"][0]["reason"], "credit exhausted")


if __name__ == "__main__":
    unittest.main()
