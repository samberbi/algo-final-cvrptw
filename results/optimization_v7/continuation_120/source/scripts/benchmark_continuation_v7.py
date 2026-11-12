"""Matched second stages from the same measured ILS prefixes; charge both stages."""
import os
for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS']:
    os.environ[key] = '1'
from pathlib import Path
import hashlib, json, multiprocessing as mp, random, sys, time, traceback
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import psutil
from scripts.benchmark_v7 import initialize
from algo.data import load
from algo.optimized import solve as ils
from algo.profiles import production_settings
from algo.external_reference import solve as external
from algo.verify import verify
from web.experiments import atomic_json, read_json

BASE = ROOT/'results/optimization_v7'


def execute(job):
    name, seed, variant = job
    output = BASE/'continuation_120/runs'/f'{name}_{seed}_{variant}.json'
    if output.exists():
        return dict(instance=name, seed=seed, variant=variant, resumed=True)
    source = BASE/'confirmation_external/runs'/f'{name}_{seed}_baseline.json'
    prefix = read_json(source)
    assert prefix['valid'] and prefix['complete']
    initial = prefix['result']['routes']
    record = dict(instance=name, seed=seed, variant=variant, search_budget_s=120.,
        prefix=dict(path=str(source.relative_to(ROOT)), sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    total_s=prefix['total_s'], search_budget_s=60.),
        continuation_seed=seed+10000, new_search_budget_s=60.,
        initial_routes=initial, initial_cost=prefix['result']['cost'])
    started = time.perf_counter()
    try:
        ins = load(ROOT/'data/instances'/(name+'.vrp'))
        if variant == 'baseline':
            result = ils(ins, production_settings('ils', seconds=60., seed=seed+10000), initial)
        else:
            result = external(ins, 60., seed+10000, initial)
        check = verify(result['routes'], ins)
        assert check['valid'] and abs(check['distance']/10-result['cost']) < 1e-7
        assert result['cost'] <= prefix['result']['cost'] + 1e-7
        ref = next(r['reference_distance'] for r in read_json(ROOT/'data/manifest.json')['reference_instances'] if r['instance'] == name)
        record.update(complete=True, valid=True, result=result,
            gap_pct=100*(result['cost']/ref-1),
            total_s=prefix['total_s']+result['runtime_s'], newly_executed_s=result['runtime_s'])
    except Exception:
        record.update(complete=True, valid=False, error=traceback.format_exc(),
                      newly_executed_s=time.perf_counter()-started)
    atomic_json(output, record)
    return dict(instance=name, seed=seed, variant=variant, valid=record['valid'], gap=record.get('gap_pct'))


if __name__ == '__main__':
    previous = read_json(BASE/'confirmation_external/protocol.json')
    jobs = [(n, s, v) for n in previous['instances'] for s in previous['seeds'] for v in ['baseline', 'hybrid_hgs']]
    random.Random(71202).shuffle(jobs)
    folder = BASE/'continuation_120'
    sources = [ROOT/name for name in previous['sources']] + [Path(__file__)]
    origins = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (BASE/'confirmation_external/runs').glob('*_baseline.json')}
    protocol = dict(instances=previous['instances'], seeds=previous['seeds'], variants=['baseline', 'hybrid_hgs'],
        seconds=120., new_stage_seconds=60., prefix_origins=origins, workers=6,
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        manifest_sha256=previous['manifest_sha256'], shuffle_seed=71202, job_order=[list(j) for j in jobs],
        objective=previous['objective'], external=previous['external'],
        timing='Both pipelines charge the same previously measured 60s ILS prefix plus a newly executed 60s stage; construction and setup charged; 24 prefixes reused, not rerun')
    if (folder/'protocol.json').exists():
        assert read_json(folder/'protocol.json') == protocol
    atomic_json(folder/'protocol.json', protocol)
    for path in sources:
        target = folder/'source'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    cpus = psutil.Process().cpu_affinity()[::2][:6]
    with mp.get_context('spawn').Pool(len(cpus), initializer=initialize, initargs=(cpus,)) as pool:
        for result in pool.imap_unordered(execute, jobs):
            print(json.dumps(result), flush=True)
