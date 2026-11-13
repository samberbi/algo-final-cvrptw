"""Feasible ILS / simulated annealing on groups of complete incumbent routes.

The parent and every subproblem keep the original demands, windows and matrices.
No benchmark reference is passed to the search; no destruction/repair is used
after the optional initial construction.
"""

from dataclasses import asdict, dataclass
import math
import random
import time

import numpy as np

from . import iterated
from .model import Instance
from .verify import verify

arrays = iterated.arrays
encode = iterated.encode
decode = iterated.decode
construct = iterated.construct


@dataclass(frozen=True)
class Settings(iterated.Settings):
    decomposition: bool = True
    group_size: int = 240
    adaptive_groups: bool = True
    sub_seconds: float = 0.2
    temperature_mode: str = "edge"
    temperature_ratio: float = 0.2

    def __post_init__(self):
        super().__post_init__()
        if (
            self.group_size < 10
            or not math.isfinite(self.sub_seconds)
            or self.sub_seconds <= 0
        ):
            raise ValueError("Invalid route-group limits")
        if self.temperature_mode not in ("edge", "total"):
            raise ValueError("Invalid temperature mode")


def core_settings(config, n, seconds, seed):
    """Prépare les paramètres du moteur direct pour un sous-problème.
    En mode edge, diviser le ratio par n évite une température proportionnelle
    à toute la distance lorsque seul un petit nombre d’arcs change."""
    fields = iterated.Settings.__dataclass_fields__
    parameters = {key: value for key, value in asdict(config).items() if key in fields}
    parameters.update(seconds=seconds, seed=seed)
    if config.temperature_mode == "edge":
        parameters["temperature_ratio"] = config.temperature_ratio / max(1, n)
    return iterated.Settings(**parameters)


def select_group(ins, routes, rng, target):
    """Choisit des tournées entières autour d’un centre de tournée tiré au hasard.
    Le nombre de clients visé limite la taille, sans couper une tournée en deux."""
    centers = np.array([ins.xy[route].mean(axis=0) for route in routes])
    pivot = rng.randrange(len(routes))
    order = np.argsort(np.linalg.norm(centers - centers[pivot], axis=1))
    selected = []
    size = 0
    for index in order:
        if selected and size + len(routes[index]) > target:
            continue
        selected.append(int(index))
        size += len(routes[index])
        if len(selected) >= 12:
            break
    return selected


