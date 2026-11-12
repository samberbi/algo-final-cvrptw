from dataclasses import replace
import numpy as np
import pytest
from algo.model import Instance
from algo.iterated import arrays, encode, decode, build_neighbors
from algo.verify import verify
from algo.penalty_hybrid import route_penalties, walk


def example():
    d = np.array(
        [[0, 10, 20, 10], [10, 0, 10, 14], [20, 10, 0, 22], [10, 14, 22, 0]], float
    )
    return Instance(
        "guide",
        np.array([[0, 0], [1, 0], [2, 0], [0, 1]], float),
        np.array([0, 1, 1, 1]),
        np.zeros(4),
        np.zeros(4),
        np.full(4, 100.0),
        d,
        2.0,
        3,
        100.0,
    )


def test_time_warp_zero_matches_original_feasibility_and_cost():
    import itertools
    from algo.model import route_metrics

    base = example()
    cases = [
        base,
        replace(base, late=np.array([100.0, 10.0, 20.0, 15.0])),
        replace(base, horizon=35.0, late=np.full(4, 35.0)),
    ]
    for ins in cases:
        for length in range(1, 4):
            for route in itertools.permutations(range(1, 4), length):
                d, c, t = route_penalties(
                    np.array(route, np.int64), length, *arrays(ins)
                )
                expected = route_metrics(list(route), ins)
                assert (c <= 1e-8 and t <= 1e-8) == (expected is not None)
                if expected:
                    assert d == pytest.approx(expected["distance"])


def test_penalty_moves_keep_complete_coverage_and_feasible_archive():
    ins = example()
    a, l = encode([[1, 2], [3]], ins)
    result = walk(
        a,
        l,
        len(l) - 1,
        *arrays(ins),
        build_neighbors(ins, 3),
        5000,
        123,
        0.01,
        0.01,
        100.0
    )
    assert sorted(c for r in decode(a, l) for c in r) == [1, 2, 3]
    assert sum(l > 0) <= ins.vehicles
    ba, bl, cost, *_ = result
    check = verify(decode(ba, bl), ins)
    assert check["valid"] and check["distance"] == pytest.approx(cost)
    assert result[7] > 0, "The test must actually explore infeasible working states"


def test_guided_search_does_not_modify_original_data():
    from algo.guided import Settings, solve
    from algo.optimized import warmup

    warmup()
    ins = example()
    matrix = ins.distance.copy()
    parent = [[1, 2], [3]]
    result = solve(
        ins, Settings(seconds=0.15, seed=4, warm_fraction=0, phase_seconds=0.02), parent
    )
    assert np.array_equal(ins.distance, matrix)
    assert result["metrics"]["valid"]
    assert result["cost"] == pytest.approx(
        verify(result["routes"], ins)["distance"] / 10
    )
    assert result["cost"] <= verify(parent, ins)["distance"] / 10


def test_penalty_hybrid_returns_only_original_feasible_metrics():
    from algo.penalty_hybrid import Settings, solve

    ins = example()
    parent = [[1, 2], [3]]
    walk(
        *encode(parent, ins),
        2,
        *arrays(ins),
        build_neighbors(ins, 3),
        1,
        0,
        1.0,
        1.0,
        1.0
    )
    result = solve(ins, Settings(seconds=0.2, seed=9, warm_fraction=0), parent)
    assert (
        result["metrics"]["valid"]
        and result["cost"] <= verify(parent, ins)["distance"] / 10
    )


@pytest.mark.parametrize('name',['C101','R202'])
def test_large_penalties_match_original_strict_local_search(name):
    from algo.data import load
    from algo.iterated import construct
    from algo import kernels
    from algo.penalty_descent import descent
    ins=load('data/instances/'+name+'.vrp');parent,_=construct(ins,42,1)
    a,l=encode(parent,ins);b,m=a.copy(),l.copy();neighbors=build_neighbors(ins,24);enabled=np.ones(4,np.bool_)
    old=kernels.local_search(a,l,*arrays(ins),neighbors,12,2,42,enabled)
    new=descent(b,m,*arrays(ins),neighbors,12,2,42,enabled,1e9,1e9)
    assert old[0]==new[0] and decode(a,l)==decode(b,m)
    assert verify(decode(new[2],new[3]),ins)['valid']


def test_penalized_descent_keeps_feasible_archive_when_current_is_infeasible():
    from algo.penalty_descent import descent
    ins=example();a,l=encode([[1,2],[3]],ins)
    result=descent(a,l,*arrays(ins),build_neighbors(ins,3),30,2,4,np.ones(4,np.bool_),0.,0.)
    assert sorted(c for r in decode(a,l) for c in r)==[1,2,3]
    assert verify(decode(result[2],result[3]),ins)['valid']
    assert not verify(decode(a,l),ins)['valid']


def test_penalized_ils_returns_true_feasible_distance():
    from algo.penalty_ils import Settings,solve
    ins=example();parent=[[1,2],[3]]
    result=solve(ins,Settings(seconds=.2,seed=5,warm_fraction=0),parent)
    assert result['metrics']['valid']
    assert result['cost']==pytest.approx(verify(result['routes'],ins)['distance']/10)
    assert result['cost']<=verify(parent,ins)['distance']/10


def test_bounded_perturbation_limits_accepted_moves():
    ins = example()
    a, l = encode([[1, 2], [3]], ins)
    result = walk(a, l, len(l)-1, *arrays(ins), build_neighbors(ins, 3),
                  5000, 12, .01, .01, 100., 4)
    assert result[6] == 4
    assert sorted(c for r in decode(a, l) for c in r) == [1, 2, 3]


def test_intensive_ils_returns_true_feasible_distance():
    from algo.intensive_ils import Settings, solve
    ins = example()
    parent = [[1, 2], [3]]
    result = solve(ins, Settings(seconds=.2, seed=6, warm_fraction=0), parent)
    assert result['metrics']['valid']
    assert result['cost'] == pytest.approx(verify(result['routes'], ins)['distance']/10)
    assert result['cost'] <= verify(parent, ins)['distance']/10


@pytest.mark.parametrize('initial', [None, [[1, 2], [3]]])
def test_optional_external_reference_cost_and_attribution(initial):
    pytest.importorskip('pyvrp')
    from algo.external_reference import solve
    ins = example()
    result = solve(ins, seconds=.1, seed=42, initial=initial)
    assert result['status'] == 'feasible'
    assert result['engine'].startswith('external-pyvrp-')
    assert result['implementation'] == 'External library, not our metaheuristic'
    checked = verify(result['routes'], ins)
    assert checked['valid']
    assert result['cost'] == pytest.approx(checked['distance']/10)


def test_external_reference_refuses_to_round_input():
    pytest.importorskip('pyvrp')
    from algo.external_reference import solve
    ins = example()
    distance = ins.distance.copy()
    distance[1, 2] = distance[2, 1] = 10.5
    fractional = replace(ins, distance=distance)
    with pytest.raises(ValueError, match='no rounding'):
        solve(fractional, seconds=.1)


def test_optional_hybrid_preserves_independently_verified_incumbent():
    pytest.importorskip('pyvrp')
    from algo.hybrid_reference import Settings, solve
    from algo.optimized import warmup
    warmup()
    ins = example()
    result = solve(ins, Settings(search_seconds=.2, seed=19), [[1, 2], [3]])
    for phase in result['components']:
        checked = verify(phase['routes'], ins)
        assert checked['valid']
        assert phase['cost'] == pytest.approx(checked['distance']/10)
    assert result['cost'] <= result['components'][0]['cost']
    assert 'external' in result['engine'] and 'not by us' in result['attribution']
