"""Connector management endpoints — generate and list data source connector specs."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.deps import verify_api_key

router = APIRouter()
logger = logging.getLogger(__name__)

_CATALOG_PATH = Path(__file__).parent.parent.parent / "sources" / "catalog.json"


# ── request / response models ─────────────────────────────────────────────────

class GenerateSpecRequest(BaseModel):
    doc_text: str
    provider_hint: str = ""


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/connectors/spec/generate", dependencies=[Depends(verify_api_key)])
async def generate_connector_spec(request: GenerateSpecRequest) -> dict[str, Any]:
    """Read API documentation text and auto-generate a ConnectorSpec.

    The LLM parses the documentation to extract base URL, auth type,
    endpoints and field mappings.  Falls back to keyword heuristics if
    the LLM client is not configured.
    """
    try:
        from src.data.connectors.copilot import ConnectorCopilot
        copilot = ConnectorCopilot()
        spec = await copilot.generate_spec(request.doc_text, provider_hint=request.provider_hint)
        return spec.model_dump(mode="json")
    except Exception as exc:
        logger.error("Connector spec generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Connector spec generation failed: {exc}",
        )


@router.get("/connectors/specs", dependencies=[Depends(verify_api_key)])
async def list_connector_specs() -> dict[str, Any]:
    """List all saved connector specs from src/sources/catalog.json."""
    try:
        if not _CATALOG_PATH.exists():
            return {"specs": []}
        catalog: dict = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
        return {"specs": list(catalog.values())}
    except Exception as exc:
        logger.error("Failed to read connector catalog: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read connector catalog: {exc}",
        )
