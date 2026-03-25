"""Source connector API — catalog browsing + CRUD management."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel

import asyncio

from src.api.deps import verify_api_key
from src.sources import adapter, store

router = APIRouter()


# ── Response models ───────────────────────────────────────────────────────────

class ProviderInfo(BaseModel):
    id: str
    title: str
    description: str
    source_channel: str
    coverage_dimension: str
    cost: str
    usage_level: str
    capabilities: list[str]


class ConnectorResponse(BaseModel):
    id: str
    provider_id: str
    title: str
    source_channel: str
    coverage_dimension: str
    cost: str
    usage_level: str
    capabilities: list[str]
    status: str
    error_message: str | None
    last_synced_at: str | None
    created_at: str


class CustomProviderConfig(BaseModel):
    title: str
    base_url: str
    auth_style: str          # query_param | bearer | x_api_key
    auth_param: str          # param name or header name
    validate_path: str = "" # optional — empty means skip validation
    source_channel: str = "custom"
    coverage_dimension: str = "custom"
    cost: str = "custom"
    usage_level: str = "exploratory"
    capabilities: list[str] = []


class CreateConnectorRequest(BaseModel):
    provider_id: str                        # catalog key or "custom"
    api_key: str
    custom_config: CustomProviderConfig | None = None  # required when provider_id == "custom"


class ValidateRequest(BaseModel):
    provider_id: str
    api_key: str
    custom_config: CustomProviderConfig | None = None


class ValidateResponse(BaseModel):
    ok: bool
    error: str


class SourceEventResponse(BaseModel):
    id: str
    connector_id: str
    provider_id: str
    title: str
    summary: str | None
    dimension: str | None
    impact_direction: str
    impact_strength: float
    published_at: str | None
    ingested_at: str
    symbols: list[str]


class SourceEventListResponse(BaseModel):
    total: int
    items: list[SourceEventResponse]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _enrich(row: dict, catalog: dict) -> ConnectorResponse:
    """Merge DB row with catalog metadata (or custom_config) into a response."""
    custom = row.get("custom_config") or {}
    provider = custom if row["provider_id"] == "custom" else catalog.get(row["provider_id"], {})
    return ConnectorResponse(
        id=row["id"],
        provider_id=row["provider_id"],
        title=provider.get("title", row["provider_id"]),
        source_channel=provider.get("source_channel", "custom"),
        coverage_dimension=provider.get("coverage_dimension", "custom"),
        cost=provider.get("cost", "custom"),
        usage_level=provider.get("usage_level", "exploratory"),
        capabilities=provider.get("capabilities", []),
        status=row["status"],
        error_message=row.get("error_message"),
        last_synced_at=row.get("last_synced_at"),
        created_at=row["created_at"],
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/sources/catalog", response_model=list[ProviderInfo])
def get_catalog() -> list[ProviderInfo]:
    """Return all available providers from catalog.json."""
    catalog = adapter.load_catalog()
    return [
        ProviderInfo(id=pid, **{k: v for k, v in info.items()
                                if k in ProviderInfo.model_fields and k != "id"})
        for pid, info in catalog.items()
    ]


@router.get("/sources/connectors", response_model=list[ConnectorResponse])
def list_connectors() -> list[ConnectorResponse]:
    """Return all connected sources. Never returns api_key."""
    catalog = adapter.load_catalog()
    rows = store.list_connectors()
    return [_enrich(row, catalog) for row in rows]


@router.post("/sources/validate", response_model=ValidateResponse)
async def validate_connector(body: ValidateRequest) -> ValidateResponse:
    """Test a provider + api_key pair before saving."""
    custom = body.custom_config.model_dump() if body.custom_config else None
    ok, error = await adapter.validate_connector(body.provider_id, body.api_key, custom)
    return ValidateResponse(ok=ok, error=error)


@router.post("/sources/connectors", response_model=ConnectorResponse, status_code=status.HTTP_201_CREATED)
async def create_connector(body: CreateConnectorRequest) -> ConnectorResponse:
    """Validate connection, persist the connector, then fetch initial events."""
    if not body.api_key.strip():
        raise HTTPException(status_code=400, detail="api_key cannot be empty")

    custom = body.custom_config.model_dump() if body.custom_config else None

    if body.provider_id == "custom" and not custom:
        raise HTTPException(status_code=400, detail="custom_config is required for custom providers")

    try:
        adapter.get_provider(body.provider_id, custom)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body.provider_id!r}")

    ok, error = await adapter.validate_connector(body.provider_id, body.api_key.strip(), custom)
    if not ok:
        raise HTTPException(status_code=422, detail=f"连接验证失败: {error}")

    connector_id = store.create_connector(body.provider_id, body.api_key.strip(), custom)

    events = await adapter.fetch_initial_events(connector_id, body.provider_id, body.api_key.strip(), custom)
    if events:
        store.save_events(events)

    row = store.get_connector(connector_id)
    catalog = adapter.load_catalog()
    return _enrich(row, catalog)


@router.delete("/sources/connectors/{connector_id}")
def delete_connector(connector_id: str) -> Response:
    """Remove connector and all its events."""
    deleted = store.delete_connector(connector_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Connector not found")
    store.delete_events_by_connector(connector_id)
    return Response(status_code=204)


@router.get("/sources/events", response_model=SourceEventListResponse, dependencies=[Depends(verify_api_key)])
def list_events(
    symbol: str | None = None,
    since: datetime | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> SourceEventListResponse:
    """Return recent source events, optionally filtered by ticker."""
    effective_since = since or (datetime.now(timezone.utc) - timedelta(hours=24))
    total, rows = store.list_events(
        limit=limit,
        symbol=symbol,
        since=effective_since,
    )
    return SourceEventListResponse(
        total=total,
        items=[SourceEventResponse(**row) for row in rows],
    )
