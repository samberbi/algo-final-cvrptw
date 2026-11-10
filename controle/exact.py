"""Exact small-instance oracle by exhaustive route enumeration + subset DP.

Handles zero times and nonmetric matrices; never prunes infeasible prefixes,
because adding an intermediate client could restore feasibility.
"""
from itertools import combinations, permutations
import math
import time
from algo.model import Objective, better
from algo.verify import verify


def exact(ins, objective=Objective.DURATION, max_clients=8, time_limit=30.):
    if ins.n > max_clients:
        raise ValueError('exhaustive oracle limited to small instances')
    objective = Objective(objective)
    started = time.perf_counter()
    table = {}
    clients = list(range(1, ins.n+1))
    for size in range(1, ins.n+1):
        for subset in combinations(clients,size):
            if sum(ins.demand[i] for i in subset) > ins.capacity + 1e-8:
                continue
            mask = sum(1 << (i-1) for i in subset)
            for sequence in permutations(subset):
                if time.perf_counter()-started > time_limit:
                    return dict(status='timeout',routes=None,runtime_s=time.perf_counter()-started)
                # Independent verifier, intentionally allowing ONLY missing clients.
                check = verify([sequence],ins)
                if any(e != 'missing or duplicated clients' for e in check['errors']):
                    continue
                value = check['duration' if objective == Objective.DURATION else 'distance']
                if mask not in table or value < table[mask][0]:
                    table[mask] = (value,list(sequence))
    full = (1 << ins.n)-1
    dp = {(0,0):(0.,[])}
    for mask in range(1, full+1):
        first = mask & -mask
        sub = mask
        while sub:
            if sub & first and sub in table:
                for k in range(1,min(ins.vehicles,ins.n)+1):
                    previous = dp.get((mask ^ sub,k-1))
                    if previous is None:
                        continue
                    candidate = (previous[0]+table[sub][0],previous[1]+[table[sub][1]])
                    old = dp.get((mask,k))
                    if old is None or candidate[0] < old[0]:
                        dp[(mask,k)] = candidate
            sub = (sub-1)&mask
    possibilities = []
    for k in range(ins.vehicles+1):
        if (full,k) in dp:
            value,routes = dp[(full,k)]
            possibilities.append(((k,value) if objective == Objective.LEX else value,routes))
    if not possibilities:
        return dict(status='proven_infeasible',routes=None,runtime_s=time.perf_counter()-started)
    value,routes = min(possibilities,key=lambda x:x[0])
    return dict(status='optimal',score=value,routes=routes,runtime_s=time.perf_counter()-started)
