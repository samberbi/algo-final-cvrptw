"""Constructions multiples et intensification externe en durée, sans référence.

Prototype distinct du moteur de la campagne initiale. Les recherches locales
proviennent de PyVRP 0.12.2 ; les constructions, leur orchestration et la
validation sont celles du projet. Aucun plan BKS n'entre dans la recherche.
"""
import importlib
import math
import time
import numpy as np
from .iterated import arrays, decode
from .savings import savings_construct
from .sequential import sequential_insert
from .verify import verify
from .route_pool import RoutePool


class DurationLocalSearch:
    """Réutilise les données natives ; change seulement le voisinage à explorer."""
    def __init__(self, ins, seed):
        import pyvrp
        self.ins = ins
        self.pyvrp = pyvrp
        self.api = importlib.import_module('pyvrp.solve')
        values = [ins.travel, ins.distance, ins.demand, ins.service, ins.early, ins.late]
        if any(not np.array_equal(a, np.rint(a)) for a in values):
            raise ValueError('Exact integer data required; no rounding allowed')
        if ins.capacity != int(ins.capacity) or ins.horizon != int(ins.horizon) or ins.early[0] != 0:
            raise ValueError('Integer capacity/horizon and zero depot opening required')
        clients = [pyvrp.Client(float(ins.xy[i,0]), float(ins.xy[i,1]),
                   delivery=[int(ins.demand[i])], service_duration=int(ins.service[i]),
                   tw_early=int(ins.early[i]), tw_late=int(ins.late[i])) for i in range(1,ins.n+1)]
        self.data = pyvrp.ProblemData(clients,
            [pyvrp.Depot(float(ins.xy[0,0]),float(ins.xy[0,1]),tw_early=0,tw_late=int(ins.horizon))],
            [pyvrp.VehicleType(num_available=ins.vehicles,capacity=[int(ins.capacity)],
                tw_early=0,tw_late=int(ins.horizon),start_late=0,
                fixed_cost=0,unit_distance_cost=0,unit_duration_cost=1)],
            [ins.distance.astype(np.int64)],[ins.travel.astype(np.int64)])
        params = pyvrp.SolveParams()
        self.local = self.api.LocalSearch(self.data,pyvrp.RandomNumberGenerator(seed),self.neighbors(40))
        for operator in params.node_ops:
            if operator.supports(self.data):self.local.add_node_operator(operator(self.data))
        for operator in params.route_ops:
            if operator.supports(self.data):self.local.add_route_operator(operator(self.data))
        # Toute durée réalisable est <= n*H, puisque chaque tournée non vide
        # contient un client. Une violation entière coûte davantage que ce total.
        penalty = float(ins.n*ins.horizon+1)
        self.evaluator = pyvrp.CostEvaluator([penalty],penalty,penalty)

    def neighbors(self, count):
        from pyvrp.search import NeighbourhoodParams
        return self.api.compute_neighbours(self.data,NeighbourhoodParams(num_neighbours=count))

    def improve(self, routes, neighbors=40):
        before = verify(routes,self.ins)
        if not before['valid']:raise ValueError('Feasible complete solution required')
        self.local.neighbours = self.neighbors(neighbors)
        native = self.local(self.pyvrp.Solution(self.data,routes),self.evaluator)
        result = [list(map(int,r.visits())) for r in native.routes()]
        checked = verify(result,self.ins)
        if not checked['valid'] or checked['duration'] > before['duration']+1e-7:
            raise AssertionError('Native local search did not preserve feasible duration archive')
        assert all(r.start_time()==0 for r in native.routes())
        assert abs(sum(r.duration() for r in native.routes())-checked['duration'])<1e-7
        return result,checked['duration']


def solve(ins, seed=4101, seconds=10., restarts=4):
    """Recherche à limite souple : un appel natif commencé n'est pas interrompu.

    Toutes les durées de construction/préparation/recombinaison sont mesurées.
    Le résultat expose le dépassement éventuel, sans inventer un temps plafonné.
    """
    if not math.isfinite(seconds) or seconds<=0 or restarts<1:
        raise ValueError('Positive budget and restart count required')
    started = time.perf_counter()
    local = DurationLocalSearch(ins,seed)
    pool = RoutePool(ins,objective='duration')
    trace=[]
    cutoff=max(.1,seconds-1.)
    for restart in range(restarts):
        trial_seed = seed+10007*restart
        for method in ['savings','sequential']:
            if time.perf_counter()-started >= cutoff:break
            matrix,lengths,ok = (savings_construct(*arrays(ins),ins.vehicles,trial_seed,0. if restart==0 else .08)
                if method=='savings' else sequential_insert(*arrays(ins),ins.vehicles,trial_seed,1.,.5,0))
            if not ok:
                trace.append(dict(restart=restart,constructor=method,status='construction_failed'))
                continue
            routes,value = local.improve(decode(matrix,lengths),40)
            pool.add_solution(routes)
            trace.append(dict(elapsed_s=time.perf_counter()-started,restart=restart,
                              constructor=method,best=pool.best_cost/10))
        if pool.best_routes is None:continue
        for neighbors in [60,80,120]:
            if time.perf_counter()-started >= cutoff:break
            routes,value = local.improve(pool.best_routes,neighbors)
            pool.add_solution(routes)
            trace.append(dict(elapsed_s=time.perf_counter()-started,neighbors=neighbors,best=pool.best_cost/10))
    if pool.best_routes is None:
        return dict(status='not_found',routes=None,runtime_s=time.perf_counter()-started,trace=trace)
    remaining=seconds-(time.perf_counter()-started)
    recombination=None
    if remaining>.1:
        recombination=pool.recombine(min(1.,remaining),relative_gap=0.)
    routes=pool.best_routes
    if time.perf_counter()-started<seconds:
        routes,value=local.improve(routes,120)
    checked=verify(routes,ins)
    assert checked['valid']
    elapsed=time.perf_counter()-started
    return dict(status='feasible',objective='duration',routes=routes,cost=checked['duration']/10,
                runtime_s=elapsed,requested_total_s=seconds,overrun_s=max(0.,elapsed-seconds),
                metrics=checked,trace=trace,pool_columns=len(pool.columns),recombination=recombination,
                attribution='Own constructions/orchestration/set partitioning; external PyVRP 0.12.2 local search')
