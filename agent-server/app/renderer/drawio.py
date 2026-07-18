from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Dict
from xml.etree import ElementTree as ET

from app.diagram.ir import DiagramIR, Edge, Node
from app.layout.router import EdgeRoute, OrthogonalRouter
from app.themes import ThemeSpec, get_theme


def _style(parts: Dict[str, str]) -> str:
    return ";".join(f"{key}={value}" for key, value in parts.items()) + ";"


class DrawioRenderer:
    def __init__(self, theme: ThemeSpec | None = None) -> None:
        self.router = OrthogonalRouter()
        self.theme = theme or get_theme("default")

    def render(self, diagram: DiagramIR) -> str:
        routes = self.router.plan(diagram)
        width, height = self._page_size(diagram, routes)
        mxfile = ET.Element(
            "mxfile",
            {
                "host": "app.diagrams.net",
                "agent": "Text2Draw.io Desktop Agent",
                "version": "24.7.17",
                "modified": datetime.now(timezone.utc).isoformat(),
                "compressed": "false",
            },
        )
        page = ET.SubElement(mxfile, "diagram", {"id": "text2drawio-page", "name": "Page-1"})
        model = ET.SubElement(
            page,
            "mxGraphModel",
            {
                "dx": str(width),
                "dy": str(height),
                "grid": "1",
                "gridSize": "10",
                "guides": "1",
                "tooltips": "1",
                "connect": "1",
                "arrows": "1",
                "fold": "1",
                "page": "1",
                "pageScale": "1",
                "pageWidth": str(width),
                "pageHeight": str(height),
                "math": "0",
                "shadow": "0",
                "background": self.theme.page_background,
            },
        )
        root = ET.SubElement(model, "root")
        ET.SubElement(root, "mxCell", {"id": "0"})
        ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

        title = ET.SubElement(
            root,
            "mxCell",
            {
                "id": "diagram-title",
                "value": escape(diagram.title),
                "style": _style(
                    {
                        "text": "",
                        "html": "1",
                        "strokeColor": "none",
                        "fillColor": "none",
                        "align": "left",
                        "verticalAlign": "middle",
                        "fontSize": "28",
                        "fontStyle": "1",
                        "fontColor": self.theme.title_color,
                    }
                ),
                "vertex": "1",
                "parent": "1",
            },
        )
        ET.SubElement(
            title,
            "mxGeometry",
            {"x": "80", "y": "38", "width": str(max(600, width - 160)), "height": "52", "as": "geometry"},
        )

        for node in diagram.nodes:
            self._add_node(root, node)
        for edge in diagram.edges:
            self._add_edge(root, edge, routes[edge.id])

        ET.indent(mxfile, space="  ")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(mxfile, encoding="unicode")

    def _add_node(self, root: ET.Element, node: Node) -> None:
        fill, stroke = self.theme.palette[node.type]
        base_style = {
            "rounded": "1",
            "whiteSpace": "wrap",
            "html": "1",
            "fillColor": fill,
            "strokeColor": stroke,
            "strokeWidth": str(self.theme.stroke_width),
            "fontColor": self.theme.text_color,
            "fontSize": node.style.get("fontSize", "16"),
            "fontStyle": node.style.get("fontStyle", "1"),
            "arcSize": str(self.theme.arc_size),
            "spacing": "10",
            "shadow": "1" if self.theme.shadow else "0",
        }
        if node.type == "decision":
            base_style.update({"shape": "rhombus", "perimeter": "rhombusPerimeter", "rounded": "0"})
        base_style.update(node.style)
        if node.image_data:
            base_style.update({"align": "left", "spacingLeft": "78", "verticalAlign": "middle"})
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": node.id,
                "value": self._formatted_node_label(node),
                "style": _style(base_style),
                "vertex": "1",
                "parent": "1",
            },
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            {
                "x": str(round(node.x or 0, 2)),
                "y": str(round(node.y or 0, 2)),
                "width": str(round(node.width, 2)),
                "height": str(round(node.height, 2)),
                "as": "geometry",
            },
        )
        if node.image_data:
            image_cell = ET.SubElement(
                root,
                "mxCell",
                {
                    "id": f"{node.id}__image",
                    "value": "",
                    "style": _style(
                        {
                            "shape": "image",
                            "html": "1",
                            "imageAspect": "1",
                            "aspect": "fixed",
                            "image": node.image_data,
                            "connectable": "0",
                        }
                    ),
                    "vertex": "1",
                    "connectable": "0",
                    "parent": node.id,
                },
            )
            ET.SubElement(
                image_cell,
                "mxGeometry",
                {
                    "x": "12",
                    "y": str(round(max(8, (node.height - 54) / 2), 2)),
                    "width": "54",
                    "height": "54",
                    "as": "geometry",
                },
            )

    @staticmethod
    def _formatted_node_label(node: Node) -> str:
        lines = [line.strip() for line in node.label.replace("\r", "").split("\n") if line.strip()]
        if len(lines) <= 1:
            value = escape(node.label)
            if len(node.label) > 28:
                return f'<div style="white-space:normal;overflow-wrap:anywhere">{value}</div>'
            return value
        base_size = int(node.style.get("fontSize", "16"))
        title_size = max(16, base_size)
        body_size = max(13, min(14, base_size - 1))
        title = escape(lines[0])
        body = "<br>".join(escape(line) for line in lines[1:])
        return (
            f'<div style="font-size:{title_size}px;font-weight:600;line-height:1.25;'
            f'white-space:normal;overflow-wrap:anywhere;'
            f'margin-bottom:4px">{title}</div>'
            f'<div style="font-size:{body_size}px;font-weight:400;line-height:1.35;'
            f'white-space:normal;overflow-wrap:anywhere">{body}</div>'
        )

    def _add_edge(self, root: ET.Element, edge: Edge, route: EdgeRoute) -> None:
        stroke, dashed = self.theme.edge_colors[edge.kind]
        base_style = {
            "edgeStyle": "orthogonalEdgeStyle",
            "rounded": "0",
            "orthogonalLoop": "1",
            "jettySize": "20",
            "html": "1",
            "strokeColor": stroke,
            "strokeWidth": "2",
            "dashed": dashed,
            "endArrow": "block",
            "endFill": "1",
            "fontColor": stroke,
            "fontSize": "13",
            "labelBackgroundColor": self.theme.label_background,
        }
        base_style.update(edge.style)
        base_style.update(route.style)
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": edge.id,
                "value": escape(edge.label),
                "style": _style(base_style),
                "edge": "1",
                "parent": "1",
                "source": edge.source,
                "target": edge.target,
            },
        )
        geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        if route.points:
            points = ET.SubElement(geometry, "Array", {"as": "points"})
            for x, y in route.points:
                ET.SubElement(points, "mxPoint", {"x": str(round(x, 2)), "y": str(round(y, 2))})

    def _page_size(self, diagram: DiagramIR, routes: Dict[str, EdgeRoute]) -> tuple:
        max_x = max((node.x or 0) + node.width for node in diagram.nodes)
        max_y = max((node.y or 0) + node.height for node in diagram.nodes)
        for route in routes.values():
            for x, y in route.points:
                max_x = max(max_x, x)
                max_y = max(max_y, y)
        return max(1200, int(max_x + 120)), max(700, int(max_y + 200))
