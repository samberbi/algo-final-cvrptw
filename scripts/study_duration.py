# HISTORICAL ALNS experiment: never pool with results/revision_ils.
"""Paired continuations on held-aside business cases; no duration BKS claim."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import json,psutil
from algo.data import load
from algo.legacy_alns import solve,Settings,warmup
from algo.verify import verify
from algo.model import Objective
from metier.solver import solve as solve_business,Settings as BusinessSettings


def main():
    available=psutil.Process().cpu_affinity()
    if 8 in available:psutil.Process().cpu_affinity([8])
    out=ROOT/'results/duration';out.mkdir(exist_ok=True)
    warmup()
    names=['C105','C205','R105','R205','RC105','RC205']
    rows=[]
    for name in names:
        ins=load(ROOT/'data/instances'/(name+'.vrp'))
        initial=solve(ins,Settings(seconds=1.,seed=901))
        if initial['status']!='feasible':raise RuntimeError((name,'initial construction failed'))
        start=verify(initial['routes'],ins)
        for seed in [901,902,903]:
            for objective in [Objective.DISTANCE,Objective.DURATION]:
                cfg=BusinessSettings(objective=objective,time_limit=1.,iterations=100000)
                result=solve_business(ins,cfg,seed,initial['routes'])
                check=verify(result['routes'],ins);assert check['valid']
                row=dict(instance=name,seed=seed,objective=objective.value,shared_initial_duration=start['duration']/10,
                    shared_initial_distance=start['distance']/10,initial_search_s=initial['runtime_s'],
                    duration=check['duration']/10,distance=check['distance']/10,waiting=check['waiting']/10,
                    travel=check['travel']/10,service=(check['duration']-check['travel']-check['waiting'])/10,
                    continuation_s=result['runtime_s'],routes=result['routes'])
                rows.append(row)
                (out/'runs.json').write_text(json.dumps(rows))
        print(name,'paired business continuations complete',flush=True)
    (out/'protocol.json').write_text(json.dumps(dict(instances=names,seeds=[901,902,903],
        starting_solution_seconds=1.,continuation_seconds=1.,same_initial_routes=True,
        objective_comparison='distance versus duration with waiting and service; no BKS in duration',
        cpu_affinity=psutil.Process().cpu_affinity()),indent=2))


if __name__=='__main__':main()
