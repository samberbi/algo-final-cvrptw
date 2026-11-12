"""New adapter must preserve original constraints, units and measured traces."""
import numpy as np
import pytest
from algo.model import Instance
from algo.verify import verify


def example():
    d=np.array([[0,10,20,10],[10,0,10,14],[20,10,0,22],[10,14,22,0]],float)
    return Instance('hard-tests',np.array([[0,0],[1,0],[2,0],[0,1]],float),np.array([0,1,1,1]),
        np.zeros(4),np.zeros(4),np.full(4,100.),d,2.,3,100.)


@pytest.mark.parametrize('seed',[-1,2**31,True,1.5])
def test_hybrid_settings_reject_invalid_seeds(seed):
    from algo.refined_hybrid import Settings
    from algo.hybrid_reference import Settings as ReferenceSettings
    with pytest.raises(ValueError,match='Seed'):
        Settings(seed=seed)
    with pytest.raises(ValueError,match='Seed'):
        ReferenceSettings(seed=seed)


@pytest.mark.parametrize('neighbors',[40,60,80])
def test_tuned_hgs_preserves_feasibility_and_original_cost(neighbors):
    pytest.importorskip('pyvrp')
    from algo.hgs_tuning import solve
    ins=example();old=ins.distance.copy();initial=[[1,2],[3]]
    r=solve(ins,.1,42,initial,neighbors)
    checked=verify(r['routes'],ins)
    assert checked['valid'] and r['cost']==pytest.approx(checked['distance']/10)
    assert r['cost']<=verify(initial,ins)['distance']/10
    assert np.array_equal(old,ins.distance)
    assert r['trace'][-1]['best']==r['cost'] and r['iterations']>0
    assert all(b['best']<=a['best']+1e-7 for a,b in zip(r['trace'],r['trace'][1:]))


def test_refined_pipeline_preserves_archive_and_reports_time_shares():
    pytest.importorskip('pyvrp')
    from algo.optimized import warmup
    from algo.refined_hybrid import Settings,solve
    warmup();ins=example()
    r=solve(ins,Settings(search_seconds=.2,ils_seconds=.05,seed=43),[[1,2],[3]])
    assert r['metrics']['valid'] and r['cost']==pytest.approx(verify(r['routes'],ins)['distance']/10)
    assert r['cost']<=r['components'][0]['cost']
    assert r['actual_ils_seconds']==.05 and r['actual_hgs_seconds']==pytest.approx(.15)
    assert 'external' in r['engine']


def test_refined_profile_runs_through_the_web_worker(tmp_path):
    pytest.importorskip('pyvrp')
    from web.experiments import make_protocol,create_campaign,campaign_path,records
    from web.worker import run
    protocol=make_protocol(['C101'],[44],.2,['ILS court + HGS (v9)'])
    identifier=create_campaign(protocol,tmp_path);run(campaign_path(identifier,tmp_path))
    item=records(identifier,tmp_path)[0]
    assert item['valid'] and item['result']['engine']=='our-short-ils-then-external-hgs-v9'
    assert 'not by us' in item['result']['attribution']
