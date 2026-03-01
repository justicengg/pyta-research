from __future__ import annotations

import logging
import time
from datetime import date, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config.settings import settings
from src.db.session import (
    get_latest_macro_date,
    get_latest_trade_date,
    get_session,
    insert_raw_fundamental,
    insert_raw_macro,
    insert_raw_price,
)
from src.fetchers.fundamental.fundamental_fetcher import FundamentalFetcher
from src.fetchers.macro.macro_fetcher import MacroFetcher
from src.fetchers.market.baostock_fetcher import BaostockFetcher
from src.fetchers.market.yfinance_fetcher import YFinanceFetcher
from src.quality.checker import DataQualityChecker

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')


class PipelineScheduler:
    def __init__(self) -> None:
        self.scheduler = BlockingScheduler(timezone=settings.scheduler_timezone)

    def run_once(self) -> None:
        self._with_retry(self._run_market, max_attempts=3)
        self._with_retry(self._run_fundamental, max_attempts=3)
        self._with_retry(self._run_macro, max_attempts=3)
        self._with_retry(self._run_quality, max_attempts=2)

    def start(self) -> None:
        trigger = CronTrigger(hour=settings.scheduler_cron_hour, minute=settings.scheduler_cron_minute)
        self.scheduler.add_job(self.run_once, trigger=trigger, id='daily_pipeline', replace_existing=True)
        logger.info('scheduler started')
        self.scheduler.start()

    def _with_retry(self, fn, max_attempts: int = 3) -> None:
        for attempt in range(1, max_attempts + 1):
            try:
                fn()
                return
            except Exception as exc:
                logger.error('pipeline step failed: %s attempt=%s/%s', fn.__name__, attempt, max_attempts, exc_info=exc)
                if attempt == max_attempts:
                    raise
                time.sleep(2 ** attempt)

    def _run_market(self) -> None:
        logger.info('run market fetch')
        start = date.today() - timedelta(days=30)
        end = date.today()
        with get_session() as session:
            all_rows: list[dict] = []
            for symbol in settings.pipeline_cn_symbols:
                last = get_latest_trade_date(session, symbol=symbol, market='CN', source='baostock')
                all_rows.extend(BaostockFetcher().fetch(symbol, 'CN', start, end, incremental=True, last_date=last))
            for symbol in settings.pipeline_us_symbols:
                last = get_latest_trade_date(session, symbol=symbol, market='US', source='yfinance')
                all_rows.extend(YFinanceFetcher().fetch(symbol, 'US', start, end, incremental=True, last_date=last))
            inserted = insert_raw_price(session, all_rows)
        logger.info('market fetch done inserted=%s', inserted)

    def _run_fundamental(self) -> None:
        logger.info('run fundamental fetch')
        with get_session() as session:
            all_rows: list[dict] = []
            for symbol in settings.pipeline_cn_fundamental_symbols:
                all_rows.extend(
                    FundamentalFetcher().fetch(symbol=symbol, market='CN', asof=date.today(), incremental=True)
                )
            inserted = insert_raw_fundamental(session, all_rows)
        logger.info('fundamental fetch done inserted=%s', inserted)

    def _run_macro(self) -> None:
        logger.info('run macro fetch')
        start = date.today() - timedelta(days=365)
        end = date.today()
        with get_session() as session:
            all_rows: list[dict] = []
            for entry in settings.pipeline_macro_series:
                series, market, source = entry.split(':')
                last = get_latest_macro_date(session, series_code=series, market=market, source=source)
                all_rows.extend(
                    MacroFetcher().fetch(
                        series=series, market=market, source=source,
                        start=start, end=end, incremental=True, last_date=last,
                    )
                )
            inserted = insert_raw_macro(session, all_rows)
        logger.info('macro fetch done inserted=%s', inserted)

    def _run_quality(self) -> None:
        logger.info('run quality checks')
        checker = DataQualityChecker()
        for table in ('raw_price', 'raw_fundamental', 'raw_macro'):
            report = checker.run(table=table, run_date=date.today().isoformat())
            logger.info('quality table=%s rows=%s issues=%s', table, report.total_rows, report.issue_count)
