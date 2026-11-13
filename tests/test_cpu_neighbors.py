"""Le cache doit préserver les voisins natifs, y compris les égalités et bornes."""
import pytest
from algo.data import load
from algo.duration_refine import DurationLocalSearch


@pytest.mark.parametrize('name',['C101','R1_10_5'])
def test_cached_neighbors_equal_external_reference_for_each_size(name):
    from pathlib import Path
    from pyvrp.search import NeighbourhoodParams
    root=Path(__file__).resolve().parents[1]
    ins=load(root/'data/instances'/(name+'.vrp'))
    local=DurationLocalSearch(ins,41)
    for count in [40,60,80,120,160,40]:
        expected=local.api.compute_neighbours(local.data,NeighbourhoodParams(num_neighbours=count))
        assert local.neighbors(count)==expected
        assert local.neighbors(count) is local.neighbors(count)


def test_neighbor_cache_avoids_repeated_proximity_computation(monkeypatch):
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    local=DurationLocalSearch(load(root/'data/instances/C101.vrp'),41)
    def forbidden(*args,**kwargs):
        raise AssertionError('Previously covered neighbourhood should not be recalculated')
    monkeypatch.setattr(local.api,'compute_neighbours',forbidden)
    for count in [40,60,80,120,40]:local.neighbors(count)
