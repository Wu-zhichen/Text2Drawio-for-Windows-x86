import unittest

from app.diagram.patcher import PatchError, apply_patch
from app.layout.engine import LayoutEngine
from tests.helpers import sample_diagram


class PatcherTests(unittest.TestCase):
    def test_update_preserves_existing_positions(self) -> None:
        laid_out = LayoutEngine().apply(sample_diagram())
        original_x = laid_out.nodes[1].x
        patched = apply_patch(
            laid_out,
            [{"op": "update_node", "id": "plan", "changes": {"label": "Revised Plan"}}],
        )
        relaid = LayoutEngine().apply(patched, preserve_positions=True)
        self.assertEqual(relaid.nodes[1].x, original_x)
        self.assertEqual(relaid.nodes[1].label, "Revised Plan")

    def test_remove_node_also_removes_connected_edges(self) -> None:
        patched = apply_patch(sample_diagram(), [{"op": "remove_node", "id": "plan"}])
        self.assertEqual([node.id for node in patched.nodes], ["input", "result"])
        self.assertEqual(patched.edges, [])

    def test_rejects_id_change(self) -> None:
        with self.assertRaises(PatchError):
            apply_patch(
                sample_diagram(),
                [{"op": "update_node", "id": "plan", "changes": {"id": "new_id"}}],
            )


if __name__ == "__main__":
    unittest.main()

