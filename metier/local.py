"""Feasible first-improvement local search, bounded in evaluations and time."""
import math
import time
from algo.model import score, better, route_metrics


def improve(routes, ins, objective, rng, moves=('relocate','swap','2opt','2opt_star'),
            max_evaluations=250, deadline=math.inf):
    best = [r[:] for r in routes if r]
    cost = score(best, ins, objective)
    stats = dict(evaluations=0, accepted=0)
    # Randomised sampling keeps cost bounded on large instances.
    for step in range(max_evaluations):
        if time.perf_counter() >= deadline or not best:
            break
        op = moves[step % len(moves)]
        a, b = rng.randrange(len(best)), rng.randrange(len(best))
        p, q = rng.randrange(len(best[a])), rng.randrange(len(best[b]))
        candidate = [r[:] for r in best]
        if op == 'relocate':
            client = candidate[a].pop(p)
            candidate[b].insert(min(q, len(candidate[b])), client)
        elif op == 'swap':
            candidate[a][p], candidate[b][q] = candidate[b][q], candidate[a][p]
        elif op == '2opt':
            q = rng.randrange(len(candidate[a]))
            lo, hi = sorted((p,q))
            candidate[a][lo:hi+1] = reversed(candidate[a][lo:hi+1])
        elif op == '2opt_star':
            if a == b:
                continue
            candidate[a], candidate[b] = candidate[a][:p]+candidate[b][q:], candidate[b][:q]+candidate[a][p:]
        else:
            raise ValueError(op)
        stats['evaluations'] += 1
        if route_metrics(candidate[a], ins) is None or route_metrics(candidate[b], ins) is None:
            continue
        candidate = [r for r in candidate if r]
        value = score(candidate, ins, objective)
        if better(value, cost):
            best, cost = candidate, value
            stats['accepted'] += 1
    return best, stats
