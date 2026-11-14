"""Sélection explicite par taille, sans consulter une référence ou un gap.

Petites instances : construction regret-2, recherche locale, puis ILS propre.
Au-delà : profil renforcé existant, avec Local Search PyVRP et HiGHS.
Les deux moteurs originaux sont conservés pour les comparaisons et ablations.
"""
import math
import time
from numbers import Integral

SMALL_MAX_CLIENTS=100


def selected_method(n):
    if isinstance(n,bool) or not isinstance(n,Integral) or n<0:
        raise ValueError('Nombre de clients entier non négatif requis')
    return 'construction_ls_ils' if n<=SMALL_MAX_CLIENTS else 'refined'


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
                improved=search(ins,routes,remaining,seed+20000,method='ils')
                checked=verify(improved['routes'],ins)
                assert checked['valid'] and checked['duration']<=metrics['duration']+1e-7
                routes,metrics=improved['routes'],checked
                trace.append(dict(phase='own_ils',elapsed_s=time.perf_counter()-started,best=metrics['duration']/10))
            assert metrics['duration']/10<=initial+1e-7
            result.update(routes=routes,metrics=metrics,cost=metrics['duration']/10,
                initial_cost=initial,improvement=initial-metrics['duration']/10,trace=trace,
                runtime_s=time.perf_counter()-started)
    else:
        from .duration_refine import solve as refined
        result=refined(ins,seed=seed,seconds=seconds)
    result.update(objective='duration',method='size_based',selected_method=method,
        selection_policy=dict(version=2,small_max_clients=SMALL_MAX_CLIENTS,decision_input='number_of_clients_only',
            criterion='regret-2 + PyVRP LS + own ILS for n<=100, existing refined profile otherwise',
            no_reference_or_gap_used=True),
        requested_seconds=seconds,
        budget_kind='soft total solve budget')
    return result
