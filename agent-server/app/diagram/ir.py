from __future__ import annotations

from dataclasses import asdict, dataclass, field
from collections.abc import Mapping
from typing import Any, Dict, List, Optional


ALLOWED_DIAGRAM_TYPES = {"flowchart", "architecture", "pipeline", "concept", "custom"}
ALLOWED_NODE_TYPES = {"input", "process", "data", "system", "output", "decision", "note"}
ALLOWED_EDGE_KINDS = {"main", "feedback", "error", "association"}
ALLOWED_DIRECTIONS = {"left-to-right", "top-to-bottom"}


def _coerce_style(value: Any) -> Dict[str, str]:
    """Accept either a JSON object or a draw.io ``key=value;`` style string."""
    if isinstance(value, Mapping):
        return {
            str(key): str(item)
            for key, item in value.items()
            if key is not None and item is not None and not isinstance(item, (dict, list, tuple, set))
        }
    if not isinstance(value, str):
        return {}

    result: Dict[str, str] = {}
    for part in value.split(";"):
        if "=" not in part:
            continue
        key, item = part.split("=", 1)
        key = key.strip()
        if key:
            result[key] = item.strip()
    return result


def _optional_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _float_or_default(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class Node:
    id: str
    label: str
    type: str = "process"
    description: str = ""
    x: Optional[float] = None
    y: Optional[float] = None
    width: float = 240
    height: float = 100
    style: Dict[str, str] = field(default_factory=dict)
    image_data: str = ""
    image_alt: str = ""

    @classmethod
    def from_dict(cls, value: Dict[str, Any], fallback_id: str = "") -> "Node":
        return cls(
            id=str(value.get("id") or fallback_id).strip(),
            label=str(value.get("label", "")).strip(),
            type=str(value.get("type", "process")),
            description=str(value.get("description", "")),
            x=_optional_float(value.get("x")),
            y=_optional_float(value.get("y")),
            width=_float_or_default(value.get("width", 240), 240),
            height=_float_or_default(value.get("height", 100), 100),
            style=_coerce_style(value.get("style")),
            image_data=str(value.get("image_data", "")),
            image_alt=str(value.get("image_alt", "")),
        )


@dataclass
class Edge:
    id: str
    source: str
    target: str
    label: str = ""
    kind: str = "main"
    style: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Dict[str, Any], fallback_id: str = "") -> "Edge":
        return cls(
            id=str(value.get("id") or fallback_id).strip(),
            source=str(value.get("source", "")).strip(),
            target=str(value.get("target", "")).strip(),
            label=str(value.get("label", "")),
            kind=str(value.get("kind", "main")),
            style=_coerce_style(value.get("style")),
        )


@dataclass
class DiagramIR:
    diagram_type: str
    title: str
    nodes: List[Node]
    edges: List[Edge]
    version: str = "1.0"
    description: str = ""
    direction: str = "left-to-right"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "DiagramIR":
        raw_nodes = value.get("nodes", [])
        node_items = [item for item in raw_nodes if isinstance(item, dict)] if isinstance(raw_nodes, list) else []
        reserved_node_ids = {str(item.get("id", "")).strip() for item in node_items if item.get("id")}
        nodes: List[Node] = []
        used_node_ids = set(reserved_node_ids)
        for index, item in enumerate(node_items, start=1):
            fallback = f"node_{index}"
            suffix = index
            while fallback in used_node_ids:
                suffix += 1
                fallback = f"node_{suffix}"
            node = Node.from_dict(item, fallback_id=fallback)
            nodes.append(node)
            used_node_ids.add(node.id)

        raw_edges = value.get("edges", [])
        edge_items = [item for item in raw_edges if isinstance(item, dict)] if isinstance(raw_edges, list) else []
        reserved_edge_ids = {str(item.get("id", "")).strip() for item in edge_items if item.get("id")}
        edges: List[Edge] = []
        used_edge_ids = set(reserved_edge_ids)
        for index, item in enumerate(edge_items, start=1):
            fallback = f"edge_{index}"
            suffix = index
            while fallback in used_edge_ids:
                suffix += 1
                fallback = f"edge_{suffix}"
            edge = Edge.from_dict(item, fallback_id=fallback)
            edges.append(edge)
            used_edge_ids.add(edge.id)

        raw_metadata = value.get("metadata", {})
        return cls(
            version=str(value.get("version", "1.0")),
            diagram_type=str(value.get("diagram_type", "flowchart")),
            title=str(value.get("title", "Untitled Diagram")),
            description=str(value.get("description", "")),
            direction=str(value.get("direction", "left-to-right")),
            nodes=nodes,
            edges=edges,
            metadata=dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
