"""Complete-state penalized descent; keep a separate feasible distance archive."""

import numpy as np
from numba import njit
from .kernels import compact
from .penalty_hybrid import route_penalties

TOL = 1e-8


@njit(cache=True)
def augmented(
    seq,
    length,
    travel,
    distance,
    demand,
    service,
    early,
    late,
    capacity,
    horizon,
    wc,
    wt,
):
    d, c, t = route_penalties(
        seq, length, travel, distance, demand, service, early, late, capacity, horizon
    )
    return d + wc * c + wt * t


@njit(cache=True)
def descent(
    routes,
    lens,
    travel,
    distance,
    demand,
    service,
    early,
    late,
    capacity,
    horizon,
    neighbors,
    max_moves,
    chains,
    seed,
    enabled,
    capacity_weight,
    time_weight,
):
    np.random.seed(seed)
    n = len(demand) - 1
    changes = 0
    tested = 0
    old = np.zeros(len(lens))
    load = np.zeros(len(lens))
    roads = np.zeros(len(lens))
    excess = np.zeros(len(lens))
    warps = np.zeros(len(lens))
    ba, bl = routes.copy(), lens.copy()
    best_feasible = np.inf
    owner = np.full(n + 1, -1, np.int64)
    where = np.zeros(n + 1, np.int64)
    tmp = np.empty(n + 2, np.int64)
    tmp2 = np.empty(n + 2, np.int64)
    for iteration in range(max_moves):
        for r in range(len(lens)):
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
            old[r] = roads[r] + capacity_weight * excess[r] + time_weight * warps[r]
            for p in range(lens[r]):
                owner[routes[r, p]] = r
                where[routes[r, p]] = p
        if (
            excess.sum() <= TOL
            and warps.sum() <= TOL
            and roads.sum() < best_feasible - 1e-8
        ):
            best_feasible = roads.sum()
            ba, bl = routes.copy(), lens.copy()
        changed = False
        offset = np.random.randint(max(1, n))
        for ii in range(n):
            i = 1 + (ii + offset) % n
            a = owner[i]
            if a < 0:
                continue
            p = where[i]
            La = lens[a]
            for nn in range(neighbors.shape[1]):
                j = neighbors[i, nn]
                if j == 0 or j == i:
                    continue
                b = owner[j]
                if b < 0:
                    continue
                q = where[j]
                Lb = lens[b]
                # Relocate (and optional chains) into a different route.
                if enabled[0] and a != b:
                    for size in range(1, chains + 1):
                        if p + size > La:
                            break
                        chainload = 0.0
                        for z in range(size):
                            chainload += demand[routes[a, p + z]]

                        pre = routes[a, p - 1] if p else 0
                        end = routes[a, p + size] if p + size < La else 0
                        gain = (
                            distance[pre, end]
                            - distance[pre, i]
                            - distance[routes[a, p + size - 1], end]
                        )
                        for pos in range(q, min(Lb, q + 1) + 1):
                            prev = routes[b, pos - 1] if pos else 0
                            nxt = routes[b, pos] if pos < Lb else 0
                            delta = (
                                gain
                                + distance[prev, i]
                                + distance[routes[a, p + size - 1], nxt]
                                - distance[prev, nxt]
                            )
                            eliminate = False  # No lexicographic fleet priority.
                            if (
                                delta >= -1e-9
                                and old[a] - roads[a] + old[b] - roads[b] <= TOL
                            ):
                                continue
                            z = 0
                            for k in range(La):
                                if k < p or k >= p + size:
                                    tmp[z] = routes[a, k]
                                    z += 1
                            for k in range(pos):
                                tmp2[k] = routes[b, k]
                            for k in range(size):
                                tmp2[pos + k] = routes[a, p + k]
                            for k in range(pos, Lb):
                                tmp2[k + size] = routes[b, k]
                            tested += 1
                            ca = augmented(
                                tmp,
                                La - size,
                                travel,
                                distance,
                                demand,
                                service,
                                early,
                                late,
                                capacity,
                                horizon,
                                capacity_weight,
                                time_weight,
                            )
                            cb = augmented(
                                tmp2,
                                Lb + size,
                                travel,
                                distance,
                                demand,
                                service,
                                early,
                                late,
                                capacity,
                                horizon,
                                capacity_weight,
                                time_weight,
                            )
                            if ca + cb < old[a] + old[b] - 1e-8:
                                routes[a, : La - size] = tmp[: La - size]
                                lens[a] = La - size
                                routes[b, : Lb + size] = tmp2[: Lb + size]
                                lens[b] = Lb + size
                                changed = True
                                break
                        if changed:
                            break
                if changed:
                    break
                # Swap between distinct routes.
                if enabled[1] and a != b:
                    prev = routes[a, p - 1] if p else 0
                    nxt = routes[a, p + 1] if p + 1 < La else 0
                    prev2 = routes[b, q - 1] if q else 0
                    nxt2 = routes[b, q + 1] if q + 1 < Lb else 0
                    delta = (
                        distance[prev, j]
                        + distance[j, nxt]
                        - distance[prev, i]
                        - distance[i, nxt]
                        + distance[prev2, i]
                        + distance[i, nxt2]
                        - distance[prev2, j]
                        - distance[j, nxt2]
                    )
                    if delta < -1e-9 or old[a] - roads[a] + old[b] - roads[b] > TOL:
                        tmp[:La] = routes[a, :La]
                        tmp2[:Lb] = routes[b, :Lb]
                        tmp[p] = j
                        tmp2[q] = i
                        tested += 1
                        ca = augmented(
                            tmp,
                            La,
                            travel,
                            distance,
                            demand,
                            service,
                            early,
                            late,
                            capacity,
                            horizon,
                            capacity_weight,
                            time_weight,
                        )
                        cb = augmented(
                            tmp2,
                            Lb,
                            travel,
                            distance,
                            demand,
                            service,
                            early,
                            late,
                            capacity,
                            horizon,
                            capacity_weight,
                            time_weight,
                        )
                        if ca + cb < old[a] + old[b] - 1e-8:
                            routes[a, p] = j
                            routes[b, q] = i
                            changed = True
                if changed:
                    break
                # Intra-route 2-opt; symmetric DISTANCE is an explicit data invariant.
                if enabled[2] and a == b and p < q:
                    prev = routes[a, p - 1] if p else 0
                    nxt = routes[a, q + 1] if q + 1 < La else 0
                    delta = (
                        distance[prev, j]
                        + distance[i, nxt]
                        - distance[prev, i]
                        - distance[j, nxt]
                    )
                    if delta < -1e-9 or old[a] - roads[a] + old[b] - roads[b] > TOL:
                        tmp[:La] = routes[a, :La]
                        for k in range(q - p + 1):
                            tmp[p + k] = routes[a, q - k]
                        tested += 1
                        ca = augmented(
                            tmp,
                            La,
                            travel,
                            distance,
                            demand,
                            service,
                            early,
                            late,
                            capacity,
                            horizon,
                            capacity_weight,
                            time_weight,
                        )
                        if ca < old[a] - 1e-8:
                            routes[a, :La] = tmp[:La]
                            changed = True
                if changed:
                    break
                # 2-opt*: exchange tails at the selected positions.
                if enabled[3] and a != b:
                    prev = routes[a, p - 1] if p else 0
                    prev2 = routes[b, q - 1] if q else 0
                    delta = (
                        distance[prev, j]
                        + distance[prev2, i]
                        - distance[prev, i]
                        - distance[prev2, j]
                    )
                    eliminate = False  # No lexicographic fleet priority.
                    if delta < -1e-9 or old[a] - roads[a] + old[b] - roads[b] > TOL:
                        l1 = p + Lb - q
                        l2 = q + La - p
                        tmp[:p] = routes[a, :p]
                        tmp[p:l1] = routes[b, q:Lb]
                        tmp2[:q] = routes[b, :q]
                        tmp2[q:l2] = routes[a, p:La]
                        tested += 1
                        ca = augmented(
                            tmp,
                            l1,
                            travel,
                            distance,
                            demand,
                            service,
                            early,
                            late,
                            capacity,
                            horizon,
                            capacity_weight,
                            time_weight,
                        )
                        cb = augmented(
                            tmp2,
                            l2,
                            travel,
                            distance,
                            demand,
                            service,
                            early,
                            late,
                            capacity,
                            horizon,
                            capacity_weight,
                            time_weight,
                        )
                        if ca + cb < old[a] + old[b] - 1e-8:
                            routes[a, :l1] = tmp[:l1]
                            routes[b, :l2] = tmp2[:l2]
                            lens[a] = l1
                            lens[b] = l2
                            changed = True
                if changed:
                    break
            if changed:
                break
        if not changed:
            break
        changes += 1
    for r in range(len(lens)):
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
    if (
        excess.sum() <= TOL
        and warps.sum() <= TOL
        and roads.sum() < best_feasible - 1e-8
    ):
        best_feasible = roads.sum()
        ba, bl = routes.copy(), lens.copy()
    compact(routes, lens)
    return changes, tested, ba, bl, best_feasible
