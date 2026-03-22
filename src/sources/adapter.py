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


def get_provider(provider_id: str) -> dict[str, Any]:
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


async def validate_connector(provider_id: str, api_key: str) -> tuple[bool, str]:
    """Test connectivity for a provider + key pair.

    Returns (ok, error_message). error_message is empty string on success.
    """
    try:
        provider = get_provider(provider_id)
    except KeyError as e:
        return False, str(e)

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
