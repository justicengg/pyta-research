from datetime import date

import yfinance as yf

from src.fetchers.base import DataFetcher


class YFinanceFetcher(DataFetcher):
    source = 'yfinance'

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
    def _default_adapter(symbol: str, start: date, end: date) -> list[dict]:
        hist = yf.Ticker(symbol).history(start=start.isoformat(), end=end.isoformat(), auto_adjust=False)
        rows = []
        for idx, row in hist.iterrows():
            rows.append(
                {
                    'trade_date': idx.date(),
                    'open': float(row['Open']) if row['Open'] is not None else None,
                    'high': float(row['High']) if row['High'] is not None else None,
                    'low': float(row['Low']) if row['Low'] is not None else None,
                    'close': float(row['Close']) if row['Close'] is not None else None,
                    'volume': float(row['Volume']) if row['Volume'] is not None else None,
                    'adj_factor': None,
                }
            )
        return rows
