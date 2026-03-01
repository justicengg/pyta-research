from datetime import date

from src.fetchers.base import DataFetcher


class BaostockFetcher(DataFetcher):
    source = 'baostock'

    def fetch(
        self,
        symbol: str,
        market: str,
        start: date,
        end: date,
        incremental: bool = True,
        adapter=None,
        last_date: date | None = None,
    ) -> list[dict]:
        start_date = self.incremental_start(last_date, start) if incremental else start
        adapter = adapter or self._default_adapter
        rows = adapter(symbol=symbol, start=start_date, end=end)
        results: list[dict] = []
        seen: set[tuple] = set()
        for row in rows:
            trade_date = self.normalize_date(row['trade_date'])
            key = (symbol, market, trade_date, self.source)
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    'symbol': symbol,
                    'market': market,
                    'trade_date': trade_date,
                    'open': row.get('open'),
                    'high': row.get('high'),
                    'low': row.get('low'),
                    'close': row.get('close'),
                    'volume': row.get('volume'),
                    'adj_factor': row.get('adj_factor'),
                    'source': self.source,
                }
            )
        return results

    @staticmethod
    def _default_adapter(**kwargs):
        raise RuntimeError('baostock adapter not configured in MVP; inject adapter for tests/runtime wrapper')
