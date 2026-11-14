"""ILS temporel propre pour le pilote Dabia2013, distinct du moteur statique.

Notre code construit et explore les ordres de visite (insertion, relocate,
swap, 2-opt, 2-opt*). Les horaires de départ optimaux et les coûts temporels
sont fournis par le contrôleur externe MAMUT 0.12.0, explicitement attribué.
Aucune BKS n'est lue ni transmise à la recherche. Pas de HGS statique utilisé.
"""
from functools import lru_cache
import math
import random
import time


class TemporalEvaluator:
    def __init__(self, loaded):
        from mamut_routing_lib.td import compute_route_duration
        self.loaded = loaded
        self.ins = loaded.instance
        self.native = compute_route_duration
        self.calls = 0
        self.evaluate = lru_cache(maxsize=60000)(self._evaluate)

    def _evaluate(self, route):
        if not route:
            return (0., 0.)
        if sum(self.ins.demands[i] for i in route) > self.ins.vehicle_capacity:
            return (math.inf, None)
        self.calls += 1
        value = self.native(self.ins, self.loaded.atfs, list(route))
        if not value.feasible:
            return (math.inf, None)
        return (value.duration, value.departure_time)

    def cost(self, routes):
        # Même ordre d'addition que le contrat canonique.
        return sum(self.evaluate(tuple(r))[0] for r in sorted((r for r in routes if r), key=lambda r:r[0]))


def construct(evaluator, rng, variant=0):
    """Insertion séquentielle réalisable ; le score d'insertion est temporel.

    Toute position proposée optimise son départ via le contrôleur MAMUT.
    Les fenêtres au plus tôt servent à ordonner les clients, jamais à remplacer
    le vrai coût dépendant de l'heure. Pas de recherche dans une BKS.
    """
    ins = evaluator.ins
    clients = list(range(1, ins.num_customers+1))
    if variant == 0:
        clients.sort(key=lambda i:ins.time_windows[i][1])
    elif variant == 1:
        clients.sort(key=lambda i:ins.time_windows[i][0])
    else:
        rng.shuffle(clients)
    routes = []
    for client in clients:
        best = (math.inf, None, None)
        for ridx, route in enumerate(routes):
            old = evaluator.evaluate(tuple(route))[0]
            for pos in range(len(route)+1):
                trial = route[:pos]+[client]+route[pos:]
                cost = evaluator.evaluate(tuple(trial))[0]
                if cost-old < best[0]:
                    best = (cost-old, ridx, trial)
        single = evaluator.evaluate((client,))[0]
        if len(routes) < ins.num_vehicles and single < best[0]:
            routes.append([client])
        elif best[1] is not None:
            routes[best[1]] = best[2]
        else:
            return None
    return routes


def candidates(routes, rng):
    """Quatre mouvements conservant les clients ; contraintes contrôlées après.

    La liste des mouvements est mélangée pour éviter une priorité systématique
    au premier client. Les doublons entre voisinages restent sans conséquence.
    """
    moves = []
    for a, first in enumerate(routes):
        for p in range(len(first)):
            for q in range(p+2, len(first)+1):
                moves.append(('two_opt', a, p, a, q))
            for b, second in enumerate(routes):
                for q in range(len(second)+1):
                    if a != b or q not in (p, p+1):
                        moves.append(('relocate', a, p, b, q))
                if b > a:
                    for q in range(len(second)):
                        moves.append(('swap', a, p, b, q))
        for b in range(a+1, len(routes)):
            for p in range(len(first)+1):
                for q in range(len(routes[b])+1):
                    moves.append(('two_opt_star', a, p, b, q))
    rng.shuffle(moves)
    for kind, a, p, b, q in moves:
        trial = [r[:] for r in routes]
        if kind == 'two_opt':
            trial[a][p:q] = reversed(trial[a][p:q])
        elif kind == 'relocate':
            client = trial[a].pop(p)
            trial[b].insert(q-int(a == b and q > p), client)
        elif kind == 'swap':
            trial[a][p], trial[b][q] = trial[b][q], trial[a][p]
        else:
            trial[a], trial[b] = trial[a][:p]+trial[b][q:], trial[b][:q]+trial[a][p:]
        yield kind, [r for r in trial if r]


