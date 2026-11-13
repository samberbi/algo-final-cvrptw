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
