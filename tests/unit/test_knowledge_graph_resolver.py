from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ai_orchestrator.knowledge_graph.builder import build_graph
from ai_orchestrator.knowledge_graph.resolver import resolve


class KnowledgeGraphResolverTests(unittest.TestCase):
    def test_resolver_uses_local_content_terms_for_ui_change_requests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            components = workspace / "frontend" / "src" / "components"
            components.mkdir(parents=True)
            (components / "TasksBoard.jsx").write_text(
                "\n".join(
                    [
                        "export function TasksBoard() {",
                        '  return <input type="date" value={dueDate} onChange={setDueDate} />;',
                        "}",
                    ]
                ),
                encoding="utf-8",
            )
            (components / "Header.jsx").write_text(
                "export function Header() { return <h1>Home</h1>; }",
                encoding="utf-8",
            )

            graph = build_graph(workspace)
            results = resolve(
                "While creating tasks restrict past dates as due date in date picker",
                graph,
            )

            self.assertTrue(results)
            self.assertEqual(results[0]["file"], "frontend/src/components/TasksBoard.jsx")
            self.assertIn("terms", graph["files"]["frontend/src/components/TasksBoard.jsx"])


if __name__ == "__main__":
    unittest.main()
