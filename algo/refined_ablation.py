"""Ablation explicite du partitionnement, sans modifier le moteur historique.

Les deux variantes exécutent le même planning de constructions et voisinages.
Le gain avant/après le MILP isole l'effet sur un même réservoir ; la comparaison
globale à temps limité peut aussi varier avec la charge et le temps restant.
"""
import math
import time
from .duration_refine import DurationLocalSearch
from .iterated import arrays, decode
from .savings import savings_construct
from .sequential import sequential_insert
from .route_pool import RoutePool
from .verify import verify


def solve(ins, seed=4101, seconds=5., partition=True, restarts=4):
    if not math.isfinite(seconds) or seconds<=0 or restarts<1:
        raise ValueError('Budget et nombre de redémarrages positifs requis')
    started=time.perf_counter()
    local=DurationLocalSearch(ins,seed)
    pool=RoutePool(ins,objective='duration')
    trace=[]
    cutoff=max(.1,seconds-1.)
    for restart in range(restarts):
        trial_seed=seed+10007*restart
        for constructor in ['savings','sequential']:
            if time.perf_counter()-started>=cutoff:break
            if constructor=='savings':
                matrix,lengths,ok=savings_construct(*arrays(ins),ins.vehicles,trial_seed,
                                                    0. if restart==0 else .08)
            else:
                matrix,lengths,ok=sequential_insert(*arrays(ins),ins.vehicles,trial_seed,1.,.5,0)
            if not ok:
                trace.append(dict(restart=restart,constructor=constructor,status='construction_failed'))
                continue
            routes,_=local.improve(decode(matrix,lengths),40)
            pool.add_solution(routes)
            trace.append(dict(elapsed_s=time.perf_counter()-started,best=pool.best_cost/10,
                              constructor=constructor,restart=restart))
        if pool.best_routes is None:continue
        for neighbors in [60,80,120]:
            if time.perf_counter()-started>=cutoff:break
            routes,_=local.improve(pool.best_routes,neighbors)
            pool.add_solution(routes)
            trace.append(dict(elapsed_s=time.perf_counter()-started,best=pool.best_cost/10,
                              neighbors=neighbors,restart=restart))
    if pool.best_routes is None:
        return dict(status='not_found',routes=None,trace=trace)
    before=pool.best_cost/10
    remaining=seconds-(time.perf_counter()-started)
    recombination=pool.recombine(min(1.,remaining),relative_gap=0.) if partition and remaining>.1 else None
    after=pool.best_cost/10
    routes=pool.best_routes
    if time.perf_counter()-started<seconds:
        routes,_=local.improve(routes,120)
    metrics=verify(routes,ins)
    assert metrics['valid'] and metrics['duration']/10<=before+1e-7
    return dict(status='feasible',routes=routes,cost=metrics['duration']/10,metrics=metrics,
        objective='duration',partition_enabled=partition,recombination=recombination,
        before_partition=before,after_partition=after,partition_gain=before-after,
        pool_columns=len(pool.columns),trace=trace,runtime_s=time.perf_counter()-started,
        attribution='Own constructions/pool/partition model; external PyVRP Local Search and SciPy HiGHS')
