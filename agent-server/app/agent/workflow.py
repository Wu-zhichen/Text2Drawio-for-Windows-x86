from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from app.agent.deepseek import DeepSeekClient, DeepSeekError
from app.agent.offline import plan_offline
from app.agent.prompts import (
    build_enhancer_system_prompt,
    build_enhancer_user_prompt,
    build_repair_system_prompt,
    build_repair_user_prompt,
    build_system_prompt,
    build_user_prompt,
    enhance_prompt_offline,
)
from app.diagram.ir import DiagramIR
from app.diagram.normalizer import normalize_generated_ir
from app.diagram.validator import DiagramValidationError, validate_diagram
from app.layout.engine import LayoutEngine
from app.images.generator import NodeImageGenerator
from app.renderer.drawio import DrawioRenderer
from app.skills.loader import FigureSkillLoader
from app.themes import get_theme


@dataclass
class GenerationResult:
    diagram: DiagramIR
    drawio_xml: str
    skill_source: str
    warnings: List[str]
    enhanced_prompt: str
    prompt_was_enhanced: bool
    model_used: str
    style_template: str


class DiagramAgentWorkflow:
    """Single-agent workflow: skill -> plan -> validate -> layout -> render."""

    def __init__(
        self,
        skill_loader: FigureSkillLoader,
        deepseek: DeepSeekClient,
        allow_offline_fallback: bool = True,
        image_generator: NodeImageGenerator | None = None,
    ) -> None:
        self.skill_loader = skill_loader
        self.deepseek = deepseek
        self.allow_offline_fallback = allow_offline_fallback
        self.image_generator = image_generator

    async def run(
        self,
        request: str,
        use_default_style: bool,
        current_xml: str = "",
        selected_cells: str = "",
        enhance_prompt: bool = True,
        generate_node_images: bool = False,
        attachment_context: str = "",
        model: str = "",
        style_template: str = "default",
    ) -> GenerationResult:
        skill = self.skill_loader.load(use_default_style=use_default_style)
        client = (
            self.deepseek.with_model(model)
            if hasattr(self.deepseek, "with_model")
            else self.deepseek
        )
        theme = get_theme(style_template)
        layout = LayoutEngine(
            margin_x=theme.margin_x, margin_y=theme.margin_y, layer_gap=theme.layer_gap,
            row_gap=theme.row_gap, component_gap=theme.component_gap,
        )
        renderer = DrawioRenderer(theme)
        warnings: List[str] = []
        effective_request = request
        prompt_was_enhanced = False
        if enhance_prompt:
            if client.api_key:
                try:
                    effective_request = await client.enhance_diagram_prompt(
                        build_enhancer_system_prompt(skill),
                        build_enhancer_user_prompt(request, attachment_context),
                    )
                    prompt_was_enhanced = True
                except DeepSeekError:
                    warnings.append("Prompt enhancement failed; continued with the original request.")
            else:
                effective_request = enhance_prompt_offline(request)
                prompt_was_enhanced = True

        if client.api_key:
            # A successful enhancer has already distilled the attachment into a
            # bounded professional specification. If enhancement was disabled
            # or failed, provide the extracted source directly to the planner.
            planner_attachment_context = "" if prompt_was_enhanced else attachment_context
            raw = await client.create_diagram_ir(
                build_system_prompt(skill),
                build_user_prompt(
                    effective_request,
                    current_xml=current_xml,
                    selected_cells=selected_cells,
                    attachment_context=planner_attachment_context,
                ),
            )
        elif self.allow_offline_fallback:
            # The offline planner extracts arrow-separated labels literally; keep
            # its structural input concise while still returning the enhanced spec.
            raw = plan_offline(request)
            warnings.append(
                "DeepSeek is not configured; returned an offline deterministic draft."
            )
            if attachment_context:
                warnings.append(
                    "Attachments were extracted, but offline draft mode cannot analyze their content."
                )
        else:
            raise DeepSeekError("DeepSeek is not configured and offline fallback is disabled")

        normalized_raw, normalization_warnings = normalize_generated_ir(raw)
        warnings.extend(normalization_warnings)
        diagram = DiagramIR.from_dict(normalized_raw)
        try:
            validate_diagram(diagram)
        except DiagramValidationError as initial_error:
            if not client.api_key:
                raise
            repaired_raw = await client.create_diagram_ir(
                build_repair_system_prompt(),
                build_repair_user_prompt(effective_request, raw, initial_error.errors),
            )
            normalized_repair, repair_warnings = normalize_generated_ir(repaired_raw)
            warnings.append("DeepSeek repaired Diagram IR after initial validation failed.")
            warnings.extend(repair_warnings)
            diagram = DiagramIR.from_dict(normalized_repair)
            validate_diagram(diagram)
        laid_out = layout.apply(diagram, preserve_positions=True)
        if generate_node_images:
            if self.image_generator is None:
                warnings.append("Node images were requested but no image generator is configured.")
            else:
                laid_out, image_warnings = await self.image_generator.enrich(laid_out)
                warnings.extend(image_warnings)
                # Image cards are slightly wider; recompute the symmetric tree
                # after enrichment so icons cannot disturb alignment or spacing.
                laid_out = layout.apply(laid_out, preserve_positions=False)
        validate_diagram(laid_out)
        return GenerationResult(
            diagram=laid_out,
            drawio_xml=renderer.render(laid_out),
            skill_source=skill.source,
            warnings=warnings,
            enhanced_prompt=effective_request,
            prompt_was_enhanced=prompt_was_enhanced,
            model_used=getattr(client, "model", model or "configured-default"),
            style_template=theme.id,
        )


def build_langgraph(workflow: DiagramAgentWorkflow):
    """Expose the same workflow through LangGraph when the optional dependency is installed."""
    try:
        from langgraph.graph import END, StateGraph  # type: ignore
    except ImportError:
        return None

    async def generate(state: Dict[str, Any]) -> Dict[str, Any]:
        result = await workflow.run(
            request=state["request"],
            use_default_style=state.get("use_default_style", False),
            current_xml=state.get("current_xml", ""),
            selected_cells=state.get("selected_cells", ""),
            enhance_prompt=state.get("enhance_prompt", True),
            generate_node_images=state.get("generate_node_images", False),
            attachment_context=state.get("attachment_context", ""),
            model=state.get("model", ""),
            style_template=state.get("style_template", "default"),
        )
        return {
            **state,
            "diagram_ir": result.diagram.to_dict(),
            "drawio_xml": result.drawio_xml,
            "skill_source": result.skill_source,
            "warnings": result.warnings,
            "enhanced_prompt": result.enhanced_prompt,
            "prompt_was_enhanced": result.prompt_was_enhanced,
            "model_used": result.model_used,
            "style_template": result.style_template,
        }

    graph = StateGraph(dict)
    graph.add_node("generate_diagram", generate)
    graph.set_entry_point("generate_diagram")
    graph.add_edge("generate_diagram", END)
    return graph.compile()
