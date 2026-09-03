from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from ai_orchestrator.cli.ui import APP_NAME, TAGLINE


class ForgeFlowBrandingTests(unittest.TestCase):
    def test_public_brand_name(self) -> None:
        self.assertEqual(APP_NAME, "ForgeFlow")
        self.assertTrue(TAGLINE)

    def test_primary_and_compatibility_commands_are_registered(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        config = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))
        scripts = config["project"]["scripts"]

        self.assertEqual(config["project"]["name"], "forgeflow")
        self.assertEqual(scripts["forgeflow"], "ai_orchestrator.cli:main")
        self.assertEqual(scripts["ai-orchestrator"], "ai_orchestrator.cli:main")


if __name__ == "__main__":
    unittest.main()
