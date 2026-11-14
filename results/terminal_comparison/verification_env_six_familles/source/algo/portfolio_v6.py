"""Three complete ILS searches and restricted partitioning; no BKS access.

The per-search limit is explicit: total time includes three searches plus the
initial construction and restricted partitioning, not one per-search budget.
"""

from dataclasses import dataclass, asdict
import math, time
from .iterated import construct
from .optimized import solve as baseline_solve
from .experimental_v6 import Settings as VariantSettings, solve as variant_solve
from .profiles import production_settings
from .route_pool import RoutePool
from .verify import verify


@dataclass(frozen=True)
class Settings:
    per_search_seconds: float = 40.0
    partition_seconds: float = 2.0
    seed: int = 1801

    def __post_init__(self):
        if any(
            not math.isfinite(t) or t <= 0
            for t in [self.per_search_seconds, self.partition_seconds]
        ):
            raise ValueError("Positive finite budgets required")


def solve(ins, settings=None, initial=None):
    cfg = settings or Settings()
    started = time.perf_counter()
    construction_s = 0.0
    if initial is None:
        initial, info = construct(ins, cfg.seed, 12)
        construction_s = info["seconds"]
    if initial is None:
        return dict(
            status="not_found",
            routes=None,
            reason="construction failed",
            runtime_s=time.perf_counter() - started,
        )
    checked = verify(initial, ins)
    if not checked["valid"]:
        raise ValueError("Invalid initial solution")
    if ins.n == 0:
        return dict(
            status="feasible",
            engine="ils-portfolio-v6",
            routes=[],
            cost=0.0,
            metrics=checked,
            vehicles=0,
            runtime_s=time.perf_counter() - started,
            settings=asdict(cfg),
            components=[],
        )
    pool = RoutePool(ins)
    components = []
    for variant in ["baseline", "combined", "cache"]:
        base = production_settings("ils", seconds=cfg.per_search_seconds, seed=cfg.seed)
        if variant == "baseline":
            result = baseline_solve(ins, base, initial)
        else:
            parameters = asdict(base)
            parameters.update(
                cached_evaluation=True, temporal_groups=variant == "combined"
            )
            result = variant_solve(ins, VariantSettings(**parameters), initial)
        pool.add_solution(result["routes"])
        components.append(dict(variant=variant, result=result))
    result = pool.recombine(cfg.partition_seconds)
    result["partition_runtime_s"] = result["runtime_s"]
    result["best_component_cost"] = result["initial_cost"]
    result["initial_cost"] = checked["distance"] / 10
    result.update(
        status="feasible",
        engine="ils-portfolio-v6",
        method="ils_portfolio",
        settings=asdict(cfg),
        components=components,
        construction_s=construction_s,
        per_search_budget_s=cfg.per_search_seconds,
        nominal_search_and_partition_budget_s=3 * cfg.per_search_seconds
        + cfg.partition_seconds,
        runtime_s=time.perf_counter() - started,
        accounting="One shared construction, three full searches, actual partitioning time; compilation excluded by caller",
    )
    return result
