"""Strategy card generator — 大呆子（策略官）auto-fill layer.

Takes a list of ScreenerCandidate objects (from Screener.run), queries
raw_price for entry price, optionally computes ATR-based stop-loss,
builds a human-readable valuation note from derived_factors, and returns
a list of row dicts ready for insert_strategy_card.

Also renders each card to a Markdown string for human review / archiving.

Stop-loss methods (configured in settings, see FRAMEWORK.md)
------------------------------------------------------------
``pct``  — stop_loss = entry_price × (1 - stop_loss_pct)
``atr``  — stop_loss = entry_price − multiplier × ATR(window)
         ATR = average True Range over *window* trading days.
         True Range = max(high-low, |high-prev_close|, |low-prev_close|)

Auto-filled fields
------------------
- valuation_note  : formatted snapshot of available factors
- entry_price     : latest close on or before asof_date
- entry_date      : asof_date
- stop_loss_price : computed from entry_price (None if entry_price missing)

Human-filled fields (left None/placeholder)
-------------------------------------------
- thesis       : "赚什么钱？" — filled by analyst
- position_pct : target portfolio weight — filled by analyst
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import RawPrice
from src.screener.screener import ScreenerCandidate


class CardGenerator:
    """Generate draft strategy cards from screener candidates."""

    def generate(
        self,
        candidates: list[ScreenerCandidate],
        asof: date,
        session: Session,
        stop_loss_method: str = 'pct',
        stop_loss_pct: float = 0.08,
        stop_loss_atr_window: int = 14,
        stop_loss_atr_multiplier: float = 2.0,
    ) -> list[dict]:
        """Return a list of strategy_card row dicts (one per candidate)."""
        rows: list[dict] = []
        for cand in candidates:
            entry_price = self._get_entry_price(cand.symbol, cand.market, asof, session)

            if entry_price is None:
                stop_loss = None
            elif stop_loss_method == 'atr':
                atr = self._compute_atr(cand.symbol, cand.market, asof, session, stop_loss_atr_window)
                stop_loss = (entry_price - stop_loss_atr_multiplier * atr) if atr is not None else None
            else:  # 'pct'
                stop_loss = entry_price * (1.0 - stop_loss_pct)

            rows.append({
                'symbol': cand.symbol,
                'market': cand.market,
                'thesis': None,
                'position_pct': None,
                'valuation_note': self._build_valuation_note(cand.factors),
                'entry_price': entry_price,
                'entry_date': asof,
                'stop_loss_price': stop_loss,
                'status': 'draft',
                'close_reason': None,
            })
        return rows

    def to_markdown(
        self,
        card: dict,
        candidate: ScreenerCandidate,
        stop_loss_method: str = 'pct',
        stop_loss_pct: float = 0.08,
        stop_loss_atr_multiplier: float = 2.0,
    ) -> str:
        """Render a strategy card dict + its screener candidate to Markdown."""
        symbol = card['symbol']
        market = card['market']
        asof = card['entry_date']
        entry = card['entry_price']
        stop = card['stop_loss_price']

        def _fmt_price(v: float | None) -> str:
            return f'{v:.4f}' if v is not None else '*(缺失)*'

        stop_label = (
            f'固定 {stop_loss_pct * 100:.0f}%'
            if stop_loss_method == 'pct'
            else f'ATR×{stop_loss_atr_multiplier}'
        )

        lines: list[str] = [
            f'# 策略卡 — {symbol} ({market})',
            '',
            f'**生成日期**: {asof}  **状态**: Draft',
            '',
            '---',
            '',
            '## 基本信息',
            '',
            '| 字段 | 值 |',
            '|------|-----|',
            f'| 标的代码 | {symbol} ({market}) |',
            f'| 进场参考价 | {_fmt_price(entry)} |',
            f'| 止损价 | {_fmt_price(stop)}（{stop_label}）|',
            '| 目标仓位 | *(待填写)* |',
            '',
        ]

        # Valuation snapshot
        lines += [
            f'## 估值快照 (as of {asof})',
            '',
            '| 因子 | 值 |',
            '|------|-----|',
        ]
        factor_display = [
            ('roe_latest',        'ROE (最新季)',      lambda v: f'{v * 100:.2f}%'),
            ('debt_ratio_latest', '负债率',            lambda v: f'{v * 100:.2f}%'),
            ('revenue_yoy',       '营收同比',          lambda v: f'{v * 100:+.2f}%'),
            ('net_profit_yoy',    '净利同比',          lambda v: f'{v * 100:+.2f}%'),
            ('momentum_5d',       '5日涨幅',           lambda v: f'{v * 100:+.2f}%'),
            ('momentum_20d',      '20日涨幅',          lambda v: f'{v * 100:+.2f}%'),
            ('volume_ratio_5_20', '量比(5/20日)',      lambda v: f'{v:.2f}x'),
        ]
        for key, label, fmt in factor_display:
            val = candidate.factors.get(key)
            lines.append(f'| {label} | {fmt(val) if val is not None else "*(缺失)*"} |')

        lines += [
            '',
            '## 投资逻辑',
            '',
            '> *(待填写：赚什么钱？催化剂是什么？)*',
            '',
            '## 筛选命中规则',
            '',
        ]
        for r in candidate.matched_rules:
            factor_name, oper, thresh = r.split(':')
            actual = candidate.factors.get(factor_name)
            actual_str = f'{actual:.4f}' if actual is not None else '?'
            lines.append(f'- ✓ `{r}` （实际: {actual_str}）')
        for r in candidate.skipped_rules:
            lines.append(f'- ⊘ `{r}` （跳过：因子缺失）')

        lines += [
            '',
            '---',
            '',
            '*由 大呆子（策略官）自动生成 · 人工字段待填写*',
        ]
        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_entry_price(symbol: str, market: str, asof: date, session: Session) -> float | None:
        """Return the latest close price on or before asof_date."""
        stmt = (
            select(RawPrice.close)
            .where(
                RawPrice.symbol == symbol,
                RawPrice.market == market,
                RawPrice.trade_date <= asof,
                RawPrice.close.isnot(None),
            )
            .order_by(RawPrice.trade_date.desc())
            .limit(1)
        )
        result = session.scalar(stmt)
        return float(result) if result is not None else None

    @staticmethod
    def _compute_atr(
        symbol: str,
        market: str,
        asof: date,
        session: Session,
        window: int,
    ) -> float | None:
        """Compute Average True Range over *window* trading days up to asof_date."""
        stmt = (
            select(RawPrice.high, RawPrice.low, RawPrice.close)
            .where(
                RawPrice.symbol == symbol,
                RawPrice.market == market,
                RawPrice.trade_date <= asof,
                RawPrice.trade_date >= asof - timedelta(days=window * 3),  # buffer
            )
            .order_by(RawPrice.trade_date.desc())
            .limit(window + 1)  # need prev_close for each bar
        )
        prices = session.execute(stmt).fetchall()
        if len(prices) < 2:
            return None

        true_ranges: list[float] = []
        for i in range(min(window, len(prices) - 1)):
            high = float(prices[i].high or 0)
            low = float(prices[i].low or 0)
            prev_close = float(prices[i + 1].close or 0)
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)

        return sum(true_ranges) / len(true_ranges) if true_ranges else None

    @staticmethod
    def _build_valuation_note(factors: dict[str, float | None]) -> str:
        """Build a compact valuation text from available factors."""
        parts: list[str] = []
        mapping = [
            ('roe_latest',        'ROE',         lambda v: f'{v * 100:.2f}%'),
            ('debt_ratio_latest', '负债率',       lambda v: f'{v * 100:.2f}%'),
            ('revenue_yoy',       '营收同比',     lambda v: f'{v * 100:+.2f}%'),
            ('net_profit_yoy',    '净利同比',     lambda v: f'{v * 100:+.2f}%'),
            ('momentum_20d',      '20日动量',     lambda v: f'{v * 100:+.2f}%'),
            ('volume_ratio_5_20', '量比5/20日',   lambda v: f'{v:.2f}x'),
        ]
        for key, label, fmt in mapping:
            val = factors.get(key)
            if val is not None:
                parts.append(f'{label}: {fmt(val)}')
        return ' | '.join(parts) if parts else '(无可用因子数据)'
