import json
from dataclasses import asdict

from src.types import QualityReport


def report_to_json(report: QualityReport) -> str:
    return json.dumps(asdict(report), ensure_ascii=False, indent=2)
