"""Portfolio report serializer.

Converts a PortfolioSnapshot dataclass to a JSON string suitable for
file output or API responses.
"""
from __future__ import annotations

import json
from dataclasses import asdict

from src.types import PortfolioSnapshot


def snapshot_to_json(snapshot: PortfolioSnapshot, indent: int = 2) -> str:
    """Serialize a PortfolioSnapshot to a JSON string.

    The ``snapshot_date`` field (a ``datetime.date``) is converted to an
    ISO-8601 string.  All other non-serialisable values fall back to
    ``str()`` via the *default* parameter of :func:`json.dumps`.
    """
    data = asdict(snapshot)
    data['snapshot_date'] = snapshot.snapshot_date.isoformat()
    return json.dumps(data, indent=indent, default=str)
