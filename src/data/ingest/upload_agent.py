"""UploadAgent — parses Excel / CSV / Markdown files and stores canonical data.

Workflow
--------
1. Detect file format from filename extension (.xlsx, .csv, .md).
2. Parse into a list of row dicts (column → value).
3. Map column names to CanonicalSecurityData fields:
   a. Rule-based matching first (Chinese + English aliases).
   b. LLM fallback for unrecognised column names.
4. Build a CanonicalSecurityData snapshot from the last (most recent) row.
5. Store via CanonicalDataStore with source="customer_upload".
6. Return IngestResult.

Usage::

    from src.data.ingest.upload_agent import UploadAgent

    agent = UploadAgent()
    result = await agent.ingest(file_bytes, "data.csv", "NVDA", "US")
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from src.data.canonical import CanonicalSecurityData, Fundamentals, PriceSnapshot
from src.data.ingest.result import IngestResult
from src.sandbox.llm.client import SandboxLLMClient

logger = logging.getLogger(__name__)

# ── rule-based column alias map ───────────────────────────────────────────────
# Maps lowercase column name (or substring) → canonical field name

_COLUMN_ALIASES: dict[str, str] = {
    # Price fields
    "close": "close",
    "close_price": "close",
    "closing": "close",
    "收盘": "close",
    "收盘价": "close",
    "收盘价格": "close",
    "open": "open",
    "open_price": "open",
    "开盘": "open",
    "开盘价": "open",
    "high": "high",
    "最高": "high",
    "最高价": "high",
    "low": "low",
    "最低": "low",
    "最低价": "low",
    "price": "close",
    "current_price": "close",
    "当前价": "close",
    "最新价": "close",
    "price_close": "close",
    # Volume
    "volume": "volume",
    "vol": "volume",
    "成交量": "volume",
    "交易量": "volume",
    "成交额": "volume",
    # Market cap
    "market_cap": "market_cap",
    "marketcap": "market_cap",
    "市值": "market_cap",
    "总市值": "market_cap",
    "流通市值": "market_cap",
    # Change
    "change": "change_1d_pct",
    "change_pct": "change_1d_pct",
    "change_percent": "change_1d_pct",
    "涨跌幅": "change_1d_pct",
    "日涨跌幅": "change_1d_pct",
    # Fundamentals
    "pe": "pe_ratio",
    "pe_ratio": "pe_ratio",
    "市盈率": "pe_ratio",
    "pb": "pb_ratio",
    "pb_ratio": "pb_ratio",
    "市净率": "pb_ratio",
    "eps": "eps_ttm",
    "每股收益": "eps_ttm",
    "revenue": "revenue_ttm",
    "营收": "revenue_ttm",
    "revenue_ttm": "revenue_ttm",
    # Date — not a canonical field but useful for ordering
    "date": "_date",
    "trade_date": "_date",
    "trading_date": "_date",
    "日期": "_date",
    "交易日": "_date",
    "时间": "_date",
    # Symbol / name
    "symbol": "_symbol",
    "ticker": "_symbol",
    "代码": "_symbol",
    "股票代码": "_symbol",
    "name": "_name",
    "stock_name": "_name",
    "名称": "_name",
    "股票名称": "_name",
}

# LLM prompt for column inference
_COL_SYSTEM_PROMPT = """\
You are a financial data column mapper.
Given a list of column names with sample values, map each column to a canonical field.

Canonical fields: close, open, high, low, volume, market_cap, change_1d_pct,
pe_ratio, pb_ratio, eps_ttm, revenue_ttm, _date, _symbol, _name

Return ONLY valid JSON — a flat object mapping original_column_name → canonical_field.
If a column cannot be mapped, map it to null.
Example: {"收盘价": "close", "成交量": "volume", "备注": null}
"""


def _rule_map_column(col: str) -> str | None:
    """Try to map a column name to a canonical field using the alias table."""
    key = col.strip().lower()
    if key in _COLUMN_ALIASES:
        return _COLUMN_ALIASES[key]
    # Substring matching for composite names
    for alias, field in _COLUMN_ALIASES.items():
        if alias in key or key in alias:
            return field
    return None


def _parse_csv(file_bytes: bytes) -> list[dict[str, str]]:
    """Parse CSV bytes into a list of row dicts."""
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def _parse_xlsx(file_bytes: bytes) -> list[dict[str, str]]:
    """Parse Excel bytes into a list of row dicts."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h) if h is not None else "" for h in rows[0]]
    result: list[dict[str, str]] = []
    for row in rows[1:]:
        result.append({headers[i]: (str(v) if v is not None else "") for i, v in enumerate(row)})
    return result


