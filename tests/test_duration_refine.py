import numpy as np
import pytest
from algo.model import Instance
from algo.route_pool import RoutePool
from algo.duration_refine import solve


def example():
    matrix=np.array([[0,80,50],[80,0,50],[50,50,0]],float)
    return Instance('duration-choice',np.zeros((3,2)),np.array([0,2,3]),
        np.array([0,50,40]),np.array([0,150,0]),np.array([600,250,400]),matrix,6,1,600)


def test_route_pool_selects_duration_when_distances_tie():
    pool=RoutePool(example(),objective='duration')
    pool.add_solution([[1,2]])
    pool.add_solution([[2,1]])
    result=pool.recombine(2)
    assert result['routes']==[[2,1]]
    assert result['cost']==pytest.approx(28.)
    assert result['objective']=='duration'


def test_refinement_counts_waiting_keeps_zero_departure_and_feasibility():
    result=solve(example(),seed=4101,seconds=2,restarts=1)
    assert result['status']=='feasible'
    assert result['metrics']['valid']
    assert result['cost']==pytest.approx(28.)
    assert result['metrics']['duration']==pytest.approx(280.)
