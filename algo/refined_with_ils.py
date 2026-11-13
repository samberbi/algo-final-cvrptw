"""Variante expérimentale : utiliser le budget restant en ILS propre.

Le profil renforcé peut finir ses quatre redémarrages bien avant son budget.
Cette variante conserve sa solution puis intensifie avec les mouvements du
projet. Elle ne change ni les contraintes ni la référence de comparaison.
"""
import math
import time
from .refined_ablation import solve as refine
from .duration import search
from .verify import verify


def solve(ins,seed=4101,seconds=5.):
    if not math.isfinite(seconds) or seconds<=0:raise ValueError('Budget positif requis')
    started=time.perf_counter()
    # Réserver la moitié du budget à l'ILS ; les appels natifs restent non préemptifs.
    first=refine(ins,seed,max(.05,seconds*.5),partition=True)
    if first.get('routes') is None:return first
    components=[first]
    remaining=seconds-(time.perf_counter()-started)
    if remaining>.02:
        components.append(search(ins,first['routes'],remaining,seed+20000,method='ils'))
    final=components[-1]
    metrics=verify(final['routes'],ins)
    assert metrics['valid'] and metrics['duration']/10<=first['cost']+1e-7
    return dict(status='feasible',objective='duration',routes=final['routes'],cost=metrics['duration']/10,
        metrics=metrics,before_ils=first['cost'],own_ils_gain=first['cost']-metrics['duration']/10,
        components=components,runtime_s=time.perf_counter()-started,
        attribution='Own constructions, pool model and ILS; external PyVRP Local Search and SciPy HiGHS',
        limitation='Experimental candidate, not automatically selected as production default')
