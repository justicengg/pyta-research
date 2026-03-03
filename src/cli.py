from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import json

from src.db.session import (
    get_latest_macro_date,
    get_latest_trade_date,
    get_session,
    insert_derived_factors,
    insert_raw_fundamental,
    insert_raw_macro,
    insert_raw_price,
    insert_strategy_card,
    insert_trade_log,
)
from src.config.settings import settings
from src.factors.calculator import FactorCalculator
from src.fetchers.fundamental.fundamental_fetcher import FundamentalFetcher
from src.fetchers.macro.macro_fetcher import MacroFetcher
from src.fetchers.market.baostock_fetcher import BaostockFetcher
from src.fetchers.market.yfinance_fetcher import YFinanceFetcher
from src.quality.checker import DataQualityChecker
from src.quality.report import report_to_json
from src.scheduler.scheduler import PipelineScheduler
from src.screener.report import result_to_json as screener_result_to_json
from src.screener.screener import Screener, ScreenerCandidate
from src.strategy.card_generator import CardGenerator
from src.portfolio.tracker import PortfolioTracker
from src.portfolio.report import snapshot_to_json as portfolio_snapshot_to_json
from src.risk.checker import RiskChecker
from src.risk.report import report_to_json as risk_report_to_json
from src.decision.advisor import DecisionAdvisor
from src.decision.report import report_to_json as decision_report_to_json
from src.report.generator import ReportGenerator
from src.report.pusher import FeishuPusher


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

    screener = sub.add_parser('screener')
    screener_sub = screener.add_subparsers(dest='screener_cmd', required=True)
    screener_run = screener_sub.add_parser('run')
    screener_run.add_argument('--asof', required=True, help='ISO date, e.g. 2026-03-02')
    screener_run.add_argument('--out', required=True, help='Output JSON file path')

    strategy = sub.add_parser('strategy')
    strategy_sub = strategy.add_subparsers(dest='strategy_cmd', required=True)
    strategy_gen = strategy_sub.add_parser('generate')
    strategy_gen.add_argument('--candidate', required=True,
                              help='Path to candidates.json from screener run')
    strategy_gen.add_argument('--out', required=True,
                              help='Output directory for Markdown files')

    portfolio = sub.add_parser('portfolio')
    portfolio_sub = portfolio.add_subparsers(dest='portfolio_cmd', required=True)
    portfolio_snap = portfolio_sub.add_parser('snapshot')
    portfolio_snap.add_argument('--asof', default=None,
                                help='ISO date, e.g. 2026-03-02 (default: today)')
    portfolio_snap.add_argument('--out', default=None,
                                help='Output JSON file path (default: stdout)')

    decision = sub.add_parser('decision')
    decision_sub = decision.add_subparsers(dest='decision_cmd', required=True)
    decision_eval = decision_sub.add_parser('evaluate')
    decision_eval.add_argument('--asof', default=None,
                               help='ISO date, e.g. 2026-03-02 (default: today)')
    decision_eval.add_argument('--out', default=None,
                               help='Output JSON file path (default: stdout)')

    risk = sub.add_parser('risk')
    risk_sub = risk.add_subparsers(dest='risk_cmd', required=True)
    risk_check = risk_sub.add_parser('check')
    risk_check.add_argument('--asof', default=None,
                            help='ISO date, e.g. 2026-03-02 (default: today)')
    risk_check.add_argument('--out', default=None,
                            help='Output JSON file path (default: stdout)')

    report = sub.add_parser('report')
    report_sub = report.add_subparsers(dest='report_cmd', required=True)
    report_push = report_sub.add_parser('push')
    report_push.add_argument('--type', dest='report_type', choices=['daily', 'weekly'],
                             default='daily', help='Report type (default: daily)')
    report_push.add_argument('--asof', default=None,
                             help='ISO date, e.g. 2026-03-02 (default: today)')
    report_push.add_argument('--out', default=None,
                             help='Also write report text to this file path')
    report_push.add_argument('--dry-run', action='store_true',
                             help='Generate report but do not push to Feishu')

    quality = sub.add_parser('quality')
    quality_sub = quality.add_subparsers(dest='quality_cmd', required=True)
    quality_check = quality_sub.add_parser('check')
    quality_check.add_argument('--table', choices=['raw_price', 'raw_fundamental', 'raw_macro'], required=True)
    quality_check.add_argument('--date', required=True)
    quality_check.add_argument('--out', required=True)

    api = sub.add_parser('api')
    api_sub = api.add_subparsers(dest='api_cmd', required=True)
    api_start = api_sub.add_parser('start')
    api_start.add_argument('--host', default=None,
                           help='Bind host (default: settings.api_host)')
    api_start.add_argument('--port', type=int, default=None,
                           help='Bind port (default: settings.api_port)')
    api_start.add_argument('--reload', action='store_true',
                           help='Enable uvicorn auto-reload (dev mode)')

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

    if args.command == 'screener' and args.screener_cmd == 'run':
        asof = date.fromisoformat(args.asof)
        symbols = (
            [(s, 'CN') for s in settings.pipeline_cn_symbols]
            + [(s, 'US') for s in settings.pipeline_us_symbols]
        )
        with get_session() as session:
            result = Screener().run(
                asof=asof,
                symbols=symbols,
                session=session,
                rules=settings.screener_rules,
            )
        out = Path(args.out)
        out.write_text(screener_result_to_json(result), encoding='utf-8')
        print(f'screener screened={result.total_screened} candidates={result.total_candidates} out={out}')
        return

    if args.command == 'strategy' and args.strategy_cmd == 'generate':
        candidate_path = Path(args.candidate)
        payload = json.loads(candidate_path.read_text(encoding='utf-8'))
        asof = date.fromisoformat(payload['asof_date'])
        candidates = [
            ScreenerCandidate(
                symbol=c['symbol'],
                market=c['market'],
                matched_rules=c['matched_rules'],
                skipped_rules=c['skipped_rules'],
                factors=c['factors'],
            )
            for c in payload.get('candidates', [])
        ]
        gen = CardGenerator()
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        inserted = 0
        with get_session() as session:
            rows = gen.generate(
                candidates=candidates,
                asof=asof,
                session=session,
                stop_loss_method=settings.strategy_stop_loss_method,
                stop_loss_pct=settings.strategy_stop_loss_pct,
                stop_loss_atr_window=settings.strategy_stop_loss_atr_window,
                stop_loss_atr_multiplier=settings.strategy_stop_loss_atr_multiplier,
            )
            for card, cand in zip(rows, candidates):
                card_id = insert_strategy_card(session, card)
                md = gen.to_markdown(
                    card, cand,
                    stop_loss_method=settings.strategy_stop_loss_method,
                    stop_loss_pct=settings.strategy_stop_loss_pct,
                    stop_loss_atr_multiplier=settings.strategy_stop_loss_atr_multiplier,
                )
                md_path = out_dir / f'{card["symbol"].replace(".", "_")}_{card["market"]}_{asof}.md'
                md_path.write_text(md, encoding='utf-8')
                inserted += 1
        print(f'strategy cards generated={inserted} out={out_dir}')
        return

    if args.command == 'portfolio' and args.portfolio_cmd == 'snapshot':
        asof = date.fromisoformat(args.asof) if args.asof else date.today()
        with get_session() as session:
            snap = PortfolioTracker().snapshot(
                asof=asof,
                session=session,
                price_source_cn=settings.price_source_cn,
                price_source_us=settings.price_source_us,
            )
        output = portfolio_snapshot_to_json(snap)
        if args.out:
            out = Path(args.out)
            out.write_text(output, encoding='utf-8')
            print(f'portfolio snapshot positions={len(snap.positions)} out={out}')
        else:
            print(output)
        return

    if args.command == 'decision' and args.decision_cmd == 'evaluate':
        asof = date.fromisoformat(args.asof) if args.asof else date.today()
        with get_session() as session:
            report = DecisionAdvisor().evaluate(
                asof=asof,
                session=session,
                price_source_cn=settings.price_source_cn,
                price_source_us=settings.price_source_us,
                max_position_pct=settings.risk_max_position_pct,
                max_positions=settings.risk_max_positions,
                max_drawdown_pct=settings.risk_max_drawdown_pct,
            )
        output = decision_report_to_json(report)
        if args.out:
            out = Path(args.out)
            out.write_text(output, encoding='utf-8')
            print(
                f'decision evaluate positions={report.total_positions} '
                f'exit={report.exit_count} trim={report.trim_count} '
                f'hold={report.hold_count} enter={report.enter_count} '
                f'watch={report.watch_count} risk={report.risk_status} out={out}'
            )
        else:
            print(output)
        return

    if args.command == 'risk' and args.risk_cmd == 'check':
        asof = date.fromisoformat(args.asof) if args.asof else date.today()
        with get_session() as session:
            snap = PortfolioTracker().snapshot(
                asof=asof,
                session=session,
                price_source_cn=settings.price_source_cn,
                price_source_us=settings.price_source_us,
            )
        report = RiskChecker().check(
            portfolio=snap,
            max_position_pct=settings.risk_max_position_pct,
            max_positions=settings.risk_max_positions,
            max_drawdown_pct=settings.risk_max_drawdown_pct,
        )
        output = risk_report_to_json(report)
        if args.out:
            out = Path(args.out)
            out.write_text(output, encoding='utf-8')
            print(f'risk check status={report.status} violations={len(report.violations)} out={out}')
        else:
            print(output)
        return

    if args.command == 'report' and args.report_cmd == 'push':
        asof = date.fromisoformat(args.asof) if args.asof else date.today()
        with get_session() as session:
            decision = DecisionAdvisor().evaluate(
                asof=asof,
                session=session,
                price_source_cn=settings.price_source_cn,
                price_source_us=settings.price_source_us,
                max_position_pct=settings.risk_max_position_pct,
                max_positions=settings.risk_max_positions,
                max_drawdown_pct=settings.risk_max_drawdown_pct,
            )
        gen = ReportGenerator()
        text = gen.generate_daily(decision) if args.report_type == 'daily' else gen.generate_weekly(decision)
        if args.out:
            Path(args.out).write_text(text, encoding='utf-8')
            print(f'report written out={args.out}')
        if args.dry_run:
            print(text)
            print('(dry-run: push skipped)')
        else:
            pushed = FeishuPusher().push(text=text, webhook_url=settings.feishu_webhook_url)
            print(f'report push pushed={pushed} type={args.report_type} asof={asof}')
        return

    if args.command == 'quality' and args.quality_cmd == 'check':
        report = DataQualityChecker().run(table=args.table, run_date=args.date)
        out = Path(args.out)
        out.write_text(report_to_json(report), encoding='utf-8')
        print(f'quality report rows={report.total_rows} issues={report.issue_count} out={out}')
        return

    if args.command == 'api' and args.api_cmd == 'start':
        import uvicorn
        host = args.host or settings.api_host
        port = args.port or settings.api_port
        uvicorn.run(
            'src.api.app:app',
            host=host,
            port=port,
            reload=args.reload,
        )
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
