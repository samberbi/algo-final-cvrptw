"""ILS/recuit et hybridation HGS minimisant la durée cumulée des tournées.

Tous les départs sont fixés à zéro. L'objectif inclut trajets, attentes et
services ; le temps CPU/mural du solveur est une mesure distincte.
"""
from dataclasses import dataclass, asdict
import math
import random
import time
import numpy as np
from .iterated import arrays, encode, decode, build_neighbors
from . import kernels
from .duration_moves import walk
from .verify import verify


def construct(ins, seed, attempts=12):
    """Sélectionne en durée le meilleur départ réalisable parmi les insertions.

    Les surcoûts de trajet guident regret-2, mais le choix entre les solutions
    complètes utilise leur véritable durée, avec toutes les attentes.
    """
    started=time.perf_counter();rng=random.Random(seed)
    best=None;value=math.inf
    for attempt in range(attempts):
        matrix,lengths=encode([],ins)
        valid=kernels.repair_fast(matrix,lengths,len(lengths)-1,*arrays(ins),2,
                                  0. if attempt==0 else .2,rng.randrange(2**31))
        if valid:
            routes=decode(matrix,lengths);checked=verify(routes,ins)
            if checked['valid'] and checked['duration']<value:
                best,value=routes,checked['duration']
    return best,dict(seconds=time.perf_counter()-started,attempts=attempts,
                     duration=value/10 if best is not None else None)


@dataclass(frozen=True)
class Settings:
    seconds: float = 10.0
    seed: int = 4101
    method: str = 'hybrid'
    ils_fraction: float = 0.5
    neighbors: int = 40
    tolerance: float = 0.005

    def __post_init__(self):
        if not math.isfinite(self.seconds) or self.seconds <= 0:
            raise ValueError('Positive finite search time required')
        if type(self.seed) is not int or not 0 <= self.seed < 2**31:
            raise ValueError('Invalid seed')
        if self.method not in ('ils', 'sa', 'hybrid'):
            raise ValueError('Choose ils, sa or hybrid')
        if not 0 < self.ils_fraction < 1 or self.neighbors < 1:
            raise ValueError('Invalid hybrid share or neighbourhood')
        if not math.isfinite(self.tolerance) or not 0 <= self.tolerance <= .2:
            raise ValueError('Invalid ILS tolerance')


def search(ins, initial, seconds, seed, method='ils', tolerance=.005):
    """Perturbe puis intensifie des solutions complètes avec un coût en durée.

    La descente locale est échantillonnée et bornée, pas une preuve d'optimum
    local. Les quatre mouvements réévaluent les tournées touchées intégralement.
    """
    started = time.perf_counter()
    checked = verify(initial, ins)
    if not checked['valid']:
        raise ValueError('Invalid initial solution')
    routes, lengths = encode(initial, ins)
    best_routes, best_lengths = routes.copy(), lengths.copy()
    current = best = checked['duration']
    initial_cost = best
    neighbors = build_neighbors(ins, 24, 'geographic')
    rng = random.Random(seed)
    trace = [dict(elapsed_s=0., best=best / 10, phase=method)]
    counts = np.zeros(7, np.int64)
    proposals = accepted = cycles = stagnant = 0
    next_log = 0.0
    while time.perf_counter() - started < seconds:
        cycles += 1
        if method == 'sa':
            fraction = min(1., (time.perf_counter() - started) / seconds)
            temperature = .02 * initial_cost / max(1, ins.n) * (.005 ** fraction)
            result = walk(routes, lengths, len(lengths)-1, *arrays(ins), neighbors,
                          256, rng.randrange(2**31), temperature, 1, counts)
            current = result[0]
            candidate, candidate_lengths, value = result[1], result[2], result[3]
            proposals += result[-1]
            accepted += result[5]
        else:
            work, lens = routes.copy(), lengths.copy()
            # Diversification : quelques mouvements réalisables, même dégradants.
            for _ in range(4):
                if time.perf_counter() - started >= seconds:
                    break
                result = walk(work, lens, len(lens)-1, *arrays(ins), neighbors,
                              64, rng.randrange(2**31), 0., 0, counts)
                proposals += result[-1]
            # Intensification : Metropolis à température nulle accepte les baisses.
            result = walk(work, lens, len(lens)-1, *arrays(ins), neighbors,
                          512, rng.randrange(2**31), 0., 1, counts)
            proposals += result[-1]
            candidate, candidate_lengths, value = result[1], result[2], result[3]
            if value <= best * (1 + tolerance) + 1e-8:
                routes, lengths, current = candidate.copy(), candidate_lengths.copy(), value
                accepted += 1
        if value < best - 1e-8:
            best_routes, best_lengths, best = candidate.copy(), candidate_lengths.copy(), value
            stagnant = 0
        else:
            stagnant += 1
        if method == 'ils' and stagnant >= 100:
            routes, lengths, current = best_routes.copy(), best_lengths.copy(), best
            stagnant = 0
        elapsed = time.perf_counter() - started
        if elapsed >= next_log:
            trace.append(dict(elapsed_s=elapsed, best=best/10, current=current/10, phase=method))
            next_log = elapsed + max(.05, seconds/100)
    solution = decode(best_routes, best_lengths)
    final = verify(solution, ins)
    assert final['valid'] and abs(final['duration']-best) < 1e-6
    elapsed = time.perf_counter()-started
    trace.append(dict(elapsed_s=elapsed, best=best/10, phase=method))
    return dict(status='feasible', objective='duration', routes=solution, cost=best/10,
                metrics=final, runtime_s=elapsed, trace=trace, iterations=proposals,
                cycles=cycles, accepted=accepted, diagnostics=counts.tolist())


