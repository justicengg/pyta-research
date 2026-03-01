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
            last_baostock = get_latest_trade_date(session, symbol='sh.600000', market='CN', source='baostock')
            last_yf = get_latest_trade_date(session, symbol='SPY', market='US', source='yfinance')
            rows_cn = BaostockFetcher().fetch('sh.600000', 'CN', start, end, incremental=True, last_date=last_baostock, adapter=lambda **_: [])
            rows_us = YFinanceFetcher().fetch('SPY', 'US', start, end, incremental=True, last_date=last_yf, adapter=lambda **_: [])
            inserted = insert_raw_price(session, rows_cn + rows_us)
        logger.info('market fetch done inserted=%s', inserted)

    def _run_fundamental(self) -> None:
        logger.info('run fundamental fetch')
        with get_session() as session:
            rows = FundamentalFetcher().fetch(
                symbol='600000', market='CN', asof=date.today(), incremental=True, adapter=lambda **_: []
            )
            inserted = insert_raw_fundamental(session, rows)
        logger.info('fundamental fetch done inserted=%s', inserted)

    def _run_macro(self) -> None:
        logger.info('run macro fetch')
        start = date.today() - timedelta(days=365)
        end = date.today()
        with get_session() as session:
            last = get_latest_macro_date(session, series_code='CPIAUCSL', market='US', source='fred')
            rows = MacroFetcher().fetch(
                series='CPIAUCSL', market='US', source='fred', start=start, end=end, incremental=True, last_date=last, adapter=lambda **_: []
            )
            inserted = insert_raw_macro(session, rows)
        logger.info('macro fetch done inserted=%s', inserted)

    def _run_quality(self) -> None:
        logger.info('run quality checks')
        checker = DataQualityChecker()
        for table in ('raw_price', 'raw_fundamental', 'raw_macro'):
            report = checker.run(table=table, run_date=date.today().isoformat())
            logger.info('quality table=%s rows=%s issues=%s', table, report.total_rows, report.issue_count)
