from pathlib import Path
import tempfile
import unittest

from ai_orchestrator.core import context as ctx_store
from ai_orchestrator.config import load_config
from ai_orchestrator.scaffolding import init_project


class OrchestratorConfigTests(unittest.TestCase):
    """Tests for the plan-only parts of the pipeline that don't require live model
    providers (Orchestrator() now constructs a ModelRegistry, which needs a
    configured .env — covered separately in tests/unit/test_llm_registry.py)."""

    def test_init_creates_expected_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "app"
            init_project(project_dir, "sample-app")

            self.assertTrue((project_dir / "orchestrator.toml").exists())
            self.assertTrue((project_dir / ".env").exists())

            config = load_config(project_dir)
            self.assertEqual(config.name, "sample-app")
            self.assertIn("10_frontend_gemini", [s.name for s in config.stages])

    def test_agent_persona_and_provider_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "app"
            init_project(project_dir, "sample-app")
            config = load_config(project_dir)

            frontend = config.agents["gemini_frontend"]
            self.assertEqual(frontend.provider, "nvidia")
            self.assertIn("Frontend Engineer", frontend.role)

            engineering = config.agents["codex_engineering"]
            self.assertEqual(engineering.provider, "lightning")
            self.assertIn("Engineering Lead", engineering.role)

    def test_shared_context_appended_to_task_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "app"
            init_project(project_dir, "sample-app")
            ctx_store.set_user_preference(project_dir, "theme", "dark")

            context_block = ctx_store.inject_context_block(project_dir)
            self.assertIn("Shared Project Context", context_block)
            self.assertIn("theme", context_block)

    def test_context_records_stage_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "app"
            init_project(project_dir, "sample-app")
            ctx_store.record_stage_complete(project_dir, "00_intake_architecture", "codex_engineering", "lightning")

            data = ctx_store.load(project_dir)
            self.assertEqual(len(data["completed_stages"]), 1)
            self.assertEqual(data["completed_stages"][0]["stage"], "00_intake_architecture")
            self.assertEqual(data["completed_stages"][0]["model_used"], "lightning")

    def test_context_records_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "app"
            init_project(project_dir, "sample-app")
            ctx_store.record_stage_failure(
                project_dir, "10_frontend_gemini", "gemini_frontend", "nvidia", "credit exhausted"
            )

            data = ctx_store.load(project_dir)
            self.assertEqual(len(data["failures"]), 1)
            self.assertEqual(data["failures"][0]["reason"], "credit exhausted")


if __name__ == "__main__":
    unittest.main()
