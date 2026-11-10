import numpy as np
import pytest
from algo.model import Instance,Objective
from algo.verify import verify
from controle.plne import solve_plne
from controle.exact import exact


@pytest.mark.parametrize('zero',[False,True])
def test_actual_plne_matches_enumeration_and_handles_zero_arcs(zero):
    d=np.array([[0,10,10,10],[10,0,50,50],[10,50,0,50],[10,50,50,0]],float)
    if zero:d[:]=0
    ins=Instance('test',np.zeros((4,2)),np.array([0,1,1,1]),np.zeros(4),np.zeros(4),np.full(4,100.),d,3.,3,100.)
    result=solve_plne(ins,5)
    oracle=exact(ins,Objective.DISTANCE)
    assert result['status']=='optimal' and verify(result['routes'],ins)['valid']
    assert result['cost']==pytest.approx(oracle['score']/10)


def test_plne_proves_capacity_infeasibility():
    ins=Instance('impossible',np.zeros((3,2)),np.array([0,2,2]),np.zeros(3),np.zeros(3),np.full(3,100.),np.zeros((3,3)),3.,1,100.)
    assert solve_plne(ins,5)['status']=='proven_infeasible'
