"""Decision advisor — 大善人（总监）决策层.

Evaluates the current portfolio state against active/draft strategy cards and
produces a DecisionReport with per-symbol action recommendations.

Decision rules (thresholds configurable via settings / method params)
---------------------------------------------------------------------
For open positions:
  R1 — stop_loss_hit     current_price ≤ stop_loss_price  → action='exit'
  R2 — concentration     position flagged in RiskReport    → action='trim'
  R3 — default                                             → action='hold'

For strategy cards with no open position:
  R4 — card_active       card.status == 'active'           → action='enter'
  R5 — card_draft        card.status == 'draft'            → action='watch'

Rule priority: R1 > R2 > R3  (stop-loss always beats trim)
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import ActionQueue, RawFundamental, StrategyCard
from src.portfolio.tracker import PortfolioTracker
from src.risk.checker import RiskChecker
from src.types import DecisionAdvice, DecisionReport


class DecisionAdvisor:
    """Produce a DecisionReport by evaluating portfolio + strategy cards."""

    def evaluate(
        self,
        asof: date,
        session: Session,
        price_source_cn: str = 'baostock',
        price_source_us: str = 'yfinance',
        max_position_pct: float = 0.20,
        max_positions: int = 10,
        max_drawdown_pct: float = 0.15,
    ) -> DecisionReport:
        """Evaluate the portfolio and return a DecisionReport.

        Parameters
        ----------
        asof:
            Cut-off date (inclusive). Trades and prices after this date are
            excluded.
        session:
            SQLAlchemy session to query against.
        price_source_cn / price_source_us:
            Preferred ``raw_price.source`` per market, forwarded to
            ``PortfolioTracker``.
        max_position_pct / max_positions / max_drawdown_pct:
            Risk thresholds forwarded to ``RiskChecker``.
        """
        # 1. Portfolio snapshot
        portfolio = PortfolioTracker().snapshot(
            asof=asof,
            session=session,
            price_source_cn=price_source_cn,
            price_source_us=price_source_us,
        )

        # 2. Risk report (feeds concentration violations into R2)
        risk_report = RiskChecker().check(
            portfolio=portfolio,
            max_position_pct=max_position_pct,
            max_positions=max_positions,
            max_drawdown_pct=max_drawdown_pct,
        )

        # 3. Fetch active / draft strategy cards
        stmt = (
            select(StrategyCard)
            .where(StrategyCard.status.in_(['draft', 'active']))
        )
        cards = list(session.scalars(stmt).all())

        # 4. Index open positions by (symbol, market)
        position_index = {(p.symbol, p.market): p for p in portfolio.positions}

        # 5. Symbols flagged with concentration breach (C1, severity=warning)
        concentration_keys = {
            (v.symbol, v.market)
            for v in risk_report.violations
            if v.check == 'position_concentration'
        }

        # 6. Card index: (symbol, market) → StrategyCard
        #    When both active and draft exist, prefer active.
        card_index: dict[tuple[str, str], StrategyCard] = {}
        for card in sorted(cards, key=lambda c: 0 if c.status == 'active' else 1):
            key = (card.symbol, card.market)
            if key not in card_index:
                card_index[key] = card

        advice: list[DecisionAdvice] = []

        # 7. Evaluate every open position (R1 / R2 / R3)
        for key, pos in position_index.items():
            card = card_index.get(key)
            stop_loss_price = (
                float(card.stop_loss_price)
                if card and card.stop_loss_price is not None
                else None
            )

            # R1 — stop-loss hit (highest priority)
            if (
                stop_loss_price is not None
                and pos.current_price is not None
                and pos.current_price <= stop_loss_price
            ):
                action, reason = 'exit', 'stop_loss_hit'

            # R2 — concentration breach → trim
            elif key in concentration_keys:
                action, reason = 'trim', 'concentration_breach'

            # R3 — default hold
            else:
                action, reason = 'hold', 'within_limits'

            advice.append(DecisionAdvice(
                symbol=pos.symbol,
                market=pos.market,
                action=action,
                reason=reason,
                net_shares=pos.net_shares,
                avg_cost=pos.avg_cost,
                current_price=pos.current_price,
                unrealized_pnl=pos.unrealized_pnl,
                unrealized_pnl_pct=pos.unrealized_pnl_pct,
                card_id=card.id if card else None,
                card_status=card.status if card else None,
                stop_loss_price=stop_loss_price,
            ))

        # 8. Evaluate cards with no open position (R4 / R5)
        for key, card in card_index.items():
            if key in position_index:
                continue  # already handled above

            if card.status == 'active':
                action, reason = 'enter', 'card_active'
            else:
                action, reason = 'watch', 'card_draft'

            advice.append(DecisionAdvice(
                symbol=card.symbol,
                market=card.market,
                action=action,
                reason=reason,
                net_shares=None,
                avg_cost=None,
                current_price=None,
                unrealized_pnl=None,
                unrealized_pnl_pct=None,
                card_id=card.id,
                card_status=card.status,
                stop_loss_price=(
                    float(card.stop_loss_price)
                    if card.stop_loss_price is not None
                    else None
                ),
            ))

        # 9. Aggregate action counts
        counts: dict[str, int] = {a: 0 for a in ('exit', 'trim', 'hold', 'enter', 'watch')}
        for a in advice:
            counts[a.action] += 1

        return DecisionReport(
            asof=asof,
            advice=advice,
            risk_status=risk_report.status,
            risk_violations=len(risk_report.violations),
            total_positions=len(portfolio.positions),
            exit_count=counts['exit'],
            trim_count=counts['trim'],
            hold_count=counts['hold'],
            enter_count=counts['enter'],
            watch_count=counts['watch'],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def generate_queue(
        self,
        asof: date,
        session: Session,
        price_source_cn: str = 'baostock',
        price_source_us: str = 'yfinance',
        max_position_pct: float = 0.20,
        max_positions: int = 10,
        max_drawdown_pct: float = 0.15,
    ) -> int:
        """Generate and persist action queue rows for the given asof date.

        Idempotency: same-day reruns update existing rows (by business key)
        instead of inserting duplicates.
        """
        now = datetime.now(timezone.utc)

        # Expire pending rows from previous days.
        stale_stmt = select(ActionQueue).where(
            ActionQueue.generated_date < asof,
            ActionQueue.status == 'pending',
        )
        for row in session.scalars(stale_stmt).all():
            row.status = 'expired'
            row.updated_at = now

        portfolio = PortfolioTracker().snapshot(
            asof=asof,
            session=session,
            price_source_cn=price_source_cn,
            price_source_us=price_source_us,
        )
        risk_report = RiskChecker().check(
            portfolio=portfolio,
            max_position_pct=max_position_pct,
            max_positions=max_positions,
            max_drawdown_pct=max_drawdown_pct,
        )

        cards = list(session.scalars(select(StrategyCard).where(StrategyCard.status != 'closed')).all())
        position_index = {(p.symbol, p.market): p for p in portfolio.positions}
        concentration_keys = {
            (v.symbol, v.market)
            for v in risk_report.violations
            if v.check == 'position_concentration'
        }

        card_index: dict[tuple[str, str], StrategyCard] = {}
        status_rank = {'active': 0, 'paused': 1, 'draft': 2}
        for card in sorted(cards, key=lambda c: status_rank.get(c.status, 9)):
            key = (card.symbol, card.market)
            if key not in card_index:
                card_index[key] = card

        symbol_keys = set(position_index.keys()) | set(card_index.keys())
        advice_rows: list[dict] = []
        for key in symbol_keys:
            pos = position_index.get(key)
            card = card_index.get(key)
            action, rule_tag, reason = self._decide_queue_action(
                key=key,
                position=pos,
                card=card,
                concentration_keys=concentration_keys,
                asof=asof,
                session=session,
            )
            if action is None:
                continue
            priority = self._priority_for_action(action)
            advice_rows.append(
                {
                    'card_id': card.id if card else None,
                    'symbol': key[0],
                    'market': key[1],
                    'action': action,
                    'priority': priority,
                    'reason': reason,
                    'rule_tag': rule_tag,
                    'status': 'pending',
                    'generated_date': asof,
                    'created_at': now,
                    'updated_at': now,
                }
            )

        inserted_or_updated = 0
        for row in advice_rows:
            existing = session.scalar(
                select(ActionQueue).where(
                    ActionQueue.generated_date == row['generated_date'],
                    ActionQueue.symbol == row['symbol'],
                    ActionQueue.market == row['market'],
                    ActionQueue.action == row['action'],
                    ActionQueue.card_id == row['card_id'],
                    ActionQueue.rule_tag == row['rule_tag'],
                )
            )
            if existing is None:
                session.add(ActionQueue(**row))
                inserted_or_updated += 1
                continue
            existing.priority = row['priority']
            existing.reason = row['reason']
            existing.updated_at = now
            existing.status = 'pending'
            inserted_or_updated += 1

        session.flush()
        return inserted_or_updated

    def _decide_queue_action(
        self,
        key: tuple[str, str],
        position,
        card: StrategyCard | None,
        concentration_keys: set[tuple[str, str]],
        asof: date,
        session: Session,
    ) -> tuple[str | None, str | None, str]:
        # R1: stop loss
        if position and card and card.stop_loss_price is not None and position.current_price is not None:
            if position.current_price <= float(card.stop_loss_price):
                return 'exit', 'stop_loss_hit', 'R1 stop loss hit'

        # R1b: thesis break
        if position and card and self._thesis_break_hit(card, position):
            return 'exit', 'thesis_break', 'R1b thesis break'

        # R2: concentration
        if position and key in concentration_keys:
            return 'trim', 'concentration_breach', 'R2 concentration breach'

        # R2b: take profit
        if position and card and self._take_profit_hit(card, position):
            action = 'exit' if self._take_profit_prefers_exit(card) else 'trim'
            return action, 'take_profit_hit', 'R2b take profit condition'

        # R3: default hold for open position
        if position:
            return 'hold', 'within_limits', 'R3 within limits'

        # R6: review due
        if card and self._review_due(card, asof):
            return 'review', 'review_due', 'R6 review cadence due'

        # R4b: entry signal from strategy rules
        if card and card.status == 'active' and self._entry_signal_hit(card, session):
            return 'enter', 'entry_signal', 'R4b entry conditions met'

        # R4: active card without position
        if card and card.status == 'active':
            return 'enter', 'card_active', 'R4 active card'

        # R5: draft card
        if card and card.status == 'draft':
            return 'watch', 'card_draft', 'R5 draft card'

        return None, None, ''

    def _priority_for_action(self, action: str) -> str:
        if action in ('exit', 'trim'):
            return 'urgent'
        if action == 'review':
            return 'normal'
        return 'informational'

    def _take_profit_prefers_exit(self, card: StrategyCard) -> bool:
        exit_rules = card.exit_rules or {}
        tp = exit_rules.get('take_profit') if isinstance(exit_rules, dict) else None
        if not isinstance(tp, dict):
            return False
        mode = str(tp.get('mode', '')).lower()
        return mode == 'exit'

    def _take_profit_hit(self, card: StrategyCard, position) -> bool:
        exit_rules = card.exit_rules or {}
        tp = exit_rules.get('take_profit') if isinstance(exit_rules, dict) else None
        if not isinstance(tp, dict):
            return False
        metric = str(tp.get('metric', '')).lower()
        threshold = tp.get('threshold')
        if threshold is None:
            return False
        try:
            threshold_val = float(threshold)
        except (TypeError, ValueError):
            return False

        if metric == 'unrealized_pnl_pct':
            if position.unrealized_pnl_pct is None:
                return False
            return position.unrealized_pnl_pct >= threshold_val
        if metric == 'current_price':
            if position.current_price is None:
                return False
            return position.current_price >= threshold_val
        return False

    def _thesis_break_hit(self, card: StrategyCard, position) -> bool:
        exit_rules = card.exit_rules or {}
        thesis_break = exit_rules.get('thesis_break') if isinstance(exit_rules, dict) else None
        if not thesis_break:
            return False
        marker = str(thesis_break).lower()
        if marker == 'always_true':
            return True
        if marker == 'drawdown_breach':
            if position.unrealized_pnl_pct is None:
                return False
            return position.unrealized_pnl_pct <= -0.20
        return False

    def _review_due(self, card: StrategyCard, asof: date) -> bool:
        if not card.review_cadence:
            return False
        cadence_days = {'weekly': 7, 'monthly': 30, 'quarterly': 90}
        days = cadence_days.get(str(card.review_cadence).lower())
        if days is None:
            return False
        last_dt = card.updated_at or card.created_at
        if last_dt is None:
            return False
        return (asof - last_dt.date()).days >= days

    def _entry_signal_hit(self, card: StrategyCard, session: Session) -> bool:
        entry_rules = card.entry_rules if isinstance(card.entry_rules, dict) else {}
        trigger_conditions = entry_rules.get('trigger_conditions') or []
        filter_conditions = entry_rules.get('filter_conditions') or []
        if not isinstance(trigger_conditions, list) or not isinstance(filter_conditions, list):
            return False

        # Current implementation supports one deterministic trigger:
        # valuation anchor metric "price" below fair_low.
        trigger_ok = False
        for cond in trigger_conditions:
            if cond != 'valuation_below_fair_low':
                continue
            if self._valuation_below_fair_low(card, session):
                trigger_ok = True
                break

        if not trigger_ok:
            return False

        # Supported filter: "always_true". Unknown filters fail closed.
        for cond in filter_conditions:
            if cond == 'always_true':
                continue
            return False
        return True

    def _valuation_below_fair_low(self, card: StrategyCard, session: Session) -> bool:
        anchor = card.valuation_anchor if isinstance(card.valuation_anchor, dict) else {}
        if not anchor:
            return False
        metric = str(anchor.get('core_metric', '')).lower()
        fair_low = anchor.get('fair_low')
        if fair_low is None:
            return False
        try:
            fair_low_value = float(fair_low)
        except (TypeError, ValueError):
            return False

        metric_value = self._get_metric_value(card.symbol, card.market, metric, session)
        if metric_value is None:
            # Fixed behavior for missing metrics: skip trigger.
            return False
        return metric_value <= fair_low_value

    def _get_metric_value(self, symbol: str, market: str, metric: str, session: Session) -> float | None:
        if metric == 'price':
            # Reuse entry_price as a stable input channel for v1 rule matching.
            row = session.scalar(
                select(StrategyCard.entry_price)
                .where(StrategyCard.symbol == symbol, StrategyCard.market == market, StrategyCard.status != 'closed')
                .order_by(StrategyCard.updated_at.desc())
                .limit(1)
            )
            return float(row) if row is not None else None

        # Map supported fundamental metrics from raw_fundamental.
        field_map = {
            'roe': RawFundamental.roe,
            'debt_ratio': RawFundamental.debt_ratio,
        }
        col = field_map.get(metric)
        if col is None:
            return None
        row = session.scalar(
            select(col)
            .where(RawFundamental.symbol == symbol, RawFundamental.market == market)
            .order_by(RawFundamental.publish_date.desc())
            .limit(1)
        )
        return float(row) if row is not None else None
