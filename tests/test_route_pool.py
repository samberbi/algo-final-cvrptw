import numpy as np
import pytest

from algo.model import Instance
from algo.route_pool import RoutePool
from algo.verify import verify


def instance():
    # Deliberately nonmetric distances: improvements require route recombination.
    distance = np.full((5, 5), 20.0)
    np.fill_diagonal(distance, 0)
    distance[0, 1:] = distance[1:, 0] = 10
    distance[1, 2] = distance[2, 1] = 1
    distance[3, 4] = distance[4, 3] = 1
    return Instance(
        "pool",
        np.zeros((5, 2)),
        np.array([0, 1, 1, 1, 1]),
        np.zeros(5),
        np.zeros(5),
        np.full(5, 1000),
        distance,
        2,
        3,
        1000,
    )


def test_pool_combines_routes_from_different_parents():
    ins = instance()
    pool = RoutePool(ins)
    pool.add_solution([[1, 2], [3], [4]])
    pool.add_solution([[1], [2], [3, 4]])
    result = pool.recombine(2)
    assert result["optimal_in_pool"]
    assert result["cost"] == pytest.approx(4.2)
    assert result["cost"] < result["initial_cost"]
    assert verify(result["routes"], ins)["valid"]
    assert result["vehicles"] == 2


def test_pool_rejects_incomplete_or_infeasible_routes():
    pool = RoutePool(instance())
    for routes in ([[1, 2], [3]], [[1, 2, 3], [4]], [[1, 2], [2, 3, 4]]):
        with pytest.raises(ValueError):
            pool.add_solution(routes)
    with pytest.raises(ValueError):
        pool.recombine(1)


def test_pool_fallback_preserves_feasible_archive(monkeypatch):
    from types import SimpleNamespace
    import algo.route_pool as module

    pool = RoutePool(instance())
    parent = [[1, 2], [3], [4]]
    pool.add_solution(parent)
    monkeypatch.setattr(
        module,
        "milp",
        lambda *a, **k: SimpleNamespace(
            x=None, status=1, message="Time limit", mip_dual_bound=None
        ),
    )
    result = pool.recombine(0.001)
    assert result["fallback_to_archive"] and result["routes"] == parent
    assert result["cost"] == result["initial_cost"]


