from datetime import date, timedelta

from src.fetchers.base import DataFetcher


class FundamentalFetcher(DataFetcher):
    source = 'fundamental'

    def fetch(
        self,
        symbol: str,
        market: str,
        asof: date,
        incremental: bool = True,
        adapter=None,
        last_publish_date: date | None = None,
    ) -> list[dict]:
        adapter = adapter or self._default_adapter
        rows = adapter(symbol=symbol, market=market, asof=asof)
        results: list[dict] = []
        seen: set[tuple] = set()
        for row in rows:
            publish_date = self.normalize_date(row['publish_date'])
            report_period = self.normalize_date(row['report_period'])
            if publish_date > asof:
                continue
            if incremental and last_publish_date and publish_date <= last_publish_date:
                continue
            key = (symbol, market, report_period, publish_date, self.source)
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    'symbol': symbol,
                    'market': market,
                    'report_period': report_period,
                    'publish_date': publish_date,
                    'roe': row.get('roe'),
                    'revenue': row.get('revenue'),
                    'net_profit': row.get('net_profit'),
                    'debt_ratio': row.get('debt_ratio'),
                    'operating_cashflow': row.get('operating_cashflow'),
                    'source': self.source,
                }
            )
        return results

    @staticmethod
    def _default_adapter(symbol: str, market: str, asof: date) -> list[dict]:
        try:
            import baostock as bs
        except ImportError:
            raise RuntimeError('baostock package required: pip install baostock')

        def _safe_float(v: str) -> float | None:
            try:
                return float(v) if v else None
            except (ValueError, TypeError):
                return None

        def _quarters_up_to(d: date, n: int = 8) -> list[tuple[int, int]]:
            q = (d.month - 1) // 3 + 1
            result, y, cur_q = [], d.year, q
            for _ in range(n):
                result.append((y, cur_q))
                cur_q -= 1
                if cur_q == 0:
                    cur_q, y = 4, y - 1
            return result

        lg = bs.login()
        try:
            rows = []
            seen_periods: set[str] = set()
            for year, quarter in _quarters_up_to(asof):
                profit_rs = bs.query_profit_data(code=symbol, year=year, quarter=quarter)
                balance_rs = bs.query_balance_data(code=symbol, year=year, quarter=quarter)
                cash_rs = bs.query_cash_flow_data(code=symbol, year=year, quarter=quarter)

                profit_map: dict[str, dict] = {}
                while profit_rs.error_code == '0' and profit_rs.next():
                    d = dict(zip(profit_rs.fields, profit_rs.get_row_data()))
                    profit_map[d['statDate']] = d

                balance_map: dict[str, dict] = {}
                while balance_rs.error_code == '0' and balance_rs.next():
                    d = dict(zip(balance_rs.fields, balance_rs.get_row_data()))
                    balance_map[d['statDate']] = d

                cash_map: dict[str, dict] = {}
                while cash_rs.error_code == '0' and cash_rs.next():
                    d = dict(zip(cash_rs.fields, cash_rs.get_row_data()))
                    cash_map[d['statDate']] = d

                for stat_date, p in profit_map.items():
                    if stat_date in seen_periods:
                        continue
                    seen_periods.add(stat_date)
                    b = balance_map.get(stat_date, {})
                    c = cash_map.get(stat_date, {})
                    # baostock provides pubDate (公告日) directly; fall back to stat_date + 30d
                    pub_date = p.get('pubDate') or (
                        date.fromisoformat(stat_date) + timedelta(days=30)
                    ).isoformat()
                    rows.append(
                        {
                            'report_period': stat_date,
                            'publish_date': pub_date,
                            'roe': _safe_float(p.get('roeAvg')),
                            'revenue': _safe_float(p.get('MBRevenue')),
                            'net_profit': _safe_float(p.get('netProfit')),
                            'debt_ratio': _safe_float(b.get('liabilityToAsset')),
                            'operating_cashflow': _safe_float(c.get('operateNetIncome')),
                        }
                    )
            return rows
        finally:
            bs.logout()
