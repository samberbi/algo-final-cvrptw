"""Extension de taille : chargement IGP à la demande et ILS à voisins bornés.

L'évaluateur temporel MAMUT reste externe et inchangé. Le pilote à 25 clients
est conservé dans algo.dabia. Aucune BKS n'entre dans la construction/recherche.
"""
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
import math
import random
import time
from .dabia import TemporalEvaluator


class LazyIGPArcs(Mapping):
    """Mêmes fonctions natives que le matérialiseur complet, calculées à la demande.

    Cache borné ; les empreintes des données et catégories sont vérifiées par
    le chargeur. L'empreinte de sérialisation de la matrice ATF complète n'est
    pas calculée dans ce mode, ce qui est explicitement enregistré au protocole.
    """
    def __init__(self, instance, categories):
        from mamut_routing_lib.td.igp import build_arc_atf, euclidean_distance
        self.ins, self.categories = instance, categories
        self.build, self.distance = build_arc_atf, euclidean_distance
        self.zones = [(float(a), float(b)) for a,b in instance.td.time_periods]
        self.speeds = [[float(x) for x in row] for row in instance.td.speeds]
        self.horizon = tuple(map(float, instance.horizon))
        self.cached = lru_cache(maxsize=20000)(self._make)

    def _make(self, key):
        i,j = key
        if i == j or not 0 <= i <= self.ins.num_customers or not 0 <= j <= self.ins.num_customers:
            raise KeyError(key)
        return self.build(self.zones, self.speeds[self.categories.category(i,j)],
                          self.distance(self.ins.coordinates[i], self.ins.coordinates[j]), self.horizon)

    def __getitem__(self, key):
        return self.cached(key)

    def __iter__(self):
        for i in range(self.ins.num_customers+1):
            for j in range(self.ins.num_customers+1):
                if i != j:
                    yield (i,j)

    def __len__(self):
        return self.ins.num_customers*(self.ins.num_customers+1)


def load_temporal(path):
    from mamut_routing_lib.td import load_td_benchmark_instance, load_td_instance
    from mamut_routing_lib.td.artifacts import InstanceATFs, LoadedTDInstance
    from mamut_routing_lib.td.igp import load_instance_categories, compute_categories_sha256
    path = Path(path)
    ins = load_td_benchmark_instance(path)
    if ins.td.model != 'igp-profile':
        return load_td_instance(path)
    categories_path = path.parent/ins.td.categories_path
    cats = load_instance_categories(categories_path)
    if (cats.num_customers != ins.num_customers or cats.num_categories != ins.td.num_categories()
            or cats.benchmark_name != ins.benchmark_name.value):
        raise ValueError('Catégories incompatibles')
    if compute_categories_sha256(cats) != ins.td.categories_sha256:
        raise ValueError('Empreinte des catégories différente')
    atfs = InstanceATFs(instance_name=ins.instance_name, benchmark_name=ins.benchmark_name.value,
        horizon=tuple(map(float, ins.horizon)), num_customers=ins.num_customers,
        arcs=LazyIGPArcs(ins, cats), generator={'mode':'native IGP functions, lazy per arc'})
    return LoadedTDInstance(instance=ins, atfs=atfs, instance_path=path,
                            atf_path=None, categories_path=categories_path)


def construct(ev, rng, deadline):
    """Insertion à nombre de routes candidates borné, puis secours exhaustif.

    Les positions sont toutes examinées dans les routes sélectionnées ; le coût
    de toute proposition reste la durée avec départ optimisé. Si aucune insertion
    n'est faisable et qu'un véhicule est disponible, une nouvelle tournée est créée.
    """
    ins = ev.ins
    order = sorted(range(1, ins.num_customers+1), key=lambda i:ins.time_windows[i][1])
    routes = []
    for client in order:
        if time.perf_counter() >= deadline:
            return None
        xy = ins.coordinates[client]
        def proximity(ridx):
            route = routes[ridx]
            return min((xy[0]-ins.coordinates[i][0])**2+(xy[1]-ins.coordinates[i][1])**2 for i in route)
        ranked = sorted(range(len(routes)), key=proximity)
        best = (math.inf, None, None)
        for ridx in ranked[:8]:
            route = routes[ridx]
            if sum(ins.demands[i] for i in route)+ins.demands[client] > ins.vehicle_capacity:
                continue
            old = ev.evaluate(tuple(route))[0]
            for pos in range(len(route)+1):
                if time.perf_counter() >= deadline:
                    return None
                trial = route[:pos]+[client]+route[pos:]
                value = ev.evaluate(tuple(trial))[0]
                if value-old < best[0]:
                    best = (value-old, ridx, trial)
        singleton = ev.evaluate((client,))[0]
        if len(routes) < ins.num_vehicles and singleton < best[0]:
            routes.append([client])
        elif best[1] is not None:
            routes[best[1]] = best[2]
        else:
            # Toutes les routes restantes sont essayées avant de déclarer l'échec.
            inserted = False
            for ridx in ranked[8:]:
                route = routes[ridx]
                for pos in range(len(route)+1):
                    if time.perf_counter() >= deadline:
                        return None
                    trial = route[:pos]+[client]+route[pos:]
                    if math.isfinite(ev.evaluate(tuple(trial))[0]):
                        routes[ridx] = trial;inserted = True;break
                if inserted:break
            if not inserted:
                return None
    return routes


