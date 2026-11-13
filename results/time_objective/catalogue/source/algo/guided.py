"""Feasible guided local search over our ILS; true objective remains distance."""

from dataclasses import dataclass, asdict
import math, time
import numpy as np
from .iterated import construct
from .optimized import solve as ils
from .profiles import production_settings
from .model import Instance
from .verify import verify


@dataclass(frozen=True)
class Settings:
    seconds: float = 60.0
    seed: int = 0
    alpha: float = 0.3
    phase_seconds: float = 0.5
    warm_fraction: float = 0.2

    def __post_init__(self):
        if any(
            not math.isfinite(x) or x <= 0
            for x in [self.seconds, self.alpha, self.phase_seconds]
        ):
            raise ValueError("Positive finite limits required")
        if not 0 <= self.warm_fraction < 1:
            raise ValueError("Invalid warm-up fraction")


def solve(ins, settings=None, initial=None):
    cfg = settings or Settings()
    started = time.perf_counter()
    construction_s = 0.0
    if initial is None:
        initial, info = construct(ins, cfg.seed, 12)
        construction_s = info["seconds"]
    if initial is None:
        return dict(
            status="not_found", routes=None, runtime_s=time.perf_counter() - started
        )
    checked = verify(initial, ins)
    if not checked["valid"]:
        raise ValueError("Invalid initial solution")
    routes = [list(r) for r in initial if r]
    best_routes = [r[:] for r in routes]
    best = initial_cost = checked["distance"] / 10
    trace = [dict(elapsed_s=0.0, best=best)]
    phases = 0
    updates = 0
    left = cfg.seconds - (time.perf_counter() - started)
    if left > 0 and cfg.warm_fraction:
        warm = ils(
            ins,
            production_settings(
                "ils",
                seconds=max(1e-6, min(left, cfg.seconds * cfg.warm_fraction)),
                seed=cfg.seed,
            ),
            routes,
        )
        routes = warm["routes"]
        best = warm["cost"]
        best_routes = [r[:] for r in routes]
        trace.extend(warm["trace"])
    penalties = np.zeros_like(ins.distance)
    weight = cfg.alpha * best * 10 / max(1, ins.n + len(routes))
    while routes and time.perf_counter() - started < cfg.seconds:
        left = cfg.seconds - (time.perf_counter() - started)
        if left <= 0:
            break
        # Temporary search costs only: travel durations and all constraints stay original.
        guided = Instance(
            ins.name,
            ins.xy,
            ins.demand,
            ins.service,
            ins.early,
            ins.late,
            ins.travel,
            ins.capacity,
            ins.vehicles,
            ins.horizon,
            ins.distance + weight * penalties,
        )
        left = cfg.seconds - (time.perf_counter() - started)
        if left <= 0:
            break
        result = ils(
            guided,
            production_settings(
                "ils",
                seconds=min(cfg.phase_seconds, left),
                seed=cfg.seed + 100003 * (phases + 1),
            ),
            routes,
        )
        routes = result["routes"]
        checked = verify(routes, ins)
        if not checked["valid"]:
            raise AssertionError(checked)
        cost = checked["distance"] / 10
        if cost < best - 1e-8:
            best = cost
            best_routes = [r[:] for r in routes]
        edges = []
        for route in routes:
            edges.extend(zip([0] + route, route + [0]))
        if edges:
            utilities = np.array(
                [ins.distance[i, j] / (1 + penalties[i, j]) for i, j in edges]
            )
            maximum = utilities.max()
            for (i, j), utility in zip(edges, utilities):
                if utility >= maximum - 1e-8 and i != j:
                    penalties[i, j] += 1
                    penalties[j, i] += 1
                    updates += 1
        phases += 1
        trace.append(
            dict(
                elapsed_s=time.perf_counter() - started,
                best=best,
                current=cost,
                penalty_updates=updates,
            )
        )
    checked = verify(best_routes, ins)
    return dict(
        status="feasible",
        engine="own-guided-ils-v7",
        method="gls",
        settings=asdict(cfg),
        routes=best_routes,
        cost=best,
        initial_cost=initial_cost,
        metrics=checked,
        vehicles=checked["vehicles"],
        trace=trace,
        phases=phases,
        penalty_updates=updates,
        runtime_s=time.perf_counter() - started,
        construction_s=construction_s,
    )
