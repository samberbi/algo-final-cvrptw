"""Explicit extra-budget continuation of all declared above-threshold trials."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS']:os.environ[name]='1'
from pathlib import Path
import argparse,hashlib,json,multiprocessing as mp,random,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
import psutil
from algo.data import load
from algo.hgs_tuning import solve
from algo.verify import verify
from web.experiments import atomic_json,read_json


def initialize(cpus):
    psutil.Process().cpu_affinity([cpus[(mp.current_process()._identity[0]-1)%len(cpus)]])


def execute(job):
    source,folder,seconds,neighbors,offset=job;source=Path(source);prior=read_json(source)
    name,seed=prior['instance'],prior['seed'];target=Path(folder)/'runs'/f'{name}_{seed}.json'
    if target.exists():
        assert read_json(target)['complete'];return dict(instance=name,seed=seed,resumed=True)
    paid=prior.get('total_effort_s',prior.get('total_s'))
    r=dict(instance=name,seed=seed,source=str(source.relative_to(ROOT)),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),previous_total_s=paid,
        previous_cost=prior['result']['cost'],previous_gap=prior['gap_pct'],
        search_budget_s=seconds,neighbors=neighbors,continuation_seed=seed+offset)
    started=time.perf_counter()
    try:
        assert prior['valid'] and prior['complete']
        ins=load(ROOT/'data/instances'/(name+'.vrp'))
        result=solve(ins,seconds,seed+offset,prior['result']['routes'],neighbors)
        check=verify(result['routes'],ins);assert check['valid']
        ref=next(x['reference_distance'] for x in read_json(ROOT/'data/manifest.json')['reference_instances'] if x['instance']==name)
        r.update(complete=True,valid=True,result=result,reference_distance=ref,
            gap_pct=100*(result['cost']/ref-1),total_effort_s=paid+result['runtime_s'],
            additional_runtime_s=result['runtime_s'])
    except Exception:r.update(complete=True,valid=False,error=traceback.format_exc(),elapsed_s=time.perf_counter()-started)
    atomic_json(target,r)
    return dict(instance=name,seed=seed,valid=r['valid'],before=r['previous_gap'],after=r.get('gap_pct'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--label',required=True)
    p.add_argument('--seconds',type=float,default=180.)
    p.add_argument('--neighbors',type=int,default=60)
    p.add_argument('--offset',type=int,default=20000)
    p.add_argument('--previous-folder')
    p.add_argument('--threshold',type=float,default=7.)
    a=p.parse_args();assert a.label.replace('_','').isalnum() and a.seconds>0 and a.neighbors>0
    folder=ROOT/'results/worst_v9'/a.label
    if a.previous_folder:
        origins=[q for q in (ROOT/a.previous_folder/'runs').glob('*.json') if read_json(q).get('gap_pct',-1)>=a.threshold]
    else:
        frame=pd.read_csv(ROOT/'results/catalog_v8/flat.csv')
        origins=[ROOT/path for path in frame[frame.valid&frame.gap_pct.ge(a.threshold)].source]
    assert origins,'No above-threshold trials'
    jobs=[(str(q),str(folder),a.seconds,a.neighbors,a.offset) for q in sorted(origins)]
    random.Random(93202).shuffle(jobs)
    sources=[ROOT/'algo/hgs_tuning.py',ROOT/'algo/data.py',ROOT/'algo/model.py',ROOT/'algo/verify.py',Path(__file__),ROOT/'web/experiments.py']
    protocol=dict(selection='All completed feasible source trials with measured gap >= threshold; post-hoc recovery, not a new fixed-budget catalog',
        threshold=a.threshold,seconds=a.seconds,neighbors=a.neighbors,seed_offset=a.offset,workers=6,
        origins={str(q.relative_to(ROOT)):hashlib.sha256(q.read_bytes()).hexdigest() for q in origins},
        sources={q.relative_to(ROOT).as_posix():hashlib.sha256(q.read_bytes()).hexdigest() for q in sources},
        job_order=[str(Path(j[0]).relative_to(ROOT)) for j in jobs],
        accounting='Every source trajectory plus every additional continuation charged in full',
        manifest_sha256=hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest())
    if (folder/'protocol.json').exists():assert read_json(folder/'protocol.json')==protocol
    atomic_json(folder/'protocol.json',protocol)
    for src in sources:
        dst=folder/'source'/src.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
    cpus=psutil.Process().cpu_affinity()[::2][:6]
    with mp.get_context('spawn').Pool(min(len(cpus),len(jobs)),initializer=initialize,initargs=(cpus,)) as pool:
        for r in pool.imap_unordered(execute,jobs):print(json.dumps(r),flush=True)
