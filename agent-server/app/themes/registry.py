from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping


DEFAULT_THEME_ID = "default"


@dataclass(frozen=True)
class ThemeSpec:
    id: str
    name: str
    description: str
    source_name: str
    source_url: str
    palette: Mapping[str, tuple[str, str]]
    edge_colors: Mapping[str, tuple[str, str]]
    page_background: str = "#FFFFFF"
    text_color: str = "#263238"
    title_color: str = "#1F2937"
    label_background: str = "#FFFFFF"
    stroke_width: int = 2
    arc_size: int = 12
    shadow: bool = False
    margin_x: float = 70
    margin_y: float = 100
    layer_gap: float = 96
    row_gap: float = 44
    component_gap: float = 56

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "swatches": [fill for fill, _ in self.palette.values()][:5],
        }


_DEFAULT_PALETTE = {
    "input": ("#FCE9E4", "#E07A5F"),
    "process": ("#ECEBFF", "#6C63FF"),
    "data": ("#E8F5FC", "#56B4E9"),
    "system": ("#E7F5F3", "#2A9D8F"),
    "output": ("#FFF4CF", "#E9C46A"),
    "decision": ("#FFF4CF", "#E07A5F"),
    "note": ("#F4F6F8", "#8A959B"),
}


THEMES: Dict[str, ThemeSpec] = {
    "default": ThemeSpec(
        id="default",
        name="默认 · 智能均衡",
        description="自动适配大多数流程图与论文总结图。",
        source_name="Text2Draw.io",
        source_url="",
        palette=_DEFAULT_PALETTE,
        edge_colors={
            "main": ("#263238", "0"), "feedback": ("#2A9D8F", "1"),
            "error": ("#E07A5F", "1"), "association": ("#56B4E9", "1"),
        },
    ),
    "carbon-blue": ThemeSpec(
        id="carbon-blue",
        name="Carbon 专业蓝",
        description="克制、高密度，适合系统架构和工程流程。",
        source_name="IBM Carbon Design System",
        source_url="https://carbondesignsystem.com/elements/color/overview/",
        palette={
            "input": ("#E8F1FF", "#0F62FE"), "process": ("#DDE1E6", "#525252"),
            "data": ("#D0E2FF", "#0043CE"), "system": ("#E5F6FF", "#0072C3"),
            "output": ("#DEFBE6", "#198038"), "decision": ("#FFF1F1", "#DA1E28"),
            "note": ("#F4F4F4", "#8D8D8D"),
        },
        edge_colors={
            "main": ("#161616", "0"), "feedback": ("#198038", "1"),
            "error": ("#DA1E28", "1"), "association": ("#0F62FE", "1"),
        },
        text_color="#161616", title_color="#161616", layer_gap=86, row_gap=38,
        component_gap=48, arc_size=6,
    ),
    "material-purple": ThemeSpec(
        id="material-purple",
        name="Material 清新紫",
        description="柔和层次与圆润节点，适合概念图和产品流程。",
        source_name="Material Design color system",
        source_url="https://m3.material.io/styles/color/overview",
        palette={
            "input": ("#F3EDF7", "#6750A4"), "process": ("#EADDFF", "#6750A4"),
            "data": ("#D7E3FF", "#415F91"), "system": ("#D8E2DC", "#3F6357"),
            "output": ("#F9DEDC", "#8C1D18"), "decision": ("#FFE08A", "#7D5700"),
            "note": ("#F5F2FA", "#79747E"),
        },
        edge_colors={
            "main": ("#49454F", "0"), "feedback": ("#3F6357", "1"),
            "error": ("#B3261E", "1"), "association": ("#6750A4", "1"),
        },
        text_color="#1D1B20", title_color="#1D1B20", layer_gap=102, row_gap=48,
        component_gap=60, arc_size=20, shadow=True,
    ),
    "colorbrewer-green": ThemeSpec(
        id="colorbrewer-green",
        name="ColorBrewer 数据绿",
        description="色盲友好的定性配色，适合数据分析和多类别图。",
        source_name="ColorBrewer 2.0",
        source_url="https://colorbrewer2.org/",
        palette={
            "input": ("#E5F5F9", "#2CA25F"), "process": ("#E5F5E0", "#31A354"),
            "data": ("#D0D1E6", "#756BB1"), "system": ("#D9F0A3", "#238443"),
            "output": ("#FEE6CE", "#E6550D"), "decision": ("#FDD49E", "#D94801"),
            "note": ("#F7F7F7", "#737373"),
        },
        edge_colors={
            "main": ("#25352F", "0"), "feedback": ("#238443", "1"),
            "error": ("#D94801", "1"), "association": ("#756BB1", "1"),
        },
        text_color="#17352A", title_color="#17352A", layer_gap=90, row_gap=40,
        component_gap=50, arc_size=10,
    ),
    "tableau-orange": ThemeSpec(
        id="tableau-orange",
        name="Tableau 商务橙",
        description="清晰的类别区分，适合经营分析与指标看板。",
        source_name="Tableau color palettes",
        source_url="https://help.tableau.com/current/pro/desktop/en-us/viewparts_marks_markproperties_color.htm",
        palette={
            "input": ("#FDE8D3", "#F28E2B"), "process": ("#EAF2F8", "#4E79A7"),
            "data": ("#D9F0EF", "#59A14F"), "system": ("#E8E1F0", "#B07AA1"),
            "output": ("#FFF0C2", "#EDC948"), "decision": ("#FADBD8", "#E15759"),
            "note": ("#F2F2F2", "#79706E"),
        },
        edge_colors={
            "main": ("#2F2F2F", "0"), "feedback": ("#59A14F", "1"),
            "error": ("#E15759", "1"), "association": ("#4E79A7", "1"),
        },
        text_color="#2F2F2F", title_color="#222222", layer_gap=94, row_gap=42,
        component_gap=54, arc_size=10,
    ),
    "accessible-contrast": ThemeSpec(
        id="accessible-contrast",
        name="无障碍高对比",
        description="强调轮廓、文字对比和宽松间距，适合投影与打印。",
        source_name="NIST Okabe–Ito palette reference",
        source_url="https://www.itl.nist.gov/div898/software/dataplot/dpmacros/rgb_color_palettes.pdf",
        palette={
            "input": ("#FFF1CC", "#E69F00"), "process": ("#DDF3FF", "#0072B2"),
            "data": ("#D8F2E7", "#009E73"), "system": ("#EFE5F5", "#CC79A7"),
            "output": ("#FFF0F6", "#CC79A7"), "decision": ("#FFF3D6", "#D55E00"),
            "note": ("#F5F5F5", "#4D4D4D"),
        },
        edge_colors={
            "main": ("#000000", "0"), "feedback": ("#009E73", "1"),
            "error": ("#D55E00", "1"), "association": ("#0072B2", "1"),
        },
        text_color="#000000", title_color="#000000", stroke_width=3, layer_gap=112,
        row_gap=54, component_gap=66, arc_size=8,
    ),
}


def get_theme(theme_id: str | None) -> ThemeSpec:
    normalized = (theme_id or DEFAULT_THEME_ID).strip().lower()
    return THEMES.get(normalized, THEMES[DEFAULT_THEME_ID])


def public_themes() -> list[dict]:
    return [theme.public_dict() for theme in THEMES.values()]
