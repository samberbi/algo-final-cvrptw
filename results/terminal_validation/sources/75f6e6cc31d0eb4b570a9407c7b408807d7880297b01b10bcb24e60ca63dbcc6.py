"""Profil de reprise courte : construction renforcée puis budget HGS explicite.

La solution est calculée à neuf, sans lire de BKS ou de solution archivée.
Les temps mesurés incluent construction, préparation et vérification finale.
"""
import math
import time
from .duration_refine import solve as refine
from .hgs_tuning import solve as hgs
from .verify import verify


def solve(ins,seed=4101,construction_seconds=10.,hgs_seconds=5.,neighbors=80):
    if not all(math.isfinite(x) and x>0 for x in [construction_seconds,hgs_seconds]):
        raise ValueError('Positive finite phase budgets required')
    start=time.perf_counter();cpu=time.process_time()
    first=refine(ins,seed,seconds=construction_seconds,restarts=4)
    if first['status']!='feasible':
        return dict(status='not_found',routes=None,runtime_s=time.perf_counter()-start,
                    cpu_s=time.process_time()-cpu,components=[first])
    second=hgs(ins,hgs_seconds,seed+30000,first['routes'],neighbors,objective='duration')
    check=verify(second['routes'],ins)
    assert check['valid'] and check['duration']<=first['metrics']['duration']+1e-7
    return dict(status='feasible',objective='duration',method='duration_quick',routes=second['routes'],
        cost=check['duration']/10,metrics=check,vehicles=check['vehicles'],
        runtime_s=time.perf_counter()-start,cpu_s=time.process_time()-cpu,
        hgs_search_s=hgs_seconds,construction_limit_s=construction_seconds,neighbors=neighbors,
        components=[first,second],
        attribution='Own strengthened construction/cache/route pool; external PyVRP local search and HGS')
