"""Sequential ILS / direct-move annealing under a single search budget."""
from dataclasses import dataclass, asdict
import math
import time
from .iterated import construct
from .optimized import solve as group_solve
from .profiles import production_settings
from .verify import verify


@dataclass(frozen=True)
class Settings:
    seconds: float = 40
    seed: int = 0
    ils_fraction: float = .25
    polish_rvnd: bool = False

    def __post_init__(self):
        if not math.isfinite(self.seconds) or self.seconds <= 0 or not 0 < self.ils_fraction < 1:
            raise ValueError("Positive finite budget and fraction in (0,1) required")


def solve(ins, settings=None, initial=None):
    cfg = settings or Settings()
    started = time.perf_counter()
    construction_s = 0.0
    if initial is None:
        initial, info = construct(ins, cfg.seed, 12)
        construction_s = info["seconds"]
    if initial is None:
        return dict(status="not_found", routes=None, runtime_s=time.perf_counter() - started)
    check = verify(initial, ins)
    if not check["valid"]:
        raise ValueError("Invalid initial solution")
    initial_cost = check["distance"] / 10
    routes = [list(r) for r in initial]
    stages, trace = [], []
    available = max(0.0, cfg.seconds - (time.perf_counter() - started))
    for index, method in enumerate(("ils", "sa")):
        remaining = cfg.seconds - (time.perf_counter() - started)
        if remaining <= 0:
            break
        budget = min(remaining, available * cfg.ils_fraction) if index == 0 else remaining
        offset = time.perf_counter() - started
        if index == 1 and cfg.polish_rvnd:
            from .ils_rvnd import Settings as RVNDSettings, solve as rvnd_solve
            result = rvnd_solve(ins, RVNDSettings(seconds=max(1e-6, budget),
                                seed=cfg.seed + 100000, adaptive=False), routes)
            method = "rvnd"
        else:
            result = group_solve(ins, production_settings(method, seconds=max(1e-6, budget),
                                                         seed=cfg.seed + index * 100000), routes)
        routes = result["routes"]
        stages.append(dict(method=method, cost=result["cost"], runtime_s=result["runtime_s"]))
        trace.extend(dict(elapsed_s=offset + p["elapsed_s"], best=p["best"], phase=method)
                     for p in result["trace"])
    checked = verify(routes, ins)
    if not checked["valid"]:
        raise AssertionError(checked)
    return dict(status="feasible", engine="ils-sa-relay-v5", method="relay",
                settings=asdict(cfg), routes=routes, cost=checked["distance"] / 10,
                initial_cost=initial_cost, metrics=checked, vehicles=checked["vehicles"],
                stages=stages, trace=trace, construction_s=construction_s,
                runtime_s=time.perf_counter() - started)
