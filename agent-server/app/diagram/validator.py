from __future__ import annotations

import re
from typing import List

from .ir import (
    ALLOWED_DIAGRAM_TYPES,
    ALLOWED_DIRECTIONS,
    ALLOWED_EDGE_KINDS,
    ALLOWED_NODE_TYPES,
    DiagramIR,
)


ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
DRAWIO_RESERVED_IDS = {"join"}


class DiagramValidationError(ValueError):
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_diagram(diagram: DiagramIR) -> List[str]:
    errors: List[str] = []
    if diagram.version != "1.0":
        errors.append("version must be '1.0'")
    if diagram.diagram_type not in ALLOWED_DIAGRAM_TYPES:
        errors.append(f"unsupported diagram_type: {diagram.diagram_type}")
    if diagram.direction not in ALLOWED_DIRECTIONS:
        errors.append(f"unsupported direction: {diagram.direction}")
    if not diagram.title.strip() or len(diagram.title) > 160:
        errors.append("title must contain 1-160 characters")
    if not diagram.nodes:
        errors.append("at least one node is required")
    if len(diagram.nodes) > 80:
        errors.append("a diagram can contain at most 80 nodes")
    if len(diagram.edges) > 160:
        errors.append("a diagram can contain at most 160 edges")

    node_ids = set()
    for node in diagram.nodes:
        if not ID_PATTERN.fullmatch(node.id):
            errors.append(f"invalid node id: {node.id!r}")
        if node.id.lower() in DRAWIO_RESERVED_IDS:
            errors.append(f"node id is reserved by draw.io: {node.id}")
        if node.id in node_ids:
            errors.append(f"duplicate node id: {node.id}")
        node_ids.add(node.id)
        if node.type not in ALLOWED_NODE_TYPES:
            errors.append(f"node {node.id} has unsupported type: {node.type}")
        if not node.label.strip() or len(node.label) > 120:
            errors.append(f"node {node.id} label must contain 1-120 characters")
        if not 80 <= node.width <= 800 or not 40 <= node.height <= 600:
            errors.append(f"node {node.id} has invalid dimensions")
        if node.image_data:
            if not node.image_data.startswith(("data:image/png;base64,", "data:image/webp;base64,", "data:image/jpeg;base64,")):
                errors.append(f"node {node.id} image_data must be an embedded PNG, WebP, or JPEG data URI")
            if len(node.image_data) > 750_000:
                errors.append(f"node {node.id} image_data exceeds the 750 KB limit")

    edge_ids = set()
    for edge in diagram.edges:
        if not ID_PATTERN.fullmatch(edge.id):
            errors.append(f"invalid edge id: {edge.id!r}")
        if edge.id.lower() in DRAWIO_RESERVED_IDS:
            errors.append(f"edge id is reserved by draw.io: {edge.id}")
        if edge.id in edge_ids:
            errors.append(f"duplicate edge id: {edge.id}")
        edge_ids.add(edge.id)
        if edge.source not in node_ids:
            errors.append(f"edge {edge.id} has unknown source: {edge.source}")
        if edge.target not in node_ids:
            errors.append(f"edge {edge.id} has unknown target: {edge.target}")
        if edge.source == edge.target:
            errors.append(f"edge {edge.id} cannot connect a node to itself")
        if edge.kind not in ALLOWED_EDGE_KINDS:
            errors.append(f"edge {edge.id} has unsupported kind: {edge.kind}")
        if len(edge.label) > 80:
            errors.append(f"edge {edge.id} label exceeds 80 characters")

    if errors:
        raise DiagramValidationError(errors)
    return []
