"""Create an auditable experimental copy; preserve measured baseline sources."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

HEADER = '''"""Local search reuses unchanged prefix metrics; moves and checks are unchanged."""
import numpy as np
from numba import njit
from .kernels import compact
TOL = 1e-8


@njit(cache=True)
def cache_route(seq, length, r, travel, distance, demand, service, early, late,
                capacity, horizon, depart, road, quantity):
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
        depart[r, p+1], road[r, p+1], quantity[r, p+1] = clock, cost, load
        previous = client
    if length:
        clock += travel[previous, 0]
        cost += distance[previous, 0]
    return clock <= horizon + TOL, cost, load


@njit(cache=True)
def evaluate_tail(seq, length, start, r, travel, distance, demand, service,
                  early, late, capacity, horizon, depart, road, quantity):
    clock, cost, load = depart[r, start], road[r, start], quantity[r, start]
    previous = seq[start-1] if start else 0
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
'''


def main():
    source = (ROOT / "algo/kernels.py").read_text(encoding="utf-8-sig")
    body = source[source.index("def local_search("):]
    body = body.replace('    old=np.zeros(len(lens));load=np.zeros(len(lens))',
                        '    old=np.zeros(len(lens));load=np.zeros(len(lens))\n    width=int(np.max(lens))+5\n    depart=np.zeros((len(lens),width));road=np.zeros((len(lens),width));quantity=np.zeros((len(lens),width))')
    body = body.replace('    for iteration in range(max_moves):',
                        '    for iteration in range(max_moves):\n        required=int(np.max(lens))+1\n        if required>width:\n            width=max(required,width+width//2)\n            depart=np.zeros((len(lens),width));road=np.zeros((len(lens),width));quantity=np.zeros((len(lens),width))')
    old = 'route_eval(routes[r],lens[r],travel,distance,demand,service,early,late,capacity,horizon)'
    body = body.replace(old, 'cache_route(routes[r],lens[r],r,travel,distance,demand,service,early,late,capacity,horizon,depart,road,quantity)')
    for seq, length, start, row in [('tmp','La-size','p','a'), ('tmp2','Lb+size','pos','b'),
                                   ('tmp','La','p','a'), ('tmp2','Lb','q','b'),
                                   ('tmp','l1','p','a'), ('tmp2','l2','q','b')]:
        old = f'route_eval({seq},{length},travel,distance,demand,service,early,late,capacity,horizon)'
        new = f'evaluate_tail({seq},{length},{start},{row},travel,distance,demand,service,early,late,capacity,horizon,depart,road,quantity)'
        body = body.replace(old, new)
    assert 'route_eval(' not in body
    (ROOT / 'algo/cached_local.py').write_text(HEADER + body, encoding='utf-8')
    core = (ROOT / 'algo/iterated.py').read_text(encoding='utf-8-sig')
    core = core.replace('from .direct import walk', 'from .direct import walk\nfrom .cached_local import local_search')
    core = core.replace('k.local_search(', 'local_search(')
    (ROOT / 'algo/cached_iterated.py').write_text(core, encoding='utf-8')
    groups = (ROOT / 'algo/optimized.py').read_text(encoding='utf-8-sig')
    groups = groups.replace('from . import iterated', 'from . import iterated\nfrom . import cached_iterated\nfrom .temporal_groups import affinity_matrix, choose_group')
    groups = groups.replace('    decomposition: bool = True', '    cached_evaluation: bool = True\n    temporal_groups: bool = False\n    decomposition: bool = True')
    groups = groups.replace('    config = settings or Settings()', '    config = settings or Settings()\n    core = cached_iterated if config.cached_evaluation else iterated')
    groups = groups.replace('result = iterated.solve(', 'result = core.solve(')
    groups = groups.replace('    rng = random.Random(config.seed)', '    affinity = affinity_matrix(ins) if config.temporal_groups else None\n    rng = random.Random(config.seed)')
    groups = groups.replace('selected = select_group(ins, routes, rng, target)', 'selected = (choose_group(ins, routes, rng, target, affinity) if affinity is not None else select_group(ins, routes, rng, target))')
    groups = groups.replace('optimized-v2-', 'experimental-v6-')
    (ROOT / 'algo/experimental_v6.py').write_text(groups, encoding='utf-8')


if __name__ == '__main__':
    main()
