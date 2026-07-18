from __future__ import annotations

import math
from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import dataclass
from typing import DefaultDict, Dict, List, Set

from app.diagram.ir import DiagramIR, Edge, Node
from app.layout.quality import LayoutQualityGate
from app.layout.text import TextSizer


@dataclass
class _ComponentBox:
    node_ids: List[str]
    nodes: List[Node]
    edges: List[Edge]
    width: float
    height: float
    min_x: float
    min_y: float


@dataclass(frozen=True)
class _PlacedBox:
    x: float
    y: float
    width: float
    height: float


class LayoutEngine:
    """Deterministic layered layout prepared for obstacle-free routing lanes."""

    def __init__(
        self,
        margin_x: float = 70,
        margin_y: float = 100,
        layer_gap: float = 96,
        row_gap: float = 44,
        component_gap: float = 56,
    ) -> None:
        self.margin_x = margin_x
        self.margin_y = margin_y
        self.layer_gap = layer_gap
        self.row_gap = row_gap
        self.component_gap = component_gap
        self.text_sizer = TextSizer()
        self.quality_gate = LayoutQualityGate()

    def apply(self, source: DiagramIR, preserve_positions: bool = True) -> DiagramIR:
        diagram = deepcopy(source)
        levels = self._levels(diagram)
        self.text_sizer.apply(diagram, levels)
        by_level = self._ordered_levels(diagram, levels)

        node_by_id = {node.id: node for node in diagram.nodes}
        layout_mode = "layered"
        components = self._main_components(diagram)
        has_explicit_positions = any(
            node.x is not None and node.y is not None for node in diagram.nodes
        )
        component_bounds: List[Dict[str, object]] = []
        if len(components) > 1 and (not preserve_positions or not has_explicit_positions):
            component_bounds = self._apply_compact_components(diagram, components)
            layout_mode = "compact-components"
        elif diagram.direction == "left-to-right":
            column_heights = {
                level: sum(node_by_id[node_id].height for node_id in node_ids)
                + self.row_gap * max(0, len(node_ids) - 1)
                for level, node_ids in by_level.items()
            }
            layout_height = max(column_heights.values(), default=0)
            cursor_x = self.margin_x
            for level in sorted(by_level):
                column = [node_by_id[node_id] for node_id in by_level[level]]
                column_width = max(node.width for node in column)
                cursor_y = self.margin_y + (layout_height - column_heights[level]) / 2
                for node in column:
                    if not preserve_positions or node.x is None or node.y is None:
                        node.x = cursor_x + (column_width - node.width) / 2
                        node.y = cursor_y
                    cursor_y += node.height + self.row_gap
                cursor_x += column_width + self.layer_gap
        else:
            if self._apply_top_down_tree(diagram, levels, by_level, preserve_positions):
                layout_mode = "hierarchical-tree"
            else:
                row_widths = {
                    level: self._balanced_child_span(
                        [node_by_id[node_id].width for node_id in node_ids]
                    )[0]
                    for level, node_ids in by_level.items()
                }
                layout_width = max(row_widths.values(), default=0)
                cursor_y = self.margin_y
                for level in sorted(by_level):
                    row = [node_by_id[node_id] for node_id in by_level[level]]
                    row_height = max(node.height for node in row)
                    row_left = self.margin_x + (layout_width - row_widths[level]) / 2
                    _, center_step = self._balanced_child_span([node.width for node in row])
                    group_midpoint = center_step * (len(row) - 1) / 2
                    first_center = row_left + row_widths[level] / 2 - group_midpoint
                    for index, node in enumerate(row):
                        if not preserve_positions or node.x is None or node.y is None:
                            node.x = first_center + index * center_step - node.width / 2
                            node.y = cursor_y + (row_height - node.height) / 2
                    cursor_y += row_height + self.layer_gap

        quality_report = self.quality_gate.enforce(diagram, levels)
        diagram.metadata = dict(diagram.metadata)
        diagram.metadata["layout"] = {
            "engine": "deterministic-layered-v5",
            "mode": layout_mode,
            "feedback_lane": "outside-main-flow",
            "levels": levels,
            "order": {str(level): node_ids for level, node_ids in sorted(by_level.items())},
            "layer_gap": self.layer_gap,
            "sibling_gap": self.row_gap,
            "component_gap": self.component_gap,
            "component_count": len(components),
            "component_bounds": component_bounds,
            "quality": quality_report.to_dict(),
        }
        return diagram

    def _apply_compact_components(
        self, diagram: DiagramIR, components: List[List[str]]
    ) -> List[Dict[str, object]]:
        """Layout primary components independently, then pack them into a compact rectangle."""
        node_by_id = {node.id: node for node in diagram.nodes}
        original_index = {node.id: index for index, node in enumerate(diagram.nodes)}
        boxes: List[_ComponentBox] = []
        for node_ids in components:
            node_set = set(node_ids)
            component_nodes = [deepcopy(node_by_id[node_id]) for node_id in node_ids]
            component_edges = [
                deepcopy(edge)
                for edge in diagram.edges
                if edge.source in node_set and edge.target in node_set
            ]
            subdiagram = DiagramIR(
                diagram_type=diagram.diagram_type,
                title=diagram.title,
                description=diagram.description,
                direction=diagram.direction,
                nodes=component_nodes,
                edges=component_edges,
                metadata={},
            )
            sublayout = LayoutEngine(
                margin_x=0,
                margin_y=0,
                layer_gap=self.layer_gap,
                row_gap=self.row_gap,
                component_gap=self.component_gap,
            ).apply(subdiagram, preserve_positions=False)
            min_x = min((node.x or 0) for node in sublayout.nodes)
            min_y = min((node.y or 0) for node in sublayout.nodes)
            max_x = max((node.x or 0) + node.width for node in sublayout.nodes)
            max_y = max((node.y or 0) + node.height for node in sublayout.nodes)
            boxes.append(
                _ComponentBox(
                    node_ids=node_ids,
                    nodes=sublayout.nodes,
                    edges=sublayout.edges,
                    width=max_x - min_x,
                    height=max_y - min_y,
                    min_x=min_x,
                    min_y=min_y,
                )
            )

        boxes.sort(
            key=lambda box: (
                -(box.width * box.height),
                min(original_index[node_id] for node_id in box.node_ids),
            )
        )
        padded_area = sum(
            (box.width + self.component_gap) * (box.height + self.component_gap)
            for box in boxes
        )
        widest = max((box.width for box in boxes), default=0)
        target_width = max(widest, math.sqrt(padded_area * 1.35))

        placed: List[_PlacedBox] = []
        bounds: List[Dict[str, object]] = []
        for box in boxes:
            x, y = self._find_compact_position(
                box.width, box.height, target_width, placed
            )
            placement = _PlacedBox(x, y, box.width, box.height)
            placed.append(placement)
            positioned_nodes = {node.id: node for node in box.nodes}
            for node_id in box.node_ids:
                source_node = positioned_nodes[node_id]
                target_node = node_by_id[node_id]
                target_node.x = self.margin_x + x + (source_node.x or 0) - box.min_x
                target_node.y = self.margin_y + y + (source_node.y or 0) - box.min_y
            bounds.append(
                {
                    "nodes": box.node_ids,
                    "x": self.margin_x + x,
                    "y": self.margin_y + y,
                    "width": box.width,
                    "height": box.height,
                }
            )
        return bounds

    def _find_compact_position(
        self,
        width: float,
        height: float,
        target_width: float,
        placed: List[_PlacedBox],
    ) -> tuple[float, float]:
        if not placed:
            return 0, 0
        candidate_x = {0.0}
        for box in placed:
            candidate_x.add(box.x)
            candidate_x.add(box.x + box.width + self.component_gap)
        current_height = max(box.y + box.height for box in placed)
        choices: List[tuple[float, float, float]] = []
        for x in sorted(candidate_x):
            if x + width > target_width + 0.1:
                continue
            y = 0.0
            while True:
                collisions = [
                    box
                    for box in placed
                    if x < box.x + box.width + self.component_gap
                    and x + width + self.component_gap > box.x
                    and y < box.y + box.height + self.component_gap
                    and y + height + self.component_gap > box.y
                ]
                if not collisions:
                    break
                y = max(box.y + box.height + self.component_gap for box in collisions)
            choices.append((max(current_height, y + height), y, x))
        if not choices:
            return 0, current_height + self.component_gap
        _, y, x = min(choices)
        return x, y

    @staticmethod
    def _main_components(diagram: DiagramIR) -> List[List[str]]:
        """Components are defined by primary flow only; auxiliary edges do not stretch layout."""
        order = {node.id: index for index, node in enumerate(diagram.nodes)}
        neighbors: DefaultDict[str, List[str]] = defaultdict(list)
        for edge in diagram.edges:
            if edge.kind != "main":
                continue
            neighbors[edge.source].append(edge.target)
            neighbors[edge.target].append(edge.source)
        components: List[List[str]] = []
        visited: Set[str] = set()
        for node in diagram.nodes:
            if node.id in visited:
                continue
            queue = deque([node.id])
            visited.add(node.id)
            component: List[str] = []
            while queue:
                current = queue.popleft()
                component.append(current)
                for neighbor in neighbors[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            component.sort(key=lambda node_id: order[node_id])
            components.append(component)
        return components

    def _apply_top_down_tree(
        self,
        diagram: DiagramIR,
        levels: Dict[str, int],
        by_level: Dict[int, List[str]],
        preserve_positions: bool,
    ) -> bool:
        """Center every parent over the exact span occupied by its primary children."""
        nodes = {node.id: node for node in diagram.nodes}
        children: DefaultDict[str, List[str]] = defaultdict(list)
        parents: DefaultDict[str, List[str]] = defaultdict(list)
        for edge in diagram.edges:
            if edge.kind != "main" or levels.get(edge.target) != levels.get(edge.source, 0) + 1:
                continue
            children[edge.source].append(edge.target)
            parents[edge.target].append(edge.source)

        if any(len(node_parents) > 1 for node_parents in parents.values()):
            return False

        positions = {node_id: index for node_ids in by_level.values() for index, node_id in enumerate(node_ids)}
        for node_children in children.values():
            node_children.sort(key=lambda node_id: positions.get(node_id, 0))

        roots = [node.id for node in diagram.nodes if not parents[node.id]]
        if not roots:
            return False
        roots.sort(key=lambda node_id: (levels.get(node_id, 0), positions.get(node_id, 0)))

        subtree_widths: Dict[str, float] = {}
        visiting: Set[str] = set()

        def subtree_width(node_id: str) -> float:
            if node_id in subtree_widths:
                return subtree_widths[node_id]
            if node_id in visiting:
                return nodes[node_id].width
            visiting.add(node_id)
            child_widths = [subtree_width(child_id) for child_id in children[node_id]]
            descendants, _ = self._balanced_child_span(child_widths)
            width = max(nodes[node_id].width, descendants)
            visiting.remove(node_id)
            subtree_widths[node_id] = width
            return width

        for root_id in roots:
            subtree_width(root_id)

        row_heights = {
            level: max(nodes[node_id].height for node_id in node_ids)
            for level, node_ids in by_level.items()
        }
        row_tops: Dict[int, float] = {}
        cursor_y = self.margin_y
        for level in sorted(row_heights):
            row_tops[level] = cursor_y
            cursor_y += row_heights[level] + self.layer_gap

        placed: Set[str] = set()

        def place(node_id: str, left: float) -> None:
            node = nodes[node_id]
            span = subtree_widths[node_id]
            level = levels[node_id]
            if not preserve_positions or node.x is None or node.y is None:
                node.x = left + (span - node.width) / 2
                node.y = row_tops[level] + (row_heights[level] - node.height) / 2
            placed.add(node_id)
            child_ids = children[node_id]
            child_widths = [subtree_widths[child_id] for child_id in child_ids]
            _, center_step = self._balanced_child_span(child_widths)
            if child_ids:
                group_midpoint = center_step * (len(child_ids) - 1) / 2
                first_center = left + span / 2 - group_midpoint
                for index, child_id in enumerate(child_ids):
                    child_center = first_center + index * center_step
                    place(
                        child_id,
                        child_center - subtree_widths[child_id] / 2,
                    )

        cursor_x = self.margin_x
        for root_id in roots:
            place(root_id, cursor_x)
            cursor_x += subtree_widths[root_id] + self.row_gap

        return len(placed) == len(diagram.nodes)

    def _balanced_child_span(self, child_widths: List[float]) -> tuple[float, float]:
        """Return a symmetric span and an equal child-center step without subtree overlap."""
        if not child_widths:
            return 0.0, 0.0
        if len(child_widths) == 1:
            return child_widths[0], 0.0
        center_step = max(
            (first + second) / 2 + self.row_gap
            for first, second in zip(child_widths, child_widths[1:])
        )
        group_midpoint = center_step * (len(child_widths) - 1) / 2
        left_extent = group_midpoint + child_widths[0] / 2
        right_extent = group_midpoint + child_widths[-1] / 2
        return 2 * max(left_extent, right_extent), center_step

    def _ordered_levels(self, diagram: DiagramIR, levels: Dict[str, int]) -> Dict[int, List[str]]:
        """Use barycentric sweeps to reduce crossings between adjacent layers."""
        original_index = {node.id: index for index, node in enumerate(diagram.nodes)}
        by_level: DefaultDict[int, List[str]] = defaultdict(list)
        predecessors: DefaultDict[str, List[str]] = defaultdict(list)
        successors: DefaultDict[str, List[str]] = defaultdict(list)
        for node in diagram.nodes:
            by_level[levels[node.id]].append(node.id)
        for edge in diagram.edges:
            if edge.kind != "main":
                continue
            predecessors[edge.target].append(edge.source)
            successors[edge.source].append(edge.target)

        ordered = {level: list(node_ids) for level, node_ids in by_level.items()}
        for _ in range(3):
            positions = self._positions(ordered)
            for level in sorted(ordered):
                ordered[level].sort(
                    key=lambda node_id: self._barycenter_key(
                        predecessors[node_id], positions, original_index[node_id]
                    )
                )
            positions = self._positions(ordered)
            for level in sorted(ordered, reverse=True):
                ordered[level].sort(
                    key=lambda node_id: self._barycenter_key(
                        successors[node_id], positions, original_index[node_id]
                    )
                )
        return ordered

    @staticmethod
    def _positions(by_level: Dict[int, List[str]]) -> Dict[str, float]:
        positions: Dict[str, float] = {}
        for node_ids in by_level.values():
            count = max(1, len(node_ids) - 1)
            for index, node_id in enumerate(node_ids):
                positions[node_id] = index / count
        return positions

    @staticmethod
    def _barycenter_key(
        neighbors: List[str], positions: Dict[str, float], fallback: int
    ) -> tuple[float, int]:
        available = [positions[node_id] for node_id in neighbors if node_id in positions]
        if not available:
            return 2.0, fallback
        return sum(available) / len(available), fallback

    def _levels(self, diagram: DiagramIR) -> Dict[str, int]:
        node_ids = [node.id for node in diagram.nodes]
        incoming: Dict[str, int] = {node_id: 0 for node_id in node_ids}
        outgoing: DefaultDict[str, List[str]] = defaultdict(list)
        for edge in diagram.edges:
            if edge.kind != "main":
                continue
            outgoing[edge.source].append(edge.target)
            incoming[edge.target] += 1

        queue = deque(node_id for node_id in node_ids if incoming[node_id] == 0)
        levels = {node_id: 0 for node_id in node_ids}
        visited: Set[str] = set()
        while queue:
            current = queue.popleft()
            visited.add(current)
            for target in outgoing[current]:
                levels[target] = max(levels[target], levels[current] + 1)
                incoming[target] -= 1
                if incoming[target] == 0:
                    queue.append(target)

        # Cycles that are not marked as feedback are placed deterministically at the end.
        next_level = max(levels.values(), default=0) + 1
        for node_id in node_ids:
            if node_id not in visited:
                levels[node_id] = next_level
                next_level += 1
        return levels
