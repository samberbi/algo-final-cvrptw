"""Campaign execution, cancellation, failure accounting and dashboard navigation."""
import time

import pandas as pd
import pytest

from web.experiments import (ROOT, PROFILES, atomic_json, campaign_path, create_campaign,
                             frame, launch, make_protocol, progress, read_json, records, statistics, stop)


def test_protocol_rejects_invalid_parameters():
    for kwargs in [dict(instances=['../../secret']), dict(seeds=[11, 11]), dict(seconds=float('nan')),
                   dict(profiles=['unknown']), dict(polish_seconds=-1), dict(seeds=[-1])]:
        args = dict(instances=['C101'], seeds=[11], seconds=.1, profiles=[next(iter(PROFILES))])
        args.update(kwargs)
        with pytest.raises(ValueError):
            make_protocol(**args)


def test_real_detached_campaign(tmp_path):
    protocol = make_protocol(['C101'], [11, 22], .1, [next(iter(PROFILES))], .05)
    identifier = create_campaign(protocol, tmp_path)
    launch(identifier, tmp_path)
    with pytest.raises(FileExistsError):
        launch(identifier, tmp_path)
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        state = progress(identifier, tmp_path)
        if state['status'] not in {'queued', 'warming', 'running'}:
            break
        time.sleep(.1)
    assert state['status'] == 'completed', state
    items = records(identifier, tmp_path)
    assert len(items) == 2 and all(r['valid'] for r in items)
    assert all(r['result']['metrics']['valid'] for r in items)
    assert all(abs(r['gap_pct'] - 100 * (r['result']['cost'] / r['reference_distance'] - 1)) < 1e-9 for r in items)
    assert all(r['result']['runtime_s'] >= .1 for r in items)
    assert statistics(frame(items))['runs'].sum() == 2


def test_stop_keeps_completed_results(tmp_path):
    protocol = make_protocol(['C101'], [11], .1, [next(iter(PROFILES))])
    identifier = create_campaign(protocol, tmp_path)
    stop(identifier, tmp_path)
    from web.worker import run
    run(campaign_path(identifier, tmp_path))
    assert read_json(campaign_path(identifier, tmp_path) / 'progress.json')['status'] == 'stopped'
    assert records(identifier, tmp_path) == []


def test_failures_not_counted_as_low_gaps():
    df = pd.DataFrame([
        dict(instance='C101', profile='test', status='feasible', valid=True, reference_distance=100., gap_pct=2., runtime_s=1.),
        dict(instance='C101', profile='test', status='error', valid=False, reference_distance=100., gap_pct=None, runtime_s=1.),
    ])
    row = statistics(df).iloc[0]
    assert row.runs == 2 and row.feasible == 1 and row.under5 == 1 and row.mean_gap == 2


def test_worker_records_error_and_continues(tmp_path, monkeypatch):
    from web import worker
    protocol = make_protocol(['C101'], [11], .1, [next(iter(PROFILES))])
    identifier = create_campaign(protocol, tmp_path)
    def fail(*args, **kwargs):
        raise RuntimeError('Deliberate test failure')
    monkeypatch.setattr(worker, 'solve', fail)
    worker.run(campaign_path(identifier, tmp_path))
    item = records(identifier, tmp_path)[0]
    assert item['result']['status'] == 'error' and not item['valid'] and item['gap_pct'] is None
    assert progress(identifier, tmp_path)['completed'] == 1


def test_streamlit_pages():
    pytest.importorskip('streamlit')
    pytest.importorskip('plotly')
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / 'web/app.py'), default_timeout=30).run()
    assert not at.exception
    for label in at.sidebar.radio[0].options[1:]:
        at.sidebar.radio[0].set_value(label).run()
        assert not at.exception, [e.message for e in at.exception]
    at.selectbox[0].select_index(1).run()
    assert not at.exception
    assert any('80' in m.value for m in at.metric)
