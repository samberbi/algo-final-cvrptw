"""Frozen tests of new guidance mechanisms and explicit external references."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
from dataclasses import asdict
import argparse,hashlib,json,multiprocessing as mp,random,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import psutil
from algo.data import load
from algo.iterated import construct,arrays,encode,build_neighbors
from algo.optimized import solve as baseline,warmup
from algo.profiles import production_settings
from algo.guided import solve as gls,Settings as GLSSettings
from algo.penalty_hybrid import solve as penalized,Settings as PenaltySettings,walk
from algo.external_reference import solve as external
from algo.verify import verify
from web.experiments import atomic_json,read_json


def initialize(cpus):
    psutil.Process().cpu_affinity([cpus[(mp.current_process()._identity[0]-1)%len(cpus)]])
    warmup()
    ins=load(ROOT/'data/instances/C101.vrp');initial,_=construct(ins,0,1)
    a,l=encode(initial,ins)
    walk(a,l,len(l)-1,*arrays(ins),build_neighbors(ins,24),1,0,1.,1.,1.)


def execute(job):
    name,seed,variant,seconds,folder=job
    path=Path(folder)/'runs'/f'{name}_{seed}_{variant}.json'
    if path.exists():
        old=read_json(path)
        if not old.get('complete'):raise ValueError('Incomplete existing trial')
        return dict(instance=name,variant=variant,resumed=True)
    record=dict(instance=name,seed=seed,variant=variant,search_budget_s=seconds)
    try:
        ins=load(ROOT/'data/instances'/(name+'.vrp'))
        initial=None;info=dict(seconds=0.)
        if variant!='external_cold':initial,info=construct(ins,seed,12)
        if variant!='external_cold' and initial is None:raise RuntimeError('Construction failed')
        if variant=='baseline':result=baseline(ins,production_settings('ils',seconds=seconds,seed=seed),initial)
        elif variant=='gls':result=gls(ins,GLSSettings(seconds=seconds,seed=seed),initial)
        elif variant=='penalty':result=penalized(ins,PenaltySettings(seconds=seconds,seed=seed),initial)
        elif variant=='penalty_hot':result=penalized(ins,PenaltySettings(seconds=seconds,seed=seed,temperature_ratio=1.),initial)
        elif variant in ('external_cold','external_warm'):result=external(ins,seconds,seed,initial)
        else:raise ValueError('Unknown variant')
        valid=result.get('status')=='feasible'
        if valid:
            check=verify(result['routes'],ins)
            if not check['valid'] or abs(check['distance']/10-result['cost'])>1e-7:raise AssertionError(check)
        ref=next(r['reference_distance'] for r in read_json(ROOT/'data/manifest.json')['reference_instances'] if r['instance']==name)
        record.update(complete=True,valid=valid,initial_routes=initial,construction=info,result=result,
            initial_cost=verify(initial,ins)['distance']/10 if initial is not None else None,
            gap_pct=100*(result['cost']/ref-1) if valid else None,
            total_s=info['seconds']+result['runtime_s'])
    except Exception:
        record.update(complete=True,valid=False,error=traceback.format_exc())
    atomic_json(path,record)
    return dict(instance=name,seed=seed,variant=variant,valid=record['valid'],gap=record.get('gap_pct'),error=record.get('error','')[-180:])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--label',required=True)
    p.add_argument('--instances',nargs='+',default=['C2_10_8','R2_10_8','RC2_10_8'])
    p.add_argument('--seeds',nargs='+',type=int,default=[2002])
    p.add_argument('--variants',nargs='+',default=['baseline','gls','penalty','external_cold','external_warm'])
    p.add_argument('--seconds',type=float,default=60)
    a=p.parse_args();PenaltySettings(seconds=a.seconds)
    if not a.label.replace('_','').isalnum():p.error('Invalid label')
    folder=ROOT/'results/optimization_v7'/a.label
    sources=[ROOT/'algo'/(n+'.py') for n in ['__init__','data','direct','intensify','iterated','kernels','model','optimized','profiles','verify','guided','penalty_hybrid','external_reference']]+[Path(__file__)]
    jobs=[(name,seed,variant,a.seconds,str(folder)) for name in a.instances for seed in a.seeds for variant in a.variants]
    random.Random(71001).shuffle(jobs)
    protocol=dict(instances=a.instances,seeds=a.seeds,variants=a.variants,seconds=a.seconds,
        shuffle_seed=71001,job_order=[list(j[:3]) for j in jobs],workers=6,
        sources={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources},
        manifest_sha256=hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest(),
        objective='Original DIMACS distance, capacity and strict windows on every final solution',
        external='PyVRP is an external reference, never our implementation',
        timing='Same search allowance; actual external setup and original construction charged separately')
    if (folder/'protocol.json').exists() and read_json(folder/'protocol.json')!=protocol:raise ValueError('Frozen protocol differs')
    atomic_json(folder/'protocol.json',protocol)
    for f in sources:
        t=folder/'source'/f.relative_to(ROOT);t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(f.read_bytes())
    cpus=psutil.Process().cpu_affinity()[::2][:6]
    with mp.get_context('spawn').Pool(len(cpus),initializer=initialize,initargs=(cpus,)) as pool:
        for result in pool.imap_unordered(execute,jobs):print(json.dumps(result),flush=True)
