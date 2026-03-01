"""Unit tests for Screener and rule parser.

Uses an in-memory SQLite database (Base.metadata.create_all) — no Alembic needed.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.base import Base
from src.db.models import DerivedFactor
from src.screener.screener import Screener, ScreenerResult, parse_rule
from src.screener.report import result_to_json


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
SYMBOLS = [('sh.600000', 'CN'), ('sh.000001', 'CN')]


def _insert_factor(session: Session, symbol: str, market: str, name: str, value: float | None) -> None:
    session.add(DerivedFactor(symbol=symbol, market=market, asof_date=ASOF, factor_name=name, factor_value=value))
    session.commit()


def _insert_all_passing_factors(session: Session, symbol: str = 'sh.600000', market: str = 'CN') -> None:
    """Insert a factor set that passes all 4 default rules."""
    for name, val in [
        ('roe_latest', 0.15),          # >= 0.08 ✓
        ('momentum_20d', 0.05),        # >= 0.0  ✓
        ('debt_ratio_latest', 0.45),   # <= 0.70 ✓
        ('volume_ratio_5_20', 1.2),    # >= 0.80 ✓
    ]:
        session.add(DerivedFactor(symbol=symbol, market=market, asof_date=ASOF, factor_name=name, factor_value=val))
    session.commit()


DEFAULT_RULES = [
    'roe_latest:>=:0.08',
    'momentum_20d:>=:0.0',
    'debt_ratio_latest:<=:0.70',
    'volume_ratio_5_20:>=:0.80',
]


# ---------------------------------------------------------------------------
# parse_rule tests
# ---------------------------------------------------------------------------

class TestParseRule:
    def test_valid_gte(self) -> None:
        import operator as op
        name, func, thresh = parse_rule('roe_latest:>=:0.08')
        assert name == 'roe_latest'
        assert func is op.ge
        assert thresh == pytest.approx(0.08)

    def test_valid_lte(self) -> None:
        import operator as op
        _, func, thresh = parse_rule('debt_ratio_latest:<=:0.70')
        assert func is op.le
        assert thresh == pytest.approx(0.70)

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match='factor_name:operator:threshold'):
            parse_rule('roe_latest>=0.08')

    def test_invalid_operator_raises(self) -> None:
        with pytest.raises(ValueError, match='unsupported operator'):
            parse_rule('roe_latest:!=:0.08')

    def test_non_numeric_threshold_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_rule('roe_latest:>=:high')


# ---------------------------------------------------------------------------
# Screener.run — empty / no data cases
# ---------------------------------------------------------------------------

class TestScreenerNoData:
    def test_empty_symbols_returns_empty_result(self, mem_session: Session) -> None:
        result = Screener().run(asof=ASOF, symbols=[], session=mem_session, rules=DEFAULT_RULES)
        assert isinstance(result, ScreenerResult)
        assert result.total_screened == 0
        assert result.total_candidates == 0
        assert result.candidates == []

    def test_no_factors_in_db_produces_no_candidates(self, mem_session: Session) -> None:
        result = Screener().run(asof=ASOF, symbols=SYMBOLS, session=mem_session, rules=DEFAULT_RULES)
        assert result.total_screened == 2
        assert result.total_candidates == 0

    def test_result_metadata_populated(self, mem_session: Session) -> None:
        result = Screener().run(asof=ASOF, symbols=SYMBOLS, session=mem_session, rules=DEFAULT_RULES)
        assert result.asof_date == ASOF
        assert result.generated_at  # non-empty ISO timestamp
        assert result.rules_applied == DEFAULT_RULES


# ---------------------------------------------------------------------------
# Screener.run — pass / fail cases
# ---------------------------------------------------------------------------

class TestScreenerRules:
    def test_all_rules_pass_symbol_becomes_candidate(self, mem_session: Session) -> None:
        _insert_all_passing_factors(mem_session)
        result = Screener().run(asof=ASOF, symbols=[('sh.600000', 'CN')], session=mem_session, rules=DEFAULT_RULES)
        assert result.total_candidates == 1
        assert result.candidates[0].symbol == 'sh.600000'

    def test_one_rule_fails_symbol_excluded(self, mem_session: Session) -> None:
        # All factors present but momentum_20d is negative → fail
        for name, val in [
            ('roe_latest', 0.15),
            ('momentum_20d', -0.05),   # fails momentum_20d:>=:0.0
            ('debt_ratio_latest', 0.45),
            ('volume_ratio_5_20', 1.2),
        ]:
            mem_session.add(DerivedFactor(symbol='sh.600000', market='CN', asof_date=ASOF, factor_name=name, factor_value=val))
        mem_session.commit()

        result = Screener().run(asof=ASOF, symbols=[('sh.600000', 'CN')], session=mem_session, rules=DEFAULT_RULES)
        assert result.total_candidates == 0

    def test_missing_factor_rule_skipped_not_failed(self, mem_session: Session) -> None:
        """If a factor is absent, its rule is skipped (not failed)."""
        # Only roe_latest and momentum_20d present, debt_ratio_latest and volume_ratio_5_20 missing
        for name, val in [('roe_latest', 0.15), ('momentum_20d', 0.05)]:
            mem_session.add(DerivedFactor(symbol='sh.600000', market='CN', asof_date=ASOF, factor_name=name, factor_value=val))
        mem_session.commit()

        result = Screener().run(asof=ASOF, symbols=[('sh.600000', 'CN')], session=mem_session, rules=DEFAULT_RULES)
        assert result.total_candidates == 1
        cand = result.candidates[0]
        assert len(cand.matched_rules) == 2
        assert len(cand.skipped_rules) == 2

    def test_all_factors_missing_no_matched_rules_excluded(self, mem_session: Session) -> None:
        """Symbol with no factors → no matched rules → excluded (no data guard)."""
        result = Screener().run(asof=ASOF, symbols=[('sh.600000', 'CN')], session=mem_session, rules=DEFAULT_RULES)
        assert result.total_candidates == 0

    def test_multiple_symbols_mixed_results(self, mem_session: Session) -> None:
        # sh.600000 passes, sh.000001 fails
        _insert_all_passing_factors(mem_session, 'sh.600000', 'CN')
        # sh.000001: roe_latest below threshold
        for name, val in [
            ('roe_latest', 0.03),      # fails: < 0.08
            ('momentum_20d', 0.05),
            ('debt_ratio_latest', 0.45),
            ('volume_ratio_5_20', 1.2),
        ]:
            mem_session.add(DerivedFactor(symbol='sh.000001', market='CN', asof_date=ASOF, factor_name=name, factor_value=val))
        mem_session.commit()

        result = Screener().run(asof=ASOF, symbols=SYMBOLS, session=mem_session, rules=DEFAULT_RULES)
        assert result.total_screened == 2
        assert result.total_candidates == 1
        assert result.candidates[0].symbol == 'sh.600000'

    def test_candidate_matched_rules_are_correct(self, mem_session: Session) -> None:
        _insert_all_passing_factors(mem_session)
        result = Screener().run(asof=ASOF, symbols=[('sh.600000', 'CN')], session=mem_session, rules=DEFAULT_RULES)
        cand = result.candidates[0]
        assert set(cand.matched_rules) == set(DEFAULT_RULES)
        assert cand.skipped_rules == []

    def test_factors_dict_in_candidate(self, mem_session: Session) -> None:
        _insert_all_passing_factors(mem_session)
        result = Screener().run(asof=ASOF, symbols=[('sh.600000', 'CN')], session=mem_session, rules=DEFAULT_RULES)
        factors = result.candidates[0].factors
        assert 'roe_latest' in factors
        assert abs(factors['roe_latest'] - 0.15) < 1e-9

    def test_pit_only_uses_asof_date(self, mem_session: Session) -> None:
        """Factors with a different asof_date must not be used."""
        wrong_asof = ASOF + timedelta(days=1)
        for name, val in [('roe_latest', 0.15), ('momentum_20d', 0.05)]:
            mem_session.add(DerivedFactor(symbol='sh.600000', market='CN', asof_date=wrong_asof, factor_name=name, factor_value=val))
        mem_session.commit()

        result = Screener().run(asof=ASOF, symbols=[('sh.600000', 'CN')], session=mem_session, rules=DEFAULT_RULES)
        assert result.total_candidates == 0


# ---------------------------------------------------------------------------
# result_to_json
# ---------------------------------------------------------------------------

class TestResultToJson:
    def test_json_is_valid_and_contains_key_fields(self, mem_session: Session) -> None:
        import json
        _insert_all_passing_factors(mem_session)
        result = Screener().run(asof=ASOF, symbols=[('sh.600000', 'CN')], session=mem_session, rules=DEFAULT_RULES)
        payload = json.loads(result_to_json(result))

        assert payload['asof_date'] == '2026-03-01'
        assert payload['total_screened'] == 1
        assert payload['total_candidates'] == 1
        assert len(payload['candidates']) == 1
        cand = payload['candidates'][0]
        assert cand['symbol'] == 'sh.600000'
        assert 'matched_rules' in cand
        assert 'skipped_rules' in cand
        assert 'factors' in cand

    def test_empty_result_serializes(self, mem_session: Session) -> None:
        import json
        result = Screener().run(asof=ASOF, symbols=[], session=mem_session, rules=DEFAULT_RULES)
        payload = json.loads(result_to_json(result))
        assert payload['candidates'] == []
        assert payload['total_candidates'] == 0
