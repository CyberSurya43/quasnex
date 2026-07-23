from __future__ import annotations

import unittest

from ai_orchestrator.core.agent_graph import _parse_raw_tool_call


class RawToolCallParsingTests(unittest.TestCase):
    def test_parses_lightning_style_tool_call_json(self) -> None:
        parsed = _parse_raw_tool_call(
            """
            {
              "name": "read_file",
              "arguments": {
                "path": "frontend/src/components/TasksBoard.jsx"
              }
            }
            """
        )

        self.assertEqual(
            parsed,
            ("read_file", {"path": "frontend/src/components/TasksBoard.jsx"}),
        )

    def test_parses_fenced_tool_call_json(self) -> None:
        parsed = _parse_raw_tool_call(
            """```json
            {"name": "build_knowledge_graph", "arguments": {}}
            ```"""
        )

        self.assertEqual(parsed, ("build_knowledge_graph", {}))

    def test_ignores_regular_chat_text(self) -> None:
        self.assertIsNone(_parse_raw_tool_call("Hello! How can I assist you today?"))


if __name__ == "__main__":
    unittest.main()

