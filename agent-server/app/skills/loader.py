from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


SUPPORTED_REFERENCES = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".pdf", ".drawio"}


class SkillLoadError(RuntimeError):
    pass


class SkillSelectionRequired(RuntimeError):
    pass


@dataclass(frozen=True)
class SkillBundle:
    source: str
    skill_dir: Path
    skill_markdown: str
    preferences: Dict[str, Any]
    style_profile_text: str
    output_modes: str
    figure_rules: str
    reference_files: List[str]
    template_path: Path

    def public_summary(self) -> dict:
        return {
            "source": self.source,
            "skill_dir": str(self.skill_dir),
            "reference_files": self.reference_files,
            "template": str(self.template_path),
            "preferences": self.preferences,
        }


class FigureSkillLoader:
    def __init__(self, skill_dir: Path) -> None:
        self.skill_dir = skill_dir.resolve()

    def load(self, use_default_style: bool = False) -> SkillBundle:
        self._require_tree()
        preferences = _load_yaml(self.skill_dir / "config" / "preferences.yaml")
        user_dir = self.skill_dir / str(preferences.get("user_reference_dir", "style-references/user"))
        default_dir = self.skill_dir / str(
            preferences.get("default_reference_dir", "style-references/default")
        )
        references = _reference_files(user_dir)
        if references:
            source = "user-references"
            selected_references = references
            style_path = default_dir / "style-profile.yaml"
        else:
            if bool(preferences.get("ask_before_default", True)) and not use_default_style:
                raise SkillSelectionRequired(
                    "No custom style reference was found. Confirm use_default_style to use the default scientific profile."
                )
            source = "confirmed-default"
            selected_references = _reference_files(default_dir)
            profile_name = str(
                preferences.get(
                    "default_style_profile", "style-references/default/style-profile.yaml"
                )
            )
            style_path = self.skill_dir / profile_name

        template_name = str(
            preferences.get("drawio_template", "assets/drawio-scientific-template.drawio")
        )
        return SkillBundle(
            source=source,
            skill_dir=self.skill_dir,
            skill_markdown=_read(self.skill_dir / "SKILL.md"),
            preferences=preferences,
            style_profile_text=_read(style_path),
            output_modes=_read(self.skill_dir / "references" / "output-modes.md"),
            figure_rules=_read(self.skill_dir / "references" / "figure-style-and-prompts.md"),
            reference_files=[str(path.relative_to(self.skill_dir)) for path in selected_references],
            template_path=(self.skill_dir / template_name).resolve(),
        )

    def status(self) -> dict:
        self._require_tree()
        preferences = _load_yaml(self.skill_dir / "config" / "preferences.yaml")
        user_dir = self.skill_dir / str(preferences.get("user_reference_dir", "style-references/user"))
        refs = _reference_files(user_dir)
        return {
            "loaded": True,
            "path": str(self.skill_dir),
            "has_user_references": bool(refs),
            "user_reference_files": [str(path.relative_to(self.skill_dir)) for path in refs],
            "default_confirmation_required": bool(preferences.get("ask_before_default", True))
            and not refs,
        }

    def _require_tree(self) -> None:
        required = [
            self.skill_dir / "SKILL.md",
            self.skill_dir / "config" / "preferences.yaml",
            self.skill_dir / "references" / "figure-style-and-prompts.md",
            self.skill_dir / "references" / "output-modes.md",
            self.skill_dir / "assets" / "drawio-scientific-template.drawio",
            self.skill_dir / "style-references" / "default" / "style-profile.yaml",
        ]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise SkillLoadError("figure skill is incomplete: " + ", ".join(missing))


def _reference_files(path: Path) -> List[Path]:
    if not path.is_dir():
        return []
    return sorted(
        item
        for item in path.rglob("*")
        if item.is_file() and not item.name.startswith(".") and item.suffix.lower() in SUPPORTED_REFERENCES
    )


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SkillLoadError(f"cannot read skill file: {path}") from exc


def _load_yaml(path: Path) -> Dict[str, Any]:
    text = _read(path)
    try:
        import yaml  # type: ignore

        value = yaml.safe_load(text)
        return dict(value or {})
    except ImportError:
        # The flat preferences file remains readable before optional dependencies are installed.
        result: Dict[str, Any] = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, raw_value = line.split(":", 1)
            value = raw_value.strip().strip('"').strip("'")
            if value.lower() in {"true", "false"}:
                result[key.strip()] = value.lower() == "true"
            elif value.isdigit():
                result[key.strip()] = int(value)
            else:
                result[key.strip()] = value
        return result

