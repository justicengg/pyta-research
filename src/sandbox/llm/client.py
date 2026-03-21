"""Minimal OpenAI-compatible async LLM client for sandbox agents."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from src.config.settings import settings


@dataclass
class LLMResponse:
    content: str
    raw: dict[str, Any]
    stub: bool = False


class SandboxLLMClient:
    def __init__(self) -> None:
        self.provider = settings.llm_provider
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url.rstrip("/")
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.model)

    async def generate_json(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if not self.enabled:
            raise RuntimeError("LLM client is not configured")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        content = self._extract_message_text(data)
        content = self._extract_json_text(content)
        json.loads(content)
        return LLMResponse(content=content, raw=data, stub=False)

    def _extract_message_text(self, data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("LLM response missing choices")

        message = choices[0].get("message") or {}
        content = message.get("content", "")

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    if isinstance(item.get("text"), str):
                        text_parts.append(item["text"])
                    elif item.get("type") == "text":
                        text = item.get("text")
                        if isinstance(text, str):
                            text_parts.append(text)
                        elif isinstance(text, dict) and isinstance(text.get("value"), str):
                            text_parts.append(text["value"])
            if text_parts:
                return "".join(text_parts)

        raise ValueError(f"Unsupported LLM content format: {type(content).__name__}")

    def _extract_json_text(self, content: str) -> str:
        stripped = content.strip()
        if not stripped:
            raise ValueError("LLM response content is empty")

        # Fast path: already valid JSON.
        try:
            json.loads(stripped)
            return stripped
        except json.JSONDecodeError:
            pass

        # Common provider pattern: fenced JSON blocks.
        fenced = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", stripped, re.DOTALL | re.IGNORECASE)
        if fenced:
            candidate = fenced.group(1).strip()
            json.loads(candidate)
            return candidate

        # Fallback: scan for the first valid JSON object/array embedded in text.
        decoder = json.JSONDecoder()
        for idx, char in enumerate(stripped):
            if char not in "{[":
                continue
            try:
                obj, end = decoder.raw_decode(stripped[idx:])
            except json.JSONDecodeError:
                continue
            return stripped[idx : idx + end]

        preview = stripped[:300].replace("\n", "\\n")
        raise ValueError(f"Unable to extract JSON from LLM response: {preview}")
