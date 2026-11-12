"""Compare one 360s search with three 120s searches, then measure pooling."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS']:os.environ[key]='1'
from pathlib import Path
import hashlib,json,multiprocessing as mp,random,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import psutil
from algo.refined_hybrid import solve,Settings
from algo.optimized import warmup
from algo.route_pool import RoutePool
from algo.data import load
from algo.verify import verify
from web.experiments import atomic_json,read_json

BASE=ROOT/'results/worst_v9/restarts360'


def initialize(cpus):
    psutil.Process().cpu_affinity([cpus[(mp.current_process()._identity[0]-1)%len(cpus)]])
    warmup()


def execute(job):
    name,strategy=job;target=BASE/'runs'/f'{name}_{strategy}.json'
    if target.exists():assert read_json(target)['complete'];return dict(instance=name,strategy=strategy,resumed=True)
    r=dict(instance=name,strategy=strategy,nominal_search_s=360.,partition_budget_s=5.)
    started=time.perf_counter()
    try:
        ins=load(ROOT/'data/instances'/(name+'.vrp'));algorithm_started=time.perf_counter()
        pool=RoutePool(ins);components=[]
        for seed in ([3301] if strategy=='long' else [3301,3302,3303]):
            result=solve(ins,Settings(search_seconds=360. if strategy=='long' else 120.,seed=seed))
            assert result['status']=='feasible'
            for phase in result['components']:pool.add_solution(phase['routes'])
            components.append(result)
        before=pool.best_cost/10
        pool_preparation_s=time.perf_counter()-algorithm_started-sum(x['runtime_s'] for x in components)
        mixed=pool.recombine(seconds=5.)
        check=verify(mixed['routes'],ins);assert check['valid'] and mixed['cost']<=before+1e-7
        ref=next(x['reference_distance'] for x in read_json(ROOT/'data/manifest.json')['reference_instances'] if x['instance']==name)
        r.update(complete=True,valid=True,components=components,result=mixed,reference_distance=ref,
            best_input_cost=before,best_input_gap=100*(before/ref-1),gap_pct=100*(mixed['cost']/ref-1),
            pool_preparation_s=pool_preparation_s,
            total_s=sum(x['runtime_s'] for x in components)+pool_preparation_s+mixed['runtime_s'],
            attribution='Our ILS/integration/restricted pooling, external PyVRP HGS')
    except Exception:r.update(complete=True,valid=False,error=traceback.format_exc(),elapsed_s=time.perf_counter()-started)
    atomic_json(target,r)
    return dict(instance=name,strategy=strategy,valid=r['valid'],before_pool=r.get('best_input_gap'),after=r.get('gap_pct'))


if __name__=='__main__':
    jobs=[(n,s) for n in ['R2_10_8','R2_10_7','RC2_10_4'] for s in ['long','multistart']]
    random.Random(93303).shuffle(jobs)
    sources=list((ROOT/'algo').glob('*.py'))+[Path(__file__),ROOT/'web/experiments.py']
    p=dict(instances=['R2_10_8','R2_10_7','RC2_10_4'],strategies=['long','multistart'],
        search_seconds=360.,partition_seconds=5.,ils_seconds_per_pipeline=20.,neighbors=40,
        long_seeds=[3301],multistart_seeds=[3301,3302,3303],workers=6,
        sources={x.relative_to(ROOT).as_posix():hashlib.sha256(x.read_bytes()).hexdigest() for x in sources},
        manifest_sha256=hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest(),
        job_order=jobs,scope='Post-hoc development, equal nominal search and MIP allowances; all actual constructions/setups charged')
    p=json.loads(json.dumps(p))
    if (BASE/'protocol.json').exists():assert read_json(BASE/'protocol.json')==p
    atomic_json(BASE/'protocol.json',p)
    for src in sources:
        dst=BASE/'source'/src.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
    cpus=psutil.Process().cpu_affinity()[::2][:6]
    with mp.get_context('spawn').Pool(len(cpus),initializer=initialize,initargs=(cpus,)) as pool:
        for r in pool.imap_unordered(execute,jobs):print(json.dumps(r),flush=True)