def solve(ins, settings=None, initial=None):
    """Optimise les tournées sous un budget global de temps réel.
    Petite instance : appel direct de l’ILS/recuit. Grande instance : résolution
    de groupes de tournées, puis contrôle de leur réintégration dans la solution.
    Sans initial, la construction fait partie de ce budget."""
    config = settings or Settings()
    if not config.decomposition or ins.n <= config.group_size:
        result = iterated.solve(
            ins, core_settings(config, ins.n, config.seconds, config.seed), initial
        )
        result["settings"] = asdict(config)
        result["engine"] = "optimized-v2-direct"
        return result

    started = time.perf_counter()
    cpu_started = time.process_time()
    deadline = started + config.seconds
    impossible = ins.proven_impossible()
    if impossible:
        return dict(
            status="proven_infeasible",
            reason=impossible,
            routes=None,
            runtime_s=time.perf_counter() - started,
            method=config.method,
            settings=asdict(config),
        )
    construction_s = 0.0
    if initial is None:
        initial, info = construct(ins, config.seed, config.construction_attempts)
        construction_s = info["seconds"]
    if initial is None:
        return dict(
            status="not_found",
            reason="construction failed",
            routes=None,
            runtime_s=time.perf_counter() - started,
            method=config.method,
            settings=asdict(config),
        )
    checked = verify(initial, ins)
    if not checked["valid"]:
        raise ValueError("Invalid initial solution")
    routes = [list(route) for route in initial if route]
    initial_cost = best = checked["distance"] / 10
    trace = [
        dict(
            elapsed_s=time.perf_counter() - started,
            best=best,
            current=best,
            iteration=0,
        )
    ]
    rng = random.Random(config.seed)
    iterations = cycles = accepted = valid_proposals = improvements = 0
    operators = np.zeros(4, dtype=np.int64)
    diagnostics = {}
    while routes and time.perf_counter() < deadline and iterations < config.iterations:
        target = config.group_size
        if config.adaptive_groups:
            target = max(120, min(360, 8 * math.ceil(ins.n / len(routes))))
        selected = select_group(ins, routes, rng, target)
        selected_set = set(selected)
        # Numérotation locale : le dépôt reste 0 ; mapping permet ensuite le retour aux identifiants originaux.
        mapping = [0] + [client for index in selected for client in routes[index]]
        reverse = {client: index for index, client in enumerate(mapping)}
        ids = np.asarray(mapping)
        # Les tournées hors du groupe consomment déjà une partie de la flotte autorisée.
        unused_fleet = ins.vehicles - (len(routes) - len(selected))
        group_fleet = min(unused_fleet, len(selected) + 3, len(mapping) - 1)
        # On extrait les matrices originales : aucune fenêtre ni demande n’est assouplie.
        group = Instance(
            "group",
            ins.xy[ids],
            ins.demand[ids],
            ins.service[ids],
            ins.early[ids],
            ins.late[ids],
            ins.travel[np.ix_(ids, ids)],
            ins.capacity,
            group_fleet,
            ins.horizon,
            ins.distance[np.ix_(ids, ids)],
        )
        start_routes = [
            [reverse[client] for client in routes[index]] for index in selected
        ]
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            break
        direct = core_settings(
            config, group.n, min(config.sub_seconds, remaining), rng.randrange(2**31)
        )
        result = iterated.solve(group, direct, start_routes)
        cycles += 1
        iterations += result.get("iterations", 0)
        accepted += result.get("accepted", 0)
        valid_proposals += result.get("valid_proposals", 0)
        operators += np.asarray(result.get("operators", [0, 0, 0, 0]))
        for key, value in result.get("diagnostics", {}).items():
            diagnostics[key] = diagnostics.get(key, 0) + value
        if result["status"] != "feasible":
            continue
        proposal = [
            route for index, route in enumerate(routes) if index not in selected_set
        ]
        proposal.extend(
            [[mapping[client] for client in route] for route in result["routes"]]
        )
        # Un sous-problème valide ne suffit pas : la solution complète est contrôlée après réintégration.
        candidate = verify(proposal, ins)
        if not candidate["valid"]:
            raise AssertionError(candidate["errors"])
        distance = candidate["distance"] / 10
        # L’archive globale ne remplace son résultat que par une amélioration de distance.
        if distance < best - 1e-8:
            routes, best = proposal, distance
            improvements += 1
        trace.append(
            dict(
                elapsed_s=time.perf_counter() - started,
                best=best,
                current=best,
                iteration=iterations,
                group_n=group.n,
            )
        )
    metrics = verify(routes, ins)
    if not metrics["valid"]:
        raise AssertionError(metrics["errors"])
    elapsed = time.perf_counter() - started
    trace.append(dict(elapsed_s=elapsed, best=best, current=best, iteration=iterations))
    return dict(
        status="feasible",
        engine="optimized-v2-groups",
        method=config.method,
        objective="distance",
        seed=config.seed,
        settings=asdict(config),
        routes=routes,
        cost=best,
        initial_cost=initial_cost,
        vehicles=metrics["vehicles"],
        metrics=metrics,
        runtime_s=elapsed,
        cpu_s=time.process_time() - cpu_started,
        construction_s=construction_s,
        trace=trace,
        iterations=iterations,
        cycles=cycles,
        accepted=accepted,
        valid_proposals=valid_proposals,
        improved=improvements,
        operators=operators.tolist(),
        diagnostics=diagnostics,
    )


def warmup():
    """Préchauffe les noyaux et SWAP* avant les résolutions chronométrées.
    Le temps de compilation est retourné séparément par les points d’entrée."""
    started = time.perf_counter()
    iterated.warmup()
    from .intensify import swap_star

    xy = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
    matrix = np.array([[0.0, 10.0, 20.0], [10.0, 0.0, 10.0], [20.0, 10.0, 0.0]])
    tiny = Instance(
        "compile",
        xy,
        np.array([0, 1, 1]),
        np.zeros(3),
        np.zeros(3),
        np.full(3, 100.0),
        matrix,
        2.0,
        2,
        100.0,
    )
    encoded, lengths = encode([[1], [2]], tiny)
    neighbors = iterated.build_neighbors(tiny, 2)
    swap_star(encoded, lengths, *arrays(tiny), neighbors, 1, 0)
    return time.perf_counter() - started
