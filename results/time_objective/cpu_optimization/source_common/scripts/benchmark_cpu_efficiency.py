"""Mesures CPU avant/après à travail fixé, sans modifier l'historique."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):
    os.environ[key]='1'
from pathlib import Path
import argparse
import cProfile
import hashlib
import importlib.util
import io
import json
import pstats
import random
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import psutil
from algo.data import load,reference
from algo.duration_refine import solve as after_solve
from algo.iterated import arrays
from algo.savings import savings_construct
from algo.sequential import sequential_insert
from algo.verify import verify

FOLDER=ROOT/'results/time_objective/cpu_optimization'
CASES=['C103','C1_10_6','R1_10_5','RC2_10_5']
SEEDS=[8301,8302,8303]


def before_solver():
    path=FOLDER/'source_before/algo/duration_refine.py'
    spec=importlib.util.spec_from_file_location('algo._cpu_baseline',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.solve


def warmup():
    ins=load(ROOT/'data/instances/C101.vrp')
    savings_construct(*arrays(ins),ins.vehicles,0,0.)
    sequential_insert(*arrays(ins),ins.vehicles,0,1.,.5,0)
    after_solve(ins,0,seconds=60,restarts=1)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile-after',action='store_true')
    args=parser.parse_args()
    FOLDER.mkdir(parents=True,exist_ok=True)
    before=before_solver()
    cpu_id=psutil.Process().cpu_affinity()[0]
    psutil.Process().cpu_affinity([cpu_id])
    warmup()
    jobs=[(name,seed) for name in CASES for seed in SEEDS]
    random.Random(20261113).shuffle(jobs)
    protocol=dict(objective='sum_route_duration',departures=0,cases=CASES,seeds=SEEDS,
        methods=['before','cached_neighbors'],restarts=4,safety_wall_limit_s=60,
        work='Same four restarts, constructors, neighbourhoods and route pool; no time cutoff reached',
        cpu_measure='time.process_time: all threads of this single solver process',wall_measure='time.perf_counter',
        warmup_excluded=True,cpu_affinity=[cpu_id],jobs=jobs)
    path=FOLDER/'paired_protocol.json'
    if path.exists():assert json.loads(path.read_text())==json.loads(json.dumps(protocol))
    else:path.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    snapshot=FOLDER/'source_after/algo';snapshot.mkdir(parents=True,exist_ok=True)
    for name in ['duration_refine','route_pool']:
        source=ROOT/'algo'/(name+'.py');dest=snapshot/source.name
        if dest.exists():assert dest.read_bytes()==source.read_bytes()
        else:dest.write_bytes(source.read_bytes())
    for index,(name,seed) in enumerate(jobs):
        ins=load(ROOT/'data/instances'/(name+'.vrp'))
        order=['before','cached_neighbors'] if index%2==0 else ['cached_neighbors','before']
        for method in order:
            target=FOLDER/'paired'/f'{name}_{seed}_{method}.json'
            if target.exists():continue
            solve=before if method=='before' else after_solve
            wall=time.perf_counter();cpu=time.process_time()
            result=solve(ins,seed,seconds=60,restarts=4)
            elapsed=time.perf_counter()-wall;consumed=time.process_time()-cpu
            checked=verify(result['routes'],ins)
            assert checked['valid'] and elapsed<59,'Work was truncated; comparison invalid'
            refs,_=reference(ROOT/'data/instances'/(name+'.sol'))
            ref=verify(refs,ins);assert ref['valid']
            record=dict(instance=name,n=ins.n,seed=seed,method=method,valid=True,
                wall_s=elapsed,cpu_s=consumed,duration=checked['duration']/10,
                delta_reference_pct=100*(checked['duration']/ref['duration']-1),
                trace_entries=len(result['trace']),result=result)
            target.parent.mkdir(exist_ok=True)
            target.write_text(json.dumps(record,indent=2),encoding='utf-8')
            print({k:v for k,v in record.items() if k!='result'},flush=True)
    if args.profile_after:
        ins=load(ROOT/'data/instances/C1_10_6.vrp')
        profiler=cProfile.Profile();profiler.enable()
        result=after_solve(ins,4101,seconds=60,restarts=4)
        profiler.disable();profiler.dump_stats(str(FOLDER/'after.prof'))
        stream=io.StringIO()
        pstats.Stats(profiler,stream=stream).strip_dirs().sort_stats('cumtime').print_stats(35)
        (FOLDER/'PROFIL_APRES.txt').write_text(stream.getvalue(),encoding='utf-8')
        print(stream.getvalue(),flush=True)


if __name__=='__main__':main()
