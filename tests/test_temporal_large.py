"""Contrat du chargement IGP paresseux et faisabilité du moteur échantillonné."""
from pathlib import Path
import json
import math
import pytest
pytest.importorskip('mamut_routing_lib')
from mamut_routing_lib.td import load_td_instance, check_td_solution
from mamut_routing_lib.models import BenchmarkSolution
from algo.temporal_large import load_temporal, solve
ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT/'data/temporal_sizes/Lera2026/n200/Lera-C1_2_1-S2.vrp.json'


@pytest.fixture(scope='module')
def lazy():
    if not PATH.exists():pytest.skip('Lot Lera200 non téléchargé')
    return load_temporal(PATH)


def test_lazy_functions_equal_complete_materialization(lazy):
    full = load_td_instance(PATH)
    for key in [(0,1),(1,0),(7,19),(200,0),(0,200),(77,112)]:
        assert lazy.atfs.arcs[key].xs == full.atfs.arcs[key].xs
        assert lazy.atfs.arcs[key].ys == full.atfs.arcs[key].ys


def test_reference_cost_identical(lazy):
    ref = json.loads(PATH.with_name('Lera-C1_2_1-S2.bks.Duration.json').read_text())
    checked = check_td_solution(lazy,BenchmarkSolution(instance_name=lazy.instance.instance_name,routes=ref['routes'],cost=ref['cost']))
    assert checked.is_valid() and checked.routing_cost == ref['cost']


def test_lazy_bounds_and_cache(lazy):
    arc = lazy.atfs.arcs[(2,3)]
    assert lazy.atfs.arcs[(2,3)] is arc
    for key in [(0,0),(-1,1),(201,0)]:
        with pytest.raises(KeyError):lazy.atfs.arcs[key]


def test_large_solver_archive_is_feasible():
    loaded = load_td_instance(ROOT/'data/dabia2013/n25/R201.vrp.json')
    result = solve(loaded,seconds=.4,seed=4101)
    assert result['status'] == 'feasible'
    assert result['cost'] <= result['initial_cost']
    checked = check_td_solution(loaded,BenchmarkSolution(instance_name='R201',routes=result['routes'],cost=result['cost']))
    assert checked.is_valid()
    assert all(a['best']>=b['best'] for a,b in zip(result['trace'],result['trace'][1:]))


@pytest.mark.parametrize('budget',[0,-1,float('nan'),float('inf')])
def test_invalid_budget(lazy,budget):
    with pytest.raises(ValueError):solve(lazy,seconds=budget)
