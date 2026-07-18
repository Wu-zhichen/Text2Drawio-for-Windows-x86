import unittest
from xml.etree import ElementTree as ET

from app.diagram.ir import DiagramIR
from app.layout.engine import LayoutEngine
from app.renderer.drawio import DrawioRenderer
from tests.helpers import sample_diagram


class LayoutRendererTests(unittest.TestCase):
    def test_layout_assigns_non_overlapping_columns(self) -> None:
        diagram = LayoutEngine().apply(sample_diagram())
        input_node, plan_node, result_node = diagram.nodes
        self.assertLess(input_node.x + input_node.width, plan_node.x)
        self.assertLess(plan_node.x + plan_node.width, result_node.x)

    def test_renderer_creates_native_vertices_and_edges(self) -> None:
        diagram = LayoutEngine().apply(sample_diagram())
        xml = DrawioRenderer().render(diagram)
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, "mxfile")
        cells = root.findall(".//mxCell")
        vertices = [cell for cell in cells if cell.get("vertex") == "1"]
        edges = [cell for cell in cells if cell.get("edge") == "1"]
        self.assertEqual(len(vertices), 4)  # title + three nodes
        self.assertEqual(len(edges), 3)
        self.assertTrue(all(cell.get("source") and cell.get("target") for cell in edges))
        self.assertTrue(all("orthogonalEdgeStyle" in cell.get("style", "") for cell in edges))

    def test_feedback_edge_has_external_waypoints(self) -> None:
        diagram = LayoutEngine().apply(sample_diagram())
        root = ET.fromstring(DrawioRenderer().render(diagram))
        feedback = root.find(".//mxCell[@id='feedback']")
        self.assertIsNotNone(feedback)
        self.assertEqual(len(feedback.findall(".//mxPoint")), 4)

    def test_top_to_bottom_hierarchy_is_centered_and_uses_fixed_ports(self) -> None:
        diagram = LayoutEngine().apply(self._hierarchy())
        by_id = {node.id: node for node in diagram.nodes}
        root_center = (by_id["root"].x or 0) + by_id["root"].width / 2
        child_centers = [(by_id[node_id].x or 0) + by_id[node_id].width / 2 for node_id in ("a", "b", "c")]
        self.assertAlmostEqual(root_center, sum(child_centers) / len(child_centers))
        self.assertGreaterEqual((by_id["a"].y or 0) - ((by_id["root"].y or 0) + by_id["root"].height), 90)

        xml_root = ET.fromstring(DrawioRenderer().render(diagram))
        local = xml_root.find(".//mxCell[@id='root_a']")
        self.assertIsNotNone(local)
        style = self._style_dict(local.get("style", ""))
        self.assertEqual(style["exitY"], "1")
        self.assertEqual(style["entryY"], "0")
        self.assertEqual(len(local.findall(".//mxPoint")), 2)

    def test_routes_do_not_cross_unrelated_nodes(self) -> None:
        diagram = LayoutEngine().apply(self._hierarchy())
        by_id = {node.id: node for node in diagram.nodes}
        xml_root = ET.fromstring(DrawioRenderer().render(diagram))
        max_node_right = max((node.x or 0) + node.width for node in diagram.nodes)

        long_edge = xml_root.find(".//mxCell[@id='root_c1']")
        self.assertIsNotNone(long_edge)
        long_points = [
            (float(point.get("x", "0")), float(point.get("y", "0")))
            for point in long_edge.findall(".//mxPoint")
        ]
        self.assertEqual(len(long_points), 4)
        self.assertTrue(any(x > max_node_right for x, _ in long_points))

        for edge in diagram.edges:
            cell = xml_root.find(f".//mxCell[@id='{edge.id}']")
            self.assertIsNotNone(cell)
            style = self._style_dict(cell.get("style", ""))
            source = by_id[edge.source]
            target = by_id[edge.target]
            polyline = [
                (
                    (source.x or 0) + source.width * float(style["exitX"]),
                    (source.y or 0) + source.height * float(style["exitY"]),
                )
            ]
            polyline.extend(
                (float(point.get("x", "0")), float(point.get("y", "0")))
                for point in cell.findall(".//mxPoint")
            )
            polyline.append(
                (
                    (target.x or 0) + target.width * float(style["entryX"]),
                    (target.y or 0) + target.height * float(style["entryY"]),
                )
            )
            for first, second in zip(polyline, polyline[1:]):
                for node in diagram.nodes:
                    if node.id not in {edge.source, edge.target}:
                        self.assertFalse(
                            self._segment_hits_node(first, second, node),
                            f"{edge.id} crosses {node.id}: {first} -> {second}",
                        )

    def test_fanout_uses_one_centered_trunk_and_shared_bus(self) -> None:
        diagram = LayoutEngine().apply(self._hierarchy())
        xml_root = ET.fromstring(DrawioRenderer().render(diagram))
        fanout = [xml_root.find(f".//mxCell[@id='root_{child}']") for child in ("a", "b", "c")]
        styles = [self._style_dict(cell.get("style", "")) for cell in fanout if cell is not None]
        self.assertEqual([style["exitX"] for style in styles], ["0.5", "0.5", "0.5"])
        first_points = [cell.findall(".//mxPoint")[0] for cell in fanout if cell is not None]
        self.assertEqual(len({point.get("x") for point in first_points}), 1)
        self.assertEqual(len({point.get("y") for point in first_points}), 1)

    def test_renderer_embeds_node_image_as_editable_child_cell(self) -> None:
        diagram = LayoutEngine().apply(sample_diagram())
        diagram.nodes[0].image_data = "data:image/webp;base64,AAAA"
        diagram.nodes[0].image_alt = "Input icon"
        xml_root = ET.fromstring(DrawioRenderer().render(diagram))
        image = xml_root.find(".//mxCell[@id='input__image']")
        self.assertIsNotNone(image)
        self.assertEqual(image.get("parent"), "input")
        self.assertEqual(image.get("vertex"), "1")
        self.assertIn("shape=image", image.get("style", ""))

    def test_long_multiline_text_grows_card_and_uses_title_body_typography(self) -> None:
        diagram = DiagramIR.from_dict(
            {
                "diagram_type": "custom",
                "title": "Typography",
                "direction": "top-to-bottom",
                "nodes": [
                    {
                        "id": "metrics",
                        "label": "月度业务规模与自动化水平\n1月：18万/87.2% 2月：19万/88.5%\n3月：20万/89.7% 4月：21万/90.8%\n5月：23万/91.6% 6月：27万/92.4%",
                        "type": "data",
                    }
                ],
                "edges": [],
            }
        )
        laid_out = LayoutEngine().apply(diagram)
        node = laid_out.nodes[0]
        self.assertGreater(node.width, 240)
        self.assertGreater(node.height, 100)
        xml_root = ET.fromstring(DrawioRenderer().render(laid_out))
        cell = xml_root.find(".//mxCell[@id='metrics']")
        self.assertIsNotNone(cell)
        self.assertIn("font-size:16px", cell.get("value", ""))
        self.assertIn("font-size:13px", cell.get("value", ""))

    def test_page_section_and_body_font_sizes_are_distinct(self) -> None:
        diagram = LayoutEngine().apply(self._hierarchy())
        xml_root = ET.fromstring(DrawioRenderer().render(diagram))
        title_style = self._style_dict(xml_root.find(".//mxCell[@id='diagram-title']").get("style", ""))
        root_style = self._style_dict(xml_root.find(".//mxCell[@id='root']").get("style", ""))
        leaf_style = self._style_dict(xml_root.find(".//mxCell[@id='a1']").get("style", ""))
        self.assertEqual(title_style["fontSize"], "28")
        self.assertEqual(root_style["fontSize"], "18")
        self.assertEqual(leaf_style["fontSize"], "16")

    def test_uneven_subtrees_still_use_symmetric_equal_center_fanout(self) -> None:
        diagram = LayoutEngine().apply(self._uneven_hierarchy())
        by_id = {node.id: node for node in diagram.nodes}
        centers = [
            (by_id[node_id].x or 0) + by_id[node_id].width / 2
            for node_id in ("experiment", "modulation", "demodulation")
        ]
        parent_center = (by_id["method"].x or 0) + by_id["method"].width / 2
        self.assertAlmostEqual(parent_center, (centers[0] + centers[-1]) / 2)
        self.assertAlmostEqual(centers[1] - centers[0], centers[2] - centers[1])
        self.assertTrue(diagram.metadata["layout"]["quality"]["valid"])
        self.assertGreaterEqual(diagram.metadata["layout"]["quality"]["checked_fanouts"], 1)
        xml_root = ET.fromstring(DrawioRenderer().render(diagram))
        fanout = [xml_root.find(f".//mxCell[@id='e{index}']") for index in (3, 4, 5)]
        first_points = [cell.findall(".//mxPoint")[0] for cell in fanout if cell is not None]
        self.assertEqual(len({point.get("x") for point in first_points}), 1)
        self.assertEqual(len({point.get("y") for point in first_points}), 1)

    def test_fork_join_uses_balanced_fanout_and_shared_convergence_bus(self) -> None:
        diagram = LayoutEngine().apply(self._fork_join())
        by_id = {node.id: node for node in diagram.nodes}
        branch_centers = [
            (by_id[node_id].x or 0) + by_id[node_id].width / 2
            for node_id in ("branch_a", "branch_b", "branch_c")
        ]
        fork_center = (by_id["fork"].x or 0) + by_id["fork"].width / 2
        join_center = (by_id["merge"].x or 0) + by_id["merge"].width / 2
        self.assertAlmostEqual(fork_center, (branch_centers[0] + branch_centers[-1]) / 2)
        self.assertAlmostEqual(join_center, fork_center)
        self.assertAlmostEqual(branch_centers[1] - branch_centers[0], branch_centers[2] - branch_centers[1])
        xml_root = ET.fromstring(DrawioRenderer().render(diagram))
        convergence = [
            xml_root.find(f".//mxCell[@id='{edge_id}']")
            for edge_id in ("a_join", "b_join", "c_join")
        ]
        styles = [self._style_dict(cell.get("style", "")) for cell in convergence if cell is not None]
        self.assertEqual({style["entryX"] for style in styles}, {"0.5"})
        last_points = [cell.findall(".//mxPoint")[-1] for cell in convergence if cell is not None]
        self.assertEqual(len({point.get("x") for point in last_points}), 1)
        self.assertEqual(len({point.get("y") for point in last_points}), 1)

    def test_disconnected_dashboard_sections_are_packed_compactly(self) -> None:
        nodes = [
            {"id": f"chain_{index}", "label": f"流程 {index}", "type": "process"}
            for index in range(7)
        ]
        nodes.extend(
            {"id": f"card_{index}", "label": f"指标 {index}", "type": "data"}
            for index in range(14)
        )
        edges = [
            {"id": f"edge_{index}", "source": f"chain_{index}", "target": f"chain_{index + 1}"}
            for index in range(6)
        ]
        diagram = LayoutEngine().apply(
            DiagramIR.from_dict(
                {
                    "diagram_type": "custom",
                    "title": "Compact dashboard",
                    "direction": "top-to-bottom",
                    "nodes": nodes,
                    "edges": edges,
                }
            )
        )
        width = max((node.x or 0) + node.width for node in diagram.nodes) - min(
            node.x or 0 for node in diagram.nodes
        )
        height = max((node.y or 0) + node.height for node in diagram.nodes) - min(
            node.y or 0 for node in diagram.nodes
        )
        card_rows = {node.y for node in diagram.nodes if node.id.startswith("card_")}
        self.assertLess(width, 1800)
        self.assertLess(height, 1600)
        self.assertGreater(len(card_rows), 2)
        self.assertEqual(diagram.metadata["layout"]["mode"], "compact-components")
        for index, first in enumerate(diagram.nodes):
            for second in diagram.nodes[index + 1 :]:
                self.assertFalse(self._nodes_overlap(first, second))

    @staticmethod
    def _style_dict(style: str) -> dict[str, str]:
        result = {}
        for part in style.split(";"):
            if "=" in part:
                key, value = part.split("=", 1)
                result[key] = value
        return result

    @staticmethod
    def _segment_hits_node(first: tuple[float, float], second: tuple[float, float], node) -> bool:
        left = node.x or 0
        top = node.y or 0
        right = left + node.width
        bottom = top + node.height
        (x1, y1), (x2, y2) = first, second
        if abs(x1 - x2) < 0.1:
            return left < x1 < right and max(min(y1, y2), top) < min(max(y1, y2), bottom)
        if abs(y1 - y2) < 0.1:
            return top < y1 < bottom and max(min(x1, x2), left) < min(max(x1, x2), right)
        return True

    @staticmethod
    def _nodes_overlap(first, second) -> bool:
        return not (
            (first.x or 0) + first.width <= (second.x or 0)
            or (second.x or 0) + second.width <= (first.x or 0)
            or (first.y or 0) + first.height <= (second.y or 0)
            or (second.y or 0) + second.height <= (first.y or 0)
        )

    @staticmethod
    def _hierarchy() -> DiagramIR:
        return DiagramIR.from_dict(
            {
                "diagram_type": "concept",
                "title": "Knowledge Outline",
                "direction": "top-to-bottom",
                "nodes": [
                    {"id": "root", "label": "Root", "type": "system"},
                    {"id": "a", "label": "A", "type": "process"},
                    {"id": "b", "label": "B", "type": "process"},
                    {"id": "c", "label": "C", "type": "process"},
                    {"id": "a1", "label": "A1", "type": "output"},
                    {"id": "b1", "label": "B1", "type": "output"},
                    {"id": "c1", "label": "C1", "type": "output"},
                ],
                "edges": [
                    {"id": "root_a", "source": "root", "target": "a"},
                    {"id": "root_b", "source": "root", "target": "b"},
                    {"id": "root_c", "source": "root", "target": "c"},
                    {"id": "a_a1", "source": "a", "target": "a1"},
                    {"id": "b_b1", "source": "b", "target": "b1"},
                    {"id": "c_c1", "source": "c", "target": "c1"},
                    {"id": "root_c1", "source": "root", "target": "c1", "kind": "association"},
                ],
            }
        )

    @staticmethod
    def _uneven_hierarchy() -> DiagramIR:
        return DiagramIR.from_dict(
            {
                "diagram_type": "concept",
                "title": "Research summary",
                "direction": "top-to-bottom",
                "nodes": [
                    {"id": "background", "label": "研究背景与问题", "type": "input"},
                    {"id": "problem", "label": "核心问题", "type": "process"},
                    {"id": "method", "label": "研究方法", "type": "system"},
                    {
                        "id": "experiment",
                        "label": "实验设计\n数据集：Cityscapes, Pascal Context, ADE20K\n基线：低通池化, DeformConv, SOTA\n指标：mIoU, FLOPs, Params",
                        "type": "data",
                    },
                    {"id": "modulation", "label": "调制(Modulation)\n自适应重采样(ARS)"},
                    {"id": "demodulation", "label": "解调(Demodulation)\n多尺度自适应上采样(MSAU)"},
                    {"id": "conclusion", "label": "结论\n有效缓解混叠并提升精度", "type": "output"},
                    {"id": "results", "label": "主要结果\nADE20K: +1.5 mIoU", "type": "output"},
                ],
                "edges": [
                    {"id": "e1", "source": "background", "target": "problem"},
                    {"id": "e2", "source": "problem", "target": "method"},
                    {"id": "e3", "source": "method", "target": "experiment"},
                    {"id": "e4", "source": "method", "target": "modulation"},
                    {"id": "e5", "source": "method", "target": "demodulation"},
                    {"id": "e6", "source": "experiment", "target": "conclusion"},
                    {"id": "e7", "source": "conclusion", "target": "results"},
                ],
            }
        )

    @staticmethod
    def _fork_join() -> DiagramIR:
        return DiagramIR.from_dict(
            {
                "diagram_type": "pipeline",
                "title": "Fork join",
                "direction": "top-to-bottom",
                "nodes": [
                    {"id": "fork", "label": "研究方法", "type": "system"},
                    {"id": "branch_a", "label": "调制", "type": "process"},
                    {"id": "branch_b", "label": "解调与多尺度自适应上采样", "type": "process"},
                    {"id": "branch_c", "label": "频率约束", "type": "process"},
                    {"id": "merge", "label": "统一实验设计", "type": "data"},
                    {"id": "result", "label": "结果与结论", "type": "output"},
                ],
                "edges": [
                    {"id": "fork_a", "source": "fork", "target": "branch_a"},
                    {"id": "fork_b", "source": "fork", "target": "branch_b"},
                    {"id": "fork_c", "source": "fork", "target": "branch_c"},
                    {"id": "a_join", "source": "branch_a", "target": "merge"},
                    {"id": "b_join", "source": "branch_b", "target": "merge"},
                    {"id": "c_join", "source": "branch_c", "target": "merge"},
                    {"id": "join_result", "source": "merge", "target": "result"},
                ],
            }
        )


if __name__ == "__main__":
    unittest.main()
