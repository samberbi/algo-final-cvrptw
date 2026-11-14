"""Figures issues des mesures réelles, sans compléter artificiellement les traces."""
import copy
import json
import pytest
from scripts.plot_terminal_results import trace_points,render


def test_continuation_offset_is_recorded_not_guessed():
    record={'result':dict(trace=[dict(elapsed_s=1,best=34)],
        continuation={'trace':[dict(elapsed_s=.5,best=28)]},continuation_started_s=2)}
    assert [p['elapsed_s'] for p in trace_points(record)]==[1,2.5]
    del record['result']['continuation_started_s']
    assert [p['elapsed_s'] for p in trace_points(record)]==[1]
    assert not any('temperature' in p for p in trace_points(record))


def recorded(method,valid=True):
    return dict(measurement=dict(instance='manual',n=2,seed=4101,method=method,
        valid=valid,status='feasible' if valid else 'not_found',
        duration=28 if valid else None,reference_duration=30,vehicles=1 if valid else None,
        wall_s=1.,cpu_s=.9),result=dict(routes=[[2,1]] if valid else None,trace=[]))


def test_render_preserves_measures_and_does_not_invent_missing_progress(monkeypatch,tmp_path):
    from tests.test_final_static import example
    import scripts.terminal_support as support
    monkeypatch.setattr(support,'catalog',lambda:[dict(instance='manual',n=2)])
    monkeypatch.setattr(support,'load_case',lambda e:example())
    records=[recorded('ils'),recorded('size_based')];before=copy.deepcopy(records)
    assert trace_points(records[0])==[]
    page=render(tmp_path,records)
    assert records==before and page.is_file()
    assert (tmp_path/'figures/manual_2_4101.png').stat().st_size>1000
    receipt=json.loads((tmp_path/'GRAPHIQUES.json').read_text(encoding='utf-8'))
    assert receipt['groups']==1 and receipt['trials']==2 and receipt['plotting_outside_solver_timers']
    assert 'Référence dépassée' in page.read_text(encoding='utf-8')


def test_render_keeps_failed_method_visible(monkeypatch,tmp_path):
    from tests.test_final_static import example
    import scripts.terminal_support as support
    monkeypatch.setattr(support,'catalog',lambda:[dict(instance='manual',n=2)])
    monkeypatch.setattr(support,'load_case',lambda e:example())
    page=render(tmp_path,[recorded('ils',False),recorded('size_based')])
    assert 'Échec de recherche' in page.read_text(encoding='utf-8')


def test_invalid_routes_cannot_be_drawn_as_feasible(monkeypatch,tmp_path):
    from tests.test_final_static import example
    import scripts.terminal_support as support
    monkeypatch.setattr(support,'catalog',lambda:[dict(instance='manual',n=2)])
    monkeypatch.setattr(support,'load_case',lambda e:example())
    record=recorded('ils');record['result']['routes']=[[1]]
    with pytest.raises(AssertionError):render(tmp_path,[record])
