from datetime import date

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
    def _default_adapter(**kwargs):
        raise RuntimeError('fundamental adapter not configured in MVP; inject adapter for tests/runtime wrapper')
