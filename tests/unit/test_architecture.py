#!/usr/bin/env python3
"""Tests for the model-provider registry (replaces the old keyword-routing tests)."""

from pathlib import Path
import tempfile
import unittest

from ai_orchestrator.llm import ModelRegistry, UnknownModelError, UnknownProviderError


def _write_env(project_dir: Path) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "DEFAULT_PROVIDER=lightning",
                "LIGHTNING_BASE_URL=https://example-instance.cloudspaces.litng.ai/v1",
                "LIGHTNING_API_KEY=test-lightning-key",
                "LIGHTNING_MODELS=qwen2.5-coder:14b,qwen2.5-coder:7b",
                "NVIDIA_API_KEY=test-nvidia-key",
                "NVIDIA_MODELS=qwen/qwen3-next-80b-a3b-instruct,openai/gpt-oss-20b",
            ]
        ),
        encoding="utf-8",
    )


class ModelRegistryTests(unittest.TestCase):
    def test_defaults_to_configured_default_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_env(project_dir)

            registry = ModelRegistry(project_dir)
            provider, model = registry.current()

            self.assertEqual(provider, "lightning")
            self.assertEqual(model, "qwen2.5-coder:14b")

    def test_list_available_returns_all_providers_and_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_env(project_dir)

            registry = ModelRegistry(project_dir)
            available = registry.list_available()

            self.assertIn("lightning", available)
            self.assertIn("nvidia", available)
            self.assertIn("openai/gpt-oss-20b", available["nvidia"])

    def test_switch_persists_across_registry_instances(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_env(project_dir)

            registry = ModelRegistry(project_dir)
            registry.switch("nvidia", "openai/gpt-oss-20b")

            reloaded = ModelRegistry(project_dir)
            self.assertEqual(reloaded.current(), ("nvidia", "openai/gpt-oss-20b"))

    def test_switch_rejects_unknown_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_env(project_dir)

            registry = ModelRegistry(project_dir)
            with self.assertRaises(UnknownProviderError):
                registry.switch("does-not-exist")

    def test_switch_rejects_unknown_model_for_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_env(project_dir)

            registry = ModelRegistry(project_dir)
            with self.assertRaises(UnknownModelError):
                registry.switch("lightning", "not-a-real-model")

    def test_chat_model_builds_against_active_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_env(project_dir)

            registry = ModelRegistry(project_dir)
            registry.switch("nvidia", "openai/gpt-oss-20b")
            chat_model = registry.chat_model()

            self.assertEqual(chat_model.model_name, "openai/gpt-oss-20b")


if __name__ == "__main__":
    unittest.main()
