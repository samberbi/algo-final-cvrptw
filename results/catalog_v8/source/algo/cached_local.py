"""Local search reuses unchanged prefix metrics; moves and checks are unchanged."""

import numpy as np
from numba import njit
from .kernels import compact

TOL = 1e-8


@njit(cache=True)
def cache_route(
    seq,
    length,
    r,
    travel,
    distance,
    demand,
    service,
    early,
    late,
    capacity,
    horizon,
    depart,
    road,
    quantity,
):
    clock = cost = load = 0.0
    previous = 0
    depart[r, 0] = road[r, 0] = quantity[r, 0] = 0.0
    for p in range(length):
        client = seq[p]
        load += demand[client]
        clock = max(clock + travel[previous, client], early[client])
        if clock > late[client] + TOL or load > capacity + TOL:
            return False, 0.0, load
        clock += service[client]
        cost += distance[previous, client]
        depart[r, p + 1], road[r, p + 1], quantity[r, p + 1] = clock, cost, load
        previous = client
    if length:
        clock += travel[previous, 0]
        cost += distance[previous, 0]
    return clock <= horizon + TOL, cost, load


@njit(cache=True)
def evaluate_tail(
    seq,
    length,
    start,
    r,
    travel,
    distance,
    demand,
    service,
    early,
    late,
    capacity,
    horizon,
    depart,
    road,
    quantity,
):
    clock, cost, load = depart[r, start], road[r, start], quantity[r, start]
    previous = seq[start - 1] if start else 0
    for p in range(start, length):
        client = seq[p]
        load += demand[client]
        clock = max(clock + travel[previous, client], early[client])
        if clock > late[client] + TOL or load > capacity + TOL:
            return False, 0.0, load
        clock += service[client]
        cost += distance[previous, client]
        previous = client
    if length:
        clock += travel[previous, 0]
        cost += distance[previous, 0]
    return clock <= horizon + TOL, cost, load


@njit(cache=True)
def local_search(
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
):
    np.random.seed(seed)
    n = len(demand) - 1
    changes = 0
    tested = 0
    old = np.zeros(len(lens))
    load = np.zeros(len(lens))
    width = int(np.max(lens)) + 5
    depart = np.zeros((len(lens), width))
    road = np.zeros((len(lens), width))
    quantity = np.zeros((len(lens), width))
    owner = np.full(n + 1, -1, np.int64)
    where = np.zeros(n + 1, np.int64)
    tmp = np.empty(n + 2, np.int64)
    tmp2 = np.empty(n + 2, np.int64)
    for iteration in range(max_moves):
        required = int(np.max(lens)) + 1
        if required > width:
            width = max(required, width + width // 2)
            depart = np.zeros((len(lens), width))
            road = np.zeros((len(lens), width))
            quantity = np.zeros((len(lens), width))
        for r in range(len(lens)):
            valid, old[r], load[r] = cache_route(
                routes[r],
                lens[r],
                r,
                travel,
                distance,
                demand,
                service,
                early,
                late,
                capacity,
                horizon,
                depart,
                road,
                quantity,
            )
            for p in range(lens[r]):
                owner[routes[r, p]] = r
                where[routes[r, p]] = p
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
                        if load[b] + chainload > capacity + TOL:
                            continue
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
                            if not eliminate and delta >= -1e-9:
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
                            va, _, _ = evaluate_tail(
                                tmp,
                                La - size,
                                p,
                                a,
                                travel,
                                distance,
                                demand,
                                service,
                                early,
                                late,
                                capacity,
                                horizon,
                                depart,
                                road,
                                quantity,
                            )
                            vb, _, _ = evaluate_tail(
                                tmp2,
                                Lb + size,
                                pos,
                                b,
                                travel,
                                distance,
                                demand,
                                service,
                                early,
                                late,
                                capacity,
                                horizon,
                                depart,
                                road,
                                quantity,
                            )
                            if va and vb:
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
                if (
                    enabled[1]
                    and a != b
                    and load[a] - demand[i] + demand[j] <= capacity + TOL
                    and load[b] - demand[j] + demand[i] <= capacity + TOL
                ):
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
                    if delta < -1e-9:
                        tmp[:La] = routes[a, :La]
                        tmp2[:Lb] = routes[b, :Lb]
                        tmp[p] = j
                        tmp2[q] = i
                        tested += 1
                        va, _, _ = evaluate_tail(
                            tmp,
                            La,
                            p,
                            a,
                            travel,
                            distance,
                            demand,
                            service,
                            early,
                            late,
                            capacity,
                            horizon,
                            depart,
                            road,
                            quantity,
                        )
                        vb, _, _ = evaluate_tail(
                            tmp2,
                            Lb,
                            q,
                            b,
                            travel,
                            distance,
                            demand,
                            service,
                            early,
                            late,
                            capacity,
                            horizon,
                            depart,
                            road,
                            quantity,
                        )
                        if va and vb:
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
                    if delta < -1e-9:
                        tmp[:La] = routes[a, :La]
                        for k in range(q - p + 1):
                            tmp[p + k] = routes[a, q - k]
                        tested += 1
                        valid, _, _ = evaluate_tail(
                            tmp,
                            La,
                            p,
                            a,
                            travel,
                            distance,
                            demand,
                            service,
                            early,
                            late,
                            capacity,
                            horizon,
                            depart,
                            road,
                            quantity,
                        )
                        if valid:
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
                    if delta < -1e-9 or eliminate:
                        l1 = p + Lb - q
                        l2 = q + La - p
                        tmp[:p] = routes[a, :p]
                        tmp[p:l1] = routes[b, q:Lb]
                        tmp2[:q] = routes[b, :q]
                        tmp2[q:l2] = routes[a, p:La]
                        tested += 1
                        va, _, _ = evaluate_tail(
                            tmp,
                            l1,
                            p,
                            a,
                            travel,
                            distance,
                            demand,
                            service,
                            early,
                            late,
                            capacity,
                            horizon,
                            depart,
                            road,
                            quantity,
                        )
                        vb, _, _ = evaluate_tail(
                            tmp2,
                            l2,
                            q,
                            b,
                            travel,
                            distance,
                            demand,
                            service,
                            early,
                            late,
                            capacity,
                            horizon,
                            depart,
                            road,
                            quantity,
                        )
                        if va and vb:
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
    compact(routes, lens)
    return changes, tested
