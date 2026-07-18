import unittest

from app.diagram.ir import DiagramIR
from app.diagram.validator import validate_diagram
from app.layout.engine import LayoutEngine
from app.renderer.drawio import DrawioRenderer


class DiagramIrNormalizationTests(unittest.TestCase):
    def test_missing_edge_id_and_string_styles_are_normalized(self) -> None:
        diagram = DiagramIR.from_dict(
            {
                "version": "1.0",
                "diagram_type": "flowchart",
                "title": "Bubble Sort",
                "direction": "left-to-right",
                "nodes": [
                    {
                        "id": "input",
                        "label": "Input",
                        "type": "input",
                        "style": "rounded=0;fillColor=#ffffff;",
                    },
                    {
                        "id": "sort",
                        "label": "Sort",
                        "type": "process",
                        "style": {"strokeWidth": 3},
                    },
                ],
                "edges": [
                    {
                        "source": "input",
                        "target": "sort",
                        "kind": "main",
                        "style": "dashed=1;strokeColor=#123456;",
                    }
                ],
            }
        )

        self.assertEqual(diagram.edges[0].id, "edge_1")
        self.assertEqual(diagram.nodes[0].style["fillColor"], "#ffffff")
        self.assertEqual(diagram.nodes[1].style["strokeWidth"], "3")
        self.assertEqual(diagram.edges[0].style["dashed"], "1")
        validate_diagram(diagram)

        laid_out = LayoutEngine().apply(diagram)
        xml = DrawioRenderer().render(laid_out)
        self.assertIn('id="edge_1"', xml)
        self.assertIn("fillColor=#ffffff", xml)

    def test_missing_node_ids_do_not_collide_with_supplied_ids(self) -> None:
        diagram = DiagramIR.from_dict(
            {
                "diagram_type": "flowchart",
                "title": "Generated IDs",
                "nodes": [
                    {"label": "Generated", "type": "input"},
                    {"id": "node_1", "label": "Reserved", "type": "output"},
                ],
                "edges": [
                    {"source": "node_2", "target": "node_1"},
                ],
            }
        )

        self.assertEqual([node.id for node in diagram.nodes], ["node_2", "node_1"])
        self.assertEqual(diagram.edges[0].id, "edge_1")
        validate_diagram(diagram)


if __name__ == "__main__":
    unittest.main()
