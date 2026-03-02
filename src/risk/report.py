"""Serialise RiskReport to JSON."""
from __future__ import annotations

import json
from dataclasses import asdict

from src.types import RiskReport


def report_to_json(report: RiskReport, indent: int = 2) -> str:
    """Return a JSON string representation of *report*.

    ``asof`` (a ``date`` object) is serialised as an ISO-8601 string.
    All other non-serialisable values fall back to ``str()``.
    """
    data = asdict(report)
    data['asof'] = report.asof.isoformat()
    return json.dumps(data, indent=indent, default=str)