def solve(ins, settings=None, initial=None):
    """Construit un départ puis optimise la durée, sans consulter de référence.

    Regret-2 utilise les trajets comme heuristique d'insertion réalisable.
    Toutes les acceptations et l'archive de recherche sont ensuite en durée.
    Construction et préparation sont ajoutées au temps de recherche mesuré.
    """
    cfg = settings or Settings()
    started = time.perf_counter()
    impossible=ins.proven_impossible()
    if impossible:
        return dict(status='proven_infeasible',objective='duration',routes=None,
                    reason=impossible,runtime_s=time.perf_counter()-started)
    construction_s = 0.
    if initial is None:
        initial, info = construct(ins, cfg.seed, 12)
        construction_s = info['seconds']
    if initial is None:
        return dict(status='not_found', objective='duration', routes=None,
                    reason='Construction failed', runtime_s=time.perf_counter()-started)
    before = verify(initial, ins)
    if not before['valid']:
        raise ValueError('Invalid initial solution')
    own_seconds = cfg.seconds * cfg.ils_fraction if cfg.method == 'hybrid' else cfg.seconds
    first = search(ins, initial, own_seconds, cfg.seed,
                   'sa' if cfg.method == 'sa' else 'ils', cfg.tolerance)
    components = [first]
    if cfg.method == 'hybrid':
        from .hgs_tuning import solve as hgs
        components.append(hgs(ins, cfg.seconds-own_seconds, cfg.seed+10000,
                              first['routes'], cfg.neighbors, objective='duration'))
    final = verify(components[-1]['routes'], ins)
    assert final['valid'] and final['duration'] <= before['duration'] + 1e-7
    assert abs(final['duration'] - final['travel'] - final['waiting'] - ins.service.sum()) < 1e-6
    trace = [dict(elapsed_s=0., best=before['duration']/10, phase='construction')]
    offset = construction_s
    for component in components:
        trace.extend(dict(p, elapsed_s=offset+p['elapsed_s']) for p in component['trace'])
        offset += component['runtime_s']
    elapsed = time.perf_counter()-started
    trace.append(dict(elapsed_s=elapsed, best=final['duration']/10, phase='final-verified'))
    return dict(status='feasible', objective='duration', method=cfg.method,
                engine='duration-own-' + cfg.method, settings=asdict(cfg),
                routes=components[-1]['routes'], cost=final['duration']/10,
                duration=final['duration']/10, travel=final['travel']/10,
                waiting=final['waiting']/10, service=float(ins.service.sum())/10,
                makespan=final['makespan']/10, distance=final['distance']/10,
                initial_cost=before['duration']/10, vehicles=final['vehicles'],
                metrics=final, runtime_s=elapsed, search_budget_s=cfg.seconds,
                construction_s=construction_s, trace=trace, components=components,
                attribution='Own duration ILS/SA and integration; external PyVRP 0.12.2 HGS when hybrid',
                time_origin='All departures fixed at zero; no departure delay discount')


def warmup():
    """Compile les mouvements en durée avant le chronométrage des essais."""
    from .model import Instance
    from .optimized import warmup as old_warmup
    old_warmup()
    matrix = np.array([[0, 80, 50], [80, 0, 50], [50, 50, 0]], float)
    ins = Instance('compile-duration', np.zeros((3, 2)), np.array([0, 2, 3]),
                   np.array([0, 50, 40]), np.array([0, 150, 0]),
                   np.array([600, 250, 400]), matrix, 6., 2, 600.)
    search(ins, [[1, 2]], .01, 0)
