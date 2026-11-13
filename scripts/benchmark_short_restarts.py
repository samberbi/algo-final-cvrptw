"""Reprises fraîches de 5/10 s HGS sur les cas les plus longs, sans écrasement."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS']:os.environ[name]='1'
from pathlib import Path
import hashlib,json,random,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import psutil
from algo.data import load,reference
from algo.duration_quick import solve
from algo.verify import verify
from scripts.benchmark_cpu_efficiency import warmup


def main():
    folder=ROOT/'results/time_objective/short_restarts'
    folder.mkdir(parents=True,exist_ok=True)
    pairs=[('C2_10_2',4101),('C2_10_2',4102),('C2_10_7',4101),('C2_10_7',4102)]
    jobs=[(name,seed,seconds) for name,seed in pairs for seconds in [5,10]]
    random.Random(20261113).shuffle(jobs)
    cpu=psutil.Process().cpu_affinity()[0];psutil.Process().cpu_affinity([cpu])
    protocol=dict(objective='sum_route_duration',departures=0,jobs=jobs,workers=1,cpu_affinity=[cpu],
        construction_limit_s=10,restarts=4,neighbors=80,external_hgs_seconds=[5,10],
        selection='Four previously observed slow instance-seed cases; exploratory tuning',
        time='Fresh full pipeline measured continuously, warmup and data loading excluded, final verification included')
    path=folder/'protocol.json'
    if path.exists():assert json.loads(path.read_text())==json.loads(json.dumps(protocol))
    else:path.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    for source in [*sorted((ROOT/'algo').glob('*.py')),Path(__file__)]:
        destination=folder/'source'/source.relative_to(ROOT);destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists():assert destination.read_bytes()==source.read_bytes()
        else:destination.write_bytes(source.read_bytes())
    warmup()
    for name,seed,seconds in jobs:
        path=folder/'runs'/f'{name}_{seed}_{seconds}s.json'
        if path.exists():continue
        try:
            ins=load(ROOT/'data/instances'/(name+'.vrp'))
            result=solve(ins,seed,hgs_seconds=seconds)
            checked=verify(result['routes'],ins);assert checked['valid']
            refs,_=reference(ROOT/'data/instances'/(name+'.sol'))
            ref=verify(refs,ins);assert ref['valid']
            record=dict(instance=name,seed=seed,hgs_seconds=seconds,valid=True,
                duration=checked['duration']/10,delta_reference_pct=100*(checked['duration']/ref['duration']-1),
                wall_s=result['runtime_s'],cpu_s=result['cpu_s'],result=result)
        except Exception:
            record=dict(instance=name,seed=seed,hgs_seconds=seconds,valid=False,error=traceback.format_exc())
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(record,indent=2),encoding='utf-8')
        print({k:v for k,v in record.items() if k!='result'},flush=True)


if __name__=='__main__':main()
