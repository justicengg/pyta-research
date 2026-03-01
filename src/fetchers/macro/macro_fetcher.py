from datetime import date

import requests

from src.config.settings import settings
from src.fetchers.base import DataFetcher


FREQ_MAP = {'D': 'day', 'W': 'week', 'M': 'month'}


class MacroFetcher(DataFetcher):
    source = 'macro'

    def fetch(
        self,
        series: str,
        market: str,
        source: str,
        start: date,
        end: date,
        incremental: bool = True,
        adapter=None,
        last_date: date | None = None,
    ) -> list[dict]:
        start_date = self.incremental_start(last_date, start) if incremental else start
        adapter = adapter or (self._fred_adapter if source == 'fred' else self._baostock_macro_adapter)
        rows = adapter(series=series, start=start_date, end=end)
        results = []
        seen: set[tuple] = set()
        for row in rows:
            obs_date = self.normalize_date(row['obs_date'])
            key = (series, market, obs_date, source)
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    'series_code': series,
                    'market': market,
                    'obs_date': obs_date,
                    'value': row.get('value'),
                    'frequency': self._normalize_frequency(row.get('frequency')),
                    'source': source,
                }
            )
        return results

    @staticmethod
    def _normalize_frequency(freq: str | None) -> str | None:
        if freq is None:
            return None
        return FREQ_MAP.get(freq, freq.lower())

    @staticmethod
    def _fred_adapter(series: str, start: date, end: date):
        if not settings.fred_api_key:
            raise RuntimeError('FRED_API_KEY is required for fred source')
        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id': series,
            'api_key': settings.fred_api_key,
            'file_type': 'json',
            'observation_start': start.isoformat(),
            'observation_end': end.isoformat(),
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json().get('observations', [])
        return [
            {'obs_date': item['date'], 'value': None if item['value'] == '.' else float(item['value']), 'frequency': 'M'}
            for item in data
        ]

    @staticmethod
    def _baostock_macro_adapter(**kwargs):
        raise RuntimeError('baostock macro adapter not configured in MVP; inject adapter for tests/runtime wrapper')
