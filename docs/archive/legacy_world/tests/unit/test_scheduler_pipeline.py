"""Tests for PipelineScheduler graceful degradation."""
from __future__ import annotations

from src.scheduler.scheduler import PipelineScheduler


def test_run_once_graceful_all_steps_called(monkeypatch):
    svc = PipelineScheduler()
    called = []

    monkeypatch.setattr(svc, '_run_market', lambda: called.append('market'))
    monkeypatch.setattr(svc, '_run_fundamental', lambda: called.append('fundamental'))
    monkeypatch.setattr(svc, '_run_macro', lambda: called.append('macro'))
    monkeypatch.setattr(svc, '_run_factors', lambda: called.append('factors'))
    monkeypatch.setattr(svc, '_run_quality', lambda: called.append('quality'))
    monkeypatch.setattr(svc, '_run_queue', lambda: called.append('queue'))
    monkeypatch.setattr(svc, '_run_report', lambda: called.append('report'))

    results = svc.run_once(graceful=True)
    assert called == ['market', 'fundamental', 'macro', 'factors', 'quality', 'queue', 'report']
    assert all(results.values())


def test_run_once_graceful_one_step_fails_others_continue(monkeypatch):
    svc = PipelineScheduler()
    called = []

    def _fail():
        called.append('quality')
        raise RuntimeError('quality boom')

    monkeypatch.setattr(svc, '_run_market', lambda: called.append('market'))
    monkeypatch.setattr(svc, '_run_fundamental', lambda: called.append('fundamental'))
    monkeypatch.setattr(svc, '_run_macro', lambda: called.append('macro'))
    monkeypatch.setattr(svc, '_run_factors', lambda: called.append('factors'))
    monkeypatch.setattr(svc, '_run_quality', _fail)
    monkeypatch.setattr(svc, '_run_queue', lambda: called.append('queue'))
    monkeypatch.setattr(svc, '_run_report', lambda: called.append('report'))

    results = svc.run_once(graceful=True)
    # quality failed but queue and report still ran
    assert 'queue' in called
    assert 'report' in called
    assert results['quality'] is False
    assert results['queue'] is True
    assert results['report'] is True


def test_run_once_strict_raises_on_failure(monkeypatch):
    svc = PipelineScheduler()

    monkeypatch.setattr(svc, '_run_market', lambda: (_ for _ in ()).throw(RuntimeError('boom')))
    monkeypatch.setattr(svc, '_run_fundamental', lambda: None)
    monkeypatch.setattr(svc, '_run_macro', lambda: None)
    monkeypatch.setattr(svc, '_run_factors', lambda: None)
    monkeypatch.setattr(svc, '_run_quality', lambda: None)
    monkeypatch.setattr(svc, '_run_queue', lambda: None)
    monkeypatch.setattr(svc, '_run_report', lambda: None)

    import pytest
    with pytest.raises(RuntimeError, match='boom'):
        svc.run_once(graceful=False)


def test_run_once_returns_summary_dict(monkeypatch):
    svc = PipelineScheduler()

    monkeypatch.setattr(svc, '_run_market', lambda: None)
    monkeypatch.setattr(svc, '_run_fundamental', lambda: None)
    monkeypatch.setattr(svc, '_run_macro', lambda: None)
    monkeypatch.setattr(svc, '_run_factors', lambda: None)
    monkeypatch.setattr(svc, '_run_quality', lambda: None)
    monkeypatch.setattr(svc, '_run_queue', lambda: None)
    monkeypatch.setattr(svc, '_run_report', lambda: None)

    results = svc.run_once(graceful=True)
    assert isinstance(results, dict)
    assert set(results.keys()) == {'market', 'fundamental', 'macro', 'factors', 'quality', 'queue', 'report'}
    assert all(v is True for v in results.values())


def test_run_step_safe_retries_then_returns_false(monkeypatch):
    """_run_step_safe retries up to max_attempts, then returns False."""
    svc = PipelineScheduler()
    # Patch sleep to avoid real delays
    import src.scheduler.scheduler as sched_mod
    monkeypatch.setattr(sched_mod.time, 'sleep', lambda _: None)

    call_count = 0

    def _always_fail():
        nonlocal call_count
        call_count += 1
        raise RuntimeError('always fails')

    result = svc._run_step_safe('test_step', _always_fail, max_attempts=3)
    assert result is False
    assert call_count == 3
