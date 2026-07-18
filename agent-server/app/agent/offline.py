from __future__ import annotations

import re
from typing import Any, Dict, List


def plan_offline(prompt: str) -> Dict[str, Any]:
    """Create a conservative editable pipeline when no API key is configured."""
    clean = re.sub(r"\s+", " ", prompt).strip()
    title = clean[:80] if clean else "Editable Diagram"
    parts = _extract_parts(clean)
    node_types = _node_types(len(parts))
    nodes = [
        {"id": f"node_{index + 1}", "label": label[:120], "type": node_types[index]}
        for index, label in enumerate(parts)
    ]
    edges = [
        {
            "id": f"edge_{index + 1}",
            "source": nodes[index]["id"],
            "target": nodes[index + 1]["id"],
            "label": "",
            "kind": "main",
        }
        for index in range(len(nodes) - 1)
    ]
    return {
        "version": "1.0",
        "diagram_type": "architecture" if any(word in clean.lower() for word in ("架构", "architecture", "layer")) else "flowchart",
        "title": title,
        "description": "Offline deterministic draft; configure DeepSeek for semantic planning.",
        "direction": "top-to-bottom" if "自上而下" in clean or "top-to-bottom" in clean.lower() else "left-to-right",
        "nodes": nodes,
        "edges": edges,
        "metadata": {"planner": "offline-fallback"},
    }


def _extract_parts(prompt: str) -> List[str]:
    candidates = re.split(r"\s*(?:->|→|⇒|然后|接着|最后|；|;|\n)\s*", prompt)
    parts = [item.strip(" ，,。.：:") for item in candidates if item.strip(" ，,。.：:")]
    if len(parts) == 1:
        chunks = [item.strip() for item in re.split(r"[，,]", parts[0]) if item.strip()]
        if 2 <= len(chunks) <= 8:
            parts = chunks
    if len(parts) < 2:
        parts = ["User Request", "Agent Planning", "Diagram IR", "Editable draw.io"]
    return parts[:12]


def _node_types(count: int) -> List[str]:
    if count == 1:
        return ["process"]
    values = ["process"] * count
    values[0] = "input"
    values[-1] = "output"
    if count >= 4:
        values[-2] = "data"
    return values

