from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ai_orchestrator.agent_tools import shell_tools
from ai_orchestrator.agent_tools.confirm import set_confirmation_sink
from ai_orchestrator.core.agent_graph import VerificationResult, _verify_after_edit


def _tools_by_name(workspace: Path) -> dict:
    return {tool.name: tool for tool in shell_tools.build_tools(workspace)}


class VerifyAfterEditTests(unittest.TestCase):
    def test_no_test_command_detected_is_not_attempted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = _verify_after_edit(_tools_by_name(workspace), workspace, on_tool_call=None)

            self.assertEqual(
                result, VerificationResult(attempted=False, ran=False, passed=None, command=None, output=None)
            )

    def test_declined_confirmation_is_attempted_but_not_ran(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
            set_confirmation_sink(lambda _action, _detail: False)

            result = _verify_after_edit(_tools_by_name(workspace), workspace, on_tool_call=None)

            self.assertTrue(result.attempted)
            self.assertFalse(result.ran)
            self.assertIsNone(result.passed)
            self.assertEqual(result.command, "python -m pytest -q")

    def test_failing_command_is_reported_as_not_passed(self) -> None:
        # pytest is not installed in this environment, so "python -m pytest -q"
        # deterministically exits non-zero — a real failure signal, not a mock.
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
            set_confirmation_sink(lambda _action, _detail: True)

            calls = []
            result = _verify_after_edit(
                _tools_by_name(workspace), workspace, on_tool_call=lambda name, args: calls.append((name, args))
            )

            self.assertTrue(result.attempted)
            self.assertTrue(result.ran)
            self.assertFalse(result.passed)
            self.assertIn("exit code:", result.output)
            self.assertEqual(calls, [("run_tests", {"command": "python -m pytest -q", "auto_verify": True})])


if __name__ == "__main__":
    unittest.main()