def _parse_markdown(file_bytes: bytes) -> list[dict[str, str]]:
    """Parse a Markdown table into a list of row dicts."""
    text = file_bytes.decode("utf-8-sig", errors="replace")
    lines = [l.strip() for l in text.splitlines() if l.strip().startswith("|")]
    if len(lines) < 2:
        return []
    def split_row(line: str) -> list[str]:
        return [c.strip() for c in line.strip("|").split("|")]

    headers = split_row(lines[0])
    result: list[dict[str, str]] = []
    for line in lines[2:]:  # skip separator line
        cols = split_row(line)
        if len(cols) == len(headers):
            result.append(dict(zip(headers, cols)))
    return result


def _safe_float(value: Any) -> float | None:
    """Convert a string/number to float, handling common formatting."""
    if value is None or str(value).strip() in ("", "None", "NaN", "nan"):
        return None
    # Strip common suffixes: T (trillion), B (billion), M (million), %
    s = str(value).strip()
    multiplier = 1.0
    if s.endswith("%"):
        s = s[:-1]
        multiplier = 0.01
    elif s.endswith("T"):
        s = s[:-1]
        multiplier = 1e12
    elif s.endswith("B"):
        s = s[:-1]
        multiplier = 1e9
    elif s.endswith("M"):
        s = s[:-1]
        multiplier = 1e6
    # Remove commas
    s = s.replace(",", "")
    try:
        return float(s) * multiplier
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> int | None:
    f = _safe_float(value)
    return int(f) if f is not None else None


def _row_to_snapshot(
    symbol: str,
    market: str,
    col_map: dict[str, str],
    row: dict[str, str],
) -> CanonicalSecurityData:
    """Convert a data row to CanonicalSecurityData using the column mapping."""
    # Invert: canonical_field → value
    field_values: dict[str, str] = {}
    for orig_col, canonical_field in col_map.items():
        if canonical_field and canonical_field in row:
            field_values[canonical_field] = row[orig_col]
        elif orig_col in row:
            field_values[canonical_field] = row[orig_col]

    price = PriceSnapshot(
        current=_safe_float(field_values.get("close")),
        open=_safe_float(field_values.get("open")),
        high_52w=_safe_float(field_values.get("high")),
        low_52w=_safe_float(field_values.get("low")),
        change_1d_pct=_safe_float(field_values.get("change_1d_pct")),
        volume=_safe_int(field_values.get("volume")),
    )

    fundamentals = Fundamentals(
        market_cap=_safe_float(field_values.get("market_cap")),
        pe_ratio=_safe_float(field_values.get("pe_ratio")),
        pb_ratio=_safe_float(field_values.get("pb_ratio")),
        eps_ttm=_safe_float(field_values.get("eps_ttm")),
        revenue_ttm=_safe_float(field_values.get("revenue_ttm")),
    )

    return CanonicalSecurityData(
        symbol=symbol,
        market=market,
        price=price,
        fundamentals=fundamentals,
        fetched_at=datetime.now(timezone.utc),
        source="customer_upload",
        raw_payload={k: v for k, v in row.items() if k not in col_map},
    )


