"""Strictly feasible SWAP*: exchange clients and optimize their new positions."""

import numpy as np
from numba import njit
from .kernels import route_eval


@njit(cache=True)
def best_reinsertion(
    base,
    length,
    client,
    travel,
    distance,
    demand,
    service,
    early,
    late,
    capacity,
    horizon,
    output,
):
    """Find the cheapest feasible position; the base excludes the exchanged client."""
    best_cost = 1e100
    best_position = -1
    base_cost = 0.0
    previous = 0
    for index in range(length):
        node = base[index]
        base_cost += distance[previous, node]
        previous = node
    if length:
        base_cost += distance[previous, 0]
    for position in range(length + 1):
        before = base[position - 1] if position else 0
        after = base[position] if position < length else 0
        candidate_cost = (
            base_cost
            + distance[before, client]
            + distance[client, after]
            - distance[before, after]
        )
        if candidate_cost >= best_cost - 1e-9:
            continue
        output[:position] = base[:position]
        output[position] = client
        output[position + 1 : length + 1] = base[position:length]
        feasible, cost, _ = route_eval(
            output,
            length + 1,
            travel,
            distance,
            demand,
            service,
            early,
            late,
            capacity,
            horizon,
        )
        if feasible:
            best_cost = cost
            best_position = position
    return best_cost, best_position


@njit(cache=True)
def swap_star(
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
    max_moves,
    seed,
):
    """Keep only strictly improving complete solutions. No repair or penalties."""
    np.random.seed(seed)
    n = len(demand) - 1
    owner = np.full(n + 1, -1, np.int64)
    where = np.zeros(n + 1, np.int64)
    costs = np.zeros(len(lengths))
    loads = np.zeros(len(lengths))
    base_a = np.empty(n + 2, np.int64)
    base_b = np.empty(n + 2, np.int64)
    scratch = np.empty(n + 2, np.int64)
    moves = tested = 0
    for _ in range(max_moves):
        for route in range(len(lengths)):
            _, costs[route], loads[route] = route_eval(
                routes[route],
                lengths[route],
                travel,
                distance,
                demand,
                service,
                early,
                late,
                capacity,
                horizon,
            )
            for position in range(lengths[route]):
                client = routes[route, position]
                owner[client], where[client] = route, position
        changed = False
        offset = np.random.randint(max(1, n))
        for index in range(n):
            client_a = 1 + (index + offset) % n
            a, pa = owner[client_a], where[client_a]
            if a < 0:
                continue
            la = lengths[a]
            for column in range(neighbors.shape[1]):
                client_b = neighbors[client_a, column]
                if client_b <= 0 or client_b == client_a:
                    continue
                b, pb = owner[client_b], where[client_b]
                if b < 0 or a == b:
                    continue
                if loads[a] - demand[client_a] + demand[client_b] > capacity + 1e-8:
                    continue
                if loads[b] - demand[client_b] + demand[client_a] > capacity + 1e-8:
                    continue
                lb = lengths[b]
                base_a[:pa] = routes[a, :pa]
                base_a[pa : la - 1] = routes[a, pa + 1 : la]
                base_b[:pb] = routes[b, :pb]
                base_b[pb : lb - 1] = routes[b, pb + 1 : lb]
                cost_a, new_a = best_reinsertion(
                    base_a,
                    la - 1,
                    client_b,
                    travel,
                    distance,
                    demand,
                    service,
                    early,
                    late,
                    capacity,
                    horizon,
                    scratch,
                )
                tested += 1
                if new_a < 0:
                    continue
                cost_b, new_b = best_reinsertion(
                    base_b,
                    lb - 1,
                    client_a,
                    travel,
                    distance,
                    demand,
                    service,
                    early,
                    late,
                    capacity,
                    horizon,
                    scratch,
                )
                if new_b < 0 or cost_a + cost_b >= costs[a] + costs[b] - 1e-8:
                    continue
                # Commit both routes together: coverage is preserved by the exchange.
                routes[a, :new_a] = base_a[:new_a]
                routes[a, new_a] = client_b
                routes[a, new_a + 1 : la] = base_a[new_a : la - 1]
                routes[b, :new_b] = base_b[:new_b]
                routes[b, new_b] = client_a
                routes[b, new_b + 1 : lb] = base_b[new_b : lb - 1]
                moves += 1
                changed = True
                break
            if changed:
                break
        if not changed:
            break
    return moves, tested
