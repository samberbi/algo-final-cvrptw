"""Comparateur indépendant OR-Tools : somme des spans, départs fixés à zéro.

Les coûts d'arcs sont nuls. L'unique coût est sum(end-start), avec la dimension
temporelle contenant trajets, services et attentes. Pas de coût de flotte ni
de makespan. Aucun départ construit par notre ILS ou aucune BKS n'est transmis.
"""
import math
import time
import numpy as np
from .verify import verify


def solve(ins,seconds=10.,seed=4101,strategy='parallel_insertion'):
    from ortools.constraint_solver import pywrapcp,routing_enums_pb2
    if not math.isfinite(seconds) or seconds<=0:raise ValueError('Budget positif requis')
    values = [ins.travel, ins.demand, ins.service, ins.early, ins.late,
              np.array([ins.capacity, ins.horizon])]
    if any(not np.array_equal(value,np.rint(value)) for value in values):
        raise ValueError('OR-Tools exige les unités entières x10 du projet, sans arrondi silencieux')
    if type(seed) is not int or not 0 <= seed < 2**31:
        raise ValueError('Graine entière positive sur 31 bits requise')
    if strategy not in ('parallel_insertion', 'path'):
        raise ValueError('Stratégie inconnue')
    impossible = ins.proven_impossible()
    if impossible:
        return dict(status='proven_infeasible',routes=None,reason=impossible,runtime_s=0.,cpu_s=0.)
    started,cpu=time.perf_counter(),time.process_time()
    manager=pywrapcp.RoutingIndexManager(ins.n+1,ins.vehicles,0)
    routing=pywrapcp.RoutingModel(manager)
    routing.solver().ReSeed(seed)
    zero=routing.RegisterTransitCallback(lambda i,j:0)
    routing.SetArcCostEvaluatorOfAllVehicles(zero)
    def duration(i,j):
        a,b=manager.IndexToNode(i),manager.IndexToNode(j)
        return int(ins.travel[a,b]+ins.service[a])
    transit=routing.RegisterTransitCallback(duration)
    routing.AddDimension(transit,int(ins.horizon),int(ins.horizon),True,'Time')
    dimension=routing.GetDimensionOrDie('Time')
    dimension.SetSpanCostCoefficientForAllVehicles(1)
    for client in range(1,ins.n+1):
        dimension.CumulVar(manager.NodeToIndex(client)).SetRange(int(ins.early[client]),int(ins.late[client]))
    for k in range(ins.vehicles):
        dimension.CumulVar(routing.Start(k)).SetValue(0)
        dimension.CumulVar(routing.End(k)).SetMax(int(ins.horizon))
    demand=routing.RegisterUnaryTransitCallback(lambda i:int(ins.demand[manager.IndexToNode(i)]))
    routing.AddDimensionWithVehicleCapacity(demand,0,[int(ins.capacity)]*ins.vehicles,True,'Capacity')
    params=pywrapcp.DefaultRoutingSearchParameters()
    choices={'parallel_insertion':routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
             'path':routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC}
    params.first_solution_strategy=choices[strategy]
    params.local_search_metaheuristic=routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.FromMilliseconds(max(1,int(seconds*1000)))
    solution=routing.SolveWithParameters(params)
    if solution is None:
        return dict(status='not_found',routes=None,runtime_s=time.perf_counter()-started,
                    cpu_s=time.process_time()-cpu,solver_status=int(routing.status()))
    routes=[]
    for k in range(ins.vehicles):
        current=routing.Start(k);route=[]
        while not routing.IsEnd(current):
            node=manager.IndexToNode(current)
            if node:route.append(node)
            current=solution.Value(routing.NextVar(current))
        if route:routes.append(route)
    metrics=verify(routes,ins)
    if not metrics['valid']:raise AssertionError(metrics['errors'])
    if abs(solution.ObjectiveValue()-metrics['duration'])>1e-6:
        raise AssertionError('Le coût OR-Tools ne correspond pas à la durée complète')
    return dict(status='feasible',objective='duration',routes=routes,cost=metrics['duration']/10,
        vehicles=len(routes),metrics=metrics,runtime_s=time.perf_counter()-started,
        cpu_s=time.process_time()-cpu,solver_status=int(routing.status()),
        native_objective=int(solution.ObjectiveValue()),seed=seed,settings=dict(strategy=strategy,seconds=seconds),
        attribution='External Google OR-Tools; own duration encoding and independent final verification',
        reference_status='Independent feasible solution, not an optimality proof')
