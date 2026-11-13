"""Contrôles supplémentaires du contrat statique et du comparateur indépendant."""
from pathlib import Path
from dataclasses import replace
import numpy as np
import pytest
from algo.model import Instance
from algo.ortools_duration import solve
from algo.static_small import load
from algo.verify import verify
ROOT=Path(__file__).resolve().parents[1]


def example():
    return Instance('manual',np.zeros((3,2)),np.array([0,2,3]),np.array([0,50,40]),
        np.array([0,150,0]),np.array([600,250,400]),
        np.array([[0,80,50],[80,0,50],[50,50,0]],float),6.,1,600.)


def test_external_objective_is_total_duration_not_arcs_or_makespan():
    r=solve(example(),.2)
    assert r['status']=='feasible' and r['cost']==28.
    assert r['native_objective']==280
    assert r['metrics']['duration']==r['metrics']['travel']+r['metrics']['waiting']+90


def test_waiting_and_return_cannot_be_hidden():
    ins=Instance('waiting',np.zeros((2,2)),np.array([0,1]),np.array([0,20]),
        np.array([0,500]),np.array([1000,800]),np.array([[0,50],[50,0]],float),2.,2,1000.)
    result=solve(ins,.1)
    assert result['cost']==57. and result['metrics']['waiting']==450


def test_static_subinstance_is_unchanged_prefix():
    small=load(ROOT/'data/static_small/n25/C101.txt')
    from algo.data import load as original_load
    full=original_load(ROOT/'data/instances/C101.vrp')
    for field in ['xy','demand','service','early','late']:
        assert np.array_equal(getattr(small,field),getattr(full,field)[:26])
    assert np.array_equal(small.travel,full.travel[:26,:26])
    assert np.array_equal(small.travel,small.travel.T)


def test_no_silent_float_truncation():
    ins=example();matrix=ins.travel.copy();matrix[0,1]=matrix[1,0]=80.25
    with pytest.raises(ValueError,match='entières'):
        solve(replace(ins,travel=matrix),.1)


def test_exact_capacity_and_depot_boundary():
    ins=Instance('boundary',np.zeros((2,2)),np.array([0,5]),np.array([0,20]),
        np.array([0,50]),np.array([110,50]),np.array([[0,40],[40,0]],float),5.,2,110.)
    # L'ouverture de service est 50 ; retour 50+20+40=110, exactement à l'horizon.
    # La fermeture du dépôt doit être cohérente avec H.
    r=solve(ins,.1)
    assert r['cost']==11. and verify(r['routes'],ins)['valid']


def test_fractional_capacity_is_not_silently_changed():
    with pytest.raises(ValueError,match='entières'):
        solve(replace(example(),capacity=6.25),.1)


def test_no_vehicle_is_proven_impossible_without_native_crash():
    result=solve(replace(example(),vehicles=0),.1)
    assert result['status']=='proven_infeasible' and result['routes'] is None


def test_standalone_pyvrp_uses_same_duration_objective():
    from algo.pyvrp_standalone_duration import solve as standalone
    result=standalone(example(),.15,4101)
    assert result['status']=='feasible' and result['cost']==28.
    assert result['metrics']['waiting']==10  # 1 u.t. d'attente, incluse dans les 28 u.t.


@pytest.mark.parametrize('partition',[False,True])
def test_partition_ablation_preserves_verified_archive(partition):
    from algo.refined_ablation import solve as refined
    result=refined(example(),4101,.4,partition=partition,restarts=1)
    assert result['metrics']['valid'] and result['cost']==28.
    assert result['partition_gain']>=0
    assert (result['recombination'] is not None)==partition


def test_own_ils_extension_cannot_worsen_its_initial_solution():
    from algo.refined_with_ils import solve as candidate
    result=candidate(example(),4101,.2)
    assert result['metrics']['valid'] and result['cost']<=result['before_ils']
