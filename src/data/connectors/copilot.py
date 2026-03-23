"""Connector Copilot — reads API documentation and auto-generates a ConnectorSpec.

Usage::

    from src.data.connectors.copilot import ConnectorCopilot

    copilot = ConnectorCopilot()
    spec = await copilot.generate_spec(doc_text, provider_hint="alpha_vantage")
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from src.data.connectors.connector_spec import AuthType, ConnectorSpec, EndpointSpec
from src.sandbox.llm.client import SandboxLLMClient

logger = logging.getLogger(__name__)

# ── system prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a connector specification generator for a financial data platform.

Given API documentation text, extract the following and return ONLY valid JSON
(no markdown, no explanation, no code fences):

{
  "provider_id": "<snake_case_id>",
  "display_name": "<Human readable name>",
  "base_url": "<https://...>",
  "auth_type": "<api_key_header|api_key_query|bearer|none>",
  "auth_param": "<header or query param name for the key, or null>",
  "endpoints": [
    {
      "name": "<endpoint name>",
      "path": "<path, e.g. /query>",
      "method": "GET",
      "params": {"<param_name>": "<description>"},
      "response_path": "<JSONPath to data array or null>"
    }
  ],
  "field_mapping": {
    "<external field name>": "<canonical field: price|open|close|volume|change_pct|market_cap|pe_ratio|symbol>"
  },
  "notes": "<any caveats or usage notes, or null>"
}

Rules:
- auth_type must be one of: api_key_header, api_key_query, bearer, none
- Map as many external fields as possible to canonical fields
- canonical fields are: price, open, close, high, low, volume, change_pct,
  change_1d_pct, market_cap, pe_ratio, revenue, eps, dividend_yield, symbol, name
- Include at least one endpoint
- provider_id must be snake_case, e.g. alpha_vantage, polygon_io
"""


class ConnectorCopilot:
    """Agent that reads API documentation text and generates a ConnectorSpec."""

    def __init__(self, llm_client: SandboxLLMClient | None = None) -> None:
        self.llm_client = llm_client or SandboxLLMClient()

    async def generate_spec(self, doc_text: str, provider_hint: str = "") -> ConnectorSpec:
        """Parse API documentation text and return a structured ConnectorSpec.

        Falls back to a best-effort heuristic spec when the LLM is not
        configured so callers can still test without credentials.
        """
        if not self.llm_client.enabled:
            logger.warning(
                "LLM client not configured — using heuristic fallback for connector spec"
            )
            return self._heuristic_spec(doc_text, provider_hint)

        user_prompt = (
            f"Provider hint: {provider_hint}\n\n"
            f"API Documentation:\n{doc_text}"
        )
        try:
            response = await self.llm_client.generate_json(_SYSTEM_PROMPT, user_prompt)
            raw: dict = json.loads(response.content)
        except Exception as exc:
            logger.error("LLM call failed for connector copilot: %s — falling back to heuristic", exc)
            return self._heuristic_spec(doc_text, provider_hint)

        return self._build_spec(raw, provider_hint)

    # ── private helpers ────────────────────────────────────────────────────────

    def _build_spec(self, raw: dict, provider_hint: str) -> ConnectorSpec:
        """Validate and construct a ConnectorSpec from the LLM JSON output."""
        # Coerce auth_type string → enum
        auth_type_raw = str(raw.get("auth_type", "none")).lower()
        try:
            auth_type = AuthType(auth_type_raw)
        except ValueError:
            auth_type = AuthType.NONE

        # Parse endpoints list
        endpoints: list[EndpointSpec] = []
        for ep in raw.get("endpoints", []):
            try:
                endpoints.append(EndpointSpec(
                    name=ep.get("name", "unknown"),
                    path=ep.get("path", "/"),
                    method=str(ep.get("method", "GET")).upper(),
                    params=ep.get("params") or {},
                    response_path=ep.get("response_path"),
                ))
            except Exception as exc:
                logger.warning("Skipping malformed endpoint in LLM output: %s", exc)

        provider_id = raw.get("provider_id") or provider_hint or "unknown_provider"
        display_name = raw.get("display_name") or provider_id.replace("_", " ").title()

        return ConnectorSpec(
            provider_id=provider_id,
            display_name=display_name,
            base_url=raw.get("base_url", ""),
            auth_type=auth_type,
            auth_param=raw.get("auth_param"),
            endpoints=endpoints,
            field_mapping=raw.get("field_mapping") or {},
            notes=raw.get("notes"),
            generated_at=datetime.now(timezone.utc),
        )

    def _heuristic_spec(self, doc_text: str, provider_hint: str) -> ConnectorSpec:
        """Best-effort spec built from keyword scanning when the LLM is unavailable."""
        import re

        text = doc_text.lower()

        # Base URL
        url_match = re.search(r"https?://[^\s\"']+", doc_text)
        base_url = url_match.group(0).rstrip("/.,)") if url_match else ""

        # Auth type
        if "apikey" in text or "api_key" in text or "api key" in text:
            if "header" in text:
                auth_type = AuthType.API_KEY_HEADER
                auth_param = "X-Api-Key"
            else:
                auth_type = AuthType.API_KEY_QUERY
                auth_param = "apikey"
        elif "bearer" in text or "authorization" in text:
            auth_type = AuthType.BEARER
            auth_param = "Authorization"
        else:
            auth_type = AuthType.NONE
            auth_param = None

        # Endpoints — look for GET /path patterns
        endpoint_paths = re.findall(r"GET\s+(/[^\s]+)", doc_text, re.IGNORECASE)
        endpoints: list[EndpointSpec] = []
        for path in endpoint_paths[:3]:
            endpoints.append(EndpointSpec(name="query", path=path, method="GET", params={}, response_path=None))
        if not endpoints:
            endpoints = [EndpointSpec(name="query", path="/query", method="GET", params={}, response_path=None)]

        # Field mapping heuristics
        field_mapping: dict[str, str] = {}
        if "price" in text:
            field_mapping["price"] = "price"
        if "volume" in text:
            field_mapping["volume"] = "volume"
        if "change" in text:
            field_mapping["change"] = "change_1d_pct"
        if "symbol" in text:
            field_mapping["symbol"] = "symbol"

        return ConnectorSpec(
            provider_id=provider_hint or "unknown_provider",
            display_name=(provider_hint or "unknown_provider").replace("_", " ").title(),
            base_url=base_url,
            auth_type=auth_type,
            auth_param=auth_param,
            endpoints=endpoints,
            field_mapping=field_mapping,
            notes="Generated by heuristic fallback (LLM not configured)",
            generated_at=datetime.now(timezone.utc),
        )
