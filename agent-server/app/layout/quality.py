from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict, Dict, List

from app.diagram.ir import DiagramIR, Node


class LayoutQualityError(RuntimeError):
    pass


@dataclass(frozen=True)
class LayoutQualityReport:
    valid: bool
    violations: List[str]
    checked_fanouts: int

    def to_dict(self) -> Dict[str, object]:
        return {
            "valid": self.valid,
            "violations": self.violations,
            "checked_fanouts": self.checked_fanouts,
        }


class LayoutQualityGate:
    """Reject geometry that violates deterministic overlap and symmetry invariants."""

    def evaluate(
        self, diagram: DiagramIR, levels: Dict[str, int], tolerance: float = 1.5
    ) -> LayoutQualityReport:
        violations: List[str] = []
        for index, first in enumerate(diagram.nodes):
            for second in diagram.nodes[index + 1 :]:
                if self._overlap(first, second):
                    violations.append(f"nodes overlap: {first.id} and {second.id}")

        checked_fanouts = 0
        if diagram.direction == "top-to-bottom":
            children: DefaultDict[str, List[str]] = defaultdict(list)
            parents: DefaultDict[str, List[str]] = defaultdict(list)
            nodes = {node.id: node for node in diagram.nodes}
            for edge in diagram.edges:
                if edge.kind != "main" or levels.get(edge.target) != levels.get(edge.source, 0) + 1:
                    continue
                children[edge.source].append(edge.target)
                parents[edge.target].append(edge.source)

            for parent_id, child_ids in children.items():
                if len(child_ids) < 2 or any(len(parents[child_id]) != 1 for child_id in child_ids):
                    continue
                checked_fanouts += 1
                parent_center = self._center_x(nodes[parent_id])
                centers = sorted(self._center_x(nodes[child_id]) for child_id in child_ids)
                group_center = (centers[0] + centers[-1]) / 2
                if abs(parent_center - group_center) > tolerance:
                    violations.append(
                        f"fanout {parent_id} is not centered over its direct children"
                    )
                if len(centers) >= 3:
                    gaps = [second - first for first, second in zip(centers, centers[1:])]
                    if max(gaps) - min(gaps) > tolerance:
                        violations.append(
                            f"fanout {parent_id} does not use equal child-center spacing"
                        )

        return LayoutQualityReport(
            valid=not violations,
            violations=violations,
            checked_fanouts=checked_fanouts,
        )

    def enforce(self, diagram: DiagramIR, levels: Dict[str, int]) -> LayoutQualityReport:
        report = self.evaluate(diagram, levels)
        if not report.valid:
            raise LayoutQualityError("; ".join(report.violations))
        return report

    @staticmethod
    def _center_x(node: Node) -> float:
        return (node.x or 0) + node.width / 2

    @staticmethod
    def _overlap(first: Node, second: Node) -> bool:
        first_x = first.x or 0
        first_y = first.y or 0
        second_x = second.x or 0
        second_y = second.y or 0
        return not (
            first_x + first.width <= second_x
            or second_x + second.width <= first_x
            or first_y + first.height <= second_y
            or second_y + second.height <= first_y
        )
