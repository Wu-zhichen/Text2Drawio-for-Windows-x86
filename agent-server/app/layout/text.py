from __future__ import annotations

import math
import re
import unicodedata
from collections import defaultdict
from typing import DefaultDict, Dict, List

from app.diagram.ir import DiagramIR, Node


class TextSizer:
    """Estimate editable draw.io label geometry before deterministic layout."""

    def apply(self, diagram: DiagramIR, levels: Dict[str, int]) -> None:
        children: DefaultDict[str, List[str]] = defaultdict(list)
        for edge in diagram.edges:
            if edge.kind != "main":
                continue
            children[edge.source].append(edge.target)

        for node in diagram.nodes:
            level = levels.get(node.id, 0)
            is_primary_heading = level == 0 and bool(children[node.id])
            is_section_heading = (
                not is_primary_heading
                and (bool(children[node.id]) or node.type == "system")
            )
            if is_primary_heading:
                font_size, font_bold = 18, True
            elif is_section_heading:
                font_size, font_bold = 16, True
            elif self._is_long_body(node.label):
                font_size, font_bold = 14, False
            else:
                font_size, font_bold = 16, True

            node.style = dict(node.style)
            node.style["fontSize"] = str(font_size)
            node.style["fontStyle"] = "1" if font_bold else "0"
            node.style["verticalAlign"] = "middle"
            required_width, required_height = self._required_size(
                node, font_size, is_primary_heading or is_section_heading
            )

            # 240x100 is the IR default, not an explicit user size. Replace it
            # with the measured geometry; preserve intentional custom geometry.
            uses_default_geometry = abs(node.width - 240) < 0.1 and abs(node.height - 100) < 0.1
            if uses_default_geometry:
                node.width = required_width
                node.height = required_height
            else:
                node.width = max(node.width, required_width)
                node.height = max(node.height, required_height)

    def _required_size(
        self, node: Node, font_size: int, is_heading: bool
    ) -> tuple[float, float]:
        raw_lines = [line.strip() for line in re.split(r"\r?\n", node.label) if line.strip()]
        if not raw_lines:
            raw_lines = [node.label.strip() or " "]

        if is_heading:
            min_width, max_width = 240.0, 360.0
        elif node.type in {"data", "note"} or self._is_long_body(node.label):
            min_width, max_width = 260.0, 420.0
        else:
            min_width, max_width = 200.0, 340.0

        image_space = 78.0 if node.image_data else 0.0
        horizontal_padding = 36.0 + image_space
        longest_pixels = max(self._line_units(line) * font_size for line in raw_lines)
        width = min(max_width, max(min_width, longest_pixels + horizontal_padding))
        width = math.ceil(width / 10.0) * 10.0
        usable_width = max(80.0, width - horizontal_padding)

        visual_lines = 0
        for index, line in enumerate(raw_lines):
            line_font = font_size
            if len(raw_lines) > 1 and index > 0:
                line_font = max(12, font_size - 2 if font_size >= 16 else font_size)
            pixels = max(line_font, self._line_units(line) * line_font)
            visual_lines += max(1, math.ceil(pixels / usable_width))

        line_height = font_size * 1.38
        if len(raw_lines) > 1:
            line_height = max(19.0, (font_size - 1) * 1.38)
        vertical_padding = 30.0 if node.type == "decision" else 24.0
        height = vertical_padding + visual_lines * line_height
        if len(raw_lines) > 1:
            height += 6.0
        min_height = 96.0 if node.type == "decision" else (76.0 if is_heading else 68.0)
        if node.image_data:
            min_height = max(min_height, 110.0)
        height = min(320.0, max(min_height, math.ceil(height / 4.0) * 4.0))
        return width, height

    @staticmethod
    def _is_long_body(label: str) -> bool:
        return "\n" in label or TextSizer._line_units(label) > 24

    @staticmethod
    def _line_units(text: str) -> float:
        units = 0.0
        for char in text:
            if char.isspace():
                units += 0.32
            elif unicodedata.east_asian_width(char) in {"W", "F"}:
                units += 1.0
            elif char.isupper() or char.isdigit():
                units += 0.62
            elif char in ",.;:!?%+-/()[]{}":
                units += 0.42
            else:
                units += 0.55
        return units
