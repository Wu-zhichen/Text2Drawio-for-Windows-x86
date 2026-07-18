import unittest

from app.diagram.ir import DiagramIR
from app.diagram.validator import DiagramValidationError, validate_diagram
from tests.helpers import sample_diagram


class ValidatorTests(unittest.TestCase):
    def test_valid_diagram(self) -> None:
        self.assertEqual(validate_diagram(sample_diagram()), [])

    def test_rejects_unknown_endpoint(self) -> None:
        diagram = sample_diagram()
        diagram.edges[0].target = "missing"
        with self.assertRaises(DiagramValidationError) as raised:
            validate_diagram(diagram)
        self.assertIn("unknown target", str(raised.exception))

    def test_rejects_duplicate_ids(self) -> None:
        diagram = sample_diagram()
        diagram.nodes[1].id = "input"
        with self.assertRaises(DiagramValidationError) as raised:
            validate_diagram(diagram)
        self.assertIn("duplicate node id", str(raised.exception))

    def test_rejects_excessively_long_label(self) -> None:
        diagram = DiagramIR.from_dict(
            {
                "diagram_type": "flowchart",
                "title": "Example",
                "nodes": [{"id": "node", "label": "x" * 121, "type": "process"}],
                "edges": [],
            }
        )
        with self.assertRaises(DiagramValidationError):
            validate_diagram(diagram)


if __name__ == "__main__":
    unittest.main()

