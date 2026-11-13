"""Extension optionnelle TD : contrat natif, contraintes et archive ILS.

Ignorée dans l'environnement historique sans MAMUT ; à exécuter explicitement
avec l'environnement Dabia pour obtenir une validation complète de l'extension.
"""
from pathlib import Path
import json
import math
import random
import pytest

pytest.importorskip('mamut_routing_lib')
from mamut_routing_lib.td import load_td_instance, check_td_solution
from mamut_routing_lib.models import BenchmarkSolution
from algo.dabia import TemporalEvaluator, candidates, construct, simulate, solve

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'data/dabia2013/n25'


@pytest.fixture(scope='module')
def loaded():
    return load_td_instance(DATA/'C101.vrp.json')


@pytest.mark.parametrize('name', ['C101', 'C201', 'R101', 'R201', 'RC101', 'RC201'])
def test_reference_and_forward_simulation(name):
    ins = load_td_instance(DATA/(name+'.vrp.json'))
    ref = json.loads((DATA/(name+'.bks.Duration.json')).read_text())
    checked = check_td_solution(ins, BenchmarkSolution(instance_name=name, routes=ref['routes'], cost=ref['cost']))
    assert checked.is_valid() and checked.routing_cost == ref['cost']
    physical = simulate(ins, ref['routes'], [r.model_dump() for r in checked.route_evaluations])
    assert physical['valid']
    assert abs(physical['travel']+physical['waiting']+physical['service']-ref['cost']) < 1e-7


def test_travel_depends_on_departure(loaded):
    arc = loaded.atfs.arcs[(0, 1)]
    values = [arc.evaluate(t)-t for t in [0., 2500., 4000.]]
    assert max(values)-min(values) > 1


def test_departures_are_optimized(loaded):
    ev = TemporalEvaluator(loaded)
    _, departure = ev.evaluate((23, 22, 21))
    assert departure > 0


def test_duplicates_and_missing_rejected(loaded):
    checked = check_td_solution(loaded, BenchmarkSolution(instance_name='C101', routes=[[1]]))
    assert not checked.is_valid()
    # Le modèle Pydantic refuse déjà un doublon interne avant le contrôleur.
    with pytest.raises(ValueError, match='elementary'):
        BenchmarkSolution(instance_name='C101', routes=[[1, 1]])
    checked = check_td_solution(loaded, BenchmarkSolution(instance_name='C101', routes=[[1], [1]]))
    assert not checked.is_valid()


def test_capacity_rejected_before_timing(loaded):
    ev = TemporalEvaluator(loaded)
    assert math.isinf(ev.evaluate(tuple(range(1,26)))[0])


def test_moves_preserve_customer_multiset(loaded):
    ev = TemporalEvaluator(loaded)
    routes = construct(ev, random.Random(17))
    seen_kinds = set()
    for kind, trial in candidates(routes, random.Random(23)):
        seen_kinds.add(kind)
        assert sorted(c for r in trial for c in r) == list(range(1,26))
        assert all(trial)
    assert seen_kinds == {'relocate', 'swap', 'two_opt', 'two_opt_star'}


def test_search_without_reference_io(loaded, monkeypatch):
    # Une fois l'instance chargée, le solveur n'a besoin d'aucun fichier BKS.
    def forbidden(*args, **kwargs):
        raise AssertionError('Le solveur ne doit lire aucun fichier de référence')
    monkeypatch.setattr(Path, 'read_text', forbidden)
    result = solve(loaded, seconds=.1, seed=17)
    assert result['status'] == 'feasible'
    assert result['cost'] <= result['initial_cost']
    trace = [r['best'] for r in result['trace']]
    assert all(a >= b for a,b in zip(trace, trace[1:]))
    checked = check_td_solution(loaded, BenchmarkSolution(instance_name='C101', routes=result['routes'], cost=result['cost']))
    assert checked.is_valid()


@pytest.mark.parametrize('seconds', [0, -1, float('nan'), float('inf')])
def test_invalid_budget(loaded, seconds):
    with pytest.raises(ValueError):
        solve(loaded, seconds=seconds)
