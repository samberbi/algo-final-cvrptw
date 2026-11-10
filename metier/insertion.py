"""Insertion with prefix schedules and backward latest-start bounds.

Regret alternatives are ROUTES, not multiple positions of the same route.
Nonmetric matrices are supported: an invalid partial route is dismantled,
its clients return to the pending pool. Failed reconstruction rejects a move.
"""
from dataclasses import dataclass
import math
import time
import numpy as np
from algo.model import EPS, Objective, route_metrics, score, better


@dataclass
class RouteState:
    route: list
    metrics: dict
    latest: list

    @classmethod
    def build(cls, route, ins):
        met = route_metrics(route, ins)
        if met is None:
            return None
        latest = [0.] * len(route)
        next_node, next_latest = 0, ins.horizon
        for p in range(len(route) - 1, -1, -1):
            i = route[p]
            latest[p] = min(float(ins.late[i]), next_latest - ins.service[i] - ins.travel[i, next_node])
            next_node, next_latest = i, latest[p]
        return cls(list(route), met, latest)


def insertion_options(state, client, ins, objective, candidate_limit=None):
    """Return feasible (local_delta, position); never access invalid metrics."""
    if state is None or state.metrics['load'] + ins.demand[client] > ins.capacity + EPS:
        return []
    route, met = state.route, state.metrics
    positions = list(range(len(route) + 1))
    if candidate_limit and len(positions) > candidate_limit:
        positions.sort(key=lambda p: ins.travel[route[p-1] if p else 0, client]
                       + ins.travel[client, route[p] if p < len(route) else 0])
        groups = [positions[:candidate_limit], positions[candidate_limit:]]
    else:
        groups = [positions]
    options = []
    for group in groups:
        for p in group:
            prev = route[p-1] if p else 0
            nxt = route[p] if p < len(route) else 0
            depart = met['starts'][p-1] + ins.service[prev] if p else 0.
            start = max(depart + ins.travel[prev, client], ins.early[client])
            finish = start + ins.service[client]
            if start > ins.late[client] + EPS:
                continue
            limit = state.latest[p] if p < len(route) else ins.horizon
            if finish + ins.travel[client, nxt] > limit + EPS:
                continue
            delta_distance = float(ins.distance[prev, client] + ins.distance[client, nxt] - ins.distance[prev, nxt])
            if objective != Objective.DURATION:
                delta = delta_distance
            else:
                clock, previous = float(finish), client
                absorbed = False
                for j in range(p, len(route)):
                    node = route[j]
                    begin = max(clock + ins.travel[previous, node], ins.early[node])
                    # Equal schedule means all remaining values are unchanged.
                    if abs(begin - met['starts'][j]) <= 1e-12:
                        end = met['duration']
                        absorbed = True
                        break
                    clock = begin + ins.service[node]
                    previous = node
                if not absorbed:
                    end = clock + ins.travel[previous, 0]
                delta = float(end - met['duration'])
            options.append((delta, p))
        if options:  # shortlist is approximate, fallback scans rest if necessary
            break
    return options


def repair(routes, pending, ins, objective, rng, method='regret2',
           deadline=math.inf, candidate_limit=None, order=None):
    routes = [list(r) for r in routes if r]
    pending = list(pending)
    # Removing a node from a nonmetric route can make the shortcut infeasible.
    kept = []
    for route in routes:
        if route_metrics(route, ins) is None:
            pending.extend(route)
        else:
            kept.append(route)
    routes = kept
    if len(set(pending)) != len(pending):
        raise ValueError('duplicated pending clients')
    states = [RouteState.build(r, ins) for r in routes]
    ordered = list(order) if order is not None else None
    cache = {}
    while pending:
        if time.perf_counter() >= deadline:
            return None
        selection = None
        clients = pending
        if ordered is not None:
            clients = [next(i for i in ordered if i in pending)]
        for client in clients:
            if time.perf_counter() >= deadline:
                return None
            alternatives = []
            for ridx, state in enumerate(states):
                key = (client, ridx)
                if key not in cache:
                    opts = insertion_options(state, client, ins, objective, candidate_limit)
                    cache[key] = min(opts) if opts else None
                option = cache[key]
                if option is not None:
                    alternatives.append(((0, option[0]) if objective == Objective.LEX else (option[0],), ridx, option[1]))
            if len(routes) < ins.vehicles:
                singleton = route_metrics([client], ins)
                if singleton is not None:
                    value = singleton['duration' if objective == Objective.DURATION else 'distance']
                    alternatives.append(((1, value) if objective == Objective.LEX else (value,), len(routes), 0))
            if not alternatives:
                continue
            alternatives.sort()
            first = alternatives[0]
            if method in ('greedy', 'edd', 'random'):
                priority = first[0]
            else:
                k = 2 if method == 'regret2' else 3
                # Regret-k = sum of gaps from best across best k routes.
                # Scarce alternatives have explicit priority, without magic costs.
                count = min(k, len(alternatives))
                if objective == Objective.LEX:
                    gaps = tuple(sum(alternatives[j][0][d] - first[0][d] for j in range(1, count)) for d in (0, 1))
                else:
                    gaps = (sum(alternatives[j][0][0] - first[0][0] for j in range(1, count)),)
                priority = (0 if len(alternatives) < k else 1,
                            len(alternatives) if len(alternatives) < k else k,
                            *(-g for g in gaps))
            candidate = (priority, rng.random(), client, first)
            if selection is None or candidate[:2] < selection[:2]:
                selection = candidate
        if selection is None:
            return None
        _, _, client, (_, ridx, pos) = selection
        if ridx == len(routes):
            routes.append([client])
            states.append(RouteState.build([client], ins))
        else:
            routes[ridx].insert(pos, client)
            states[ridx] = RouteState.build(routes[ridx], ins)
        # Only the changed route invalidates cached insertion alternatives.
        cache = {k:v for k,v in cache.items() if k[1] != ridx and k[0] != client}
        pending.remove(client)
    return routes


def construct(ins, objective, rng, method='regret2', attempts=4,
              deadline=math.inf, candidate_limit=None):
    started = time.perf_counter()
    best, value = None, None
    fingerprints, successes = set(), 0
    for attempt in range(attempts):
        if time.perf_counter() >= deadline:
            break
        clients = list(range(1, ins.n + 1))
        order = None
        if method == 'edd':
            order = sorted(clients, key=lambda i:(ins.late[i], ins.early[i], rng.random()))
        elif method == 'random':
            rng.shuffle(clients)
            order = clients[:]
        sol = repair([], clients, ins, objective, rng, method, deadline, candidate_limit, order)
        if sol is None:
            continue
        successes += 1
        fingerprints.add(tuple(sorted(tuple(r) for r in sol)))
        cost = score(sol, ins, objective)
        if best is None or better(cost, value):
            best, value = sol, cost
    return best, dict(attempts_completed=attempt + 1 if attempts else 0,
                      successful_attempts=successes, distinct_solutions=len(fingerprints),
                      construction_s=time.perf_counter()-started)
