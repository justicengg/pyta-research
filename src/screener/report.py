import json
from dataclasses import asdict

from src.screener.screener import ScreenerResult


def result_to_json(result: ScreenerResult) -> str:
    """Serialize a ScreenerResult to a formatted JSON string."""
    data = asdict(result)
    data['asof_date'] = result.asof_date.isoformat()
    return json.dumps(data, ensure_ascii=False, indent=2)
