from dataclasses import replace
import numpy as np
import pytest
from algo.model import Instance
from algo.iterated import arrays, encode, decode, build_neighbors
from algo.verify import verify
from algo import kernels
from algo.cached_local import local_search, cache_route, evaluate_tail


def example(seed):
    rng = np.random.default_rng(seed)
    travel = rng.uniform(0, 20, (9, 9))
    travel = (travel + travel.T) / 2
    np.fill_diagonal(travel, 0)
    distance = rng.uniform(0, 30, (9, 9))
    distance = (distance + distance.T) / 2
    np.fill_diagonal(distance, 0)
    demands = np.r_[0, rng.integers(1, 4, 8)]
    services = np.r_[0, rng.uniform(0, 3, 8)]
    early = np.r_[0, rng.uniform(0, 15, 8)]
    routes = [[1, 2, 3, 4], [5, 6, 7, 8]]
    capacity = float(max(sum(demands[r]) for r in routes) + 1)
    ins = Instance(
        "cache",
        rng.random((9, 2)),
        demands,
        services,
        early,
        np.full(9, 1000.0),
        travel,
        capacity,
        3,
        1000.0,
        distance,
    )
    late = ins.late.copy()
    for route in verify(routes, ins)["routes"]:
        for step in route["schedule"]:
            late[step["client"]] = step["start"] + rng.uniform(0, 12)
    return replace(ins, late=late), routes


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize("operator", range(4))
def test_cached_local_search_matches_full_evaluation(seed, operator):
    ins, parent = example(seed)
    first, lengths = encode(parent, ins)
    second, other_lengths = first.copy(), lengths.copy()
    enabled = np.zeros(4, np.bool_)
    enabled[operator] = True
    args = arrays(ins)
    neighbors = build_neighbors(ins, 8)
    before = kernels.local_search(
        first, lengths, *args, neighbors, 12, 3, seed, enabled
    )
    after = local_search(second, other_lengths, *args, neighbors, 12, 3, seed, enabled)
    assert before == after
    assert np.array_equal(lengths, other_lengths)
    assert decode(first, lengths) == decode(second, other_lengths)
    assert verify(decode(second, other_lengths), ins)["valid"]


@pytest.mark.parametrize("seed", range(8))
def test_suffix_evaluation_matches_full_clock_and_distance(seed):
    ins, parent = example(seed)
    route = np.array(parent[0], dtype=np.int64)
    depart = np.zeros((1, 10))
    road = depart.copy()
    quantity = depart.copy()
    assert cache_route(route, 4, 0, *arrays(ins), depart, road, quantity)[0]
    rng = np.random.default_rng(seed)
    for start in range(5):
        candidate = np.r_[route[:start], rng.permutation(route[start:])].astype(
            np.int64
        )
        expected = kernels.route_eval(candidate, 4, *arrays(ins))
        actual = evaluate_tail(
            candidate, 4, start, 0, *arrays(ins), depart, road, quantity
        )
        assert actual[0] == expected[0]
        if expected[0]:
            assert actual[1:] == pytest.approx(expected[1:])


def test_temporal_group_covers_whole_routes_and_obeys_size_limit():
    import random
    from algo.temporal_groups import affinity_matrix, choose_group

    ins, routes = example(14)
    selected = choose_group(ins, routes, random.Random(0), 5, affinity_matrix(ins))
    assert len(selected) == len(set(selected)) == 1
    assert sum(len(routes[r]) for r in selected) == 4
    matrix = affinity_matrix(ins)
    assert np.allclose(matrix, matrix.T)
    assert np.isinf(matrix[0]).all() and np.isinf(np.diag(matrix)).all()


def test_cache_grows_when_two_opt_star_creates_a_longer_route():
    rng = np.random.default_rng(42)
    xy = rng.uniform(0, 10, (61, 2))
    distance = np.floor(10 * np.linalg.norm(xy[:, None] - xy[None, :], axis=2))
    ins = Instance(
        "growth",
        xy,
        np.r_[0, np.ones(60)],
        np.zeros(61),
        np.zeros(61),
        np.full(61, 10000.0),
        distance,
        60.0,
        10,
        10000.0,
    )
    parent = [list(range(i, i + 6)) for i in range(1, 61, 6)]
    a, l = encode(parent, ins)
    b, other = a.copy(), l.copy()
    enabled = np.array([False, False, False, True])
    neighbors = build_neighbors(ins, 59)
    expected = kernels.local_search(a, l, *arrays(ins), neighbors, 100, 2, 42, enabled)
    actual = local_search(b, other, *arrays(ins), neighbors, 100, 2, 42, enabled)
    assert expected == actual and decode(a, l) == decode(b, other)
    assert max(other) > 11
    assert verify(decode(b, other), ins)["valid"]


@pytest.mark.parametrize(
    "cached,temporal", [(False, False), (True, False), (False, True), (True, True)]
)
def test_experimental_group_solver_preserves_complete_feasible_input(
    monkeypatch, cached, temporal
):
    from dataclasses import asdict
    from algo.data import load
    from algo.iterated import construct
    from algo.cached_iterated import warmup
    from algo.profiles import production_settings
    from algo.experimental_v6 import Settings, solve

    warmup()
    ins = load("data/instances/C101.vrp")
    parent, _ = construct(ins, 101, 1)
    original = [r[:] for r in parent]

    def forbidden(*args, **kwargs):
        raise AssertionError("Initial constructor called during improvement")

    monkeypatch.setattr(kernels, "repair_fast", forbidden)
    cfg = asdict(production_settings("ils", seconds=0.15, seed=404))
    cfg.update(group_size=30, cached_evaluation=cached, temporal_groups=temporal)
    result = solve(ins, Settings(**cfg), parent)
    assert parent == original and result["metrics"]["valid"]
    assert result["cost"] <= verify(parent, ins)["distance"] / 10 + 1e-7


def test_portfolio_selects_only_complete_feasible_routes_and_charges_three_searches():
    from algo.portfolio_v6 import Settings, solve

    ins, parent = example(42)
    original = [r[:] for r in parent]
    result = solve(
        ins, Settings(per_search_seconds=0.03, partition_seconds=0.1, seed=42), parent
    )
    assert parent == original and result["metrics"]["valid"]
    assert len(result["components"]) == 3
    assert result["nominal_search_and_partition_budget_s"] == pytest.approx(0.19)
    assert (
        result["cost"] <= min(c["result"]["cost"] for c in result["components"]) + 1e-8
    )
    assert result["cost"] <= verify(parent, ins)["distance"] / 10 + 1e-8
