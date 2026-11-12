import itertools
import numpy as np
import pytest
from algo.model import Instance
from algo.iterated import arrays, build_neighbors, encode, decode, construct
from algo.verify import verify
from algo.rvnd import exchange_blocks


@pytest.mark.parametrize("seed", range(12))
def test_block_exchange_matches_exhaustive_existence(seed):
    rng = np.random.default_rng(seed)
    xy = rng.uniform(0, 10, (9, 2))
    distance = np.floor(10 * np.linalg.norm(xy[:, None] - xy[None, :], axis=2))
    late = np.full(9, 1000.0)
    if seed % 2:
        late[4] = sum(distance[a, b] for a, b in zip([0, 1, 2, 3], [1, 2, 3, 4]))
        late[8] = sum(distance[a, b] for a, b in zip([0, 5, 6, 7], [5, 6, 7, 8]))
    ins = Instance(
        "blocks",
        xy,
        np.r_[0, np.ones(8)],
        np.zeros(9),
        np.zeros(9),
        late,
        distance,
        5,
        2,
        1000,
    )
    parent = [[1, 2, 3, 4], [5, 6, 7, 8]]
    cost = verify(parent, ins)["distance"]
    possible = False
    for a, b in [(0, 1), (1, 0)]:
        for p, q, sa, sb in itertools.product(range(4), range(4), [1, 2], [1, 2]):
            if sa == sb == 1 or p + sa > 4 or q + sb > 4:
                continue
            candidate = [r[:] for r in parent]
            candidate[a] = parent[a][:p] + parent[b][q : q + sb] + parent[a][p + sa :]
            candidate[b] = parent[b][:q] + parent[a][p : p + sa] + parent[b][q + sb :]
            checked = verify(candidate, ins)
            possible |= checked["valid"] and checked["distance"] < cost - 1e-8
    work, lengths = encode(parent, ins)
    changed, _ = exchange_blocks(work, lengths, *arrays(ins), build_neighbors(ins, 8))
    checked = verify(decode(work, lengths), ins)
    assert bool(changed) == possible
    assert checked["valid"]
    assert checked["distance"] <= cost + 1e-8


def test_search_never_calls_partial_solution_operators(monkeypatch):
    from algo import kernels
    from algo.data import load
    from algo.ils_rvnd import Settings, solve, warmup

    warmup()
    ins = load("data/instances/R202.vrp")
    parent, _ = construct(ins, 42, 2)
    original = [r[:] for r in parent]

    def forbidden(*args, **kwargs):
        raise AssertionError("Partial-solution operator called during search")

    monkeypatch.setattr(kernels, "repair_fast", forbidden)
    assert not hasattr(kernels, "destroy_fast")
    result = solve(ins, Settings(seconds=0.3, seed=21), parent)
    assert result["metrics"]["valid"] and parent == original
    assert result["cost"] <= verify(parent, ins)["distance"] / 10
    assert all(
        b["best"] <= a["best"] for a, b in zip(result["trace"], result["trace"][1:])
    )
