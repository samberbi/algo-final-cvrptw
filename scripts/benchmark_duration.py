"""Campagne neuve en durée : données inchangées, références réévaluées après recherche."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):
    os.environ[key]='1'
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import multiprocessing as mp
import platform
import random
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import psutil
from algo.duration import Settings, solve, warmup
from algo.data import load, reference
from algo.verify import verify


def write(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
    temporary.replace(path)


def initialize(cpus):
    identity=mp.current_process()._identity
    psutil.Process().cpu_affinity([cpus[(identity[0]-1)%len(cpus)]])
    warmup()
    import pyvrp


def execute(job):
    instance,seed,method,seconds,label,core=job
    target=ROOT/'results/time_objective'/label/'runs'/f'{instance}_{seed}_{method}.json'
    if target.exists():
        record=json.loads(target.read_text())
        assert record['complete'] and record['budget_s']==seconds
        return instance,record['valid'],record.get('duration')
    started=time.perf_counter()
    record=dict(instance=instance,seed=seed,method=method,budget_s=seconds,core=core,
                objective='sum_route_duration',departures=0,reference_kind='duration_of_distance_BKS_plan')
    try:
        ins=load(ROOT/'data/instances'/(instance+'.vrp'))
        result=solve(ins,Settings(seconds=seconds,seed=seed,method=method))
        valid=result['status']=='feasible'
        # La référence n'est lue qu'après le retour du solveur.
        reference_routes,reference_distance=reference(ROOT/'data/instances'/(instance+'.sol'))
        control=verify(reference_routes,ins)
        assert control['valid'] and abs(control['distance']/10-reference_distance)<1e-7
        record.update(n=ins.n,result=result,valid=valid,reference_duration=control['duration']/10,
                      reference_travel=control['travel']/10,reference_waiting=control['waiting']/10,
                      reference_service=float(ins.service.sum())/10,total_s=result['runtime_s'])
        if valid:
            metrics=verify(result['routes'],ins)
            assert metrics['valid'] and abs(result['cost']-metrics['duration']/10)<1e-7
            record.update(duration=result['cost'],travel=metrics['travel']/10,
                          waiting=metrics['waiting']/10,service=float(ins.service.sum())/10,
                          makespan=metrics['makespan']/10,vehicles=metrics['vehicles'],
                          initial_duration=result['initial_cost'],
                          delta_reference_pct=100*(result['cost']/record['reference_duration']-1),
                          gain_initial_pct=100*(1-result['cost']/result['initial_cost']))
    except Exception:
        record.update(valid=False,error=traceback.format_exc(),total_s=time.perf_counter()-started)
    record['complete']=True
    write(target,record)
    return instance,record['valid'],record.get('duration')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',default='catalogue')
    parser.add_argument('--seconds',type=float,default=10.)
    parser.add_argument('--workers',type=int,default=6)
    parser.add_argument('--pilot',action='store_true')
    args=parser.parse_args()
    if not args.label.replace('_','').isalnum() or args.seconds<=0 or args.workers<1:
        parser.error('Invalid campaign settings')
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    if args.pilot:
        jobs=[(n,4101,m,args.seconds,args.label,False) for n in ['C101','R2_10_8'] for m in ['ils','sa','hybrid']]
    else:
        jobs=[]
        for r in manifest['reference_instances']:
            for seed in ([4101,4102] if r['n'] in (100,1000) else [4101]):
                jobs.append((r['instance'],seed,'hybrid',args.seconds,args.label,True))
        for name in ['C101','R202','R2_10_8']:
            for seed in range(4101,4121):
                if seed>4102:
                    jobs.append((name,seed,'hybrid',args.seconds,args.label,False))
                for method in ['ils','sa']:
                    jobs.append((name,seed,method,args.seconds,args.label,False))
    random.Random(20261113).shuffle(jobs)
    sources=list((ROOT/'algo').glob('*.py'))+[Path(__file__).resolve()]
    cpus=psutil.Process().cpu_affinity()[::2][:args.workers]
    if len(cpus)<args.workers:
        cpus=psutil.Process().cpu_affinity()[:args.workers]
    protocol=dict(objective='sum_route_duration',departures=0,
                  components=['travel','waiting','service'],seconds=args.seconds,
                  hybrid_shares=[.5,.5],neighbors=40,
                  reference_kind='Duration of supplied distance-BKS routes; not a time optimum',
                  jobs=jobs,workers=args.workers,cpu_affinity=cpus,
                  manifest_sha256=hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest(),
                  sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  environment=dict(python=sys.version,platform=platform.platform(),
                                   packages={p:importlib.metadata.version(p) for p in ['pyvrp','numpy','pandas','numba','scipy']}))
    folder=ROOT/'results/time_objective'/args.label
    if (folder/'protocol.json').exists():
        assert json.loads((folder/'protocol.json').read_text())==protocol,'Use a new campaign label'
    else:
        write(folder/'protocol.json',protocol)
        for p in sources:
            destination=folder/'source'/p.relative_to(ROOT)
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(p.read_bytes())
    started=time.perf_counter();complete=0;failed=0
    with ProcessPoolExecutor(max_workers=args.workers,initializer=initialize,initargs=(cpus,)) as pool:
        pending=[pool.submit(execute,job) for job in jobs]
        for future in as_completed(pending):
            name,valid,duration=future.result();complete+=1;failed+=not valid
            write(folder/'progress.json',dict(completed=complete,total=len(jobs),failed=failed,
                                            wall_s=time.perf_counter()-started,last=name))
            if complete%10==0 or complete==len(jobs):
                print(f'{complete}/{len(jobs)}; failures={failed}; wall={time.perf_counter()-started:.1f}s',flush=True)


if __name__=='__main__':
    main()
