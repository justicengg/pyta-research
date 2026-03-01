from __future__ import annotations

from datetime import date

from sqlalchemy import select

from src.db.models import RawFundamental, RawMacro, RawPrice
from src.db.session import get_session
from src.quality.rules import detect_outliers, rule_missing, rule_non_negative
from src.types import QualityIssue, QualityReport


class DataQualityChecker:
    def run(self, table: str, run_date: str) -> QualityReport:
        issues: list[QualityIssue] = []
        with get_session() as session:
            if table == 'raw_price':
                rows = session.execute(select(RawPrice).where(RawPrice.trade_date == date.fromisoformat(run_date))).scalars().all()
                values = [float(r.close) for r in rows if r.close is not None]
                outlier_idx = set(detect_outliers(values))
                value_idx = 0
                for row in rows:
                    for f in ['open', 'high', 'low', 'close', 'volume']:
                        hit, msg = rule_missing(f, getattr(row, f))
                        if hit:
                            issues.append(QualityIssue('missing', 'high', table, f'{row.symbol}:{row.trade_date}', msg))
                        hit, msg = rule_non_negative(f, getattr(row, f))
                        if hit:
                            issues.append(QualityIssue('non_negative', 'high', table, f'{row.symbol}:{row.trade_date}', msg))
                    if row.close is not None:
                        if value_idx in outlier_idx:
                            issues.append(QualityIssue('outlier', 'medium', table, f'{row.symbol}:{row.trade_date}', 'close is outlier'))
                        value_idx += 1
            elif table == 'raw_fundamental':
                rows = session.execute(select(RawFundamental).where(RawFundamental.publish_date <= date.fromisoformat(run_date))).scalars().all()
                for row in rows:
                    if row.publish_date > date.fromisoformat(run_date):
                        issues.append(
                            QualityIssue('future_leak', 'critical', table, f'{row.symbol}:{row.report_period}', 'publish_date exceeds asof')
                        )
                    for f in ['roe', 'revenue', 'net_profit', 'debt_ratio', 'operating_cashflow']:
                        hit, msg = rule_missing(f, getattr(row, f))
                        if hit:
                            issues.append(QualityIssue('missing', 'medium', table, f'{row.symbol}:{row.report_period}', msg))
            elif table == 'raw_macro':
                rows = session.execute(select(RawMacro).where(RawMacro.obs_date <= date.fromisoformat(run_date))).scalars().all()
                for row in rows:
                    hit, msg = rule_missing('value', row.value)
                    if hit:
                        issues.append(QualityIssue('missing', 'high', table, f'{row.series_code}:{row.obs_date}', msg))
            else:
                raise ValueError(f'Unsupported table: {table}')

        return QualityReport(table=table, run_date=run_date, total_rows=len(rows), issue_count=len(issues), issues=issues)
