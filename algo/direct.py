"""Compiled direct moves on complete feasible routes; no destruction/repair."""

import math
import numpy as np
from numba import njit
from .kernels import route_eval


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
    temperature,
    mode,
    diagnostics=None,
):
    """Modify complete routes by direct moves and return their best archive.

    Mode 0 accepts one feasible perturbation; mode 1 uses Metropolis. Optional
    counters record attempts, partner/structure skips, capacity/time rejections,
    Metropolis rejections and accepted moves, in that order.
    """
    np.random.seed(seed)
    n = len(demand) - 1
    owner = np.full(n + 1, -1, np.int64)
    where = np.zeros(n + 1, np.int64)
    costs = np.zeros(len(lens))
    for r in range(limit):
        _, costs[r], _ = route_eval(
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
    current = costs.sum()
    best = current
    ba, bl = routes.copy(), lens.copy()
    tmp = np.empty(n + 2, np.int64)
    tmp2 = np.empty(n + 2, np.int64)
    valid = accepted = improved = 0
    operators = np.zeros(4, np.int64)
    for iteration in range(trials):
        if n == 0:
            break
        if diagnostics is not None:
            diagnostics[0] += 1
        i = 1 + np.random.randint(n)
        a = owner[i]
        p = where[i]
        if a < 0:
            if diagnostics is not None:
                diagnostics[1] += 1
            continue
        if neighbors.shape[1] and np.random.random() < 0.85:
            j = neighbors[i, np.random.randint(neighbors.shape[1])]
        else:
            j = 1 + np.random.randint(n)
        if j <= 0 or j == i or owner[j] < 0:
            if diagnostics is not None:
                diagnostics[1] += 1
            continue
        b = owner[j]
        q = where[j]
        op = np.random.randint(4)
        operators[op] += 1
        la, lb = lens[a], lens[b]
        na, nb = la, lb
        tmp[:la] = routes[a, :la]
        tmp2[:lb] = routes[b, :lb]
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
                if diagnostics is not None:
                    diagnostics[2] += 1
                continue
            pos = min(lb, q + np.random.randint(2))
            for z in range(p, la - 1):
                tmp[z] = routes[a, z + 1]
            for z in range(pos):
                tmp2[z] = routes[b, z]
            tmp2[pos] = i
            for z in range(pos, lb):
                tmp2[z + 1] = routes[b, z]
            na, nb = la - 1, lb + 1
        elif op == 1:
            if a == b:
                tmp[p], tmp[q] = tmp[q], tmp[p]
            else:
                tmp[p] = j
                tmp2[q] = i
        elif op == 2:
            if la < 2:
                if diagnostics is not None:
                    diagnostics[2] += 1
                continue
            q = np.random.randint(la)
            lo, hi = min(p, q), max(p, q)
            if lo == hi:
                if diagnostics is not None:
                    diagnostics[2] += 1
                continue
            for z in range(hi - lo + 1):
                tmp[lo + z] = routes[a, hi - z]
            b = a
        else:
            if a == b:
                if diagnostics is not None:
                    diagnostics[2] += 1
                continue
            na, nb = p + lb - q, q + la - p
            tmp[:p] = routes[a, :p]
            tmp[p:na] = routes[b, q:lb]
            tmp2[:q] = routes[b, :q]
            tmp2[q:nb] = routes[a, p:la]
        va, ca, candidate_load = route_eval(
            tmp, na, travel, distance, demand, service, early, late, capacity, horizon
        )
        if not va:
            if diagnostics is not None:
                diagnostics[3 if candidate_load > capacity + 1e-8 else 4] += 1
            continue
        cb = 0.0
        if b != a:
            vb, cb, candidate_load = route_eval(
                tmp2,
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
            if not vb:
                if diagnostics is not None:
                    diagnostics[3 if candidate_load > capacity + 1e-8 else 4] += 1
                continue
        delta = ca - costs[a] + (cb - costs[b] if b != a else 0.0)
        valid += 1
        take = mode == 0 or delta <= 1e-9
        if not take and mode == 1:
            take = np.random.random() < math.exp(
                -min(745.0, delta / max(temperature, 1e-12))
            )
        if not take:
            if diagnostics is not None:
                diagnostics[5] += 1
            continue
        accepted += 1
        if diagnostics is not None:
            diagnostics[6] += 1
        routes[a, :na] = tmp[:na]
        lens[a] = na
        costs[a] = ca
        if b != a:
            routes[b, :nb] = tmp2[:nb]
            lens[b] = nb
            costs[b] = cb
        current += delta
        for z in range(lens[a]):
            owner[routes[a, z]] = a
            where[routes[a, z]] = z
        if b != a:
            for z in range(lens[b]):
                owner[routes[b, z]] = b
                where[routes[b, z]] = z
        if current < best - 1e-8:
            best = current
            ba = routes.copy()
            bl = lens.copy()
            improved += 1
        if mode == 0 and accepted >= 1:
            break
    return (
        current,
        ba,
        bl,
        best,
        valid,
        accepted,
        improved,
        operators,
        iteration + 1 if n else 0,
    )