class UploadAgent:
    """Parses customer-uploaded data files and stores them in the canonical data store."""

    def __init__(self, llm_client: SandboxLLMClient | None = None) -> None:
        self.llm_client = llm_client or SandboxLLMClient()

    async def ingest(
        self,
        file_bytes: bytes,
        filename: str,
        symbol: str,
        market: str,
    ) -> IngestResult:
        """Parse file → identify columns → map to canonical → store.

        Supported formats: .xlsx, .csv, .md
        """
        warnings: list[str] = []

        # ── 1. Parse file ──────────────────────────────────────────────────────
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        rows: list[dict[str, str]] = []
        try:
            if ext in ("csv", "txt"):
                rows = _parse_csv(file_bytes)
            elif ext in ("xlsx", "xls"):
                rows = _parse_xlsx(file_bytes)
            elif ext == "md":
                rows = _parse_markdown(file_bytes)
            else:
                # Try CSV as fallback
                warnings.append(f"Unknown extension '{ext}' — attempting CSV parse")
                rows = _parse_csv(file_bytes)
        except Exception as exc:
            logger.error("Failed to parse %s: %s", filename, exc)
            warnings.append(f"Parse error: {exc}")
            rows = []

        rows_parsed = len(rows)
        if rows_parsed == 0:
            return IngestResult(
                filename=filename,
                symbol=symbol,
                market=market,
                rows_parsed=0,
                rows_stored=0,
                column_mapping={},
                unmapped_columns=[],
                quality_score=0.0,
                warnings=warnings + ["No rows parsed from file"],
            )

        # ── 2. Identify column mapping ─────────────────────────────────────────
        columns = list(rows[0].keys())
        col_map: dict[str, str] = {}
        unmapped: list[str] = []

        for col in columns:
            mapped = _rule_map_column(col)
            if mapped is not None:
                # Skip internal meta-fields from the public column_mapping
                if not mapped.startswith("_"):
                    col_map[col] = mapped
            else:
                unmapped.append(col)

        # LLM fallback for unrecognised columns
        if unmapped and self.llm_client.enabled:
            sample_row = rows[0]
            col_samples = {c: sample_row.get(c, "") for c in unmapped[:10]}
            user_prompt = f"Columns with sample values:\n{json.dumps(col_samples, ensure_ascii=False, indent=2)}"
            try:
                response = await self.llm_client.generate_json(_COL_SYSTEM_PROMPT, user_prompt)
                llm_result: dict = json.loads(response.content)
                still_unmapped: list[str] = []
                for col in unmapped:
                    field = llm_result.get(col)
                    if field and not str(field).startswith("_"):
                        col_map[col] = str(field)
                    else:
                        still_unmapped.append(col)
                unmapped = still_unmapped
            except Exception as exc:
                logger.warning("LLM column mapping failed: %s", exc)
                warnings.append(f"LLM column mapping skipped: {exc}")
        elif unmapped:
            warnings.append("LLM not configured — unmapped columns kept as-is")

        # ── 3. Build canonical snapshot from last row ──────────────────────────
        canonical_snapshot: CanonicalSecurityData | None = None
        rows_stored = 0
        try:
            last_row = rows[-1]
            canonical_snapshot = _row_to_snapshot(symbol, market, col_map, last_row)

            # Store via CanonicalDataStore
            from src.data.store import CanonicalDataStore
            from src.db.session import SessionLocal
            store = CanonicalDataStore()
            db_session = SessionLocal()
            try:
                store.upsert(db_session, canonical_snapshot)
                db_session.commit()
                rows_stored = 1
            except Exception as exc:
                db_session.rollback()
                logger.warning("Failed to store canonical snapshot: %s", exc)
                warnings.append(f"DB store failed: {exc}")
            finally:
                db_session.close()
        except Exception as exc:
            logger.error("Failed to build canonical snapshot: %s", exc)
            warnings.append(f"Snapshot build failed: {exc}")

        # ── 4. Quality score ───────────────────────────────────────────────────
        # Score based on how many canonical price fields were mapped
        important_fields = {"close", "volume", "open", "market_cap", "change_1d_pct"}
        mapped_important = important_fields & set(col_map.values())
        quality_score = min(1.0, len(mapped_important) / max(1, len(important_fields)))

        return IngestResult(
            filename=filename,
            symbol=symbol,
            market=market,
            rows_parsed=rows_parsed,
            rows_stored=rows_stored,
            column_mapping=col_map,
            unmapped_columns=unmapped,
            quality_score=quality_score,
            warnings=warnings,
            canonical_snapshot=canonical_snapshot,
        )
