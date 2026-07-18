from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List

from app.agent.workflow import DiagramAgentWorkflow
from app.diagram.ir import DiagramIR
from app.diagram.patcher import apply_patch
from app.diagram.validator import validate_diagram
from app.documents import DocumentExtractor
from app.layout.engine import LayoutEngine
from app.renderer.drawio import DrawioRenderer


@dataclass
class ServiceResult:
    request_id: str
    diagram_ir: Dict[str, Any]
    drawio_xml: str
    skill_source: str
    warnings: List[str]
    enhanced_prompt: str = ""
    prompt_was_enhanced: bool = False
    model_used: str = ""
    style_template: str = "default"


class DiagramService:
    def __init__(
        self,
        workflow: DiagramAgentWorkflow,
        document_extractor: DocumentExtractor | None = None,
    ) -> None:
        self.workflow = workflow
        self.document_extractor = document_extractor or DocumentExtractor()
        self.layout = LayoutEngine()
        self.renderer = DrawioRenderer()

    async def generate(
        self,
        prompt: str,
        use_default_style: bool,
        current_xml: str = "",
        selected_cells: str = "",
        enhance_prompt: bool = True,
        generate_node_images: bool = False,
        attachments: List[Dict[str, Any]] | None = None,
        model: str = "",
        style_template: str = "default",
    ) -> ServiceResult:
        extracted = self.document_extractor.extract(attachments or [])
        result = await self.workflow.run(
            request=prompt,
            use_default_style=use_default_style,
            current_xml=current_xml,
            selected_cells=selected_cells,
            enhance_prompt=enhance_prompt,
            generate_node_images=generate_node_images,
            attachment_context=extracted.context,
            model=model,
            style_template=style_template,
        )
        return ServiceResult(
            request_id=str(uuid.uuid4()),
            diagram_ir=result.diagram.to_dict(),
            drawio_xml=result.drawio_xml,
            skill_source=result.skill_source,
            warnings=extracted.warnings + result.warnings,
            enhanced_prompt=result.enhanced_prompt,
            prompt_was_enhanced=result.prompt_was_enhanced,
            model_used=result.model_used,
            style_template=result.style_template,
        )

    def patch(self, raw_diagram: Dict[str, Any], operations: List[Dict[str, Any]]) -> ServiceResult:
        diagram = DiagramIR.from_dict(raw_diagram)
        validate_diagram(diagram)
        patched = apply_patch(diagram, operations)
        # Existing positions survive; only newly added or unpositioned nodes are placed.
        laid_out = self.layout.apply(patched, preserve_positions=True)
        return ServiceResult(
            request_id=str(uuid.uuid4()),
            diagram_ir=laid_out.to_dict(),
            drawio_xml=self.renderer.render(laid_out),
            skill_source="existing-diagram",
            warnings=[],
            enhanced_prompt="",
            prompt_was_enhanced=False,
        )

    def validate(self, raw_diagram: Dict[str, Any]) -> Dict[str, Any]:
        diagram = DiagramIR.from_dict(raw_diagram)
        validate_diagram(diagram)
        return {"valid": True, "node_count": len(diagram.nodes), "edge_count": len(diagram.edges)}
