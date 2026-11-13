"""La durée doit orienter les décisions, pas seulement changer une étiquette."""
import numpy as np
import pytest
from algo.model import Instance, Objective
from algo.verify import verify
from algo.duration import Settings, solve
from algo.duration_kernels import route_eval
from controle.exact import exact
from controle.plne import solve_plne


def example():
    return Instance('equal-distance',np.zeros((3,2)),np.array([0,2,3]),
                    np.array([0,50,40]),np.array([0,150,0]),
                    np.array([600,250,400]),
                    np.array([[0,80,50],[80,0,50],[50,50,0]],float),6.,1,600.)


def test_duration_includes_waiting_service_and_return():
    ins=example();first=verify([[1,2]],ins);second=verify([[2,1]],ins)
    assert first['distance']==second['distance']==180
    assert first['duration']==340 and second['duration']==280
    from algo.iterated import arrays
    for route in [[1,2],[2,1]]:
        valid,cost,load=route_eval(np.array(route),len(route),*arrays(ins))
        control=verify([route],ins)
        assert valid and cost==control['duration'] and load==control['routes'][0]['load']


@pytest.mark.parametrize('method',['ils','sa','hybrid'])
def test_duration_search_distinguishes_equal_distance_solutions(method):
    ins=example()
    result=solve(ins,Settings(seconds=.25,seed=12,method=method),[[1,2]])
    assert result['metrics']['valid'] and result['objective']=='duration'
    assert result['cost']==pytest.approx(28.)
    assert result['cost']==pytest.approx(result['travel']+result['waiting']+result['service'])
    assert all(b['best']<=a['best']+1e-7 for a,b in zip(result['trace'],result['trace'][1:]))


def test_duration_plne_matches_exhaustive_optimum():
    ins=example();oracle=exact(ins,Objective.DURATION)
    solved=solve_plne(ins,5,objective='duration')
    assert solved['status']=='optimal' and solved['objective']=='duration'
    assert solved['cost']==pytest.approx(oracle['score']/10)==pytest.approx(28.)


def test_external_duration_cannot_hide_waiting_by_delaying_departure():
    from algo.hgs_tuning import solve as hgs
    ins=Instance('forced-wait',np.zeros((2,2)),np.array([0,1]),np.array([0,20]),
                 np.array([0,500]),np.array([1000,800]),np.array([[0,50],[50,0]],float),2.,1,1000.)
    result=hgs(ins,.05,9,[[1]],40,objective='duration')
    assert result['cost']==57. and result['metrics']['waiting']==450


@pytest.mark.parametrize('field,value',[('seconds',0),('seed',-1),('method','unknown'),('ils_fraction',1)])
def test_invalid_duration_configuration(field,value):
    with pytest.raises(ValueError):Settings(**{field:value})


def test_web_duration_reference_is_not_mislabelled_as_an_optimality_gap(tmp_path):
    from web.experiments import make_protocol,create_campaign,campaign_path,records,frame,statistics
    from web.worker import run
    protocol=make_protocol(['C101'],[4101],.2,['ILS durée + HGS'])
    assert protocol['objective']=='duration'
    identifier=create_campaign(protocol,tmp_path);run(campaign_path(identifier,tmp_path))
    item=records(identifier,tmp_path)[0]
    assert item['valid'] and item['gap_pct'] is None
    assert item['result']['cost']==pytest.approx(item['result']['metrics']['duration']/10)
    assert item['delta_reference_pct']==pytest.approx(100*(item['result']['cost']/item['reference_duration']-1))
    assert 'not_time_optimum' in item['reference_kind']
    with pytest.raises(ValueError):statistics(frame([item]))


def test_web_rejects_mixed_objectives():
    from web.experiments import make_protocol
    with pytest.raises(ValueError):make_protocol(['C101'],[1],1.,['ILS','ILS durée'])


def test_cli_uses_duration_by_default(tmp_path):
    import json,subprocess,sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    target=tmp_path/'duration.json'
    subprocess.run([sys.executable,'cli.py','C101','--seconds','.1','--output',str(target)],
                   cwd=root,check=True,capture_output=True,text=True,timeout=60)
    result=json.loads(target.read_text())
    assert result['objective']=='duration' and result['metrics']['valid']
    assert result['cost']==pytest.approx(result['metrics']['duration']/10)


def test_public_api_optimizes_duration():
    from algo.solver import Settings as PublicSettings,solve as public_solve
    result=public_solve(example(),PublicSettings(seconds=.2,seed=12,method='ils'),[[1,2]])
    assert result['objective']=='duration' and result['cost']==pytest.approx(28.)


def test_failed_duration_runs_are_recorded_and_campaign_continues(tmp_path,monkeypatch):
    import algo.duration as duration
    from web.experiments import make_protocol,create_campaign,campaign_path,records,progress
    from web.worker import run
    protocol=make_protocol(['C101'],[4101,4102],.1,['ILS durée'])
    identifier=create_campaign(protocol,tmp_path)
    def fail(*args,**kwargs):raise RuntimeError('Failure injected by the test')
    monkeypatch.setattr(duration,'solve',fail)
    run(campaign_path(identifier,tmp_path))
    items=records(identifier,tmp_path)
    assert len(items)==2 and all(not r['valid'] for r in items)
    assert all(r['delta_reference_pct'] is None and r['gap_pct'] is None for r in items)
    assert progress(identifier,tmp_path)['status']=='completed'
