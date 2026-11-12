"""Combine only three cold-start trajectories with the same instance and seed."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import psutil
import pandas as pd
from algo.data import load
from algo.route_pool import RoutePool
from web.experiments import read_json,atomic_json


def main():
    psutil.Process().cpu_affinity([psutil.Process().cpu_affinity()[0]])
    base=ROOT/'results/optimization_v6'
    protocol=read_json(base/'validation/protocol.json')
    refs={r['instance']:r['reference_distance'] for r in read_json(ROOT/'data/manifest.json')['reference_instances']}
    out=base/'cold_portfolio'
    atomic_json(out/'protocol.json',dict(instances=protocol['instances'],seeds=protocol['seeds'],
        generation='One baseline, one combined and one cache-only trajectory per seed, no other seed or historical solution',
        accounting='All three actual search and construction times charged; add actual partitioning time',
        mip_seconds=2,sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'algo/route_pool.py']}))
    rows=[]
    for name in protocol['instances']:
        ins=load(ROOT/'data/instances'/(name+'.vrp'))
        for seed in protocol['seeds']:
            path=out/f'{name}_{seed}.json'
            if path.exists():rows.append(read_json(path));continue
            pool=RoutePool(ins);effort=0.;sources={}
            for folder,variant in [('validation','baseline'),('validation','combined'),('cache_followup','cache')]:
                source=base/folder/'runs'/f'{name}_{seed}_{variant}.json'
                r=read_json(source);assert r['valid']
                pool.add_solution(r['result']['routes'])
                effort+=r['total_s']
                sources[str(source.relative_to(ROOT))]=hashlib.sha256(source.read_bytes()).hexdigest()
            before=pool.best_cost/10
            result=pool.recombine(2.)
            row=dict(instance=name,seed=seed,best_input_gap=100*(before/refs[name]-1),
                     gap_pct=100*(result['cost']/refs[name]-1),result=result,
                     generation_effort_s=effort,total_effort_s=effort+result['runtime_s'],sources_sha256=sources)
            atomic_json(path,row);rows.append(row)
    frame=pd.DataFrame([{k:r[k] for k in ['instance','seed','best_input_gap','gap_pct','total_effort_s']} for r in rows])
    frame.to_csv(out/'flat.csv',index=False)
    atomic_json(out/'analysis.json',dict(portfolios=len(rows),instances=len(protocol['instances']),seeds=protocol['seeds'],
        mean_best_input_gap=float(frame.best_input_gap.mean()),mean_gap=float(frame.gap_pct.mean()),
        worst_gap=float(frame.gap_pct.max()),mean_effort_s=float(frame.total_effort_s.mean()),
        scope='Three previously measured cold-start trajectories per portfolio, fully charged; no 120-second baseline comparison executed'))
    print(read_json(out/'analysis.json'))


if __name__=='__main__':main()
