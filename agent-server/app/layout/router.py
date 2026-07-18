from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict, Dict, List, Tuple

from app.diagram.ir import DiagramIR, Edge, Node


Point = Tuple[float, float]


@dataclass(frozen=True)
class EdgeRoute:
    style: Dict[str, str]
    points: List[Point]
    external: bool = False


class OrthogonalRouter:
    """Plans explicit draw.io ports and waypoints in empty routing lanes."""

    def __init__(
        self,
        clearance: float = 18,
        outside_gap: float = 48,
        outside_lane_gap: float = 22,
    ) -> None:
        self.clearance = clearance
        self.outside_gap = outside_gap
        self.outside_lane_gap = outside_lane_gap

    def plan(self, diagram: DiagramIR) -> Dict[str, EdgeRoute]:
        nodes = {node.id: node for node in diagram.nodes}
        levels = self._levels(diagram)
        forward: DefaultDict[tuple[str, str], List[Edge]] = defaultdict(list)
        external: List[Edge] = []

        for edge in diagram.edges:
            source_level = levels.get(edge.source, 0)
            target_level = levels.get(edge.target, 0)
            if edge.kind == "main" and target_level == source_level + 1:
                forward[(edge.source, edge.kind)].append(edge)
            else:
                external.append(edge)

        outgoing = self._edge_ranks(diagram, nodes, outgoing=True)
        incoming = self._edge_ranks(diagram, nodes, outgoing=False)
        routes: Dict[str, EdgeRoute] = {}
        for group in forward.values():
            group.sort(key=lambda edge: self._forward_sort_key(edge, nodes, diagram.direction))
            shared_lane = self._shared_forward_lane(group, nodes, diagram.direction)
            for index, edge in enumerate(group):
                routes[edge.id] = self._forward_route(
                    edge,
                    nodes,
                    diagram.direction,
                    index,
                    len(group),
                    0.5 if len(group) > 1 else outgoing[edge.id],
                    incoming[edge.id],
                    shared_lane,
                )

        convergence: DefaultDict[tuple[str, str], List[Edge]] = defaultdict(list)
        for group in forward.values():
            for edge in group:
                convergence[(edge.target, edge.kind)].append(edge)
        for group in convergence.values():
            if len(group) < 2:
                continue
            group.sort(key=lambda edge: self._forward_sort_key(edge, nodes, diagram.direction))
            shared_lane = self._shared_convergence_lane(group, nodes, diagram.direction)
            for edge in group:
                routes[edge.id] = self._convergence_route(
                    edge,
                    nodes,
                    diagram.direction,
                    outgoing[edge.id],
                    shared_lane,
                )

        external.sort(key=lambda edge: (levels.get(edge.source, 0), levels.get(edge.target, 0), edge.id))
        for index, edge in enumerate(external):
            routes[edge.id] = self._external_route(
                edge,
                nodes,
                diagram.direction,
                index,
                outgoing[edge.id],
                incoming[edge.id],
            )
        return routes

    def _forward_route(
        self,
        edge: Edge,
        nodes: Dict[str, Node],
        direction: str,
        index: int,
        count: int,
        exit_fraction: float,
        entry_fraction: float,
        shared_lane: float,
    ) -> EdgeRoute:
        source = nodes[edge.source]
        target = nodes[edge.target]
        if direction == "top-to-bottom":
            source_x = (source.x or 0) + source.width * exit_fraction
            target_x = (target.x or 0) + target.width * entry_fraction
            return EdgeRoute(
                style=self._ports(exit_fraction, 1, entry_fraction, 0),
                points=[(source_x, shared_lane), (target_x, shared_lane)],
            )

        source_y = (source.y or 0) + source.height * exit_fraction
        target_y = (target.y or 0) + target.height * entry_fraction
        return EdgeRoute(
            style=self._ports(1, exit_fraction, 0, entry_fraction),
            points=[(shared_lane, source_y), (shared_lane, target_y)],
        )

    @staticmethod
    def _shared_forward_lane(
        edges: List[Edge], nodes: Dict[str, Node], direction: str
    ) -> float:
        source = nodes[edges[0].source]
        if direction == "top-to-bottom":
            source_boundary = (source.y or 0) + source.height
            nearest_target = min(nodes[edge.target].y or 0 for edge in edges)
        else:
            source_boundary = (source.x or 0) + source.width
            nearest_target = min(nodes[edge.target].x or 0 for edge in edges)
        return source_boundary + max(0, nearest_target - source_boundary) / 2

    def _external_route(
        self,
        edge: Edge,
        nodes: Dict[str, Node],
        direction: str,
        lane_index: int,
        exit_fraction: float,
        entry_fraction: float,
    ) -> EdgeRoute:
        source = nodes[edge.source]
        target = nodes[edge.target]
        if direction == "top-to-bottom":
            right = max((node.x or 0) + node.width for node in nodes.values())
            outside_x = right + self.outside_gap + lane_index * self.outside_lane_gap
            source_x = (source.x or 0) + source.width * exit_fraction
            target_x = (target.x or 0) + target.width * entry_fraction
            source_lane = (source.y or 0) + source.height + self.clearance
            target_lane = (target.y or 0) - self.clearance
            return EdgeRoute(
                style=self._ports(exit_fraction, 1, entry_fraction, 0),
                points=[
                    (source_x, source_lane),
                    (outside_x, source_lane),
                    (outside_x, target_lane),
                    (target_x, target_lane),
                ],
                external=True,
            )

        bottom = max((node.y or 0) + node.height for node in nodes.values())
        outside_y = bottom + self.outside_gap + lane_index * self.outside_lane_gap
        source_y = (source.y or 0) + source.height * exit_fraction
        target_y = (target.y or 0) + target.height * entry_fraction
        source_lane = (source.x or 0) + source.width + self.clearance
        target_lane = (target.x or 0) - self.clearance
        return EdgeRoute(
            style=self._ports(1, exit_fraction, 0, entry_fraction),
            points=[
                (source_lane, source_y),
                (source_lane, outside_y),
                (target_lane, outside_y),
                (target_lane, target_y),
            ],
            external=True,
        )

    def _convergence_route(
        self,
        edge: Edge,
        nodes: Dict[str, Node],
        direction: str,
        exit_fraction: float,
        shared_lane: float,
    ) -> EdgeRoute:
        source = nodes[edge.source]
        target = nodes[edge.target]
        if direction == "top-to-bottom":
            source_x = (source.x or 0) + source.width * exit_fraction
            target_x = (target.x or 0) + target.width / 2
            return EdgeRoute(
                style=self._ports(exit_fraction, 1, 0.5, 0),
                points=[(source_x, shared_lane), (target_x, shared_lane)],
            )
        source_y = (source.y or 0) + source.height * exit_fraction
        target_y = (target.y or 0) + target.height / 2
        return EdgeRoute(
            style=self._ports(1, exit_fraction, 0, 0.5),
            points=[(shared_lane, source_y), (shared_lane, target_y)],
        )

    @staticmethod
    def _shared_convergence_lane(
        edges: List[Edge], nodes: Dict[str, Node], direction: str
    ) -> float:
        target = nodes[edges[0].target]
        if direction == "top-to-bottom":
            source_boundary = max(
                (nodes[edge.source].y or 0) + nodes[edge.source].height for edge in edges
            )
            target_boundary = target.y or 0
        else:
            source_boundary = max(
                (nodes[edge.source].x or 0) + nodes[edge.source].width for edge in edges
            )
            target_boundary = target.x or 0
        return source_boundary + max(0, target_boundary - source_boundary) / 2

    def _edge_ranks(
        self, diagram: DiagramIR, nodes: Dict[str, Node], outgoing: bool
    ) -> Dict[str, float]:
        grouped: DefaultDict[str, List[Edge]] = defaultdict(list)
        for edge in diagram.edges:
            grouped[edge.source if outgoing else edge.target].append(edge)

        result: Dict[str, float] = {}
        for edges in grouped.values():
            edges.sort(
                key=lambda edge: self._axis_center(
                    nodes[edge.target if outgoing else edge.source], diagram.direction
                )
            )
            for index, edge in enumerate(edges):
                result[edge.id] = self._port_fraction(index, len(edges))
        return result

    @staticmethod
    def _port_fraction(index: int, count: int) -> float:
        if count <= 1:
            return 0.5
        return 0.18 + 0.64 * index / (count - 1)

    @staticmethod
    def _axis_center(node: Node, direction: str) -> float:
        if direction == "top-to-bottom":
            return (node.x or 0) + node.width / 2
        return (node.y or 0) + node.height / 2

    def _forward_sort_key(
        self, edge: Edge, nodes: Dict[str, Node], direction: str
    ) -> tuple[float, float, str]:
        return (
            self._axis_center(nodes[edge.source], direction),
            self._axis_center(nodes[edge.target], direction),
            edge.id,
        )

    @staticmethod
    def _ports(exit_x: float, exit_y: float, entry_x: float, entry_y: float) -> Dict[str, str]:
        return {
            "exitX": str(round(exit_x, 4)),
            "exitY": str(round(exit_y, 4)),
            "exitDx": "0",
            "exitDy": "0",
            "exitPerimeter": "1",
            "entryX": str(round(entry_x, 4)),
            "entryY": str(round(entry_y, 4)),
            "entryDx": "0",
            "entryDy": "0",
            "entryPerimeter": "1",
        }

    @staticmethod
    def _levels(diagram: DiagramIR) -> Dict[str, int]:
        layout = diagram.metadata.get("layout", {})
        raw = layout.get("levels", {}) if isinstance(layout, dict) else {}
        if isinstance(raw, dict):
            return {str(node_id): int(level) for node_id, level in raw.items()}
        return {}
