"""Experimental, attributed HGS adapter with explicit neighbourhood and traces.

The production reference adapter remains frozen. No BKS enters this module.
"""

import importlib
import importlib.metadata
import math
import time
import numpy as np
from .verify import verify


def solve(ins, seconds=100.0, seed=0, initial=None, neighbor_count=40):
    """Lance le HGS externe avec un voisinage configurable et une trace observée.
    Exige une solution initiale complète et réalisable ; conserve au moins sa qualité.
    Les statistiques proviennent des itérations exécutées, pas d’une interpolation.
    Le temps de préparation s’ajoute au budget de recherche seconds."""
    import pyvrp
    from pyvrp.search import NeighbourhoodParams
    from pyvrp.stop import MaxRuntime

    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Positive finite search time required")
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("External seed must be a 32-bit unsigned integer")
    if type(neighbor_count) is not int or neighbor_count < 1:
        raise ValueError("Positive integer neighbourhood required")
    if initial is None or not verify(initial, ins)["valid"]:
        raise ValueError("A complete feasible incumbent is required")
    started = time.perf_counter()
    # Refuser des valeurs non entières évite une seconde conversion qui changerait le benchmark.
    values = [ins.distance, ins.travel, ins.demand, ins.service, ins.early, ins.late]
    if any(not np.array_equal(a, np.rint(a)) for a in values):
        raise ValueError("Exact integer representation required; no rounding")
    if (
        ins.capacity != int(ins.capacity)
        or ins.horizon != int(ins.horizon)
        or ins.early[0] != 0
    ):
        raise ValueError("Integer capacity/horizon and zero depot opening required")
    clients = [
        pyvrp.Client(
            float(ins.xy[i, 0]),
            float(ins.xy[i, 1]),
            delivery=[int(ins.demand[i])],
            service_duration=int(ins.service[i]),
            tw_early=int(ins.early[i]),
            tw_late=int(ins.late[i]),
        )
        for i in range(1, ins.n + 1)
    ]
    data = pyvrp.ProblemData(
        clients,
        [
            pyvrp.Depot(
                float(ins.xy[0, 0]),
                float(ins.xy[0, 1]),
                tw_early=0,
                tw_late=int(ins.horizon),
            )
        ],
        [
            pyvrp.VehicleType(
                num_available=ins.vehicles,
                capacity=[int(ins.capacity)],
                tw_early=0,
                tw_late=int(ins.horizon),
                fixed_cost=0,
                unit_distance_cost=1,
                unit_duration_cost=0,
            )
        ],
        [ins.distance.astype(np.int64)],
        [ins.travel.astype(np.int64)],
    )
    api = importlib.import_module("pyvrp.solve")
    params = pyvrp.SolveParams(
        neighbourhood=NeighbourhoodParams(num_neighbours=neighbor_count)
    )
    rng = pyvrp.RandomNumberGenerator(seed)
    local = api.LocalSearch(
        data, rng, api.compute_neighbours(data, params.neighbourhood)
    )
    for operator in params.node_ops:
        if operator.supports(data):
            local.add_node_operator(operator(data))
    for operator in params.route_ops:
        if operator.supports(data):
            local.add_route_operator(operator(data))
    manager = pyvrp.PenaltyManager.init_from(data, params.penalty)
    population = pyvrp.Population(api.bpd, params.population)
    # La population contient notre solution réalisable et des départs aléatoires pour la diversité.
    starts = [pyvrp.Solution(data, initial)] + [
        pyvrp.Solution.make_random(data, rng)
        for _ in range(params.population.min_pop_size - 1)
    ]
    algorithm = pyvrp.GeneticAlgorithm(
        data, manager, rng, population, local, api.srex, starts, params.genetic
    )
    # La préparation est mesurée séparément ; MaxRuntime limite ensuite la recherche HGS.
    setup = time.perf_counter() - started
    output = algorithm.run(MaxRuntime(seconds), collect_stats=True, display=False)
    if not output.is_feasible():
        raise RuntimeError("External HGS failed to preserve feasible incumbent")
    routes = [list(map(int, r.visits())) for r in output.best.routes()]
    checked = verify(routes, ins)
    parent = verify(initial, ins)
    if not checked["valid"] or checked["distance"] > parent["distance"] + 1e-6:
        raise AssertionError("Invalid or worse returned archive")
    clock = 0.0
    best = parent["distance"] / 10
    trace = [dict(elapsed_s=setup, best=best, phase="external-start")]
    # Les durées et coûts ci-dessous sont réellement enregistrés par le moteur à chaque itération.
    for duration, datum in zip(output.stats.runtimes, output.stats.feas_stats):
        clock += float(duration)
        if math.isfinite(datum.best_cost):
            best = min(best, float(datum.best_cost) / 10)
        trace.append(
            dict(elapsed_s=setup + clock, best=best, phase="external-observed")
        )
    runtime = time.perf_counter() - started
    trace.append(
        dict(elapsed_s=runtime, best=checked["distance"] / 10, phase="external-end")
    )
    return dict(
        status="feasible",
        engine="external-pyvrp-" + importlib.metadata.version("pyvrp"),
        attribution="External HGS implemented by PyVRP; our adapter and independent verification",
        routes=routes,
        cost=checked["distance"] / 10,
        metrics=checked,
        vehicles=checked["vehicles"],
        runtime_s=runtime,
        setup_s=setup,
        search_budget_s=seconds,
        neighbor_count=neighbor_count,
        seed=seed,
        trace=trace,
        iterations=output.stats.num_iterations,
        collect_stats=True,
    )
