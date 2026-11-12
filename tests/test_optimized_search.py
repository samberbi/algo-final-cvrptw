"""Independent feasibility and exhaustive insertion checks for the new search."""

import numpy as np
import pytest

from algo.data import load
from algo.iterated import arrays, build_neighbors, construct, decode, encode
from algo.model import Instance
from algo.optimized import Settings, solve
from algo.verify import verify


def test_best_reinsertion_matches_exhaustive_feasible_positions():
    from algo.intensify import best_reinsertion

    xy = np.array([[0, 0], [2, 0], [4, 0], [1, 3]], float)
    distance = np.floor(
        10 * np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(axis=2))
    )
    ins = Instance(
        "insert",
        xy,
        np.array([0, 1, 1, 1]),
        np.zeros(4),
        np.array([0, 0, 0, 20]),
        np.array([200, 60, 140, 150]),
        distance,
        4.0,
        2,
        200.0,
    )
    candidates = [
        route
        for position in range(3)
        if verify([route := [1, 2][:position] + [3] + [1, 2][position:]], ins)["valid"]
    ]
    expected = min(verify([route], ins)["distance"] for route in candidates)
    base = np.array([1, 2, 0, 0, 0], dtype=np.int64)
    cost, position = best_reinsertion(
        base, 2, 3, *arrays(ins), np.empty(5, dtype=np.int64)
    )
    assert position >= 0 and cost == pytest.approx(expected)


def test_swap_star_preserves_unique_clients_and_cannot_worsen():
    from algo.intensify import swap_star

    ins = load("data/instances/R202.vrp")
    initial, _ = construct(ins, 401, 2)
    before = verify(initial, ins)["distance"]
    encoded, lengths = encode(initial, ins)
    moves, tested = swap_star(
        encoded, lengths, *arrays(ins), build_neighbors(ins, 24), 10, 402
    )
    check = verify(decode(encoded, lengths), ins)
    assert check["valid"] and check["distance"] <= before + 1e-7 and tested >= moves


@pytest.mark.parametrize("mode", ["geographic", "mixed"])
def test_neighbors_exclude_self_and_depot(mode):
    ins = load("data/instances/C101.vrp")
    neighbors = build_neighbors(ins, 24, mode)
    assert neighbors.shape == (101, 24)
    for client in range(1, 101):
        assert 0 not in neighbors[client] and client not in neighbors[client]
        assert len(set(neighbors[client])) == 24


@pytest.mark.parametrize("method", ["ils", "sa"])
def test_group_search_does_not_repair_or_modify_input(monkeypatch, method):
    from algo import kernels

    ins = load("data/instances/C101.vrp")
    initial, _ = construct(ins, 411, 1)
    original = [route[:] for route in initial]

    def forbidden(*args, **kwargs):
        raise AssertionError("Repair inside a route group is forbidden")

    monkeypatch.setattr(kernels, "repair_fast", forbidden)
    result = solve(
        ins,
        Settings(seconds=0.06, method=method, group_size=25, sub_seconds=0.02),
        initial,
    )
    assert initial == original and verify(result["routes"], ins)["valid"]
    assert result["cost"] <= verify(original, ins)["distance"] / 10 + 1e-7


def test_direct_diagnostics_account_for_every_attempt():
    from algo.direct import walk

    ins = load("data/instances/R202.vrp")
    initial, _ = construct(ins, 421, 1)
    encoded, lengths = encode(initial, ins)
    counters = np.zeros(7, dtype=np.int64)
    result = walk(
        encoded,
        lengths,
        len(lengths) - 1,
        *arrays(ins),
        build_neighbors(ins),
        5000,
        422,
        10.0,
        1,
        counters,
    )
    assert counters[0] == result[-1] and counters[1:].sum() == counters[0]
    assert counters[-1] == result[5] and verify(decode(encoded, lengths), ins)["valid"]
