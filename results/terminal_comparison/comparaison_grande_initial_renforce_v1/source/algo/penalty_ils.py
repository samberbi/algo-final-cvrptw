"""Penalty-guided ILS with a real descent, complete coverage and feasible output."""

from dataclasses import dataclass, asdict
import math, random, time
import numpy as np
from numba import njit
from .iterated import construct, arrays, encode, decode, build_neighbors
from .optimized import solve as ils
from .profiles import production_settings
from .penalty_hybrid import route_penalties, walk
from .penalty_descent import descent
from .verify import verify


@njit(cache=True)
def metrics(
    routes, lens, travel, distance, demand, service, early, late, capacity, horizon
):
    road = cap = warp = 0.0
    for r in range(len(lens)):
        d, c, t = route_penalties(
            routes[r],
            lens[r],
            travel,
            distance,
            demand,
            service,
            early,
            late,
            capacity,
            horizon,
        )
        road += d
        cap += c
        warp += t
    return road, cap, warp


@dataclass(frozen=True)
class Settings:
    seconds: float = 60.0
    seed: int = 0
    warm_fraction: float = 0.15
    neighbor_count: int = 32
    descent_moves: int = 50
    temperature_ratio: float = 0.5

    def __post_init__(self):
        if not math.isfinite(self.seconds) or self.seconds <= 0:
            raise ValueError("Invalid time")
        if (
            not 0 <= self.warm_fraction < 1
            or self.neighbor_count < 1
            or self.descent_moves < 1
        ):
            raise ValueError("Invalid work limits")


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
    check = verify(initial, ins)
    if not check["valid"]:
        raise ValueError("Invalid initial solution")
    best = initial_cost = check["distance"] / 10
    best_routes = [list(r) for r in initial if r]
    if cfg.warm_fraction and time.perf_counter() - started < cfg.seconds:
        warm = ils(
            ins,
            production_settings(
                "ils",
                seconds=max(
                    1e-6,
                    min(
                        cfg.seconds - (time.perf_counter() - started),
                        cfg.seconds * cfg.warm_fraction,
                    ),
                ),
                seed=cfg.seed,
            ),
            best_routes,
        )
        best_routes = warm["routes"]
        best = warm["cost"]
    a, l = encode(best_routes, ins)
    ba, bl = a.copy(), l.copy()
    args = arrays(ins)
    neighbors = build_neighbors(ins, cfg.neighbor_count)
    enabled = np.ones(4, np.bool_)
    rng = random.Random(cfg.seed)
    edge = best * 10 / max(1, ins.n + len(best_routes))
    wc = 5 * edge / max(1.0, float(ins.demand[1:].mean()) if ins.n else 1.0)
    wt = 2.0
    cycles = moves = tests = 0
    cap_ok = tw_ok = 0
    last = 0
    infeasible_states = 0
    trace = [dict(elapsed_s=0.0, best=best)]
    while ins.n and time.perf_counter() - started < cfg.seconds:
        if cycles:
            strength = min(2048, 128 + 32 * (cycles - last))
            walk(
                a,
                l,
                len(l) - 1,
                *args,
                neighbors,
                strength,
                rng.randrange(2**31),
                wc,
                wt,
                cfg.temperature_ratio * edge
            )
        if time.perf_counter() - started >= cfg.seconds:
            break
        moved, tested, aa, ll, value = descent(
            a,
            l,
            *args,
            neighbors,
            cfg.descent_moves,
            2,
            rng.randrange(2**31),
            enabled,
            wc,
            wt
        )
        cycles += 1
        moves += moved
        tests += tested
        if value < best * 10 - 1e-7:
            candidate = decode(aa, ll)
            checked = verify(candidate, ins)
            if not checked["valid"] or abs(checked["distance"] - value) > 1e-5:
                raise AssertionError(checked)
            best = value / 10
            best_routes = candidate
            ba, bl = aa.copy(), ll.copy()
            last = cycles
        current, cap, warp = metrics(a, l, *args)
        cap_ok += int(cap <= 1e-8)
        tw_ok += int(warp <= 1e-8)
        infeasible_states += int(cap > 1e-8 or warp > 1e-8)
        if cycles % 10 == 0:
            wc *= 1.25 if cap_ok / 10 < 0.2 else 0.85 if cap_ok / 10 > 0.6 else 1.0
            wt *= 1.25 if tw_ok / 10 < 0.2 else 0.85 if tw_ok / 10 > 0.6 else 1.0
            wc = max(0.01, min(1e7, wc))
            wt = max(0.01, min(1e7, wt))
            cap_ok = tw_ok = 0
        if cycles - last >= 80:
            a, l = ba.copy(), bl.copy()
            last = cycles
        trace.append(
            dict(
                elapsed_s=time.perf_counter() - started,
                best=best,
                current=current / 10,
                capacity_excess=cap,
                time_warp=warp,
                capacity_weight=wc,
                time_weight=wt,
            )
        )
    check = verify(best_routes, ins)
    if not check["valid"]:
        raise AssertionError(check)
    return dict(
        status="feasible",
        engine="own-penalized-ils-v7",
        method="penalty_ils",
        settings=asdict(cfg),
        routes=best_routes,
        cost=check["distance"] / 10,
        initial_cost=initial_cost,
        metrics=check,
        vehicles=check["vehicles"],
        runtime_s=time.perf_counter() - started,
        construction_s=construction_s,
        cycles=cycles,
        moves=moves,
        tested=tests,
        temporary_infeasible_local_optima=infeasible_states,
        trace=trace,
    )
