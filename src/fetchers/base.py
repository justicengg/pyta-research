from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta


class DataFetcher(ABC):
    source: str

    @abstractmethod
    def fetch(self, **kwargs) -> list[dict]:
        raise NotImplementedError

    @staticmethod
    def incremental_start(last_date: date | None, requested_start: date) -> date:
        if last_date is None:
            return requested_start
        return max(requested_start, last_date + timedelta(days=1))

    @staticmethod
    def normalize_date(value: str | date | datetime) -> date:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        return datetime.fromisoformat(value).date()
