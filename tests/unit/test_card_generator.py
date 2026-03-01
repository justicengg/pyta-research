"""Unit tests for CardGenerator (INV-40).

Uses in-memory SQLite + Base.metadata.create_all().
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.base import Base
from src.db.models import RawPrice, StrategyCard
from src.screener.screener import ScreenerCandidate
from src.strategy.card_generator import CardGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mem_session() -> Session:
    engine = create_engine('sqlite:///:memory:', future=True)
    Base.metadata.create_all(engine)
    SL = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    with SL() as session:
        yield session


ASOF = date(2026, 3, 1)
SYMBOL = 'sh.600000'
MARKET = 'CN'


def _add_price(session: Session, symbol: str, market: str, d: date,
               close: float, high: float | None = None, low: float | None = None) -> None:
    session.add(RawPrice(
        symbol=symbol, market=market, trade_date=d,
        open=close, high=high or close * 1.01, low=low or close * 0.99,
        close=close, volume=1_000_000.0, adj_factor=None, source='test',
    ))


def _make_candidate(
    symbol: str = SYMBOL,
    market: str = MARKET,
    matched_rules: list[str] | None = None,
    factors: dict | None = None,
) -> ScreenerCandidate:
    return ScreenerCandidate(
        symbol=symbol,
        market=market,
        matched_rules=matched_rules or ['roe_latest:>=:0.08'],
        skipped_rules=[],
        factors=factors or {'roe_latest': 0.15, 'momentum_20d': 0.05, 'debt_ratio_latest': 0.45},
    )


# ---------------------------------------------------------------------------
# _get_entry_price
# ---------------------------------------------------------------------------

class TestEntryPrice:
    def test_returns_none_when_no_prices(self, mem_session: Session) -> None:
        result = CardGenerator._get_entry_price(SYMBOL, MARKET, ASOF, mem_session)
        assert result is None

    def test_returns_latest_close_on_or_before_asof(self, mem_session: Session) -> None:
        _add_price(mem_session, SYMBOL, MARKET, ASOF, 10.50)
        _add_price(mem_session, SYMBOL, MARKET, ASOF - timedelta(days=1), 10.00)
        mem_session.commit()

        result = CardGenerator._get_entry_price(SYMBOL, MARKET, ASOF, mem_session)
        assert abs(result - 10.50) < 1e-6

    def test_excludes_future_prices(self, mem_session: Session) -> None:
        _add_price(mem_session, SYMBOL, MARKET, ASOF + timedelta(days=1), 11.00)
        mem_session.commit()

        result = CardGenerator._get_entry_price(SYMBOL, MARKET, ASOF, mem_session)
        assert result is None


# ---------------------------------------------------------------------------
# _compute_atr
# ---------------------------------------------------------------------------

class TestComputeATR:
    def test_returns_none_with_insufficient_prices(self, mem_session: Session) -> None:
        _add_price(mem_session, SYMBOL, MARKET, ASOF, 10.0)
        mem_session.commit()

        result = CardGenerator._compute_atr(SYMBOL, MARKET, ASOF, mem_session, window=14)
        assert result is None

    def test_atr_uniform_bars(self, mem_session: Session) -> None:
        """When H=10.1, L=9.9, prev_close=10.0: TR=0.2 every day → ATR=0.2."""
        for i in range(16):
            d = ASOF - timedelta(days=i)
            session_obj = mem_session
            session_obj.add(RawPrice(
                symbol=SYMBOL, market=MARKET, trade_date=d,
                open=10.0, high=10.1, low=9.9, close=10.0,
                volume=1_000_000.0, adj_factor=None, source='test',
            ))
        mem_session.commit()

        atr = CardGenerator._compute_atr(SYMBOL, MARKET, ASOF, mem_session, window=14)
        assert atr is not None
        assert abs(atr - 0.2) < 1e-6


# ---------------------------------------------------------------------------
# generate()
# ---------------------------------------------------------------------------

class TestGenerate:
    def test_empty_candidates_returns_empty(self, mem_session: Session) -> None:
        rows = CardGenerator().generate([], ASOF, mem_session)
        assert rows == []

    def test_generates_one_row_per_candidate(self, mem_session: Session) -> None:
        candidates = [_make_candidate(), _make_candidate('sh.000001', 'CN')]
        rows = CardGenerator().generate(candidates, ASOF, mem_session)
        assert len(rows) == 2

    def test_pct_stop_loss(self, mem_session: Session) -> None:
        _add_price(mem_session, SYMBOL, MARKET, ASOF, 10.0)
        mem_session.commit()

        rows = CardGenerator().generate(
            [_make_candidate()], ASOF, mem_session,
            stop_loss_method='pct', stop_loss_pct=0.08,
        )
        assert abs(rows[0]['stop_loss_price'] - 9.2) < 1e-6

    def test_atr_stop_loss(self, mem_session: Session) -> None:
        # Add 16 uniform bars: ATR = 0.2, entry = 10.0 → stop = 10.0 - 2*0.2 = 9.6
        for i in range(16):
            mem_session.add(RawPrice(
                symbol=SYMBOL, market=MARKET, trade_date=ASOF - timedelta(days=i),
                open=10.0, high=10.1, low=9.9, close=10.0,
                volume=1_000_000.0, adj_factor=None, source='test',
            ))
        mem_session.commit()

        rows = CardGenerator().generate(
            [_make_candidate()], ASOF, mem_session,
            stop_loss_method='atr', stop_loss_atr_window=14, stop_loss_atr_multiplier=2.0,
        )
        assert abs(rows[0]['stop_loss_price'] - 9.6) < 1e-4

    def test_stop_loss_none_when_no_price(self, mem_session: Session) -> None:
        rows = CardGenerator().generate(
            [_make_candidate()], ASOF, mem_session,
            stop_loss_method='pct', stop_loss_pct=0.08,
        )
        assert rows[0]['entry_price'] is None
        assert rows[0]['stop_loss_price'] is None

    def test_status_is_draft(self, mem_session: Session) -> None:
        rows = CardGenerator().generate([_make_candidate()], ASOF, mem_session)
        assert rows[0]['status'] == 'draft'

    def test_thesis_and_position_pct_are_none(self, mem_session: Session) -> None:
        rows = CardGenerator().generate([_make_candidate()], ASOF, mem_session)
        assert rows[0]['thesis'] is None
        assert rows[0]['position_pct'] is None

    def test_entry_date_equals_asof(self, mem_session: Session) -> None:
        rows = CardGenerator().generate([_make_candidate()], ASOF, mem_session)
        assert rows[0]['entry_date'] == ASOF


# ---------------------------------------------------------------------------
# _build_valuation_note
# ---------------------------------------------------------------------------

class TestValuationNote:
    def test_includes_available_factors(self) -> None:
        factors = {'roe_latest': 0.15, 'debt_ratio_latest': 0.45}
        note = CardGenerator._build_valuation_note(factors)
        assert 'ROE' in note
        assert '负债率' in note

    def test_empty_factors_returns_placeholder(self) -> None:
        note = CardGenerator._build_valuation_note({})
        assert '无可用因子数据' in note

    def test_skips_none_values(self) -> None:
        factors = {'roe_latest': None, 'debt_ratio_latest': 0.45}
        note = CardGenerator._build_valuation_note(factors)
        assert 'ROE' not in note
        assert '负债率' in note


# ---------------------------------------------------------------------------
# to_markdown()
# ---------------------------------------------------------------------------

class TestToMarkdown:
    def _card(self, entry: float | None = 10.5, stop: float | None = 9.66) -> dict:
        return {
            'symbol': SYMBOL, 'market': MARKET,
            'entry_price': entry, 'entry_date': ASOF,
            'stop_loss_price': stop, 'thesis': None, 'position_pct': None,
            'valuation_note': 'ROE: 15.00%', 'status': 'draft', 'close_reason': None,
        }

    def test_markdown_contains_header(self) -> None:
        md = CardGenerator().to_markdown(self._card(), _make_candidate())
        assert f'# 策略卡 — {SYMBOL}' in md

    def test_markdown_contains_basic_info_table(self) -> None:
        md = CardGenerator().to_markdown(self._card(), _make_candidate())
        assert '进场参考价' in md
        assert '止损价' in md

    def test_markdown_contains_matched_rules(self) -> None:
        cand = _make_candidate(matched_rules=['roe_latest:>=:0.08'])
        md = CardGenerator().to_markdown(self._card(), cand)
        assert 'roe_latest:>=:0.08' in md
        assert '✓' in md

    def test_markdown_shows_skipped_rules(self) -> None:
        cand = ScreenerCandidate(
            symbol=SYMBOL, market=MARKET,
            matched_rules=['roe_latest:>=:0.08'],
            skipped_rules=['volume_ratio_5_20:>=:0.80'],
            factors={'roe_latest': 0.15},
        )
        md = CardGenerator().to_markdown(self._card(), cand)
        assert '⊘' in md
        assert 'volume_ratio_5_20:>=:0.80' in md

    def test_markdown_missing_price_shows_placeholder(self) -> None:
        md = CardGenerator().to_markdown(self._card(entry=None, stop=None), _make_candidate())
        assert '缺失' in md

    def test_markdown_pct_stop_label(self) -> None:
        md = CardGenerator().to_markdown(
            self._card(), _make_candidate(),
            stop_loss_method='pct', stop_loss_pct=0.08,
        )
        assert '固定 8%' in md

    def test_markdown_atr_stop_label(self) -> None:
        md = CardGenerator().to_markdown(
            self._card(), _make_candidate(),
            stop_loss_method='atr', stop_loss_atr_multiplier=2.0,
        )
        assert 'ATR×2.0' in md
