from fastapi.testclient import TestClient
import base64

from app.main import app


client = TestClient(app)


def test_health_does_not_expose_api_key() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "api_key" not in str(body).lower()
    assert ".pdf" in body["attachments"]["supported_extensions"]


def test_generate_requires_default_style_confirmation() -> None:
    response = client.post(
        "/api/v1/diagrams/generate",
        json={
            "prompt": "Input -> Plan -> Output",
            "use_default_style": False,
            "current_xml": "",
            "selected_cells": "",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"] == "style_confirmation_required"


def test_generate_returns_editable_xml_after_confirmation() -> None:
    response = client.post(
        "/api/v1/diagrams/generate",
        json={
            "prompt": "Input -> Plan -> Diagram IR -> Output",
            "use_default_style": True,
            "current_xml": "",
            "selected_cells": "",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["drawio_xml"].startswith("<?xml")
    assert "mxCell" in body["drawio_xml"]
    assert body["diagram_ir"]["nodes"]
    assert body["warnings"]


def test_generate_accepts_local_text_attachment() -> None:
    response = client.post(
        "/api/v1/diagrams/generate",
        json={
            "prompt": "根据附件生成总结示意图",
            "use_default_style": True,
            "attachments": [
                {
                    "filename": "paper.txt",
                    "mime_type": "text/plain",
                    "data_base64": base64.b64encode("研究方法与结论".encode()).decode(),
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["diagram_ir"]["nodes"]


def test_generate_rejects_unsupported_attachment() -> None:
    response = client.post(
        "/api/v1/diagrams/generate",
        json={
            "prompt": "根据附件生成示意图",
            "use_default_style": True,
            "attachments": [
                {
                    "filename": "archive.zip",
                    "mime_type": "application/zip",
                    "data_base64": base64.b64encode(b"not a supported file").decode(),
                }
            ],
        },
    )
    assert response.status_code == 422
    assert response.json()["error"] == "attachment_invalid"
