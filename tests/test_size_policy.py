import pytest
from algo.size_policy import selected_method,solve
from algo.verify import verify
from scripts.terminal_support import DEFAULT_METHOD


@pytest.mark.parametrize('n',[0,25,50,100])
def test_small_sizes_include_intensification(n):
    assert selected_method(n)=='construction_ls_ils'


@pytest.mark.parametrize('n',[101,200,400,600,800,1000])
def test_above_boundary_uses_refined(n):
    assert selected_method(n)=='refined_hgs'


@pytest.mark.parametrize('n',[-1,True,100.5])
def test_size_contract(n):
    with pytest.raises(ValueError):selected_method(n)


def test_small_solution_is_feasible_and_records_policy():
    from tests.test_final_static import example
    ins=example();result=solve(ins,seed=4101,seconds=1)
    assert result['status']=='feasible'
    assert verify(result['routes'],ins)['valid']
    assert result['selected_method']=='construction_ls_ils' and result['objective']=='duration'
    assert result['construction']['attempts']==12
    assert result['selection_policy']['no_reference_or_gap_used']
    assert result['selection_policy']['version']==2
    assert result['cost']<=result['initial_cost']+1e-7
    initial=verify(result['initial_routes'],ins)
    assert initial['valid'] and abs(initial['duration']/10-result['initial_cost'])<1e-7


def test_large_dispatch_forwards_budget_and_seed(monkeypatch):
    from types import SimpleNamespace
    import algo.duration_refine as refined
    received={}
    def fake(ins,seed,seconds):
        received.update(seed=seed,seconds=seconds)
        return dict(status='not_found',routes=None)
    monkeypatch.setattr(refined,'solve',fake)
    result=solve(SimpleNamespace(n=101,proven_impossible=lambda:None),seed=4102,seconds=3)
    assert result['selected_method']=='refined_hgs'
    assert received==dict(seed=4102,seconds=3)


def test_terminal_default_is_documented_size_policy():
    assert DEFAULT_METHOD=='size_based'


def test_large_continuation_receives_incumbent_and_remaining_budget(monkeypatch):
    import algo.size_policy as policy
    import algo.duration_refine as refined
    import algo.hgs_tuning as hgs
    from tests.test_final_static import example
    ins=example()
    routes=[[1,2]]
    assert verify(routes,ins)['valid']
    received={}
    monkeypatch.setattr(policy,'selected_method',lambda n:'refined_hgs')
    def base(ins,seed,seconds):
        received['base_seconds']=seconds
        return dict(status='feasible',routes=routes)
    def continuation(ins,**kwargs):
        received.update(kwargs)
        return dict(status='feasible',routes=routes)
    monkeypatch.setattr(refined,'solve',base)
    monkeypatch.setattr(hgs,'solve',continuation)
    result=policy.solve(ins,seed=4101,seconds=30)
    assert received['base_seconds']==5
    assert 0<received['seconds']<=29
    assert received['initial']==routes and received['objective']=='duration'
    assert result['improvement']==0 and result['initial_routes']==routes
    assert 'external PyVRP' in result['attribution']


def test_large_short_budget_skips_external_continuation(monkeypatch):
    import algo.size_policy as policy
    import algo.duration_refine as refined
    import algo.hgs_tuning as hgs
    from tests.test_final_static import example
    ins=example()
    monkeypatch.setattr(policy,'selected_method',lambda n:'refined_hgs')
    monkeypatch.setattr(refined,'solve',lambda *a,**k:dict(status='feasible',routes=[[1,2]]))
    def unexpected(*a,**k):
        raise AssertionError('No HGS under a short remaining budget')
    monkeypatch.setattr(hgs,'solve',unexpected)
    result=policy.solve(ins,seconds=1)
    assert result['routes']==[[1,2]] and 'continuation' not in result
