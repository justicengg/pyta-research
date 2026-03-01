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
    def _default_adapter(symbol: str, start: date, end: date) -> list[dict]:
        try:
            import baostock as bs
        except ImportError:
            raise RuntimeError('baostock package required: pip install baostock')

        def _safe_float(v: str) -> float | None:
            try:
                return float(v) if v else None
            except (ValueError, TypeError):
                return None

        lg = bs.login()
        try:
            rs = bs.query_history_k_data_plus(
                symbol,
                'date,open,high,low,close,volume',
                start_date=start.isoformat(),
                end_date=end.isoformat(),
                frequency='d',
                adjustflag='3',  # 后复权
            )
            rows = []
            while rs.error_code == '0' and rs.next():
                d = dict(zip(rs.fields, rs.get_row_data()))
                rows.append(
                    {
                        'trade_date': d['date'],
                        'open': _safe_float(d.get('open')),
                        'high': _safe_float(d.get('high')),
                        'low': _safe_float(d.get('low')),
                        'close': _safe_float(d.get('close')),
                        'volume': _safe_float(d.get('volume')),
                        'adj_factor': None,
                    }
                )
            return rows
        finally:
            bs.logout()
