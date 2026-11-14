"""Sélection explicite par taille, sans consulter une référence ou un gap.

Petites instances (au plus 100 clients) : construction propre regret-2 seule.
Au-delà : profil renforcé existant, avec Local Search PyVRP et HiGHS.
Les deux moteurs originaux sont conservés pour les comparaisons et ablations.
"""
import math
from numbers import Integral

SMALL_MAX_CLIENTS=100


def selected_method(n):
    if isinstance(n,bool) or not isinstance(n,Integral) or n<0:
        raise ValueError('Nombre de clients entier non négatif requis')
    return 'construction' if n<=SMALL_MAX_CLIENTS else 'refined'


def solve(ins,seed=4101,seconds=5.):
    if not math.isfinite(seconds) or seconds<=0:raise ValueError('Budget positif fini requis')
    if type(seed) is not int or not 0<=seed<2**31:raise ValueError('Graine sur 31 bits requise')
    method=selected_method(ins.n)
    impossible=ins.proven_impossible()
    if impossible:
        result=dict(status='proven_infeasible',routes=None,reason=impossible)
    elif method=='construction':
        from .duration import construct
        from .verify import verify
        routes,info=construct(ins,seed,attempts=12)
        result=dict(status='feasible' if routes is not None else 'not_found',routes=routes,
                    construction=info,attribution='Own regret-2 construction, no local search/HGS/partitioning')
        if routes is not None:
            metrics=verify(routes,ins)
            if not metrics['valid']:raise AssertionError(metrics['errors'])
            result.update(metrics=metrics,cost=metrics['duration']/10)
    else:
        from .duration_refine import solve as refined
        result=refined(ins,seed=seed,seconds=seconds)
    result.update(objective='duration',method='size_based',selected_method=method,
        selection_policy=dict(small_max_clients=SMALL_MAX_CLIENTS,decision_input='number_of_clients_only',
            criterion='construction for n<=100, existing refined profile otherwise',
            no_reference_or_gap_used=True),
        requested_seconds=seconds,
        budget_kind='12 construction attempts' if method=='construction' else 'soft total solve budget')
    return result
