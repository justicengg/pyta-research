"""IngestResult — returned by UploadAgent after parsing a customer data file."""
from __future__ import annotations

from pydantic import BaseModel

from src.data.canonical import CanonicalSecurityData


class IngestResult(BaseModel):
    """Summary of a file-ingest operation."""

    filename: str
    symbol: str
    market: str
    rows_parsed: int
    rows_stored: int
    column_mapping: dict[str, str]   # original_col → canonical_field
    unmapped_columns: list[str]
    quality_score: float             # 0.0 – 1.0
    warnings: list[str]
    canonical_snapshot: CanonicalSecurityData | None = None  # latest row as snapshot
