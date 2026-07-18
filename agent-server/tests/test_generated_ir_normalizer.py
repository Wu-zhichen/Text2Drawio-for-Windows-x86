import unittest

from app.diagram.ir import DiagramIR
from app.diagram.normalizer import normalize_generated_ir
from app.diagram.validator import validate_diagram


class GeneratedIrNormalizerTests(unittest.TestCase):
    def test_drawio_reserved_id_is_rewritten_and_references_follow(self) -> None:
        normalized, _ = normalize_generated_ir(
            {
                "diagram_type": "pipeline",
                "title": "Fork merge",
                "nodes": [
                    {"id": "source", "label": "Source"},
                    {"id": "join", "label": "Merge"},
                ],
                "edges": [{"id": "edge", "source": "source", "target": "join"}],
            }
        )
        diagram = DiagramIR.from_dict(normalized)
        validate_diagram(diagram)
        self.assertEqual(diagram.nodes[1].id, "node_join")
        self.assertEqual(diagram.edges[0].target, "node_join")

    def test_dashboard_aliases_ids_and_edges_are_repaired(self) -> None:
        raw = {
            "version": "2",
            "diagram_type": "dashboard",
            "title": "运营大屏",
            "direction": "vertical",
            "nodes": [
                {"id": "总览 指标", "label": "核心指标", "type": "kpi"},
                {"id": "趋势图", "label": "月度趋势", "type": "line-chart"},
                {"id": "趋势图", "label": "渠道占比", "type": "donut_chart"},
            ],
            "edges": [
                {"id": "连接 1", "from": "总览 指标", "to": "趋势图", "kind": "dependency"},
                {"source": "不存在", "target": "趋势图"},
            ],
            "metadata": {},
        }
        normalized, warnings = normalize_generated_ir(raw)
        diagram = DiagramIR.from_dict(normalized)
        validate_diagram(diagram)
        self.assertEqual(diagram.diagram_type, "custom")
        self.assertEqual(diagram.direction, "top-to-bottom")
        self.assertEqual([node.type for node in diagram.nodes], ["data", "data", "data"])
        self.assertEqual(len({node.id for node in diagram.nodes}), 3)
        self.assertEqual(len(diagram.edges), 1)
        self.assertTrue(warnings)


if __name__ == "__main__":
    unittest.main()
