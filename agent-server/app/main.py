from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent.deepseek import DeepSeekClient, DeepSeekError
from app.agent.workflow import DiagramAgentWorkflow
from app.api_models import GenerateRequest, GenerateResponse, PatchRequest, ValidateRequest
from app.config import Settings
from app.diagram.patcher import PatchError
from app.diagram.validator import DiagramValidationError
from app.documents import AttachmentError, DocumentExtractor, SUPPORTED_ATTACHMENT_EXTENSIONS
from app.images.generator import NodeImageGenerator
from app.service import DiagramService
from app.skills.loader import FigureSkillLoader, SkillLoadError, SkillSelectionRequired
from app.themes import get_theme, public_themes


settings = Settings.from_env()
skill_loader = FigureSkillLoader(settings.skill_dir)
workflow = DiagramAgentWorkflow(
    skill_loader=skill_loader,
    deepseek=DeepSeekClient(
        api_key=settings.deepseek_api_key,
        model=settings.deepseek_model,
        base_url=settings.deepseek_base_url,
        timeout_seconds=settings.deepseek_timeout_seconds,
        max_retries=settings.deepseek_max_retries,
        max_tokens=settings.deepseek_max_tokens,
    ),
    allow_offline_fallback=settings.allow_offline_fallback,
    image_generator=NodeImageGenerator(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.node_image_model,
        quality=settings.node_image_quality,
        max_images=settings.node_image_max_count,
        cache_dir=settings.node_image_cache_dir,
    ),
)
document_extractor = DocumentExtractor(
    max_files=settings.max_attachment_files,
    max_file_bytes=settings.max_attachment_bytes,
    max_chars_per_file=settings.max_attachment_chars,
    max_total_chars=settings.max_total_attachment_chars,
)
service = DiagramService(workflow, document_extractor=document_extractor)

app = FastAPI(
    title="Text2Draw.io Agent Server",
    version="1.0.0",
    description="Local natural-language to editable draw.io API",
    docs_url="/docs",
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(SkillSelectionRequired)
async def style_confirmation_required(_: Request, exc: SkillSelectionRequired) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": "style_confirmation_required",
            "message": str(exc),
            "action": "Retry with use_default_style=true or add a supported file to style-references/user.",
        },
    )


@app.exception_handler(DiagramValidationError)
async def invalid_diagram(_: Request, exc: DiagramValidationError) -> JSONResponse:
    summary = "; ".join(exc.errors[:4])
    return JSONResponse(
        status_code=422,
        content={
            "error": "invalid_diagram_ir",
            "message": f"Diagram IR validation failed: {summary}",
            "details": exc.errors,
        },
    )


@app.exception_handler(PatchError)
async def invalid_patch(_: Request, exc: PatchError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": "invalid_patch", "message": str(exc)})


@app.exception_handler(DeepSeekError)
async def deepseek_failure(_: Request, exc: DeepSeekError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"error": "planner_failed", "message": str(exc)})


@app.exception_handler(SkillLoadError)
async def skill_failure(_: Request, exc: SkillLoadError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": "skill_load_failed", "message": str(exc)})


@app.exception_handler(AttachmentError)
async def attachment_failure(_: Request, exc: AttachmentError) -> JSONResponse:
    return JSONResponse(
        status_code=422, content={"error": "attachment_invalid", "message": str(exc)}
    )


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "text2drawio-agent-server",
        "version": "1.0.0",
        "skill": skill_loader.status(),
        "deepseek_configured": bool(settings.deepseek_api_key),
        "deepseek_model": settings.deepseek_model,
        "deepseek_models": list(settings.deepseek_models),
        "style_templates": public_themes(),
        "node_image_generation_configured": bool(settings.openai_api_key),
        "attachments": {
            "supported_extensions": list(SUPPORTED_ATTACHMENT_EXTENSIONS),
            "max_files": settings.max_attachment_files,
            "max_file_bytes": settings.max_attachment_bytes,
        },
    }


@app.get("/api/v1/config")
def public_config() -> dict:
    return settings.public_dict()


@app.get("/api/v1/skill")
def skill_status() -> dict:
    return skill_loader.status()


@app.post("/api/v1/diagrams/generate", response_model=GenerateResponse)
async def generate_diagram(payload: GenerateRequest) -> GenerateResponse:
    if len(payload.prompt) > settings.max_prompt_chars:
        return JSONResponse(
            status_code=413,
            content={"error": "prompt_too_large", "message": "Prompt exceeds configured limit"},
        )
    requested_model = payload.model.strip() or settings.deepseek_model
    if requested_model not in settings.deepseek_models:
        return JSONResponse(
            status_code=422,
            content={"error": "unsupported_model", "message": "请选择服务配置中允许的 DeepSeek 模型"},
        )
    result = await service.generate(
        prompt=payload.prompt,
        use_default_style=payload.use_default_style,
        current_xml=payload.current_xml,
        selected_cells=payload.selected_cells,
        enhance_prompt=payload.enhance_prompt,
        generate_node_images=payload.generate_node_images,
        attachments=[attachment.model_dump() for attachment in payload.attachments],
        model=requested_model,
        style_template=get_theme(payload.style_template).id,
    )
    return GenerateResponse(
        request_id=result.request_id,
        diagram_ir=result.diagram_ir,
        drawio_xml=result.drawio_xml,
        skill_source=result.skill_source,
        warnings=result.warnings,
        enhanced_prompt=result.enhanced_prompt,
        prompt_was_enhanced=result.prompt_was_enhanced,
        model_used=result.model_used,
        style_template=result.style_template,
    )


@app.post("/api/v1/diagrams/patch", response_model=GenerateResponse)
def patch_diagram(payload: PatchRequest) -> GenerateResponse:
    result = service.patch(payload.diagram_ir, payload.operations)
    return GenerateResponse(
        request_id=result.request_id,
        diagram_ir=result.diagram_ir,
        drawio_xml=result.drawio_xml,
        skill_source=result.skill_source,
        warnings=result.warnings,
        enhanced_prompt=result.enhanced_prompt,
        prompt_was_enhanced=result.prompt_was_enhanced,
        model_used=result.model_used,
        style_template=result.style_template,
    )


@app.post("/api/v1/diagrams/validate")
def validate_ir(payload: ValidateRequest) -> dict:
    return service.validate(payload.diagram_ir)
