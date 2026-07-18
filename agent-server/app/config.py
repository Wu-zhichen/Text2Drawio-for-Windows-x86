from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


def _as_bool(value: str, default: bool) -> bool:
    if value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    deepseek_api_key: str
    deepseek_model: str
    deepseek_models: Tuple[str, ...]
    deepseek_base_url: str
    deepseek_timeout_seconds: int
    deepseek_max_retries: int
    deepseek_max_tokens: int
    skill_dir: Path
    allowed_origins: Tuple[str, ...]
    allow_offline_fallback: bool
    max_prompt_chars: int
    max_attachment_files: int
    max_attachment_bytes: int
    max_attachment_chars: int
    max_total_attachment_chars: int
    openai_api_key: str
    openai_base_url: str
    node_image_model: str
    node_image_quality: str
    node_image_max_count: int
    node_image_cache_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        root = _project_root()
        raw_skill_dir = os.getenv("TEXT2DRAWIO_SKILL_DIR", ".agents/skills/figure")
        skill_dir = Path(raw_skill_dir)
        if not skill_dir.is_absolute():
            skill_dir = root / skill_dir

        origins = tuple(
            item.strip()
            for item in os.getenv(
                "TEXT2DRAWIO_ALLOWED_ORIGINS",
                "null,http://localhost,https://app.diagrams.net",
            ).split(",")
            if item.strip()
        )
        return cls(
            host=os.getenv("TEXT2DRAWIO_HOST", "127.0.0.1"),
            port=int(os.getenv("TEXT2DRAWIO_PORT", "8765")),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            deepseek_models=tuple(
                item.strip()
                for item in os.getenv(
                    "DEEPSEEK_MODELS", "deepseek-v4-flash,deepseek-v4-pro"
                ).split(",")
                if item.strip()
            ),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            deepseek_timeout_seconds=max(
                30, min(600, int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "120")))
            ),
            deepseek_max_retries=max(
                0, min(4, int(os.getenv("DEEPSEEK_MAX_RETRIES", "1")))
            ),
            deepseek_max_tokens=max(
                1024, min(32768, int(os.getenv("DEEPSEEK_MAX_TOKENS", "8192")))
            ),
            skill_dir=skill_dir.resolve(),
            allowed_origins=origins,
            allow_offline_fallback=_as_bool(
                os.getenv("TEXT2DRAWIO_ALLOW_OFFLINE_FALLBACK", "true"), True
            ),
            max_prompt_chars=max(1000, int(os.getenv("TEXT2DRAWIO_MAX_PROMPT_CHARS", "20000"))),
            max_attachment_files=max(
                1, min(10, int(os.getenv("TEXT2DRAWIO_MAX_ATTACHMENT_FILES", "5")))
            ),
            max_attachment_bytes=max(
                1_000_000,
                min(
                    50 * 1024 * 1024,
                    int(os.getenv("TEXT2DRAWIO_MAX_ATTACHMENT_BYTES", str(15 * 1024 * 1024))),
                ),
            ),
            max_attachment_chars=max(
                2_000, int(os.getenv("TEXT2DRAWIO_MAX_ATTACHMENT_CHARS", "60000"))
            ),
            max_total_attachment_chars=max(
                4_000, int(os.getenv("TEXT2DRAWIO_MAX_TOTAL_ATTACHMENT_CHARS", "120000"))
            ),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            node_image_model=os.getenv("TEXT2DRAWIO_IMAGE_MODEL", "gpt-image-2"),
            node_image_quality=os.getenv("TEXT2DRAWIO_IMAGE_QUALITY", "low"),
            node_image_max_count=max(1, min(12, int(os.getenv("TEXT2DRAWIO_IMAGE_MAX_COUNT", "4")))),
            node_image_cache_dir=(
                root / os.getenv("TEXT2DRAWIO_IMAGE_CACHE_DIR", ".cache/node-images")
            ).resolve(),
        )

    def public_dict(self) -> dict:
        """Return configuration safe for the desktop plugin."""
        return {
            "deepseek_configured": bool(self.deepseek_api_key),
            "deepseek_model": self.deepseek_model,
            "deepseek_models": list(self.deepseek_models),
            "deepseek_timeout_seconds": self.deepseek_timeout_seconds,
            "skill_dir": str(self.skill_dir),
            "offline_fallback": self.allow_offline_fallback,
            "max_prompt_chars": self.max_prompt_chars,
            "max_attachment_files": self.max_attachment_files,
            "max_attachment_bytes": self.max_attachment_bytes,
            "node_image_generation_configured": bool(self.openai_api_key),
            "node_image_model": self.node_image_model,
            "node_image_max_count": self.node_image_max_count,
        }
