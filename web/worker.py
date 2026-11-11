"""Detached sequential worker. BKS values are used only after solving."""
import os
for _key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS']:
    os.environ[_key] = '1'

from pathlib import Path
import hashlib
import sys
import time
import traceback

from algo.data import load
from algo.solver import Settings, solve, warmup, production_settings
from algo.verify import verify
from web.experiments import ROOT, PROFILES, atomic_json, now, read_json


def run(folder):
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
        startup = warmup()
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
                result = solve(ins, production_settings(seconds=protocol['seconds'], seed=job['seed'], **PROFILES[job['profile']]))
                if result['status'] == 'feasible' and protocol['polish_seconds'] > 0:
                    from ameliorations.decomposition import polish
                    offset = result['runtime_s']
                    extra = polish(ins, result['routes'], protocol['polish_seconds'], job['seed'] + 600000)
                    result['trace'].append(dict(elapsed_s=offset, best=result['cost'], phase='décomposition'))
                    result['trace'].extend(dict(elapsed_s=offset + p['elapsed_s'], best=p['best'], phase='décomposition')
                                           for p in extra['trace'])
                    result.update(routes=extra['routes'], cost=extra['cost'], vehicles=extra['vehicles'],
                                  runtime_s=offset + extra['runtime_s'])
                    result['trace'].append(dict(elapsed_s=result['runtime_s'], best=result['cost'], phase='fin'))
                if result['status'] == 'feasible':
                    checked = verify(result['routes'], ins)
                    if not checked['valid'] or abs(checked['distance'] / 10 - result['cost']) > 1e-7:
                        raise AssertionError(checked['errors'] or 'Distance incohérente')
                    result['metrics'] = checked
                    valid = True
                    gap = 100 * (result['cost'] / ref['reference_distance'] - 1)
            except Exception as exc:
                result = dict(status='error', reason=str(exc), traceback=traceback.format_exc(), runtime_s=time.perf_counter() - start)
            item = dict(job=job, n=ref['n'], result=result, valid=valid, gap_pct=gap,
                        reference_distance=ref['reference_distance'],
                        budget_s=protocol['seconds'] + protocol['polish_seconds'],
                        finished_at=now(), wall_s=time.perf_counter() - start)
            atomic_json(folder / 'runs' / f'{job["id"]:05d}.json', item)
            update(completed=job['id'] + 1)
        update(status='completed', current=None, finished_at=now())
    except Exception as exc:
        update(status='error', error=str(exc), traceback=traceback.format_exc())


if __name__ == '__main__':
    run(Path(sys.argv[1]).resolve())
