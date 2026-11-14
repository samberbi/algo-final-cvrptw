import pytest
from algo.size_policy import selected_method,solve
from algo.verify import verify
from scripts.terminal_support import DEFAULT_METHOD


@pytest.mark.parametrize('n',[0,25,50,100])
def test_small_sizes_choose_construction(n):
    assert selected_method(n)=='construction'


@pytest.mark.parametrize('n',[101,200,400,600,800,1000])
def test_above_boundary_uses_refined(n):
    assert selected_method(n)=='refined'


@pytest.mark.parametrize('n',[-1,True,100.5])
def test_size_contract(n):
    with pytest.raises(ValueError):selected_method(n)


def test_small_solution_is_feasible_and_records_policy():
    from tests.test_final_static import example
    ins=example();result=solve(ins,seed=4101,seconds=1)
    assert result['status']=='feasible'
    assert verify(result['routes'],ins)['valid']
    assert result['selected_method']=='construction' and result['objective']=='duration'
    assert result['construction']['attempts']==12
    assert result['selection_policy']['no_reference_or_gap_used']


def test_large_dispatch_forwards_budget_and_seed(monkeypatch):
    from types import SimpleNamespace
    import algo.duration_refine as refined
    received={}
    def fake(ins,seed,seconds):
        received.update(seed=seed,seconds=seconds)
        return dict(status='not_found',routes=None)
    monkeypatch.setattr(refined,'solve',fake)
    result=solve(SimpleNamespace(n=101,proven_impossible=lambda:None),seed=4102,seconds=3)
    assert result['selected_method']=='refined'
    assert received==dict(seed=4102,seconds=3)


def test_terminal_default_is_documented_size_policy():
    assert DEFAULT_METHOD=='size_based'
