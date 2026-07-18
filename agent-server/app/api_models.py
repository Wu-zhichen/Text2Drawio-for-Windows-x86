from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AttachmentInput(StrictModel):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(default="application/octet-stream", max_length=120)
    data_base64: str = Field(min_length=1, max_length=70_000_000)


class GenerateRequest(StrictModel):
    prompt: str = Field(min_length=1, max_length=20000)
    use_default_style: bool = False
    current_xml: str = Field(default="", max_length=1_500_000)
    selected_cells: str = Field(default="", max_length=100_000)
    enhance_prompt: bool = True
    generate_node_images: bool = False
    model: str = Field(default="", max_length=80)
    style_template: str = Field(default="default", max_length=80)
    attachments: List[AttachmentInput] = Field(default_factory=list, max_length=10)


class GenerateResponse(StrictModel):
    request_id: str
    diagram_ir: Dict[str, Any]
    drawio_xml: str
    skill_source: str
    warnings: List[str]
    enhanced_prompt: str = ""
    prompt_was_enhanced: bool = False
    model_used: str = ""
    style_template: str = "default"


class PatchRequest(StrictModel):
    diagram_ir: Dict[str, Any]
    operations: List[Dict[str, Any]] = Field(min_length=1, max_length=100)


class ValidateRequest(StrictModel):
    diagram_ir: Dict[str, Any]
