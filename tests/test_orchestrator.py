from pathlib import Path
import tempfile
import unittest

from ai_orchestrator.runner import Orchestrator
from ai_orchestrator.scaffold import init_project


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
            stage = orchestrator.config.stages[1]
            task_file = run_dir / "tasks" / f"{stage.name}.md"

            command = orchestrator.render_command(stage, task_file, run_dir)

            self.assertTrue(command.startswith("gemini --prompt-file "))
            self.assertIn(str(task_file), command)


if __name__ == "__main__":
    unittest.main()
