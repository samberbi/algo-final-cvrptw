"""ILS with restricted set partitioning of its own feasible route archive."""
from dataclasses import dataclass, asdict
import math
import time
from .iterated import construct
from .optimized import solve as group_solve
from .profiles import production_settings
from .route_pool import RoutePool


@dataclass(frozen=True)
class Settings:
    seconds: float = 40
    seed: int = 0
    phases: int = 4

    def __post_init__(self):
        if not math.isfinite(self.seconds) or self.seconds <= 0 or self.phases < 1:
            raise ValueError("Positive finite time and phases required")


def solve(ins, settings=None, initial=None):
    cfg = settings or Settings()
    started = time.perf_counter()
    construction_s = 0.0
    if initial is None:
        initial, info = construct(ins, cfg.seed, 12)
        construction_s = info["seconds"]
    if initial is None:
        return dict(status="not_found", routes=None, runtime_s=time.perf_counter() - started)
    pool = RoutePool(ins)
    pool.add_solution(initial)
    initial_cost = pool.best_cost / 10
    routes = [list(r) for r in initial]
    reserve = min(5.0, cfg.seconds * .05)
    search_budget = max(0.0, cfg.seconds - (time.perf_counter() - started) - reserve)
    trace, stages = [], []
    for index in range(cfg.phases):
        remaining = cfg.seconds - (time.perf_counter() - started) - reserve
        if remaining <= 0:
            break
        offset = time.perf_counter() - started
        result = group_solve(ins, production_settings("ils", seconds=min(remaining, search_budget / cfg.phases),
                                                      seed=cfg.seed + index * 100000), routes)
        routes = result["routes"]
        pool.add_solution(routes)
        stages.append(dict(cost=result["cost"], runtime_s=result["runtime_s"]))
        trace.extend(dict(elapsed_s=offset + p["elapsed_s"], best=p["best"], phase="ils")
                     for p in result["trace"])
    remaining = cfg.seconds - (time.perf_counter() - started)
    if remaining > 0:
        result = pool.recombine(remaining)
    else:
        from .verify import verify
        checked = verify(pool.best_routes, ins)
        result = dict(routes=pool.best_routes, cost=pool.best_cost / 10,
                      vehicles=checked["vehicles"], metrics=checked)
    result.update(status="feasible", engine="ils-sp-v5", method="ils_sp", settings=asdict(cfg),
                  initial_cost=initial_cost, construction_s=construction_s, stages=stages,
                  runtime_s=time.perf_counter() - started)
    trace.append(dict(elapsed_s=result["runtime_s"], best=result["cost"], phase="partition"))
    result["trace"] = trace
    return result
