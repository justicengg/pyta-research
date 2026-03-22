"""Generic source connector adapter.

Adding a new provider = add an entry to catalog.json only.
No code changes required for standard auth styles.

Supported auth_style values:
  query_param  — appends ?{auth_param}={key} to the URL
  bearer       — adds Authorization: Bearer {key} header
  x_api_key    — adds {auth_param}: {key} header (e.g. X-Api-Key)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

_CATALOG_PATH = Path(__file__).parent / "catalog.json"
_TIMEOUT = 8.0  # seconds


def load_catalog() -> dict[str, Any]:
    return json.loads(_CATALOG_PATH.read_text())


def get_provider(provider_id: str, custom_config: dict | None = None) -> dict[str, Any]:
    """Return provider config from catalog, or from custom_config for custom providers."""
    if provider_id == "custom":
        if not custom_config:
            raise KeyError("Custom provider requires custom_config")
        return custom_config
    catalog = load_catalog()
    if provider_id not in catalog:
        raise KeyError(f"Unknown provider: {provider_id!r}")
    return catalog[provider_id]


def _build_auth(
    auth_style: str,
    auth_param: str,
    api_key: str,
) -> tuple[dict[str, str], dict[str, str]]:
    """Return (headers, params) tuple for the given auth style."""
    if auth_style == "query_param":
        return {}, {auth_param: api_key}
    if auth_style == "bearer":
        return {"Authorization": f"Bearer {api_key}"}, {}
    if auth_style == "x_api_key":
        return {auth_param: api_key}, {}
    raise ValueError(f"Unsupported auth_style: {auth_style!r}")


async def fetch_initial_events(
    connector_id: str,
    provider_id: str,
    api_key: str,
    custom_config: dict | None = None,
) -> list[dict]:
    """Fetch the first batch of events from a newly connected source.

    Returns a list of dicts ready for store.save_events().
    Returns empty list on any error (non-fatal — connector is already saved).
    """
    try:
        provider = get_provider(provider_id)
    except KeyError:
        return []

    headers, params = _build_auth(
        provider["auth_style"], provider["auth_param"], api_key
    )
    base = provider["base_url"]
    now = __import__("datetime").datetime.utcnow().isoformat()

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            if provider_id == "gnews":
                resp = await client.get(
                    f"{base}/top-headlines",
                    headers=headers,
                    params={**params, "max": 10, "lang": "en"},
                )
                if resp.status_code != 200:
                    return []
                articles = resp.json().get("articles", [])
                return [
                    {
                        "id": f"{connector_id}_{i}_{a.get('publishedAt', now)}",
                        "connector_id": connector_id,
                        "provider_id": provider_id,
                        "title": a.get("title", ""),
                        "summary": a.get("description", ""),
                        "dimension": "event_driven",
                        "impact_direction": "neutral",
                        "impact_strength": 0.5,
                        "published_at": a.get("publishedAt"),
                        "ingested_at": now,
                    }
                    for i, a in enumerate(articles)
                    if a.get("title")
                ]

            if provider_id == "finnhub":
                import time
                to_ts = int(time.time())
                from_ts = to_ts - 7 * 24 * 3600  # last 7 days
                resp = await client.get(
                    f"{base}/company-news",
                    headers=headers,
                    params={**params, "symbol": "0700.HK", "from": str(__import__("datetime").date.fromtimestamp(from_ts)), "to": str(__import__("datetime").date.fromtimestamp(to_ts))},
                )
                if resp.status_code != 200:
                    return []
                articles = resp.json()[:10]
                return [
                    {
                        "id": f"{connector_id}_{a.get('id', i)}",
                        "connector_id": connector_id,
                        "provider_id": provider_id,
                        "title": a.get("headline", ""),
                        "summary": a.get("summary", ""),
                        "dimension": "fundamental_research",
                        "impact_direction": "neutral",
                        "impact_strength": 0.5,
                        "published_at": str(__import__("datetime").datetime.fromtimestamp(a["datetime"]).isoformat()) if a.get("datetime") else None,
                        "ingested_at": now,
                    }
                    for i, a in enumerate(articles)
                    if a.get("headline")
                ]

            if provider_id == "newsapi":
                resp = await client.get(
                    f"{base}/top-headlines",
                    headers=headers,
                    params={**params, "pageSize": 10, "language": "en"},
                )
                if resp.status_code != 200:
                    return []
                articles = resp.json().get("articles", [])
                return [
                    {
                        "id": f"{connector_id}_{i}_{a.get('publishedAt', now)}",
                        "connector_id": connector_id,
                        "provider_id": provider_id,
                        "title": a.get("title", ""),
                        "summary": a.get("description", ""),
                        "dimension": "media_sentiment",
                        "impact_direction": "neutral",
                        "impact_strength": 0.5,
                        "published_at": a.get("publishedAt"),
                        "ingested_at": now,
                    }
                    for i, a in enumerate(articles)
                    if a.get("title")
                ]

    except Exception:
        pass

    return []


async def validate_connector(
    provider_id: str,
    api_key: str,
    custom_config: dict | None = None,
) -> tuple[bool, str]:
    """Test connectivity for a provider + key pair.

    Returns (ok, error_message). error_message is empty string on success.
    Custom providers with no validate_path skip validation and return True.
    """
    try:
        provider = get_provider(provider_id, custom_config)
    except KeyError as e:
        return False, str(e)

    # Custom providers may omit validate_path — skip validation
    if not provider.get("validate_path"):
        return True, ""

    url = provider["base_url"] + provider["validate_path"]
    headers, params = _build_auth(
        provider["auth_style"], provider["auth_param"], api_key
    )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=headers, params=params)
        if resp.status_code == 200:
            return True, ""
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except httpx.TimeoutException:
        return False, "连接超时，请检查网络或 API 地址"
    except Exception as exc:
        return False, str(exc)
