from __future__ import annotations

from fastapi.testclient import TestClient

from app.diagram.ir import DiagramIR, Edge, Node
from app.main import app
from app.renderer.drawio import DrawioRenderer
from app.themes import get_theme, public_themes


client = TestClient(app)


def _diagram() -> DiagramIR:
    return DiagramIR(
        diagram_type="flowchart",
        title="主题测试",
        description="",
        direction="top-to-bottom",
        nodes=[
            Node(id="a", label="输入", type="input", x=80, y=100),
            Node(id="b", label="输出", type="output", x=80, y=260),
        ],
        edges=[Edge(id="e", source="a", target="b")],
    )


def test_health_lists_official_models_and_six_templates() -> None:
    payload = client.get("/health").json()
    assert payload["deepseek_models"] == ["deepseek-v4-flash", "deepseek-v4-pro"]
    assert len(payload["style_templates"]) == 6
    assert payload["style_templates"][0]["id"] == "default"


def test_each_public_theme_changes_native_drawio_colors() -> None:
    diagram = _diagram()
    rendered = []
    for item in public_themes():
        theme = get_theme(item["id"])
        xml = DrawioRenderer(theme).render(diagram)
        assert theme.palette["input"][0] in xml
        assert theme.palette["output"][1] in xml
        rendered.append(xml)
    assert len(set(rendered)) == 6


def test_unknown_model_is_rejected_before_remote_request() -> None:
    response = client.post(
        "/api/v1/diagrams/generate",
        json={"prompt": "测试", "use_default_style": True, "model": "deepseek-v4"},
    )
    assert response.status_code == 422
    assert response.json()["error"] == "unsupported_model"
