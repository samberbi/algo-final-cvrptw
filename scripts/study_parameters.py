"""Post-fixed sensitivity study: never change the frozen 1,000-run profile."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dataclasses import replace,asdict
import json,random,psutil
from algo.data import load,reference
from algo.solver import Settings,solve,warmup


def main():
    cpus=psutil.Process().cpu_affinity()
    if 10 in cpus:psutil.Process().cpu_affinity([10])
    out=ROOT/'results/sensitivity';out.mkdir(exist_ok=True)
    configs={'reference':{},'sans_adaptation':{'adaptive':False},'sans_recuit':{'annealing':False},
        'temperature_basse':{'temperature_ratio':.005},'temperature_haute':{'temperature_ratio':.05},
        'petits_retraits':{'max_removed':10}}
    names=['C105','C205','R105','R205','RC105','RC205']
    jobs=[(name,seed,method) for name in names for seed in [801,802] for method in configs]
    random.Random(20261109).shuffle(jobs)
    (out/'protocol.json').write_text(json.dumps(dict(names=names,seeds=[801,802],seconds=2.,
        configs=configs,scope='post-fixed sensitivity; no retrospective selection or change to campaign',
        cpu_affinity=psutil.Process().cpu_affinity()),indent=2))
    path=out/'runs.jsonl'
    done={(r['instance'],r['seed'],r['method']) for r in map(json.loads,path.read_text().splitlines())} if path.exists() else set()
    warmup()
    for name,seed,method in jobs:
        if (name,seed,method) in done:continue
        ins=load(ROOT/'data/instances'/(name+'.vrp'))
        cfg=replace(Settings(seconds=2.,seed=seed),**configs[method])
        result=solve(ins,cfg)
        _,bks=reference(ROOT/'data/instances'/(name+'.sol'))
        record=dict(instance=name,seed=seed,method=method,settings=asdict(cfg),result=result,
            gap_pct=100*(result['cost']/bks-1) if result['status']=='feasible' else None)
        with path.open('a') as f:f.write(json.dumps(record)+'\n')
        print(name,seed,method,result['status'],record['gap_pct'],flush=True)


if __name__=='__main__':main()
