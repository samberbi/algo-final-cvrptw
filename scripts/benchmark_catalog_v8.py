"""Frozen full-catalog coverage, plus a second seed on the two requested sizes."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS']:
    os.environ[key] = '1'
from pathlib import Path
import hashlib, json, multiprocessing as mp, random, sys, time, traceback
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import psutil
from algo.data import load
from algo.hybrid_reference import solve, Settings
from algo.optimized import warmup
from algo.verify import verify
from web.experiments import atomic_json, read_json

BASE = ROOT/'results/catalog_v8'
BUDGETS = {100:10., 200:16., 400:32., 600:48., 800:64., 1000:120.}


def initialize(cpus):
    psutil.Process().cpu_affinity([cpus[(mp.current_process()._identity[0]-1)%len(cpus)]])
    warmup()


def execute(job):
    name, n, seed = job
    path = BASE/'runs'/f'{name}_{seed}.json'
    if path.exists():
        old = read_json(path)
        assert old['complete']
        return dict(instance=name,seed=seed,resumed=True)
    started = time.perf_counter()
    r = dict(instance=name,n=n,seed=seed,search_budget_s=BUDGETS[n],reused=False)
    try:
        ins = load(ROOT/'data/instances'/(name+'.vrp'))
        source = ROOT/'results/optimization_v7/continuation_120/runs'/f'{name}_{seed}_hybrid_hgs.json'
        if n == 1000 and source.exists():
            previous = read_json(source)
            assert previous['complete'] and previous['valid']
            prefix_path = ROOT/previous['prefix']['path']
            assert hashlib.sha256(prefix_path.read_bytes()).hexdigest() == previous['prefix']['sha256']
            prefix = read_json(prefix_path)
            result = dict(previous['result'])
            result.update(runtime_s=previous['total_s'], engine='our-ils-then-external-pyvrp-hgs',
                attribution='Our ILS; external HGS implemented by PyVRP, not by us',
                components=[prefix['result'], previous['result']],
                settings=dict(search_seconds=120.,seed=seed,ils_fraction=.5))
            r.update(reused=True,origin=str(source.relative_to(ROOT)),
                     origin_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        else:
            result = solve(ins,Settings(search_seconds=BUDGETS[n],seed=seed))
        valid = result.get('status') == 'feasible'
        if valid:
            checked = verify(result['routes'],ins)
            assert checked['valid'] and abs(checked['distance']/10-result['cost']) < 1e-7
        # No reference is available to the solver; read it only now.
        ref = next(x['reference_distance'] for x in read_json(ROOT/'data/manifest.json')['reference_instances'] if x['instance']==name)
        r.update(complete=True,valid=valid,result=result,total_s=result['runtime_s'],
                 reference_distance=ref,gap_pct=100*(result['cost']/ref-1) if valid else None,
                 newly_executed_s=0. if r['reused'] else result['runtime_s'])
    except Exception:
        r.update(complete=True,valid=False,error=traceback.format_exc(),
                 newly_executed_s=time.perf_counter()-started)
    atomic_json(path,r)
    return dict(instance=name,n=n,seed=seed,valid=r['valid'],gap=r.get('gap_pct'),reused=r['reused'])


if __name__=='__main__':
    manifest = read_json(ROOT/'data/manifest.json')
    jobs = [(r['instance'],r['n'],2101) for r in manifest['reference_instances']]
    jobs += [(r['instance'],r['n'],2102) for r in manifest['reference_instances'] if r['n'] in [100,1000]]
    assert len(jobs)==472 and len({j[0] for j in jobs})==356
    random.Random(81111).shuffle(jobs)
    sources = list((ROOT/'algo').glob('*.py')) + [Path(__file__),ROOT/'web/experiments.py']
    previous = read_json(ROOT/'results/optimization_v7/continuation_120/protocol.json')
    old = {Path(p).as_posix():sha for p,sha in previous['sources'].items()}
    for name in ['optimized','iterated','profiles','external_reference','direct','kernels','intensify','model','verify','data']:
        relative = f'algo/{name}.py'
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==old[relative]
    protocol = dict(instances=sorted({j[0] for j in jobs}),planned=472,
        complete_scope=dict(instances=356,seed=2101),core_scope=dict(instances=116,seeds=[2101,2102]),
        budgets_by_clients=BUDGETS,ils_fraction=.5,second_seed_offset=10000,
        workers=6,shuffle_seed=81111,job_order=[list(j) for j in jobs],
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        manifest_sha256=hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest(),
        convention=manifest['convention'],reference_revision=manifest['revision'],
        reused_scope='24 existing two-stage results, independently verified and fully charged; not new solves',
        timing='Half search allowance per engine; actual construction/setup charged additionally; warm compilation excluded',
        attribution='Our integration/ILS; external PyVRP 0.12.2 HGS')
    if (BASE/'protocol.json').exists():
        assert read_json(BASE/'protocol.json')==protocol,'Frozen protocol differs'
    atomic_json(BASE/'protocol.json',protocol)
    for p in sources:
        t=BASE/'source'/p.relative_to(ROOT);t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(p.read_bytes())
    cpus=psutil.Process().cpu_affinity()[::2][:6]
    with mp.get_context('spawn').Pool(len(cpus),initializer=initialize,initargs=(cpus,)) as pool:
        for r in pool.imap_unordered(execute,jobs):
            print(json.dumps(r),flush=True)
