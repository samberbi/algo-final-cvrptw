"""Global feasible descent before localized ILS; no unassigned customers."""
import time
import random
import numpy as np
from . import kernels
from .iterated import arrays,encode,decode,build_neighbors
from .intensify import swap_star
from .verify import verify


def descend(ins,routes,seconds=5.,seed=0,with_swap=True):
    started=time.perf_counter();deadline=started+seconds;rng=random.Random(seed)
    encoded,lengths=encode(routes,ins)
    args=arrays(ins);neighbors=build_neighbors(ins,64,'geographic')
    enabled=np.ones(4,np.bool_);moves=tested=0
    while time.perf_counter()<deadline:
        changes,evaluations=kernels.local_search(encoded,lengths,*args,neighbors,30,3,rng.randrange(2**31),enabled)
        moves+=changes;tested+=evaluations
        if changes==0:
            if not with_swap or time.perf_counter()>=deadline:break
            changes,evaluations=swap_star(encoded,lengths,*args,neighbors,5,rng.randrange(2**31))
            moves+=changes;tested+=evaluations
            if changes==0:break
    result=decode(encoded,lengths);checked=verify(result,ins)
    if not checked['valid']:raise AssertionError(checked)
    return dict(routes=result,cost=checked['distance']/10,runtime_s=time.perf_counter()-started,moves=moves,tested=tested)
