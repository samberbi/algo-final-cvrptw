"""Frozen experiments on the declared worst cases; historical catalog untouched."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS']:os.environ[name]='1'
from pathlib import Path
import argparse,hashlib,json,multiprocessing as mp,random,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import psutil
from algo.iterated import construct
from algo.optimized import solve as ils,warmup
from algo.profiles import production_settings
from algo.hgs_tuning import solve as hgs
from algo.verify import verify
from algo.data import load
from web.experiments import atomic_json,read_json

VARIANTS={'split60':(60.,60.,40),'split20':(20.,100.,40),
          'neighbors60':(20.,100.,60),'neighbors80':(20.,100.,80)}


def initialize(cpus):
    psutil.Process().cpu_affinity([cpus[(mp.current_process()._identity[0]-1)%len(cpus)]])
    warmup()


def execute(job):
    name,seed,variant,folder=job;target=Path(folder)/'runs'/f'{name}_{seed}_{variant}.json'
    if target.exists():
        old=read_json(target);assert old['complete'];return dict(instance=name,seed=seed,variant=variant,resumed=True)
    r=dict(instance=name,seed=seed,variant=variant)
    started=time.perf_counter()
    try:
        ins=load(ROOT/'data/instances'/(name+'.vrp'))
        initial,info=construct(ins,seed,12)
        if initial is None:raise RuntimeError('Construction failed')
        t1,t2,neighbors=VARIANTS[variant]
        first=ils(ins,production_settings('ils',seconds=t1,seed=seed),initial)
        second=hgs(ins,t2,seed+10000,first['routes'],neighbors)
        checked=verify(second['routes'],ins);assert checked['valid']
        ref=next(x['reference_distance'] for x in read_json(ROOT/'data/manifest.json')['reference_instances'] if x['instance']==name)
        r.update(complete=True,valid=True,initial_routes=initial,construction=info,
            result=second,first_phase=first,search_budget_s=t1+t2,
            total_s=info['seconds']+first['runtime_s']+second['runtime_s'],
            reference_distance=ref,gap_pct=100*(second['cost']/ref-1))
    except Exception:r.update(complete=True,valid=False,error=traceback.format_exc(),elapsed_s=time.perf_counter()-started)
    atomic_json(target,r)
    return dict(instance=name,seed=seed,variant=variant,valid=r['valid'],gap=r.get('gap_pct'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--label',required=True)
    p.add_argument('--instances',nargs='+',default=['R2_10_8','R2_10_7','RC2_10_4'])
    p.add_argument('--seeds',nargs='+',type=int,default=[3101])
    p.add_argument('--variants',nargs='+',choices=list(VARIANTS),default=list(VARIANTS))
    a=p.parse_args();assert a.label.replace('_','').isalnum()
    folder=ROOT/'results/worst_v9'/a.label
    jobs=[(n,s,v,str(folder)) for n in a.instances for s in a.seeds for v in a.variants]
    random.Random(93101).shuffle(jobs)
    sources=list((ROOT/'algo').glob('*.py'))+[Path(__file__),ROOT/'web/experiments.py']
    protocol=dict(instances=a.instances,seeds=a.seeds,variants={v:VARIANTS[v] for v in a.variants},
        workers=6,job_order=[list(j[:3]) for j in jobs],shuffle_seed=93101,
        sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        manifest_sha256=hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest(),
        objective='Original DIMACS distance; final feasibility independently verified',
        timing='Same 120s search allowance, actual construction/setup charged',
        scope='Post-hoc hard-case development; all new variants collect external convergence statistics')
    protocol=json.loads(json.dumps(protocol))
    if (folder/'protocol.json').exists():assert read_json(folder/'protocol.json')==protocol
    atomic_json(folder/'protocol.json',protocol)
    for src in sources:
        dst=folder/'source'/src.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
    cpus=psutil.Process().cpu_affinity()[::2][:6]
    with mp.get_context('spawn').Pool(len(cpus),initializer=initialize,initargs=(cpus,)) as pool:
        for r in pool.imap_unordered(execute,jobs):print(json.dumps(r),flush=True)
