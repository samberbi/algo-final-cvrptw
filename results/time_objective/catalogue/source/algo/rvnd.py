"""Feasible block exchanges and randomized variable-neighborhood descent."""

import time
import numpy as np
from numba import njit
from . import kernels as k


@njit(cache=True)
def exchange_blocks(
    routes,
    lengths,
    travel,
    distance,
    demand,
    service,
    early,
    late,
    capacity,
    horizon,
    neighbors,
):
    """First improving Swap(2,1), Swap(1,2), or Swap(2,2); preserve block order."""
    n = len(demand) - 1
    owner = np.full(n + 1, -1, np.int64)
    positions = np.zeros(n + 1, np.int64)
    loads = np.zeros(len(lengths))
    for r in range(len(lengths)):
        for p in range(lengths[r]):
            client = routes[r, p]
            owner[client], positions[client] = r, p
            loads[r] += demand[client]
    first = np.empty(n + 2, np.int64)
    second = np.empty(n + 2, np.int64)
    tested = 0
    for i in range(1, n + 1):
        a, p = owner[i], positions[i]
        if a < 0:
            continue
        for column in range(neighbors.shape[1]):
            j = neighbors[i, column]
            if j == 0 or j == i or owner[j] < 0 or owner[j] == a:
                continue
            b, q = owner[j], positions[j]
            la, lb = lengths[a], lengths[b]
            for sa in range(1, 3):
                for sb in range(1, 3):
                    if sa == sb == 1 or p + sa > la or q + sb > lb:
                        continue
                    qa = qb = 0.0
                    for z in range(sa):
                        qa += demand[routes[a, p + z]]
                    for z in range(sb):
                        qb += demand[routes[b, q + z]]
                    if (
                        loads[a] - qa + qb > capacity + 1e-8
                        or loads[b] - qb + qa > capacity + 1e-8
                    ):
                        continue
                    pre_a = routes[a, p - 1] if p else 0
                    end_a = routes[a, p + sa] if p + sa < la else 0
                    pre_b = routes[b, q - 1] if q else 0
                    end_b = routes[b, q + sb] if q + sb < lb else 0
                    last_a, last_b = routes[a, p + sa - 1], routes[b, q + sb - 1]
                    delta = (
                        distance[pre_a, j]
                        + distance[last_b, end_a]
                        + distance[pre_b, i]
                        + distance[last_a, end_b]
                        - distance[pre_a, i]
                        - distance[last_a, end_a]
                        - distance[pre_b, j]
                        - distance[last_b, end_b]
                    )
                    if delta >= -1e-9:
                        continue
                    na, nb = la - sa + sb, lb - sb + sa
                    first[:p] = routes[a, :p]
                    first[p : p + sb] = routes[b, q : q + sb]
                    first[p + sb : na] = routes[a, p + sa : la]
                    second[:q] = routes[b, :q]
                    second[q : q + sa] = routes[a, p : p + sa]
                    second[q + sa : nb] = routes[b, q + sb : lb]
                    tested += 1
                    va = k.route_eval(
                        first,
                        na,
                        travel,
                        distance,
                        demand,
                        service,
                        early,
                        late,
                        capacity,
                        horizon,
                    )[0]
                    vb = k.route_eval(
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
                    )[0]
                    if va and vb:
                        routes[a, :na], routes[b, :nb] = first[:na], second[:nb]
                        lengths[a], lengths[b] = na, nb
                        return 1, tested
    return 0, tested


def descend(routes, lengths, args, neighbors, rng, deadline, max_moves=15, blocks=True):
    """Reset the neighborhood list after each improvement; no partial solutions."""
    active = list(range(5 if blocks else 4))
    moves = tested = 0
    while active and moves < max_moves and time.perf_counter() < deadline:
        operator = rng.choice(active)
        if operator == 4:
            changed, evaluations = exchange_blocks(routes, lengths, *args, neighbors)
        else:
            enabled = np.zeros(4, np.bool_)
            enabled[operator] = True
            changed, evaluations = k.local_search(
                routes, lengths, *args, neighbors, 1, 3, rng.randrange(2**31), enabled
            )
        tested += evaluations
        if changed:
            moves += changed
            active = list(range(5 if blocks else 4))
        else:
            active.remove(operator)
    return moves, tested
