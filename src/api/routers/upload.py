"""Upload endpoints — accept customer market data files and store them canonically."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from src.api.deps import verify_api_key

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload/market-data", dependencies=[Depends(verify_api_key)])
async def upload_market_data(
    file: UploadFile = File(...),
    symbol: str = Form(...),
    market: str = Form(default="US"),
) -> dict[str, Any]:
    """Parse a customer-uploaded data file and store as canonical market data.

    Supported formats: .xlsx, .csv, .md (markdown tables).

    Column headers may be in English or Chinese — the agent will attempt
    automatic mapping using rule-based matching followed by LLM inference
    for unrecognised headers.

    Returns an IngestResult describing how many rows were parsed and stored,
    the column mapping detected, a quality score, and any warnings.
    """
    try:
        file_bytes = await file.read()
        filename = file.filename or "upload"
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {exc}",
        )

    try:
        from src.data.ingest.upload_agent import UploadAgent
        agent = UploadAgent()
        result = await agent.ingest(
            file_bytes=file_bytes,
            filename=filename,
            symbol=symbol.upper(),
            market=market.upper(),
        )
        return result.model_dump(mode="json")
    except Exception as exc:
        logger.error("Market data upload failed for %s/%s: %s", symbol, market, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upload processing failed: {exc}",
        )
