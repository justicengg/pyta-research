"""Candidate screener (大聪明 output stage).

Reads derived_factors for a given asof_date, applies configurable filter rules,
and produces a ScreenerResult describing which symbols passed and why.

Rule format
-----------
Rules are strings of the form ``"factor_name:operator:threshold"``, e.g.::

    roe_latest:>=:0.08
    momentum_20d:>=:0.0
    debt_ratio_latest:<=:0.70
    volume_ratio_5_20:>=:0.80

Supported operators: ``>=``, ``<=``, ``>``, ``<``, ``==``

Rules are configured in ``settings.screener_rules`` and can be overridden via
``.env`` without touching source code (see ``src/config/settings.py``).

Evaluation semantics
--------------------
For each (symbol, market) pair:
  - *matched*  — factor exists and rule passes
  - *skipped*  — factor not present in derived_factors for this asof_date
  - *failed*   — factor exists but rule does not pass → symbol excluded

A symbol is added to the candidate pool only when:
  1. No rule failed (all evaluated rules either matched or were skipped).
  2. At least one rule matched (guards against symbols with no factor data at all).
"""
from __future__ import annotations

import operator as _op
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import DerivedFactor

# Map operator strings to Python callables
_OPERATORS: dict[str, object] = {
    '>=': _op.ge,
    '<=': _op.le,
    '>': _op.gt,
    '<': _op.lt,
    '==': _op.eq,
}


def parse_rule(rule_str: str) -> tuple[str, object, float]:
    """Parse ``"factor_name:operator:threshold"`` → ``(name, func, threshold)``.

    Raises ``ValueError`` on malformed input.
    """
    parts = rule_str.split(':')
    if len(parts) != 3:
        raise ValueError(
            f'screener rule must be "factor_name:operator:threshold", got {rule_str!r}'
        )
    factor_name, oper, threshold_str = (p.strip() for p in parts)
    if oper not in _OPERATORS:
        raise ValueError(
            f'unsupported operator {oper!r} in rule {rule_str!r}; '
            f'valid: {list(_OPERATORS)}'
        )
    return factor_name, _OPERATORS[oper], float(threshold_str)


@dataclass
class ScreenerCandidate:
    symbol: str
    market: str
    matched_rules: list[str]   # rule strings that passed
    skipped_rules: list[str]   # rule strings skipped (factor missing)
    factors: dict[str, float | None]  # all factor values for this symbol/asof_date


@dataclass
class ScreenerResult:
    asof_date: date
    generated_at: str          # ISO-8601 timestamp
    rules_applied: list[str]   # full set of configured rule strings
    total_screened: int
    total_candidates: int
    candidates: list[ScreenerCandidate] = field(default_factory=list)


class Screener:
    """Applies configurable rules to derived_factors and returns candidate pool."""

    def run(
        self,
        asof: date,
        symbols: list[tuple[str, str]],
        session: Session,
        rules: list[str],
    ) -> ScreenerResult:
        """Screen *symbols* against *rules* using factors computed as of *asof*.

        Parameters
        ----------
        asof:
            Reference date — only ``derived_factors`` rows with ``asof_date == asof``
            are considered.
        symbols:
            List of ``(symbol, market)`` pairs to evaluate.
        session:
            Active SQLAlchemy session.
        rules:
            Rule strings (see module docstring).  Typically sourced from
            ``settings.screener_rules``.
        """
        parsed = [(r, *parse_rule(r)) for r in rules]  # [(rule_str, name, func, thresh), ...]

        candidates: list[ScreenerCandidate] = []

        for symbol, market in symbols:
            # Fetch all factors for this symbol/market/asof_date
            stmt = (
                select(DerivedFactor.factor_name, DerivedFactor.factor_value)
                .where(
                    DerivedFactor.symbol == symbol,
                    DerivedFactor.market == market,
                    DerivedFactor.asof_date == asof,
                )
            )
            rows = session.execute(stmt).fetchall()
            factor_map: dict[str, float | None] = {
                r.factor_name: float(r.factor_value) if r.factor_value is not None else None
                for r in rows
            }

            matched: list[str] = []
            skipped: list[str] = []
            excluded = False

            for rule_str, factor_name, func, threshold in parsed:
                value = factor_map.get(factor_name)
                if value is None:
                    skipped.append(rule_str)
                    continue
                if func(value, threshold):
                    matched.append(rule_str)
                else:
                    excluded = True
                    break

            if excluded or not matched:
                continue  # symbol does not qualify

            candidates.append(
                ScreenerCandidate(
                    symbol=symbol,
                    market=market,
                    matched_rules=matched,
                    skipped_rules=skipped,
                    factors=factor_map,
                )
            )

        return ScreenerResult(
            asof_date=asof,
            generated_at=datetime.now().isoformat(timespec='seconds'),
            rules_applied=list(rules),
            total_screened=len(symbols),
            total_candidates=len(candidates),
            candidates=candidates,
        )
