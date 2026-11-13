"""Detached sequential worker. BKS values are used only after solving."""
import os
for _key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS']:
    os.environ[_key] = '1'

from pathlib import Path
from dataclasses import asdict
import hashlib
import sys
import time
import traceback

from algo.data import load
from algo.optimized import Settings, solve, warmup
from algo.profiles import production_settings
from algo.verify import verify
from web.experiments import ROOT, PROFILES, atomic_json, now, read_json


def run(folder):
    """Exécute séquentiellement les essais décrits par un protocole enregistré.
    Contrôle les empreintes du code et des données avant de commencer, puis publie
    la progression et chaque résultat. Les échecs sont enregistrés, sans disparaître du bilan."""
    folder = Path(folder)
    protocol = read_json(folder / 'protocol.json')
    total = protocol['total']
    state = dict(status='warming', completed=0, total=total, started_at=now())
    def update(**kwargs):
        state.update(kwargs, updated_at=now())
        atomic_json(folder / 'progress.json', state)
    try:
        update()
        for relative, expected in protocol['source_sha256'].items():
            if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
                raise ValueError('Code modifié depuis la création du protocole : ' + relative)
        if hashlib.sha256((ROOT / 'data/manifest.json').read_bytes()).hexdigest() != protocol['manifest_sha256']:
            raise ValueError('Référentiel modifié depuis la création du protocole')
        refs = {r['instance']: r for r in read_json(ROOT / 'data/manifest.json')['reference_instances']}
        if protocol['objective']=='duration':
            from algo.duration import warmup as duration_warmup
            started_warmup=time.perf_counter();duration_warmup();startup=time.perf_counter()-started_warmup
        else:
            startup = warmup()
        if any(PROFILES[job['profile']]['method'] in ('ils_v6','ils_cached') for job in protocol['jobs']):
            from algo.cached_iterated import warmup as warmup_cache
            warm_start=time.perf_counter()
            warmup_cache()
            startup+=time.perf_counter()-warm_start
        if any(PROFILES[job['profile']]['method'] == 'ils_rvnd' for job in protocol['jobs']):
            from algo.ils_rvnd import warmup as warmup_rvnd
            warm_start = time.perf_counter()
            warmup_rvnd()
            startup += time.perf_counter() - warm_start
        update(status='running', warmup_s=startup)
        for job in protocol['jobs']:
            if (folder / 'STOP').exists():
                update(status='stopped', current=None)
                return
            update(current=job)
            start = time.perf_counter()
            ref = refs[job['instance']]
            valid, gap = False, None
            try:
                path = ROOT / 'data/instances' / (job['instance'] + '.vrp')
                ins = load(path)
                if protocol['objective']=='duration':
                    from algo.duration import Settings as DurationSettings,solve as duration_solve
                    method=PROFILES[job['profile']]['method'].removeprefix('duration_')
                    result=duration_solve(ins,DurationSettings(seconds=protocol['seconds'],seed=job['seed'],method=method))
                elif PROFILES[job['profile']]['method'] == 'ils_hgs_refined':
                    from algo.refined_hybrid import Settings as RefinedSettings, solve as refined_solve
                    result=refined_solve(ins,RefinedSettings(search_seconds=protocol['seconds'],seed=job['seed']))
                elif PROFILES[job['profile']]['method'] == 'ils_hgs':
                    from algo.hybrid_reference import Settings as HybridSettings, solve as hybrid_solve
                    result=hybrid_solve(ins,HybridSettings(search_seconds=protocol['seconds'],seed=job['seed']))
                elif PROFILES[job['profile']]['method'] in ('ils_v6','ils_cached'):
                    from algo.experimental_v6 import Settings as V6Settings, solve as v6_solve
                    params=asdict(production_settings('ils',seconds=protocol['seconds'],seed=job['seed']))
                    params.update(cached_evaluation=True,temporal_groups=PROFILES[job['profile']]['method']=='ils_v6')
                    result=v6_solve(ins,V6Settings(**params))
                elif PROFILES[job['profile']]['method'] == 'ils_sp':
                    from algo.ils_sp import Settings as SPSettings, solve as sp_solve
                    result = sp_solve(ins, SPSettings(seconds=protocol['seconds'], seed=job['seed']))
                elif PROFILES[job['profile']]['method'] == 'ils_rvnd':
                    from algo.ils_rvnd import Settings as RVNDSettings, solve as rvnd_solve
                    result = rvnd_solve(ins, RVNDSettings(seconds=protocol['seconds'], seed=job['seed']))
                else:
                    result = solve(ins, production_settings(seconds=protocol['seconds'], seed=job['seed'], **PROFILES[job['profile']]))
                if result['status'] == 'feasible' and protocol['polish_seconds'] > 0:
                    from ameliorations.decomposition import polish
                    offset = result['runtime_s']
                    if protocol['objective']=='duration':
                        extra=duration_solve(ins,DurationSettings(seconds=protocol['polish_seconds'],seed=job['seed']+600000,method='ils'),result['routes'])
                    else:
                        extra = polish(ins, result['routes'], protocol['polish_seconds'], job['seed'] + 600000)
                    result['trace'].append(dict(elapsed_s=offset, best=result['cost'], phase='décomposition'))
                    result['trace'].extend(dict(elapsed_s=offset + p['elapsed_s'], best=p['best'], phase='décomposition')
                                           for p in extra['trace'])
                    result.update(routes=extra['routes'], cost=extra['cost'], vehicles=extra['vehicles'],
                                  runtime_s=offset + extra['runtime_s'])
                    result['trace'].append(dict(elapsed_s=result['runtime_s'], best=result['cost'], phase='fin'))
                if result['status'] == 'feasible':
                    checked = verify(result['routes'], ins)
                    metric=protocol['objective']
                    if not checked['valid'] or abs(checked[metric] / 10 - result['cost']) > 1e-7:
                        raise AssertionError(checked['errors'] or 'Distance incohérente')
                    result['metrics'] = checked
                    valid = True
                    if metric=='distance':
                        gap = 100 * (result['cost'] / ref['reference_distance'] - 1)
            except Exception as exc:
                result = dict(status='error', reason=str(exc), traceback=traceback.format_exc(), runtime_s=time.perf_counter() - start)
            item = dict(job=job, n=ref['n'], result=result, valid=valid, gap_pct=gap,
                        reference_distance=ref['reference_distance'],
                        budget_s=protocol['seconds'] + protocol['polish_seconds'],
                        finished_at=now(), wall_s=time.perf_counter() - start)
            if protocol['objective']=='duration':
                item.update(objective='duration',reference_duration=None,
                            reference_kind='duration_of_distance_BKS_plan_not_time_optimum',
                            delta_reference_pct=None)
                if valid:
                    try:
                        from algo.data import reference
                        routes,_=reference(ROOT/'data/instances'/(job['instance']+'.sol'))
                        control=verify(routes,ins)
                        assert control['valid']
                        item.update(reference_duration=control['duration']/10,
                                    delta_reference_pct=100*(result['cost']/(control['duration']/10)-1))
                    except Exception as exc:
                        item.update(valid=False,uncompared_solution=result,
                                    result=dict(status='error',reason='Référence temporelle indisponible : '+str(exc),
                                                runtime_s=time.perf_counter()-start))
            atomic_json(folder / 'runs' / f'{job["id"]:05d}.json', item)
            update(completed=job['id'] + 1)
        update(status='completed', current=None, finished_at=now())
    except Exception as exc:
        update(status='error', error=str(exc), traceback=traceback.format_exc())


if __name__ == '__main__':
    run(Path(sys.argv[1]).resolve())
