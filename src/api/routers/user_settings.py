"""User settings API — LLM configuration management."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.api import settings_store

router = APIRouter()


class LLMConfigRequest(BaseModel):
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = ""
    timeout_seconds: float = 60.0   # reasoning models need 30-60 s


class LLMConfigStatus(BaseModel):
    configured: bool
    base_url: str
    model: str
    timeout_seconds: float


@router.post("/settings/llm", status_code=status.HTTP_204_NO_CONTENT)
def save_llm_config(body: LLMConfigRequest) -> None:
    """Save LLM config. The API key is stored server-side only and never returned."""
    if not body.api_key.strip():
        raise HTTPException(status_code=400, detail="api_key cannot be empty")
    settings_store.put("llm_api_key", body.api_key.strip())
    settings_store.put("llm_base_url", body.base_url.strip())
    settings_store.put("llm_model", body.model.strip())
    settings_store.put("llm_timeout_seconds", str(body.timeout_seconds))


@router.get("/settings/llm/status", response_model=LLMConfigStatus)
def get_llm_status() -> LLMConfigStatus:
    """Return LLM config status. Never returns the actual API key."""
    api_key = settings_store.get("llm_api_key")
    base_url = settings_store.get("llm_base_url") or "https://api.openai.com/v1"
    model = settings_store.get("llm_model") or ""
    timeout_raw = settings_store.get("llm_timeout_seconds")
    timeout = float(timeout_raw) if timeout_raw else settings.llm_timeout_seconds
    return LLMConfigStatus(
        configured=bool(api_key),
        base_url=base_url,
        model=model,
        timeout_seconds=timeout,
    )
