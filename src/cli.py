from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from src.db.session import (
    get_latest_macro_date,
    get_latest_trade_date,
    get_session,
    insert_derived_factors,
    insert_raw_fundamental,
    insert_raw_macro,
    insert_raw_price,
)
from src.factors.calculator import FactorCalculator
from src.fetchers.fundamental.fundamental_fetcher import FundamentalFetcher
from src.fetchers.macro.macro_fetcher import MacroFetcher
from src.fetchers.market.baostock_fetcher import BaostockFetcher
from src.fetchers.market.yfinance_fetcher import YFinanceFetcher
from src.quality.checker import DataQualityChecker
from src.quality.report import report_to_json
from src.scheduler.scheduler import PipelineScheduler


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='python -m src.cli')
    sub = parser.add_subparsers(dest='command', required=True)

    fetch = sub.add_parser('fetch')
    fetch_sub = fetch.add_subparsers(dest='fetch_type', required=True)

    market = fetch_sub.add_parser('market')
    market.add_argument('--source', choices=['baostock', 'yfinance'], required=True)
    market.add_argument('--symbol', required=True)
    market.add_argument('--market', default='CN')
    market.add_argument('--start', required=True)
    market.add_argument('--end', required=True)
    market.add_argument('--incremental', action='store_true')

    fundamental = fetch_sub.add_parser('fundamental')
    fundamental.add_argument('--symbol', required=True)
    fundamental.add_argument('--market', default='CN')
    fundamental.add_argument('--asof', required=True)
    fundamental.add_argument('--incremental', action='store_true')

    macro = fetch_sub.add_parser('macro')
    macro.add_argument('--series', required=True)
    macro.add_argument('--source', choices=['fred', 'baostock'], required=True)
    macro.add_argument('--market', default='US')
    macro.add_argument('--start', required=True)
    macro.add_argument('--end', required=True)
    macro.add_argument('--incremental', action='store_true')

    factors = sub.add_parser('factors')
    factors_sub = factors.add_subparsers(dest='factors_cmd', required=True)
    factors_compute = factors_sub.add_parser('compute')
    factors_compute.add_argument('--symbol', required=True)
    factors_compute.add_argument('--market', default='CN')
    factors_compute.add_argument('--asof', required=True, help='ISO date, e.g. 2026-03-02')

    quality = sub.add_parser('quality')
    quality_sub = quality.add_subparsers(dest='quality_cmd', required=True)
    quality_check = quality_sub.add_parser('check')
    quality_check.add_argument('--table', choices=['raw_price', 'raw_fundamental', 'raw_macro'], required=True)
    quality_check.add_argument('--date', required=True)
    quality_check.add_argument('--out', required=True)

    scheduler = sub.add_parser('scheduler')
    scheduler_sub = scheduler.add_subparsers(dest='scheduler_cmd', required=True)
    scheduler_sub.add_parser('run-once')
    scheduler_sub.add_parser('start')

    return parser


def main() -> None:
    args = _build_parser().parse_args()

    if args.command == 'fetch':
        if args.fetch_type == 'market':
            fetcher = BaostockFetcher() if args.source == 'baostock' else YFinanceFetcher()
            with get_session() as session:
                last = get_latest_trade_date(session, args.symbol, args.market, args.source)
                rows = fetcher.fetch(
                    symbol=args.symbol,
                    market=args.market,
                    start=date.fromisoformat(args.start),
                    end=date.fromisoformat(args.end),
                    incremental=args.incremental,
                    last_date=last,
                )
                inserted = insert_raw_price(session, rows)
            print(f'market rows inserted={inserted}')
            return

        if args.fetch_type == 'fundamental':
            with get_session() as session:
                rows = FundamentalFetcher().fetch(
                    symbol=args.symbol,
                    market=args.market,
                    asof=date.fromisoformat(args.asof),
                    incremental=args.incremental,
                )
                inserted = insert_raw_fundamental(session, rows)
            print(f'fundamental rows inserted={inserted}')
            return

        if args.fetch_type == 'macro':
            with get_session() as session:
                last = get_latest_macro_date(session, args.series, args.market, args.source)
                rows = MacroFetcher().fetch(
                    series=args.series,
                    source=args.source,
                    market=args.market,
                    start=date.fromisoformat(args.start),
                    end=date.fromisoformat(args.end),
                    incremental=args.incremental,
                    last_date=last,
                )
                inserted = insert_raw_macro(session, rows)
            print(f'macro rows inserted={inserted}')
            return

    if args.command == 'factors' and args.factors_cmd == 'compute':
        with get_session() as session:
            rows = FactorCalculator().compute(
                symbol=args.symbol,
                market=args.market,
                asof=date.fromisoformat(args.asof),
                session=session,
            )
            inserted = insert_derived_factors(session, rows)
        print(f'factors inserted={inserted}')
        return

    if args.command == 'quality' and args.quality_cmd == 'check':
        report = DataQualityChecker().run(table=args.table, run_date=args.date)
        out = Path(args.out)
        out.write_text(report_to_json(report), encoding='utf-8')
        print(f'quality report rows={report.total_rows} issues={report.issue_count} out={out}')
        return

    if args.command == 'scheduler':
        svc = PipelineScheduler()
        if args.scheduler_cmd == 'run-once':
            svc.run_once()
            print('scheduler run-once completed')
            return
        if args.scheduler_cmd == 'start':
            svc.start()
            return


if __name__ == '__main__':
    main()
