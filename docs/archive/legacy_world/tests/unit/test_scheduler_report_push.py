from __future__ import annotations

from datetime import date

import pytest

from src.scheduler.scheduler import PipelineScheduler
from src.types import DecisionReport


def _decision_report() -> DecisionReport:
    return DecisionReport(
        asof=date(2026, 3, 3),
        advice=[],
        risk_status='ok',
        risk_violations=0,
        total_positions=0,
        exit_count=0,
        trim_count=0,
        hold_count=0,
        enter_count=0,
        watch_count=0,
        generated_at='2026-03-03T00:00:00+00:00',
    )


def test_run_report_skips_push_when_webhook_empty(monkeypatch):
    from src.scheduler import scheduler as scheduler_mod

    monkeypatch.setattr(scheduler_mod.settings, 'feishu_webhook_url', '')
    monkeypatch.setattr(
        scheduler_mod.DecisionAdvisor,
        'evaluate',
        lambda self, **kwargs: _decision_report(),
    )
    monkeypatch.setattr(
        scheduler_mod.ReportGenerator,
        'generate_daily',
        lambda self, decision: 'daily report',
    )
    monkeypatch.setattr(
        scheduler_mod.FeishuPusher,
        'push',
        lambda self, text, webhook_url: (_ for _ in ()).throw(
            AssertionError('push should not be called when webhook is empty')
        ),
    )

    PipelineScheduler()._run_report()


def test_run_report_raises_when_push_failed(monkeypatch):
    from src.scheduler import scheduler as scheduler_mod

    monkeypatch.setattr(scheduler_mod.settings, 'feishu_webhook_url', 'https://example.com/hook')
    monkeypatch.setattr(
        scheduler_mod.DecisionAdvisor,
        'evaluate',
        lambda self, **kwargs: _decision_report(),
    )
    monkeypatch.setattr(
        scheduler_mod.ReportGenerator,
        'generate_daily',
        lambda self, decision: 'daily report',
    )
    monkeypatch.setattr(
        scheduler_mod.FeishuPusher,
        'push',
        lambda self, text, webhook_url: False,
    )

    with pytest.raises(RuntimeError, match='daily report push failed'):
        PipelineScheduler()._run_report()
