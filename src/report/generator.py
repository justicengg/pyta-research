"""Daily / weekly decision report → plain-text Markdown for messaging push.

三段式格式
----------
1. 【风控状态】risk_status, violations, total_positions
2. 【决策动作】action counts (exit / trim / hold / enter / watch)
3. 【明细】     per-symbol advice lines (sorted by priority: exit first)

Weekly variant omits the per-symbol detail section.
"""
from __future__ import annotations

from src.types import DecisionReport

_ACTION_EMOJI: dict[str, str] = {
    'exit':  '🔴',
    'trim':  '🟡',
    'hold':  '🟢',
    'enter': '🔵',
    'watch': '⚪',
}

_RISK_EMOJI: dict[str, str] = {
    'ok':      '✅',
    'warning': '⚠️',
    'breach':  '🚨',
}


def _action_priority(action: str) -> int:
    return {'exit': 0, 'trim': 1, 'hold': 2, 'enter': 3, 'watch': 4}.get(action, 9)


class ReportGenerator:
    """Build text reports from a :class:`DecisionReport` for messaging push."""

    def generate_daily(self, decision: DecisionReport) -> str:
        """Return a 三段式 plain-text daily report string."""
        lines: list[str] = []

        # ── Header ─────────────────────────────────────────────────────────────
        lines.append(f'📊 每日投资简报 [{decision.asof}]')
        lines.append('')

        # ── Section 1: 风控状态 ─────────────────────────────────────────────────
        risk_emoji = _RISK_EMOJI.get(decision.risk_status, '❓')
        lines.append(
            f'【风控状态】{risk_emoji} {decision.risk_status.upper()}'
        )
        lines.append(
            f'  持仓数: {decision.total_positions}'
            f'  |  违规数: {decision.risk_violations}'
        )
        lines.append('')

        # ── Section 2: 决策动作 ─────────────────────────────────────────────────
        lines.append('【决策动作】')
        lines.append(
            f'  🔴 出场: {decision.exit_count}  '
            f'🟡 减仓: {decision.trim_count}  '
            f'🟢 持有: {decision.hold_count}  '
            f'🔵 入场: {decision.enter_count}  '
            f'⚪ 观察: {decision.watch_count}'
        )
        lines.append('')

        # ── Section 3: 明细 ─────────────────────────────────────────────────────
        if decision.advice:
            lines.append('【明细】')
            sorted_advice = sorted(
                decision.advice, key=lambda a: _action_priority(a.action)
            )
            for adv in sorted_advice:
                emoji = _ACTION_EMOJI.get(adv.action, '❓')
                parts = [
                    f'  {emoji} {adv.symbol}({adv.market})'
                    f' → {adv.action} [{adv.reason}]'
                ]
                if adv.current_price is not None:
                    parts.append(f'现价={adv.current_price:.2f}')
                if adv.stop_loss_price is not None:
                    parts.append(f'止损={adv.stop_loss_price:.2f}')
                if adv.unrealized_pnl is not None:
                    sign = '+' if adv.unrealized_pnl >= 0 else ''
                    parts.append(f'浮盈={sign}{adv.unrealized_pnl:.0f}')
                lines.append(' | '.join(parts))
            lines.append('')

        # ── Footer ──────────────────────────────────────────────────────────────
        lines.append(f'生成时间: {decision.generated_at}')
        return '\n'.join(lines)

    def generate_weekly(self, decision: DecisionReport) -> str:
        """Return a concise weekly summary (no per-symbol detail)."""
        lines: list[str] = []
        lines.append(f'📋 每周投资摘要 [{decision.asof}]')
        lines.append('')

        risk_emoji = _RISK_EMOJI.get(decision.risk_status, '❓')
        lines.append(
            f'风控: {risk_emoji} {decision.risk_status.upper()}'
            f'  |  持仓: {decision.total_positions}'
            f'  |  违规: {decision.risk_violations}'
        )
        lines.append(
            f'动作: 出场 {decision.exit_count}'
            f' / 减仓 {decision.trim_count}'
            f' / 持有 {decision.hold_count}'
            f' / 入场 {decision.enter_count}'
            f' / 观察 {decision.watch_count}'
        )
        lines.append(f'生成时间: {decision.generated_at}')
        return '\n'.join(lines)
