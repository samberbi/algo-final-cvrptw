"""Optional ILS -> external HGS pipeline; never attributed to our own engine."""

from dataclasses import asdict, dataclass
import math
import time
from .iterated import construct
from .optimized import solve as ils
from .profiles import production_settings
from .external_reference import solve as external
from .verify import verify


@dataclass(frozen=True)
class Settings:
    search_seconds: float = 120.0
    seed: int = 0
    ils_fraction: float = 0.5

    def __post_init__(self):
        if type(self.seed) is not int or not 0 <= self.seed < 2**31:
            raise ValueError("Seed must be an integer between 0 and 2147483647")
        if not math.isfinite(self.search_seconds) or self.search_seconds <= 0:
            raise ValueError("Positive finite search allowance required")
        if not 0 < self.ils_fraction < 1:
            raise ValueError("Both search phases need a positive share")


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
            reason="Our construction failed",
            runtime_s=time.perf_counter() - started,
        )
    check = verify(initial, ins)
    if not check["valid"]:
        raise ValueError("Invalid initial solution")
    first = ils(
        ins,
        production_settings(
            "ils", seconds=cfg.search_seconds * cfg.ils_fraction, seed=cfg.seed
        ),
        initial,
    )
    second = external(
        ins,
        cfg.search_seconds * (1 - cfg.ils_fraction),
        cfg.seed + 10000,
        first["routes"],
    )
    if second["status"] != "feasible":
        raise RuntimeError("External phase failed; its failure must not be hidden")
    checked = verify(second["routes"], ins)
    if not checked["valid"] or second["cost"] > first["cost"] + 1e-7:
        raise AssertionError("External phase must preserve its feasible incumbent")
    elapsed = time.perf_counter() - started
    trace = [dict(elapsed_s=0.0, best=check["distance"] / 10, phase="construction")]
    trace.extend(
        dict(elapsed_s=construction_s + p["elapsed_s"], best=p["best"], phase="our-ils")
        for p in first.get("trace", [])
    )
    trace.append(
        dict(
            elapsed_s=construction_s + first["runtime_s"],
            best=first["cost"],
            phase="external-start",
        )
    )
    trace.append(dict(elapsed_s=elapsed, best=second["cost"], phase="external-end"))
    return dict(
        status="feasible",
        engine="our-ils-then-external-pyvrp-hgs",
        attribution="Our ILS; external HGS implemented by PyVRP, not by us",
        settings=asdict(cfg),
        routes=second["routes"],
        cost=checked["distance"] / 10,
        metrics=checked,
        vehicles=checked["vehicles"],
        initial_cost=check["distance"] / 10,
        runtime_s=elapsed,
        construction_s=construction_s,
        trace=trace,
        search_budget_s=cfg.search_seconds,
        components=[first, second],
        accounting="Two sequential search shares; actual construction and external setup additionally charged",
    )
