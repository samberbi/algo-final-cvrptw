"""ILS followed by penalty-guided complete-state annealing.

Temporary working states may violate load/time constraints. Coverage and fleet
are invariant; only independently verified feasible states enter the archive.
"""

from dataclasses import dataclass, asdict
import math, time, random
import numpy as np
from numba import njit
from .iterated import construct, arrays, encode, decode, build_neighbors
from .optimized import solve as ils
from .profiles import production_settings
from . import kernels
from .verify import verify


@njit(cache=True)
def route_penalties(
    seq, length, travel, distance, demand, service, early, late, capacity, horizon
):
    clock = road = load = warp = 0.0
    previous = 0
    for p in range(length):
        client = seq[p]
        load += demand[client]
        begin = max(clock + travel[previous, client], early[client])
        if begin > late[client] + 1e-8:
            warp += begin - late[client]
            begin = late[client]
        clock = begin + service[client]
        road += distance[previous, client]
        previous = client
    if length:
        clock += travel[previous, 0]
        road += distance[previous, 0]
    if clock > horizon + 1e-8:
        warp += clock - horizon
    return road, max(0.0, load - capacity), warp


@njit(cache=True)
def walk(
    routes,
    lens,
    limit,
    travel,
    distance,
    demand,
    service,
    early,
    late,
    capacity,
    horizon,
    neighbors,
    trials,
    seed,
    capacity_weight,
    time_weight,
    temperature,
):
    np.random.seed(seed)
    n = len(demand) - 1
    owner = np.full(n + 1, -1, np.int64)
    where = np.zeros(n + 1, np.int64)
    roads = np.zeros(limit)
    excess = np.zeros(limit)
    warps = np.zeros(limit)
    for r in range(limit):
        roads[r], excess[r], warps[r] = route_penalties(
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
        for p in range(lens[r]):
            owner[routes[r, p]] = r
            where[routes[r, p]] = p
    current = roads.sum()
    cap = excess.sum()
    tw = warps.sum()
    best = current if cap <= 1e-8 and tw <= 1e-8 else np.inf
    ba, bl = routes.copy(), lens.copy()
    first = np.empty(n + 2, np.int64)
    second = np.empty(n + 2, np.int64)
    accepted = infeasible = feasible = 0
    for iteration in range(trials):
        if not n:
            break
        i = 1 + np.random.randint(n)
        a = owner[i]
        p = where[i]
        if a < 0:
            continue
        if neighbors.shape[1] and np.random.random() < 0.85:
            j = neighbors[i, np.random.randint(neighbors.shape[1])]
        else:
            j = 1 + np.random.randint(n)
        if j <= 0 or j == i or owner[j] < 0:
            continue
        b = owner[j]
        q = where[j]
        op = np.random.randint(4)
        la, lb = lens[a], lens[b]
        na, nb = la, lb
        first[:la] = routes[a, :la]
        second[:lb] = routes[b, :lb]
        if op == 0:
            if np.random.random() < 0.03:
                for r in range(limit):
                    if lens[r] == 0:
                        b = r
                        q = 0
                        lb = 0
                        nb = 0
                        break
            if a == b:
                continue
            size = 2 if p + 2 <= la and np.random.random() < 0.25 else 1
            position = min(lb, q + np.random.randint(2))
            first[:p] = routes[a, :p]
            first[p : la - size] = routes[a, p + size : la]
            second[:position] = routes[b, :position]
            second[position : position + size] = routes[a, p : p + size]
            second[position + size : lb + size] = routes[b, position:lb]
            na, nb = la - size, lb + size
        elif op == 1:
            if a == b:
                first[p], first[q] = first[q], first[p]
            else:
                first[p] = j
                second[q] = i
        elif op == 2:
            if la < 2:
                continue
            other = np.random.randint(la)
            lo, hi = min(p, other), max(p, other)
            if lo == hi:
                continue
            for z in range(hi - lo + 1):
                first[lo + z] = routes[a, hi - z]
            b = a
        else:
            if a == b:
                continue
            na, nb = p + lb - q, q + la - p
            first[:p] = routes[a, :p]
            first[p:na] = routes[b, q:lb]
            second[:q] = routes[b, :q]
            second[q:nb] = routes[a, p:la]
        da, ca, ta = route_penalties(
            first, na, travel, distance, demand, service, early, late, capacity, horizon
        )
        db = cb = tb = 0.0
        if b != a:
            db, cb, tb = route_penalties(
                second,
                nb,
                travel,
                distance,
                demand,
                service,
                early,
                late,
                capacity,
                horizon,
            )
        dd = da - roads[a] + (db - roads[b] if a != b else 0.0)
        dc = ca - excess[a] + (cb - excess[b] if a != b else 0.0)
        dt = ta - warps[a] + (tb - warps[b] if a != b else 0.0)
        delta = dd + capacity_weight * dc + time_weight * dt
        if delta > 1e-9 and np.random.random() >= math.exp(
            -min(745.0, delta / max(temperature, 1e-12))
        ):
            continue
        routes[a, :na] = first[:na]
        lens[a] = na
        roads[a] = da
        excess[a] = ca
        warps[a] = ta
        if a != b:
            routes[b, :nb] = second[:nb]
            lens[b] = nb
            roads[b] = db
            excess[b] = cb
            warps[b] = tb
        current += dd
        cap += dc
        tw += dt
        accepted += 1
        is_feasible = cap <= 1e-8 and tw <= 1e-8
        if is_feasible:
            feasible += 1
        else:
            infeasible += 1
        for r in (a, b):
            for z in range(lens[r]):
                owner[routes[r, z]] = r
                where[routes[r, z]] = z
        if is_feasible and current < best - 1e-8:
            best = current
            ba = routes.copy()
            bl = lens.copy()
    return (
        ba,
        bl,
        best,
        current,
        max(0.0, cap),
        max(0.0, tw),
        accepted,
        infeasible,
        feasible,
    )


@dataclass(frozen=True)
class Settings:
    seconds: float = 60.0
    seed: int = 0
    warm_fraction: float = 0.25
    temperature_ratio: float = 0.25
    initial_penalty_scale: float = 1.0
    neighbor_count: int = 40

    def __post_init__(self):
        if not math.isfinite(self.seconds) or self.seconds <= 0:
            raise ValueError("Positive finite seconds required")
        if not 0 <= self.warm_fraction < 1:
            raise ValueError("Invalid warm fraction")
        if self.neighbor_count < 1 or any(
            not math.isfinite(v) or v <= 0
            for v in [self.temperature_ratio, self.initial_penalty_scale]
        ):
            raise ValueError("Invalid search settings")


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
    initial_cost = checked["distance"] / 10
    best_routes = [list(r) for r in initial if r]
    best = initial_cost
    trace = [dict(elapsed_s=0.0, best=best)]
    warm_s = 0.0
    remaining = cfg.seconds - (time.perf_counter() - started)
    if remaining > 0 and cfg.warm_fraction:
        warm = ils(
            ins,
            production_settings(
                "ils",
                seconds=max(1e-6, min(remaining, cfg.seconds * cfg.warm_fraction)),
                seed=cfg.seed,
            ),
            best_routes,
        )
        best_routes = warm["routes"]
        best = warm["cost"]
        warm_s = warm["runtime_s"]
    a, l = encode(best_routes, ins)
    ba, bl = a.copy(), l.copy()
    args = arrays(ins)
    neighbors = build_neighbors(ins, cfg.neighbor_count)
    edge = best * 10 / max(1, ins.n + len(best_routes))
    wc = (
        cfg.initial_penalty_scale
        * 5
        * edge
        / max(1.0, float(ins.demand[1:].mean()) if ins.n else 1.0)
    )
    wt = cfg.initial_penalty_scale * 2.0
    rng = random.Random(cfg.seed)
    batches = accepted = infeasible = feasible = 0
    cap_ok = tw_ok = 0
    last = 0
    while ins.n and time.perf_counter() - started < cfg.seconds:
        progress = min(1.0, (time.perf_counter() - started) / cfg.seconds)
        temp = max(1e-9, cfg.temperature_ratio * edge * 0.01**progress)
        aa, ll, value, current, cap, tw, acc, inf, fea = walk(
            a, l, len(l) - 1, *args, neighbors, 4096, rng.randrange(2**31), wc, wt, temp
        )
        batches += 1
        accepted += acc
        infeasible += inf
        feasible += fea
        cap_ok += int(cap <= 1e-8)
        tw_ok += int(tw <= 1e-8)
        if value < best * 10 - 1e-7:
            candidate = decode(aa, ll)
            check = verify(candidate, ins)
            if not check["valid"] or abs(check["distance"] - value) > 1e-5:
                raise AssertionError(check)
            best_routes = candidate
            best = value / 10
            ba, bl = aa.copy(), ll.copy()
            last = batches
        if (
            batches % 10 == 0
            and cap <= 1e-8
            and tw <= 1e-8
            and time.perf_counter() - started < cfg.seconds
        ):
            kernels.local_search(
                a,
                l,
                *args,
                neighbors,
                10,
                2,
                rng.randrange(2**31),
                np.ones(4, np.bool_)
            )
            check = verify(decode(a, l), ins)
            if not check["valid"]:
                raise AssertionError(check)
            if check["distance"] / 10 < best - 1e-8:
                best = check["distance"] / 10
                best_routes = decode(a, l)
                ba, bl = a.copy(), l.copy()
                last = batches
        if batches % 25 == 0:
            wc *= 1.3 if cap_ok / 25 < 0.25 else 0.85 if cap_ok / 25 > 0.6 else 1.0
            wt *= 1.3 if tw_ok / 25 < 0.25 else 0.85 if tw_ok / 25 > 0.6 else 1.0
            wc = min(1e7, max(0.01, wc))
            wt = min(1e7, max(0.01, wt))
            cap_ok = tw_ok = 0
        if batches - last >= 100:
            a, l = ba.copy(), bl.copy()
            last = batches
        if batches % 10 == 0:
            trace.append(
                dict(
                    elapsed_s=time.perf_counter() - started,
                    best=best,
                    current=current / 10,
                    capacity_excess=cap,
                    time_warp=tw,
                    capacity_weight=wc,
                    time_weight=wt,
                )
            )
    checked = verify(best_routes, ins)
    if not checked["valid"]:
        raise AssertionError(checked)
    trace.append(dict(elapsed_s=time.perf_counter() - started, best=best))
    return dict(
        status="feasible",
        engine="own-penalty-hybrid-v7",
        method="penalty_hybrid",
        settings=asdict(cfg),
        routes=best_routes,
        cost=checked["distance"] / 10,
        initial_cost=initial_cost,
        metrics=checked,
        vehicles=checked["vehicles"],
        runtime_s=time.perf_counter() - started,
        construction_s=construction_s,
        warm_ils_s=warm_s,
        trace=trace,
        batches=batches,
        accepted=accepted,
        temporary_infeasible_accepted_states=infeasible,
        feasible_accepted_states=feasible,
    )
