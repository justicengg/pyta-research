"""Unit tests for src/report/generator.py and src/report/pusher.py.

Test matrix
-----------
TestReportGeneratorDailyEmpty      — empty advice → valid header, no detail lines
TestReportGeneratorDailyRiskOk     — ok status shows ✅
TestReportGeneratorDailyRiskBreach — breach status shows 🚨 and violation count
TestReportGeneratorDailyActions    — exit/enter/hold advice lines present
TestReportGeneratorDailyCounts     — action count labels match advice list
TestReportGeneratorWeekly          — weekly format: shorter, no per-symbol arrow
TestFeishuPusherSuccess            — HTTP 200 → True, request sent once
TestFeishuPusherNon200             — HTTP 4xx → False
TestFeishuPusherNetworkError       — requests raises → False
TestFeishuPusherEmptyUrl           — empty webhook → False, no HTTP call
TestFeishuPusherPayload            — correct JSON payload sent to requests.post
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.report.generator import ReportGenerator
from src.report.pusher import FeishuPusher
from src.types import DecisionAdvice, DecisionReport

# ── constants ─────────────────────────────────────────────────────────────────

ASOF = date(2026, 3, 1)
GENERATED_AT = '2026-03-01T10:00:00+00:00'
WEBHOOK = 'https://open.feishu.cn/open-apis/bot/v2/hook/test-token'

GEN = ReportGenerator()
PUSHER = FeishuPusher()


# ── helpers ───────────────────────────────────────────────────────────────────

def _advice(
    symbol: str,
    market: str = 'CN',
    action: str = 'hold',
    reason: str = 'within_limits',
    current_price: float | None = None,
    stop_loss_price: float | None = None,
    unrealized_pnl: float | None = None,
) -> DecisionAdvice:
    has_position = action not in ('enter', 'watch')
    return DecisionAdvice(
        symbol=symbol,
        market=market,
        action=action,
        reason=reason,
        net_shares=100.0 if has_position else None,
        avg_cost=10.0 if has_position else None,
        current_price=current_price,
        unrealized_pnl=unrealized_pnl,
        unrealized_pnl_pct=None,
        card_id=None,
        card_status=None,
        stop_loss_price=stop_loss_price,
    )


def _report(
    advice: list[DecisionAdvice] | None = None,
    risk_status: str = 'ok',
    risk_violations: int = 0,
) -> DecisionReport:
    advice = advice or []
    counts: dict[str, int] = {a: 0 for a in ('exit', 'trim', 'hold', 'enter', 'watch')}
    for a in advice:
        counts[a.action] += 1
    return DecisionReport(
        asof=ASOF,
        advice=advice,
        risk_status=risk_status,
        risk_violations=risk_violations,
        total_positions=sum(1 for a in advice if a.action in ('exit', 'trim', 'hold')),
        exit_count=counts['exit'],
        trim_count=counts['trim'],
        hold_count=counts['hold'],
        enter_count=counts['enter'],
        watch_count=counts['watch'],
        generated_at=GENERATED_AT,
    )


# ── TestReportGeneratorDailyEmpty ─────────────────────────────────────────────

class TestReportGeneratorDailyEmpty:
    def test_contains_date(self):
        text = GEN.generate_daily(_report())
        assert '2026-03-01' in text

    def test_contains_risk_status_label(self):
        text = GEN.generate_daily(_report())
        assert 'OK' in text

    def test_no_per_symbol_detail_lines(self):
        """When advice is empty the 【明细】 section is omitted (no → arrow lines)."""
        text = GEN.generate_daily(_report())
        assert '→' not in text


# ── TestReportGeneratorDailyRiskOk ────────────────────────────────────────────

class TestReportGeneratorDailyRiskOk:
    def test_ok_emoji_present(self):
        text = GEN.generate_daily(_report(risk_status='ok'))
        assert '✅' in text


# ── TestReportGeneratorDailyRiskBreach ────────────────────────────────────────

class TestReportGeneratorDailyRiskBreach:
    def test_breach_emoji_present(self):
        text = GEN.generate_daily(_report(risk_status='breach', risk_violations=2))
        assert '🚨' in text

    def test_violation_count_shown(self):
        text = GEN.generate_daily(_report(risk_status='breach', risk_violations=3))
        assert '3' in text


# ── TestReportGeneratorDailyActions ───────────────────────────────────────────

class TestReportGeneratorDailyActions:
    def test_exit_symbol_in_report(self):
        advice = [_advice('AAA', action='exit', reason='stop_loss_hit',
                          stop_loss_price=8.0, current_price=7.0)]
        text = GEN.generate_daily(_report(advice))
        assert 'AAA' in text
        assert 'exit' in text

    def test_enter_action_appears(self):
        advice = [_advice('BBB', market='US', action='enter', reason='card_active')]
        text = GEN.generate_daily(_report(advice))
        assert 'enter' in text

    def test_stop_loss_price_formatted(self):
        advice = [_advice('CCC', action='exit', stop_loss_price=8.0, current_price=7.5)]
        text = GEN.generate_daily(_report(advice))
        assert '8.00' in text

    def test_positive_pnl_shown_with_plus_sign(self):
        advice = [_advice('DDD', action='hold', current_price=12.0, unrealized_pnl=200.0)]
        text = GEN.generate_daily(_report(advice))
        assert '+200' in text


# ── TestReportGeneratorDailyCounts ────────────────────────────────────────────

class TestReportGeneratorDailyCounts:
    def test_counts_match_advice(self):
        advice = [
            _advice('A', action='exit'),
            _advice('B', action='hold'),
            _advice('C', market='US', action='enter'),
            _advice('D', market='CN', action='watch'),
        ]
        text = GEN.generate_daily(_report(advice))
        assert '出场: 1' in text
        assert '持有: 1' in text
        assert '入场: 1' in text
        assert '观察: 1' in text


# ── TestReportGeneratorWeekly ─────────────────────────────────────────────────

class TestReportGeneratorWeekly:
    def test_weekly_contains_date(self):
        text = GEN.generate_weekly(_report())
        assert '2026-03-01' in text

    def test_weekly_shorter_than_daily_with_same_data(self):
        advice = [_advice(str(i), action='hold') for i in range(5)]
        r = _report(advice)
        assert len(GEN.generate_weekly(r)) < len(GEN.generate_daily(r))


# ── TestFeishuPusherSuccess ───────────────────────────────────────────────────

class TestFeishuPusherSuccess:
    def test_returns_true_on_200(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch('src.report.pusher.requests.post', return_value=mock_resp) as mock_post:
            result = PUSHER.push('hello', WEBHOOK)
        assert result is True
        mock_post.assert_called_once()


# ── TestFeishuPusherNon200 ────────────────────────────────────────────────────

class TestFeishuPusherNon200:
    def test_returns_false_on_4xx(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = 'bad request'
        with patch('src.report.pusher.requests.post', return_value=mock_resp):
            result = PUSHER.push('hello', WEBHOOK)
        assert result is False

    def test_returns_false_on_5xx(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = 'internal server error'
        with patch('src.report.pusher.requests.post', return_value=mock_resp):
            result = PUSHER.push('hello', WEBHOOK)
        assert result is False


# ── TestFeishuPusherNetworkError ──────────────────────────────────────────────

class TestFeishuPusherNetworkError:
    def test_returns_false_on_connection_error(self):
        with patch('src.report.pusher.requests.post',
                   side_effect=ConnectionError('connection refused')):
            result = PUSHER.push('hello', WEBHOOK)
        assert result is False

    def test_returns_false_on_timeout(self):
        import requests as _req
        with patch('src.report.pusher.requests.post',
                   side_effect=_req.exceptions.Timeout('timed out')):
            result = PUSHER.push('hello', WEBHOOK)
        assert result is False


# ── TestFeishuPusherEmptyUrl ──────────────────────────────────────────────────

class TestFeishuPusherEmptyUrl:
    def test_empty_url_returns_false(self):
        result = PUSHER.push('hello', '')
        assert result is False

    def test_empty_url_makes_no_http_call(self):
        with patch('src.report.pusher.requests.post') as mock_post:
            PUSHER.push('hello', '')
        mock_post.assert_not_called()


# ── TestFeishuPusherPayload ───────────────────────────────────────────────────

class TestFeishuPusherPayload:
    def test_correct_json_payload_and_url(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch('src.report.pusher.requests.post', return_value=mock_resp) as mock_post:
            PUSHER.push('test message', WEBHOOK)
        args, kwargs = mock_post.call_args
        url = args[0] if args else kwargs.get('url')
        payload = kwargs.get('json')
        assert url == WEBHOOK
        assert payload == {'msg_type': 'text', 'content': {'text': 'test message'}}
