"""Source connector API — catalog browsing + CRUD management."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

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


class CreateConnectorRequest(BaseModel):
    provider_id: str
    api_key: str


class ValidateRequest(BaseModel):
    provider_id: str
    api_key: str


class ValidateResponse(BaseModel):
    ok: bool
    error: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _enrich(row: dict, catalog: dict) -> ConnectorResponse:
    """Merge DB row with catalog metadata into a response object."""
    provider = catalog.get(row["provider_id"], {})
    return ConnectorResponse(
        id=row["id"],
        provider_id=row["provider_id"],
        title=provider.get("title", row["provider_id"]),
        source_channel=provider.get("source_channel", ""),
        coverage_dimension=provider.get("coverage_dimension", ""),
        cost=provider.get("cost", ""),
        usage_level=provider.get("usage_level", ""),
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
    ok, error = await adapter.validate_connector(body.provider_id, body.api_key)
    return ValidateResponse(ok=ok, error=error)


@router.post("/sources/connectors", response_model=ConnectorResponse, status_code=status.HTTP_201_CREATED)
async def create_connector(body: CreateConnectorRequest) -> ConnectorResponse:
    """Validate connection then persist the connector."""
    if not body.api_key.strip():
        raise HTTPException(status_code=400, detail="api_key cannot be empty")

    try:
        adapter.get_provider(body.provider_id)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body.provider_id!r}")

    ok, error = await adapter.validate_connector(body.provider_id, body.api_key.strip())
    if not ok:
        raise HTTPException(status_code=422, detail=f"连接验证失败: {error}")

    connector_id = store.create_connector(body.provider_id, body.api_key.strip())
    row = store.get_connector(connector_id)
    catalog = adapter.load_catalog()
    return _enrich(row, catalog)


@router.delete("/sources/connectors/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connector(connector_id: str) -> None:
    """Remove a connector."""
    deleted = store.delete_connector(connector_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Connector not found")
