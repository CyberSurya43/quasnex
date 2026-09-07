from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from ai_orchestrator.cli.ui import APP_NAME, BRAND_ICON, TAGLINE, brand_lockup, metadata_chip


class QuasnexBrandingTests(unittest.TestCase):
    def test_public_brand_name(self) -> None:
        self.assertEqual(APP_NAME, "Quasnex")
        self.assertEqual(BRAND_ICON, "[Q]")
        self.assertEqual(TAGLINE, "Multi-Model AI Coding Orchestrator")
        self.assertIn("Quasnex — Multi-Model AI Coding Orchestrator", brand_lockup().plain)

    def test_metadata_chip_contains_label_and_value(self) -> None:
        chip = metadata_chip("model", "openrouter/auto")

        self.assertIn("MODEL", chip.plain)
        self.assertIn("openrouter/auto", chip.plain)

    def test_primary_and_compatibility_commands_are_registered(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        config = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))
        scripts = config["project"]["scripts"]

        self.assertEqual(config["project"]["name"], "quasnex")
        self.assertEqual(scripts["quasnex"], "ai_orchestrator.cli:main")
        self.assertEqual(scripts["cosnex"], "ai_orchestrator.cli:main")
        self.assertEqual(scripts["forgeflow"], "ai_orchestrator.cli:main")
        self.assertEqual(scripts["ai-orchestrator"], "ai_orchestrator.cli:main")


if __name__ == "__main__":
    unittest.main()
