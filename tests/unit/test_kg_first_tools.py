from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ai_orchestrator.agent_tools.tool_context import ToolContext
from ai_orchestrator.agent_tools import fs_tools, kg_tools
from ai_orchestrator.agent_tools.confirm import set_confirmation_sink


def _tool_by_name(tools, name: str):
    for tool in tools:
        if tool.name == name:
            return tool
    raise AssertionError(f"Missing tool {name!r}")


class KgFirstToolTests(unittest.TestCase):
    def test_filesystem_tools_warn_until_kg_resolver_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "app.py").write_text("def loader():\n    return True\n", encoding="utf-8")
            context = ToolContext()
            fs = fs_tools.build_tools(workspace, context)
            kg = kg_tools.build_tools(workspace, workspace, context)

            list_dir = _tool_by_name(fs, "list_dir")
            resolve_issue = _tool_by_name(kg, "resolve_issue")

            before = list_dir.invoke({"path": "."})
            self.assertIn("KG-FIRST WARNING", before)

            resolve_issue.invoke({"description": "create loader for api fetch"})
            after = list_dir.invoke({"path": "."})
            self.assertNotIn("KG-FIRST WARNING", after)
            self.assertIn("app.py", after)

    def test_edit_file_hard_stops_after_repeated_bad_old_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "app.py").write_text("def loader():\n    return True\n", encoding="utf-8")
            context = ToolContext(kg_resolved=True)
            set_confirmation_sink(lambda _action, _detail: False)
            fs = fs_tools.build_tools(workspace, context)
            edit_file = _tool_by_name(fs, "edit_file")

            first = edit_file.invoke(
                {"path": "app.py", "old_text": "missing text", "new_text": "replacement"}
            )
            read_file = _tool_by_name(fs, "read_file")
            read_file.invoke({"path": "app.py", "line_start": 1, "line_end": 2})
            second = edit_file.invoke(
                {"path": "app.py", "old_text": "still missing", "new_text": "replacement"}
            )

            self.assertIn("Call read_file", first)
            self.assertIn("HARD STOP", second)
            self.assertIn("Do not call edit_file again", second)

    def test_edit_file_caps_total_attempts_even_when_old_text_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "app.py").write_text("value = 1\n", encoding="utf-8")
            context = ToolContext(kg_resolved=True)
            set_confirmation_sink(lambda _action, _detail: False)
            fs = fs_tools.build_tools(workspace, context)
            edit_file = _tool_by_name(fs, "edit_file")

            # Confirmation is stubbed to deny, so matching edits still count as attempts.
            for _ in range(3):
                edit_file.invoke({"path": "app.py", "old_text": "value = 1", "new_text": "value = 2"})
            fourth = edit_file.invoke(
                {"path": "app.py", "old_text": "value = 1", "new_text": "value = 2"}
            )

            self.assertIn("HARD STOP", fourth)
            self.assertIn("edit_file was called 4 times", fourth)

    def test_write_and_edit_permission_denial_are_hard_stops(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "app.py").write_text("value = 1\n", encoding="utf-8")
            context = ToolContext(kg_resolved=True)
            set_confirmation_sink(lambda _action, _detail: False)
            fs = fs_tools.build_tools(workspace, context)
            write_file = _tool_by_name(fs, "write_file")
            edit_file = _tool_by_name(fs, "edit_file")

            write_result = write_file.invoke({"path": "created.py", "content": "x = 1\n"})
            edit_result = edit_file.invoke(
                {"path": "app.py", "old_text": "value = 1", "new_text": "value = 2"}
            )

            self.assertIn("HARD STOP: permission required", write_result)
            self.assertIn("Do not retry", write_result)
            self.assertIn("HARD STOP: permission required", edit_result)
            self.assertIn("Do not retry", edit_result)


if __name__ == "__main__":
    unittest.main()
