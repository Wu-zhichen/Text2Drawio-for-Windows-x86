from __future__ import annotations

import asyncio
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, replace
from typing import Any, Dict


class DeepSeekError(RuntimeError):
    pass


class _RetryableDeepSeekError(DeepSeekError):
    """A transient failure that is safe to retry without exposing response data."""


@dataclass(frozen=True)
class DeepSeekClient:
    api_key: str
    model: str
    base_url: str
    timeout_seconds: int = 120
    max_retries: int = 1
    max_tokens: int = 8192

    def with_model(self, model: str | None) -> "DeepSeekClient":
        return replace(self, model=(model or self.model).strip())

    async def create_diagram_ir(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if not self.api_key:
            raise DeepSeekError("DeepSeek is not configured")
        return await asyncio.to_thread(
            self._request, system_prompt, user_prompt, self.max_tokens
        )

    async def enhance_diagram_prompt(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise DeepSeekError("DeepSeek is not configured")
        # Prompt enhancement is prose wrapped in one small JSON field; keeping
        # its budget below the Diagram IR budget reduces latency and cost.
        result = await asyncio.to_thread(
            self._request, system_prompt, user_prompt, min(self.max_tokens, 3072)
        )
        enhanced = result.get("enhanced_prompt")
        if not isinstance(enhanced, str) or not enhanced.strip():
            raise DeepSeekError("DeepSeek prompt enhancer returned an invalid response")
        return enhanced.strip()

    def _request(
        self, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> Dict[str, Any]:
        last_error: DeepSeekError | None = None
        for attempt in range(self.max_retries + 1):
            retry_prompt = user_prompt
            if attempt:
                retry_prompt += (
                    "\n\nThis is a retry. Return one complete, non-empty JSON object only; "
                    "do not use Markdown fences or explanatory prose."
                )
            try:
                return self._request_once(system_prompt, retry_prompt, max_tokens)
            except _RetryableDeepSeekError as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(0.75 * (2**attempt), 3.0))
        assert last_error is not None
        raise DeepSeekError(
            f"{last_error} (failed after {self.max_retries + 1} attempts)"
        ) from last_error

    def _request_once(
        self, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> Dict[str, Any]:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw_response = response.read()
        except urllib.error.HTTPError as exc:
            # Do not include request headers/body or remote response, which may echo sensitive data.
            if exc.code in {408, 429, 500, 502, 503, 504}:
                raise _RetryableDeepSeekError(
                    f"DeepSeek temporarily failed with HTTP {exc.code}"
                ) from exc
            raise DeepSeekError(f"DeepSeek request failed with HTTP {exc.code}") from exc
        except TimeoutError as exc:
            raise _RetryableDeepSeekError(
                f"DeepSeek request timed out after {self.timeout_seconds} seconds"
            ) from exc
        except urllib.error.URLError as exc:
            raise _RetryableDeepSeekError("Could not reach the DeepSeek API") from exc

        if not raw_response.strip():
            raise _RetryableDeepSeekError("DeepSeek returned an empty HTTP response")
        try:
            payload = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _RetryableDeepSeekError(
                "DeepSeek returned a non-JSON HTTP response"
            ) from exc

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise DeepSeekError("DeepSeek response did not contain a message") from exc
        finish_reason = payload["choices"][0].get("finish_reason")
        if not isinstance(content, str) or not content.strip():
            raise _RetryableDeepSeekError("DeepSeek returned empty JSON content")
        try:
            return _parse_json_object(content)
        except DeepSeekError as exc:
            if finish_reason == "length":
                raise DeepSeekError(
                    "DeepSeek JSON output was truncated; increase DEEPSEEK_MAX_TOKENS "
                    "or simplify the requested diagram"
                ) from exc
            raise _RetryableDeepSeekError(
                "DeepSeek returned malformed JSON content"
            ) from exc


def _parse_json_object(content: Any) -> Dict[str, Any]:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        raise DeepSeekError("DeepSeek returned an unsupported message type")
    stripped = content.strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        stripped = fence.group(1)
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as exc:
        # Be tolerant of a short preface/suffix despite JSON mode. raw_decode
        # still requires the extracted value itself to be valid JSON.
        start = stripped.find("{")
        if start >= 0:
            try:
                value, _ = json.JSONDecoder().raw_decode(stripped[start:])
            except json.JSONDecodeError:
                raise DeepSeekError("DeepSeek message was not a JSON object") from exc
        else:
            raise DeepSeekError("DeepSeek message was not a JSON object") from exc
    if not isinstance(value, dict):
        raise DeepSeekError("DeepSeek message was not a JSON object")
    return value
