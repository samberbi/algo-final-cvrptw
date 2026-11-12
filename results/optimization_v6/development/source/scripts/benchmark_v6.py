"""Paired evaluation of prefix caching and temporal route grouping."""
import os
for key in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"]:
    os.environ[key] = "1"
from dataclasses import asdict
from pathlib import Path
import argparse
import hashlib
import json
import multiprocessing as mp
import sys
import time
import traceback
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import psutil
from algo.data import load
from algo.iterated import construct
from algo.profiles import production_settings
from algo.optimized import solve as baseline_solve, warmup
from algo.cached_iterated import warmup as cache_warmup
from algo.experimental_v6 import solve, Settings
from algo.verify import verify
from web.experiments import atomic_json, read_json


def initialize(cpus):
    psutil.Process().cpu_affinity([cpus[(mp.current_process()._identity[0]-1)%len(cpus)]])
    warmup(); cache_warmup()


def execute(job):
    name, seed, variant, seconds, folder, initial_path = job
    path = Path(folder)/"runs"/f"{name}_{seed}_{variant}.json"
    if path.exists():
        old = read_json(path)
        if not old.get('complete'): raise ValueError("Incomplete prior result")
        return dict(instance=name,variant=variant,resumed=True)
    record = dict(instance=name,seed=seed,variant=variant,budget_s=seconds)
    try:
        ins = load(ROOT/'data/instances'/(name+'.vrp'))
        if initial_path:
            source = ROOT/initial_path/(name+'.json')
            initial = read_json(source)['result']['routes']
            construction = dict(seconds=0.,source=str(source.relative_to(ROOT)),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                                previous_total_effort_s=read_json(source)['total_effort_s'])
        else:
            initial,construction = construct(ins,seed,12)
        if initial is None: raise RuntimeError("Construction failed")
        cfg = production_settings('ils',seconds=seconds,seed=seed)
        if variant=='baseline':
            result = baseline_solve(ins,cfg,initial)
        else:
            params=asdict(cfg)
            params.update(cached_evaluation=variant in ('cache','combined'),temporal_groups=variant in ('temporal','combined'))
            result=solve(ins,Settings(**params),initial)
        checked=verify(result['routes'],ins)
        if not checked['valid'] or abs(checked['distance']/10-result['cost'])>1e-7: raise AssertionError(checked)
        reference=next(r['reference_distance'] for r in read_json(ROOT/'data/manifest.json')['reference_instances'] if r['instance']==name)
        record.update(complete=True,valid=True,initial_routes=initial,initial_cost=verify(initial,ins)['distance']/10,
                      construction=construction,result=result,gap_pct=100*(result['cost']/reference-1),
                      total_s=construction['seconds']+result['runtime_s'])
    except Exception:
        record.update(complete=True,valid=False,error=traceback.format_exc())
    atomic_json(path,record)
    return dict(instance=name,seed=seed,variant=variant,valid=record['valid'],gap=record.get('gap_pct'))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',required=True)
    parser.add_argument('--suffixes',nargs='+',type=int,default=[5])
    parser.add_argument('--instances',nargs='+')
    parser.add_argument('--seeds',nargs='+',type=int,default=[1701,1702])
    parser.add_argument('--variants',nargs='+',default=['baseline','cache','temporal','combined'])
    parser.add_argument('--seconds',type=float,default=20)
    parser.add_argument('--initial-folder',default=None)
    args=parser.parse_args()
    if not args.label.replace('_','').isalnum(): parser.error('Invalid label')
    if not set(args.variants)<={'baseline','cache','temporal','combined'}: parser.error('Invalid variant')
    Settings(seconds=args.seconds)
    names=args.instances or [f'{f}_10_{i}' for f in ['C1','C2','R1','R2','RC1','RC2'] for i in args.suffixes]
    folder=ROOT/'results/optimization_v6'/args.label
    sources=[ROOT/'algo'/(n+'.py') for n in ['data','direct','intensify','iterated','kernels','model','optimized','profiles','verify','cached_local','cached_iterated','temporal_groups','experimental_v6']]+[Path(__file__)]
    protocol=dict(instances=names,seeds=args.seeds,variants=args.variants,seconds=args.seconds,
                  sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  initial_folder=args.initial_folder,workers=6,objective='DIMACS distance; strict CVRPTW constraints unchanged',
                  manifest_sha256=hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest(),
                  pairing='Same deterministic initial construction per instance/seed; twelve attempts; compilation outside budget')
    if (folder/'protocol.json').exists() and read_json(folder/'protocol.json')!=protocol: raise ValueError('Frozen protocol differs')
    atomic_json(folder/'protocol.json',protocol)
    for p in sources:
        target=folder/'source'/p.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(p.read_bytes())
    jobs=[(name,seed,variant,args.seconds,str(folder),args.initial_folder) for name in names for seed in args.seeds for variant in args.variants]
    cpus=psutil.Process().cpu_affinity()[::2][:6]
    with mp.get_context('spawn').Pool(len(cpus),initializer=initialize,initargs=(cpus,)) as pool:
        for item in pool.imap_unordered(execute,jobs): print(json.dumps(item),flush=True)


if __name__=='__main__': main()
