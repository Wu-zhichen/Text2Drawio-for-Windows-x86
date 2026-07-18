from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Dict, List, Tuple

from .ir import (
    ALLOWED_DIAGRAM_TYPES,
    ALLOWED_DIRECTIONS,
    ALLOWED_EDGE_KINDS,
    ALLOWED_NODE_TYPES,
)


_NODE_TYPE_ALIASES = {
    "start": "input",
    "source": "input",
    "end": "output",
    "result": "output",
    "sink": "output",
    "gateway": "decision",
    "condition": "decision",
    "database": "data",
    "storage": "data",
    "metric": "data",
    "kpi": "data",
    "chart": "data",
    "bar_chart": "data",
    "line_chart": "data",
    "pie_chart": "data",
    "donut_chart": "data",
    "funnel": "data",
    "heatmap": "data",
    "table": "data",
    "module": "system",
    "section": "system",
    "container": "system",
    "group": "system",
    "annotation": "note",
    "text": "note",
    "title": "note",
}

_DIRECTION_ALIASES = {
    "tb": "top-to-bottom",
    "td": "top-to-bottom",
    "vertical": "top-to-bottom",
    "top-down": "top-to-bottom",
    "top_down": "top-to-bottom",
    "lr": "left-to-right",
    "horizontal": "left-to-right",
    "left-right": "left-to-right",
    "left_to_right": "left-to-right",
}

_DRAWIO_RESERVED_IDS = {"join"}


def _safe_id(value: Any, prefix: str, index: int, used: set[str]) -> str:
    candidate = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "").strip()).strip("_-")
    if not candidate or not candidate[0].isalpha():
        candidate = f"{prefix}_{index}"
    elif candidate.lower() in _DRAWIO_RESERVED_IDS:
        candidate = f"{prefix}_{candidate}"
    candidate = candidate[:64]
    base = candidate
    suffix = 2
    while candidate in used:
        suffix_text = f"_{suffix}"
        candidate = base[: 64 - len(suffix_text)] + suffix_text
        suffix += 1
    used.add(candidate)
    return candidate


def _normalize_node_type(value: Any) -> str:
    node_type = str(value or "process").strip().lower().replace("-", "_").replace(" ", "_")
    if node_type in ALLOWED_NODE_TYPES:
        return node_type
    return _NODE_TYPE_ALIASES.get(node_type, "process")


def _normalize_edge_kind(value: Any) -> str:
    kind = str(value or "main").strip().lower().replace("-", "_").replace(" ", "_")
    if kind in ALLOWED_EDGE_KINDS:
        return kind
    if kind in {"back", "backward", "loop", "retry", "cycle"}:
        return "feedback"
    if kind in {"failure", "exception"}:
        return "error"
    if kind in {"reference", "related", "dependency", "dashed"}:
        return "association"
    return "main"


def normalize_generated_ir(value: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Repair common model-only schema deviations without changing user facts."""
    warnings: List[str] = []
    result: Dict[str, Any] = dict(value) if isinstance(value, Mapping) else {}

    result["version"] = "1.0"
    diagram_type = str(result.get("diagram_type", "flowchart")).strip().lower()
    if diagram_type not in ALLOWED_DIAGRAM_TYPES:
        result["diagram_type"] = "custom"
        warnings.append(f"Mapped unsupported diagram type {diagram_type!r} to 'custom'.")

    direction = str(result.get("direction", "top-to-bottom")).strip().lower()
    direction = _DIRECTION_ALIASES.get(direction, direction)
    if direction not in ALLOWED_DIRECTIONS:
        direction = "top-to-bottom"
        warnings.append("Mapped an unsupported layout direction to 'top-to-bottom'.")
    result["direction"] = direction
    title = str(result.get("title") or "Untitled Diagram").strip()
    result["title"] = title[:160] or "Untitled Diagram"

    raw_nodes = result.get("nodes")
    node_items = raw_nodes if isinstance(raw_nodes, list) else []
    used_node_ids: set[str] = set()
    id_map: Dict[str, str] = {}
    label_map: Dict[str, str] = {}
    nodes: List[Dict[str, Any]] = []
    for index, raw_node in enumerate(node_items[:80], start=1):
        if not isinstance(raw_node, Mapping):
            continue
        node = dict(raw_node)
        original_id = str(node.get("id") or "").strip()
        node_id = _safe_id(original_id, "node", index, used_node_ids)
        if original_id and original_id not in id_map:
            id_map[original_id] = node_id
        label = str(node.get("label") or node.get("name") or node.get("title") or "").strip()
        node["id"] = node_id
        node["label"] = (label or f"节点 {index}")[:120]
        node["type"] = _normalize_node_type(node.get("type"))
        label_map.setdefault(node["label"], node_id)
        nodes.append(node)
    if len(node_items) > 80:
        warnings.append("Limited the generated diagram to the first 80 nodes.")
    result["nodes"] = nodes

    raw_edges = result.get("edges")
    edge_items = raw_edges if isinstance(raw_edges, list) else []
    used_edge_ids: set[str] = set()
    edges: List[Dict[str, Any]] = []
    dropped_edges = 0
    valid_node_ids = {node["id"] for node in nodes}

    def resolve_node_ref(ref: Any) -> str:
        raw_ref = str(ref or "").strip()
        if raw_ref in valid_node_ids:
            return raw_ref
        return id_map.get(raw_ref) or label_map.get(raw_ref) or ""

    for index, raw_edge in enumerate(edge_items[:160], start=1):
        if not isinstance(raw_edge, Mapping):
            dropped_edges += 1
            continue
        edge = dict(raw_edge)
        source = resolve_node_ref(edge.get("source") or edge.get("from"))
        target = resolve_node_ref(edge.get("target") or edge.get("to"))
        if not source or not target or source == target:
            dropped_edges += 1
            continue
        edge["id"] = _safe_id(edge.get("id"), "edge", index, used_edge_ids)
        edge["source"] = source
        edge["target"] = target
        edge["label"] = str(edge.get("label") or "")[:80]
        edge["kind"] = _normalize_edge_kind(edge.get("kind"))
        edges.append(edge)
    if len(edge_items) > 160:
        dropped_edges += len(edge_items) - 160
    if dropped_edges:
        warnings.append(f"Removed {dropped_edges} invalid or unresolved generated edge(s).")
    result["edges"] = edges
    if not isinstance(result.get("metadata"), Mapping):
        result["metadata"] = {}
    return result, warnings
