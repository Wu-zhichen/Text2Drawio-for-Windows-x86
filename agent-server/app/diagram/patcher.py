from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable

from .ir import DiagramIR, Edge, Node
from .validator import DiagramValidationError, validate_diagram


class PatchError(ValueError):
    pass


def apply_patch(diagram: DiagramIR, operations: Iterable[Dict[str, Any]]) -> DiagramIR:
    result = deepcopy(diagram)
    for operation in operations:
        op = operation.get("op")
        if op == "add_node":
            result.nodes.append(Node.from_dict(_required(operation, "node")))
        elif op == "remove_node":
            node_id = str(_required(operation, "id"))
            before = len(result.nodes)
            result.nodes = [node for node in result.nodes if node.id != node_id]
            if len(result.nodes) == before:
                raise PatchError(f"unknown node: {node_id}")
            result.edges = [edge for edge in result.edges if edge.source != node_id and edge.target != node_id]
        elif op == "update_node":
            _update(result.nodes, str(_required(operation, "id")), _required(operation, "changes"), {"id"})
        elif op == "add_edge":
            result.edges.append(Edge.from_dict(_required(operation, "edge")))
        elif op == "remove_edge":
            edge_id = str(_required(operation, "id"))
            before = len(result.edges)
            result.edges = [edge for edge in result.edges if edge.id != edge_id]
            if len(result.edges) == before:
                raise PatchError(f"unknown edge: {edge_id}")
        elif op == "update_edge":
            _update(result.edges, str(_required(operation, "id")), _required(operation, "changes"), {"id", "source", "target"})
        elif op == "set_direction":
            result.direction = str(_required(operation, "direction"))
        else:
            raise PatchError(f"unsupported operation: {op!r}")
    try:
        validate_diagram(result)
    except DiagramValidationError as exc:
        raise PatchError(str(exc)) from exc
    return result


def _required(value: Dict[str, Any], key: str) -> Any:
    if key not in value:
        raise PatchError(f"operation is missing {key!r}")
    return value[key]


def _update(items: list, item_id: str, changes: Dict[str, Any], immutable: set) -> None:
    for item in items:
        if item.id == item_id:
            for key, value in changes.items():
                if key in immutable:
                    raise PatchError(f"field {key!r} cannot be changed")
                if not hasattr(item, key):
                    raise PatchError(f"unknown field: {key}")
                setattr(item, key, value)
            return
    raise PatchError(f"unknown item: {item_id}")
