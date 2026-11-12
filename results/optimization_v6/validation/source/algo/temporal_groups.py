"""Whole-route grouping by attainable spatial and temporal customer proximity."""

import numpy as np


def affinity_matrix(ins):
    # Earliest-to-latest bounds, not a simulation or a relaxed final constraint.
    arrival_early = ins.early[:, None] + ins.service[:, None] + ins.travel
    arrival_late = ins.late[:, None] + ins.service[:, None] + ins.travel
    unavoidable_wait = np.maximum(0.0, ins.early[None, :] - arrival_late)
    unavoidable_late = np.maximum(0.0, arrival_early - ins.late[None, :])
    directed = ins.distance + 0.2 * unavoidable_wait + unavoidable_late
    result = np.minimum(directed, directed.T)
    np.fill_diagonal(result, np.inf)
    result[0, :] = result[:, 0] = np.inf
    return result


def choose_group(ins, routes, rng, target, affinity):
    pivot = rng.randrange(len(routes))
    scores = np.array(
        [
            (
                float(np.min(affinity[np.ix_(routes[pivot], route)]))
                if index != pivot
                else -np.inf
            )
            for index, route in enumerate(routes)
        ]
    )
    selected, size = [], 0
    for index in np.argsort(scores, kind="stable"):
        if selected and size + len(routes[index]) > target:
            continue
        selected.append(int(index))
        size += len(routes[index])
        if len(selected) >= 12:
            break
    return selected
