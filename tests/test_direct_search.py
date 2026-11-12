"""New methods must preserve the strict CVRPTW contract independently."""
import numpy as np
import pytest
from algo.data import load
from algo.solver import Settings, solve, construct, warmup, encode, decode, arrays
from algo.direct import walk
from algo.verify import verify


@pytest.mark.parametrize('method',['ils','sa'])
def test_complete_solutions_archive_and_trace(method):
    warmup()
    ins=load('data/instances/R202.vrp');initial,_=construct(ins,11,2)
    start=verify(initial,ins)['distance']/10
    result=solve(ins,Settings(method=method,seconds=.15,seed=17),initial)
    check=verify(result['routes'],ins)
    assert check['valid'] and result['cost']==pytest.approx(check['distance']/10)
    assert result['cost']<=start+1e-8
    costs=[p['best'] for p in result['trace']]
    assert all(b<=a+1e-8 for a,b in zip(costs,costs[1:]))
    assert result['runtime_s']>=.15 and result['method']==method


def test_all_direct_move_types_preserve_coverage_and_feasibility():
    ins=load('data/instances/R202.vrp');initial,_=construct(ins,22,2)
    a,l=encode(initial,ins);nn=np.argsort(ins.distance,axis=1)[:,1:25].astype(np.int64)
    result=walk(a,l,len(l)-1,*arrays(ins),nn,10000,31,100.,1)
    assert verify(decode(a,l),ins)['valid']
    assert all(n>0 for n in result[7])
    assert verify(decode(result[1],result[2]),ins)['distance']==pytest.approx(result[3])


def test_methods_do_not_call_repair_during_search(monkeypatch):
    ins=load('data/instances/C101.vrp');initial,_=construct(ins,11,1)
    from algo import kernels
    def forbidden(*args,**kwargs):
        raise AssertionError('Repair must not be used after initial construction')
    monkeypatch.setattr(kernels,'repair_fast',forbidden)
    for method in ('ils','sa'):
        assert solve(ins,Settings(method=method,seconds=.05),initial)['status']=='feasible'


def test_inclusive_window_capacity_and_exact_depot_return():
    from algo.model import Instance
    from dataclasses import replace
    ins=Instance('boundaries',np.zeros((2,2)),np.array([0,2]),np.array([0,3]),
        np.array([0,5]),np.array([10,5]),np.array([[0,2],[2,0]]),2.,1,10.)
    check=verify([[1]],ins)
    assert check['valid'] and check['routes'][0]['schedule'][0]['start']==5
    assert check['routes'][0]['schedule'][0]['finish']==8 and check['makespan']==10
    from algo import kernels
    a,l=encode([[1]],ins)
    assert kernels.total(a,l,*arrays(ins))[0]==1
    # Ending service after client closing is allowed; arriving home after H is not.
    too_short=replace(ins,horizon=9.,late=np.array([9,5]))
    assert not verify([[1]],too_short)['valid']
    assert kernels.total(a,l,*arrays(too_short))[0]<0