def solve(loaded, seconds=10., seed=4101):
    """Construction + ILS sous limite souple ; archive toujours réalisable.

    Le temps inclut construction et évaluation finale, mais pas chargement des
    fichiers. Une évaluation native commencée n'est pas interrompue.
    """
    if not math.isfinite(seconds) or seconds <= 0 or type(seed) is not int or seed < 0:
        raise ValueError('Budget positif fini et graine entière positive requis')
    started, cpu = time.perf_counter(), time.process_time()
    deadline = started+seconds
    ev = TemporalEvaluator(loaded)
    rng = random.Random(seed)
    best_routes = construct(ev, rng)
    if best_routes is None:
        return dict(status='not_found', routes=None, runtime_s=time.perf_counter()-started,
                    cpu_s=time.process_time()-cpu, objective='Duration')
    best = initial = ev.cost(best_routes)
    current_routes, current = best_routes, best
    trace = [dict(elapsed_s=time.perf_counter()-started, best=best, phase='construction')]
    proposals, cycles, accepted = 0, 0, 0
    operators = {k:0 for k in ['relocate', 'swap', 'two_opt', 'two_opt_star']}
    while time.perf_counter() < deadline:
        improved = False
        for kind, trial in candidates(current_routes, rng):
            if time.perf_counter() >= deadline:
                break
            proposals += 1
            cost = ev.cost(trial)
            if cost < current-1e-8:
                current_routes, current = trial, cost
                operators[kind] += 1
                accepted += 1
                improved = True
                if cost < best-1e-8:
                    best_routes, best = [r[:] for r in trial], cost
                    trace.append(dict(elapsed_s=time.perf_counter()-started, best=best, phase=kind))
                break
        if improved:
            continue
        cycles += 1
        # Plusieurs départs et perturbations de la meilleure solution : ILS,
        # sans destruction/réparation adaptative ni population génétique.
        if cycles % 3 == 0:
            trial = construct(ev, rng, 1 if cycles == 3 else 2)
        else:
            trial = None
            for _, candidate in candidates(best_routes, rng):
                if time.perf_counter() >= deadline:
                    break
                value = ev.cost(candidate)
                if math.isfinite(value):
                    trial = candidate
                    break
        if trial is not None:
            current_routes, current = trial, ev.cost(trial)
            if current < best-1e-8:
                best_routes, best = [r[:] for r in trial], current
                trace.append(dict(elapsed_s=time.perf_counter()-started, best=best, phase='restart'))
    from mamut_routing_lib.models import BenchmarkSolution
    from mamut_routing_lib.td import check_td_solution
    final = check_td_solution(loaded, BenchmarkSolution(instance_name=ev.ins.instance_name, routes=best_routes))
    if not final.is_valid() or abs(final.routing_cost-best) > 1e-7:
        raise AssertionError(final)
    elapsed = time.perf_counter()-started
    return dict(status='feasible', objective='Duration', routes=best_routes,
        cost=final.routing_cost, initial_cost=initial, runtime_s=elapsed, cpu_s=time.process_time()-cpu,
        budget_s=seconds, overrun_s=max(0., elapsed-seconds), trace=trace,
        route_evaluations=[r.model_dump() for r in final.route_evaluations],
        proposals=proposals, cycles=cycles, accepted=accepted, operators=operators,
        evaluation_calls=ev.calls, cache=ev.evaluate.cache_info()._asdict(),
        attribution='Own insertion, ILS and four move generators; external MAMUT 0.12.0 temporal evaluator/checker',
        checker_contract='td-fold/2', departures='optimized, not fixed at zero')


def simulate(loaded, routes, route_evaluations):
    """Diagnostic par simulation avant : trajets + attentes + services.

    Les départs viennent de l'optimisation canonique des horaires. Cette seconde
    lecture ne certifie pas l'optimum ; elle vérifie la décomposition physique.
    Tolérance de diagnostic 1e-7 pour les arrondis des doubles. L'acceptation
    canonique finale, elle, reste celle du contrôleur externe sans epsilon.
    """
    ins = loaded.instance
    details, errors, seen = [], [], []
    for route, evaluation in zip(routes, route_evaluations):
        departure = evaluation['departure_time']
        clock = departure
        travel = waiting = service = load = 0.
        previous = ins.depot
        for client in route:
            arrival = loaded.atfs.arcs[(previous, client)].evaluate(clock, slope_one_exact=True)
            begin = max(arrival, ins.time_windows[client][0])
            if begin > ins.time_windows[client][1]+1e-7:
                errors.append(f'window:{client}')
            travel += arrival-clock
            waiting += begin-arrival
            service += ins.service_times[client]
            clock = begin+ins.service_times[client]
            load += ins.demands[client]
            previous = client
            seen.append(client)
        returned = loaded.atfs.arcs[(previous, ins.depot)].evaluate(clock, slope_one_exact=True)
        travel += returned-clock
        duration = returned-departure
        if load > ins.vehicle_capacity or returned > ins.time_windows[0][1]+1e-7:
            errors.append('capacity_or_depot')
        if abs(duration-evaluation['duration']) > 1e-7:
            errors.append('duration_mismatch')
        details.append(dict(departure=departure, returned=returned, duration=duration,
                            travel=travel, waiting=waiting, service=service, load=load))
    if sorted(seen) != list(range(1, ins.num_customers+1)):
        errors.append('coverage')
    if len(details) != len(route_evaluations) or len(routes) > ins.num_vehicles:
        errors.append('fleet_or_evaluation_count')
    return dict(valid=not errors, errors=errors, routes=details,
                **{k:sum(r[k] for r in details) for k in ['duration', 'travel', 'waiting', 'service']})
