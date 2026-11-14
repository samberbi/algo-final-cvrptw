"""Sélection explicite par taille, sans consulter une référence ou un gap.

Petites instances : construction regret-2, recherche locale, puis ILS propre.
Au-delà : profil renforcé, puis HGS externe si le budget restant le permet.
Les deux moteurs originaux sont conservés pour les comparaisons et ablations.
"""
import math
import time
from numbers import Integral

SMALL_MAX_CLIENTS=100


def selected_method(n):
    if isinstance(n,bool) or not isinstance(n,Integral) or n<0:
        raise ValueError('Nombre de clients entier non négatif requis')
    return 'construction_ls_ils' if n<=SMALL_MAX_CLIENTS else 'refined_hgs'


def solve(ins,seed=4101,seconds=5.):
    if not math.isfinite(seconds) or seconds<=0:raise ValueError('Budget positif fini requis')
    if type(seed) is not int or not 0<=seed<2**31:raise ValueError('Graine sur 31 bits requise')
    method=selected_method(ins.n)
    impossible=ins.proven_impossible()
    if impossible:
        result=dict(status='proven_infeasible',routes=None,reason=impossible)
    elif method=='construction_ls_ils':
        from .duration import construct,search
        from .verify import verify
        started=time.perf_counter()
        routes,info=construct(ins,seed,attempts=12)
        result=dict(status='feasible' if routes is not None else 'not_found',routes=routes,
                    construction=info,trace=[],
                    attribution='Own regret-2 and ILS; external PyVRP Local Search; no HGS or set partitioning on small cases')
        if routes is not None:
            metrics=verify(routes,ins)
            if not metrics['valid']:raise AssertionError(metrics['errors'])
            initial=metrics['duration']/10
            initial_routes=[list(route) for route in routes]
            trace=[dict(phase='construction',elapsed_s=time.perf_counter()-started,best=initial)]
            if seconds-(time.perf_counter()-started)>.02:
                from .duration_refine import DurationLocalSearch
                local=DurationLocalSearch(ins,seed)
                for count in [40,80,120]:
                    if time.perf_counter()-started>=seconds:break
                    candidate,_=local.improve(routes,count)
                    checked=verify(candidate,ins)
                    assert checked['valid'] and checked['duration']<=metrics['duration']+1e-7
                    routes,metrics=candidate,checked
                    trace.append(dict(phase='external_pyvrp_ls',neighbors=count,
                        elapsed_s=time.perf_counter()-started,best=metrics['duration']/10))
            remaining=seconds-(time.perf_counter()-started)
            if remaining>.05:
                ils_offset=time.perf_counter()-started
                improved=search(ins,routes,remaining,seed+20000,method='ils')
                checked=verify(improved['routes'],ins)
                assert checked['valid'] and checked['duration']<=metrics['duration']+1e-7
                routes,metrics=improved['routes'],checked
                for point in improved.get('trace',[]):
                    trace.append(dict(point,elapsed_s=ils_offset+point['elapsed_s'],phase='own_ils_observed'))
                trace.append(dict(phase='own_ils',elapsed_s=time.perf_counter()-started,best=metrics['duration']/10))
            assert metrics['duration']/10<=initial+1e-7
            result.update(routes=routes,metrics=metrics,cost=metrics['duration']/10,
                initial_routes=initial_routes,initial_cost=initial,improvement=initial-metrics['duration']/10,trace=trace,
                runtime_s=time.perf_counter()-started)
    else:
        from .duration_refine import solve as refined
        from .verify import verify
        started=time.perf_counter()
        # Le profil fini ne consomme pas spontanément tout un budget long.
        # Garder une première solution, puis exploiter le reliquat sans cible BKS.
        result=refined(ins,seed=seed,seconds=min(5.,seconds))
        if result.get('routes') is not None:
            initial_routes=[list(route) for route in result['routes']]
            initial=verify(initial_routes,ins)
            assert initial['valid']
            result.update(initial_routes=initial_routes,initial_cost=initial['duration']/10)
            remaining=seconds-(time.perf_counter()-started)
            if remaining>2.:
                from .hgs_tuning import solve as hgs
                continuation_started=time.perf_counter()-started
                continuation=hgs(ins,seconds=remaining-1.,seed=seed,
                    initial=initial_routes,neighbor_count=60,objective='duration')
                checked=verify(continuation['routes'],ins)
                assert checked['valid'] and checked['duration']<=initial['duration']+1e-7
                result.update(routes=continuation['routes'],metrics=checked,cost=checked['duration']/10,
                    continuation=continuation,
                    continuation_started_s=continuation_started,
                    attribution='Own constructions and route-pool model; external PyVRP LS and HGS, SciPy HiGHS partitioning')
            checked=verify(result['routes'],ins)
            result.update(improvement=(initial['duration']-checked['duration'])/10,
                          runtime_s=time.perf_counter()-started)
    result.update(objective='duration',method='size_based',selected_method=method,
        selection_policy=dict(version=2,small_max_clients=SMALL_MAX_CLIENTS,decision_input='number_of_clients_only',
            criterion='regret-2 + PyVRP LS + own ILS for n<=100; refined then external HGS within remaining time otherwise',
            no_reference_or_gap_used=True),
        requested_seconds=seconds,
        budget_kind='soft total solve budget')
    return result
