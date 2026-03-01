from src.scheduler.scheduler import PipelineScheduler


def test_scheduler_run_once_calls_pipeline_steps(monkeypatch):
    svc = PipelineScheduler()
    called = []

    monkeypatch.setattr(svc, '_run_market', lambda: called.append('market'))
    monkeypatch.setattr(svc, '_run_fundamental', lambda: called.append('fundamental'))
    monkeypatch.setattr(svc, '_run_macro', lambda: called.append('macro'))
    monkeypatch.setattr(svc, '_run_factors', lambda: called.append('factors'))
    monkeypatch.setattr(svc, '_run_quality', lambda: called.append('quality'))

    svc.run_once()
    assert called == ['market', 'fundamental', 'macro', 'factors', 'quality']
