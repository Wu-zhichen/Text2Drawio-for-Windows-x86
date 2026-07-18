from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import urllib.error
import urllib.request
from copy import deepcopy
from pathlib import Path
from typing import List, Tuple

from PIL import Image

from app.diagram.ir import DiagramIR, Node


class NodeImageError(RuntimeError):
    pass


class NodeImageGenerator:
    """Generate a small cached illustration for a bounded set of major nodes."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        quality: str,
        max_images: int,
        cache_dir: Path,
        timeout_seconds: int = 150,
        concurrency: int = 2,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.quality = quality if quality in {"low", "medium", "high", "auto"} else "low"
        self.max_images = max(1, max_images)
        self.cache_dir = cache_dir
        self.timeout_seconds = timeout_seconds
        self.concurrency = max(1, concurrency)

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def enrich(self, source: DiagramIR) -> Tuple[DiagramIR, List[str]]:
        diagram = deepcopy(source)
        if not self.configured:
            return diagram, ["Node images were requested but OPENAI_API_KEY is not configured."]

        candidates = self._select_nodes(diagram)
        warnings: List[str] = []
        if len([node for node in diagram.nodes if node.type != "note"]) > len(candidates):
            warnings.append(
                f"Generated illustrations for {len(candidates)} major nodes; remaining nodes use vector-only cards."
            )
        semaphore = asyncio.Semaphore(self.concurrency)

        async def generate(node: Node) -> Tuple[Node, str, str]:
            async with semaphore:
                try:
                    data_uri = await asyncio.to_thread(self._generate_or_cached, node, diagram.title)
                    return node, data_uri, ""
                except NodeImageError as exc:
                    return node, "", str(exc)

        results = await asyncio.gather(*(generate(node) for node in candidates))
        for node, data_uri, error in results:
            if data_uri:
                node.image_data = data_uri
                node.image_alt = node.label
                node.width = max(node.width, 260)
                node.height = max(node.height, 110)
            elif error:
                warnings.append(f"Illustration skipped for {node.label}: {error}")
        return diagram, warnings

    def _select_nodes(self, diagram: DiagramIR) -> List[Node]:
        layout = diagram.metadata.get("layout", {})
        raw_levels = layout.get("levels", {}) if isinstance(layout, dict) else {}
        levels = raw_levels if isinstance(raw_levels, dict) else {}
        candidates = [node for node in diagram.nodes if node.type != "note"]
        candidates.sort(key=lambda node: (int(levels.get(node.id, 999)), diagram.nodes.index(node)))
        return candidates[: self.max_images]

    def _generate_or_cached(self, node: Node, diagram_title: str) -> str:
        prompt = self._prompt(node, diagram_title)
        cache_key = hashlib.sha256(f"{self.model}\n{self.quality}\n{prompt}".encode("utf-8")).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.webp"
        if cache_file.is_file():
            return self._data_uri(cache_file.read_bytes())

        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024",
                "quality": self.quality,
                "background": "opaque",
                "output_format": "webp",
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/images/generations",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
            encoded = result["data"][0]["b64_json"]
            raw = base64.b64decode(encoded, validate=True)
        except urllib.error.HTTPError as exc:
            raise NodeImageError(f"image API returned HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise NodeImageError("image API failed or returned invalid image data") from exc

        optimized = self._optimize(raw)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(optimized)
        return self._data_uri(optimized)

    @staticmethod
    def _prompt(node: Node, diagram_title: str) -> str:
        description = node.description.strip() or node.label
        return (
            "Create one publication-quality flat vector pictogram for a scientific diagram node. "
            f"Diagram context: {diagram_title}. Node concept: {node.label}. Meaning: {description}. "
            "One centered symbolic object, minimal geometric line-art, restrained blue-gray and one muted accent color, "
            "pure white solid background, generous empty margin, no border, no card, no arrow, no text, no letters, "
            "no numbers, no watermark, no logo, not photorealistic, not 3D. The icon must remain recognizable at 48 px."
        )

    @staticmethod
    def _optimize(raw: bytes) -> bytes:
        try:
            with Image.open(io.BytesIO(raw)) as image:
                image = image.convert("RGB")
                image.thumbnail((128, 128), Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (128, 128), "white")
                x = (128 - image.width) // 2
                y = (128 - image.height) // 2
                canvas.paste(image, (x, y))
                output = io.BytesIO()
                canvas.save(output, format="WEBP", quality=82, method=6)
                data = output.getvalue()
        except (OSError, ValueError) as exc:
            raise NodeImageError("generated image could not be decoded") from exc
        if len(data) > 500_000:
            raise NodeImageError("optimized image exceeds the size limit")
        return data

    @staticmethod
    def _data_uri(data: bytes) -> str:
        return "data:image/webp;base64," + base64.b64encode(data).decode("ascii")
