from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pytest
from algo.model import Instance
from algo.verify import verify
from algo.solver import Settings,solve,arrays,encode,decode,warmup
from algo import kernels
from algo.data import load,reference


def tiny():
    d=np.array([[0,1,1,1],[1,0,10,10],[1,10,0,10],[1,10,10,0]],float)
    return Instance('nonmetric',np.zeros((4,2)),np.array([0,1,1,1]),np.zeros(4),
        np.zeros(4),np.full(4,100.),d,3.,3,100.)


def test_distance_repair_can_open_a_vehicle_when_it_saves_distance():
    ins=tiny();a,l=encode([[1,2]],ins)
    assert kernels.repair_fast(a,l,len(l)-1,*arrays(ins),2,0.,0)
    check=verify(decode(a,l),ins)
    assert check['valid'] and check['vehicles']==2
    assert check['distance']==14  # One vehicle would cost 22; it has no priority.


@pytest.mark.parametrize('routes,error',[
    ([[1,2]],'missing'),([[1,2],[2,3]],'duplicated'),([[1,2,4]],'invalid')])
def test_coverage_rejected(routes,error):
    assert not verify(routes,tiny())['valid']


def test_waiting_and_late_return_are_independently_checked():
    ins=tiny()
    from dataclasses import replace
    wait=replace(ins,early=np.array([0,20,0,0.]))
    checked=verify([[1],[2],[3]],wait)
    assert checked['valid'] and checked['waiting']==19
    narrow=replace(ins,late=np.array([100,0,100,100.]))
    assert not verify([[1],[2],[3]],narrow)['valid']
    horizon=replace(ins,horizon=1.,late=np.ones(4))
    assert not verify([[1],[2],[3]],horizon)['valid']


def test_capacity_and_fleet_are_hard_limits():
    from dataclasses import replace
    assert not verify([[1,2,3]],replace(tiny(),capacity=2.))['valid']
    assert not verify([[1],[2],[3]],replace(tiny(),vehicles=2))['valid']


def test_final_archive_cannot_trade_distance_for_fewer_vehicles():
    warmup();ins=tiny();initial=[[1],[2],[3]]
    result=solve(ins,Settings(seconds=.1,iterations=0),initial)
    assert result['status']=='feasible' and result['cost']<=.6+1e-8
    assert result['vehicles']==3


@pytest.mark.parametrize('name',['C101','R202','C1_10_1'])
def test_public_reference_cost_and_feasibility(name):
    ins=load(ROOT/'data/instances'/f'{name}.vrp')
    routes,cost=reference(ROOT/'data/instances'/f'{name}.sol')
    checked=verify(routes,ins)
    assert checked['valid'] and checked['distance']/10==pytest.approx(cost)


def test_kernel_matches_full_evaluation():
    ins=load(ROOT/'data/instances/C101.vrp');routes,_=reference(ROOT/'data/instances/C101.sol')
    a,l=encode(routes,ins);count,cost=kernels.total(a,l,*arrays(ins))
    check=verify(routes,ins)
    assert count==check['vehicles'] and cost==pytest.approx(check['distance'])


def test_invalid_initial_and_budget_rejected():
    with pytest.raises(ValueError):solve(tiny(),initial=[[1,2]])
    with pytest.raises(ValueError):Settings(seconds=0)


def test_teaching_case_equal_distance_different_waiting_and_duration():
    ins=Instance('example',np.array([[0,0],[8,0],[4,3]]),np.array([0,2,3]),
        np.array([0,5,4]),np.array([0,15,0]),np.array([60,25,40]),
        np.array([[0,8,5],[8,0,5],[5,5,0]]),6.,2,60.)
    forward=verify([[1,2]],ins);backward=verify([[2,1]],ins)
    assert forward['valid'] and backward['valid']
    assert forward['distance']==backward['distance']==18
    assert forward['duration']==34 and backward['duration']==28
    assert forward['waiting']==7 and backward['waiting']==1


def test_decomposition_preserves_coverage_and_never_worsens_distance():
    from ameliorations.decomposition import polish
    ins=tiny();initial=[[1],[2],[3]]
    result=polish(ins,initial,.03,seed=70)
    assert verify(result['routes'],ins)['valid']
    assert result['cost']<=.6+1e-8


def test_exhaustive_distance_oracle_allows_more_vehicles():
    from controle.exact import exact
    from algo.model import Objective
    result=exact(tiny(),Objective.DISTANCE)
    assert result['status']=='optimal' and result['score']==6
    assert len(result['routes'])==3
