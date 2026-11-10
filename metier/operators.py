"""Destruction scores are heuristic preferences, never feasibility tests."""
import numpy as np
from algo.model import route_metrics, Objective


def related_scores(ins, anchor, variant='r1', weights=(.4,.2,.2,.2)):
    alpha, b1, b2, gamma = weights
    if min(weights) < 0 or not np.isfinite(weights).all() or sum(weights) <= 0:
        raise ValueError('related weights must be finite, nonnegative, nonzero')
    maximum=float(ins.travel.max())
    geo = ins.travel[anchor] / (maximum if maximum>0 else 1.)
    if variant == 'r0':
        return geo
    result = (alpha * geo + b1 * abs(ins.early - ins.early[anchor]) / ins.horizon
              + b2 * abs(ins.late - ins.late[anchor]) / ins.horizon
              + gamma * abs(ins.demand - ins.demand[anchor]) / ins.capacity) / sum(weights)
    if variant == 'r2':
        # Directed temporal slack: positive means potentially compatible.
        # Compare BOTH directions; windows alone cannot determine compatibility.
        slack1 = ins.late - (ins.early[anchor] + ins.service[anchor] + ins.travel[anchor])
        slack2 = ins.late[anchor] - (ins.early + ins.service + ins.travel[:,anchor])
        incompat = np.maximum(0., -np.maximum(slack1, slack2)) / ins.horizon
        result = result + incompat
    return result


def destroy(routes, ins, rng, method, fraction=.2, weights=(.4,.2,.2,.2), objective=Objective.DURATION):
    clients = [i for r in routes for i in r]
    if not clients:
        return [], []
    count = min(len(clients), max(1, round(fraction * len(clients))))
    if method == 'random':
        removed = rng.sample(clients, count)
    elif method in ('r0','r1','r2'):
        anchor = rng.choice(clients)
        values = related_scores(ins, anchor, method, weights)
        ranking = sorted(clients, key=lambda i:(values[i],rng.random()))
        removed = []
        while ranking and len(removed) < count:
            # Biased random rank avoids always repeating the same cluster.
            pos = int(rng.random() ** 3 * len(ranking))
            removed.append(ranking.pop(pos))
    elif method == 'worst':
        contributions = []
        field = 'duration' if objective == Objective.DURATION else 'distance'
        for route in routes:
            before = route_metrics(route, ins)[field]
            for p, client in enumerate(route):
                after = route_metrics(route[:p] + route[p+1:], ins)
                gain = before - after[field] if after is not None else -float('inf')
                contributions.append((gain,rng.random(),client))
        contributions.sort(reverse=True)
        removed = [x[2] for x in contributions[:count]]
    elif method == 'route':
        # Route removal directly supports fleet minimisation.
        target = min(routes, key=lambda r:len(r)+rng.random()*2)
        removed = list(target)
    else:
        raise ValueError(f'unknown destruction {method}')
    remove = set(removed)
    return [[i for i in r if i not in remove] for r in routes], removed