def solve(loaded, seconds=20., seed=4101, neighbors=32):
    """ILS échantillonné : coût temporel exact, choix de mouvements heuristique.

    Les évaluations locales ne concernent que les tournées touchées. Les proches
    voisins guident les propositions, et une part aléatoire conserve la diversité.
    Une proposition irréalisable n'entre jamais dans l'état courant ni l'archive.
    """
    if not math.isfinite(seconds) or seconds <= 0 or neighbors < 1:
        raise ValueError('Budget positif et voisinage non vide requis')
    started, cpu = time.perf_counter(), time.process_time()
    deadline = started+seconds
    ins = loaded.instance
    ev = TemporalEvaluator(loaded)
    rng = random.Random(seed)
    routes = construct(ev, rng, deadline)
    if routes is None:
        return dict(status='not_found', routes=None, reason='Construction failed or budget exhausted',
                    runtime_s=time.perf_counter()-started, cpu_s=time.process_time()-cpu)
    best = initial = current = ev.cost(routes)
    best_routes = [r[:] for r in routes]
    trace = [dict(elapsed_s=time.perf_counter()-started, best=best, phase='construction')]
    # Cette préparation fait partie du budget mesuré.
    nearest = {}
    for i in range(1, ins.num_customers+1):
        x,y = ins.coordinates[i]
        nearest[i] = sorted((j for j in range(1, ins.num_customers+1) if j != i),
            key=lambda j:(x-ins.coordinates[j][0])**2+(y-ins.coordinates[j][1])**2)[:neighbors]
    def positions():
        return {c:(a,p) for a,r in enumerate(routes) for p,c in enumerate(r)}
    where = positions()
    proposals = accepted = 0
    stagnant = 0
    kicks = 0
    operators = {k:0 for k in ['relocate','swap','two_opt','two_opt_star']}
    while time.perf_counter() < deadline:
        proposals += 1
        client = rng.randint(1, ins.num_customers)
        other = (rng.choice(nearest[client]) if rng.random() < .8 else rng.randint(1, ins.num_customers))
        if client == other:
            continue
        a,p = where[client];b,q = where[other]
        first, second = routes[a], routes[b]
        kind = rng.choices(['relocate','swap','two_opt','two_opt_star'], [4,2,1,2])[0]
        if kind == 'two_opt':
            if a != b:
                continue
            left,right = sorted((p,q))
            ra = first[:left]+list(reversed(first[left:right+1]))+first[right+1:]
            rb = None
        elif kind == 'relocate':
            ra = first[:p]+first[p+1:]
            pos = q+rng.randrange(2)
            if a == b:
                pos -= int(pos > p)
                ra = ra[:pos]+[client]+ra[pos:];rb = None
            else:
                rb = second[:pos]+[client]+second[pos:]
        elif kind == 'swap':
            if a == b:
                ra = first[:];ra[p],ra[q] = ra[q],ra[p];rb = None
            else:
                ra = first[:p]+[other]+first[p+1:]
                rb = second[:q]+[client]+second[q+1:]
        else:
            if a == b:
                continue
            ra,rb = first[:p]+second[q:],second[:q]+first[p:]
        old = ev.evaluate(tuple(first))[0]
        value = ev.evaluate(tuple(ra))[0]
        if rb is not None:
            old += ev.evaluate(tuple(second))[0]
            value += ev.evaluate(tuple(rb))[0]
        stagnant += 1
        if math.isfinite(value) and (value < old-1e-8 or kicks > 0):
            trial = [r[:] for r in routes]
            trial[a] = ra
            if rb is not None:trial[b] = rb
            routes = [r for r in trial if r]
            current = ev.cost(routes)
            where = positions()
            accepted += 1;operators[kind] += 1
            kicks = max(0, kicks-1)
            if current < best-1e-8:
                best_routes, best = [r[:] for r in routes], current
                trace.append(dict(elapsed_s=time.perf_counter()-started, best=best, phase=kind))
                stagnant = 0
        if stagnant >= 2000:
            routes = [r[:] for r in best_routes];where = positions()
            current = best;stagnant = 0;kicks = 3
    from mamut_routing_lib.models import BenchmarkSolution
    from mamut_routing_lib.td import check_td_solution
    final = check_td_solution(loaded, BenchmarkSolution(instance_name=ins.instance_name, routes=best_routes))
    if not final.is_valid():
        raise AssertionError(final)
    elapsed = time.perf_counter()-started
    return dict(status='feasible', objective='Duration', routes=best_routes, cost=final.routing_cost,
        initial_cost=initial, runtime_s=elapsed, cpu_s=time.process_time()-cpu,
        budget_s=seconds, overrun_s=max(0.,elapsed-seconds), trace=trace,
        route_evaluations=[r.model_dump() for r in final.route_evaluations],
        proposals=proposals, accepted=accepted, operators=operators,
        evaluation_calls=ev.calls, cache=ev.evaluate.cache_info()._asdict(),
        attribution='Own bounded-neighbor insertion/ILS; external MAMUT temporal evaluator and final checker')
