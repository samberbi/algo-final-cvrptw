"""Explicit external PyVRP reference, never presented as our implementation."""

import time, importlib.metadata
import numpy as np
from .verify import verify


def solve(ins, seconds=40.0, seed=0, initial=None):
    import pyvrp
    from pyvrp.stop import MaxRuntime

    started = time.perf_counter()
    integer_arrays = [
        ins.distance,
        ins.travel,
        ins.demand,
        ins.service,
        ins.early,
        ins.late,
    ]
    if any(not np.array_equal(a, np.rint(a)) for a in integer_arrays):
        raise ValueError(
            "Exact integer representation required; no rounding in this adapter"
        )
    if ins.capacity != int(ins.capacity) or ins.horizon != int(ins.horizon):
        raise ValueError("Integer capacity and horizon required")
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
    setup = time.perf_counter() - started
    if initial is None:
        result = pyvrp.solve(
            data, MaxRuntime(seconds), seed=seed, collect_stats=False, display=False
        )
    else:
        from importlib import import_module

        api = import_module("pyvrp.solve")
        checked = verify(initial, ins)
        if not checked["valid"]:
            raise ValueError("Invalid initial solution")
        parameters = pyvrp.SolveParams()
        rng = pyvrp.RandomNumberGenerator(seed)
        local = api.LocalSearch(
            data, rng, api.compute_neighbours(data, parameters.neighbourhood)
        )
        for operator in parameters.node_ops:
            if operator.supports(data):
                local.add_node_operator(operator(data))
        for operator in parameters.route_ops:
            if operator.supports(data):
                local.add_route_operator(operator(data))
        manager = pyvrp.PenaltyManager.init_from(data, parameters.penalty)
        population = pyvrp.Population(api.bpd, parameters.population)
        starts = [pyvrp.Solution(data, initial)] + [
            pyvrp.Solution.make_random(data, rng)
            for _ in range(parameters.population.min_pop_size - 1)
        ]
        algorithm = pyvrp.GeneticAlgorithm(
            data, manager, rng, population, local, api.srex, starts, parameters.genetic
        )
        setup = time.perf_counter() - started
        result = algorithm.run(MaxRuntime(seconds), collect_stats=False, display=False)
    if not result.is_feasible():
        return dict(
            status="not_found", routes=None, runtime_s=time.perf_counter() - started
        )
    routes = [list(map(int, r.visits())) for r in result.best.routes()]
    checked = verify(routes, ins)
    if not checked["valid"]:
        raise AssertionError(checked)
    return dict(
        status="feasible",
        engine="external-pyvrp-" + importlib.metadata.version("pyvrp"),
        implementation="External library, not our metaheuristic",
        routes=routes,
        cost=checked["distance"] / 10,
        metrics=checked,
        vehicles=checked["vehicles"],
        runtime_s=time.perf_counter() - started,
        setup_s=setup,
        search_budget_s=seconds,
        seed=seed,
        warm_start=initial is not None,
    )
