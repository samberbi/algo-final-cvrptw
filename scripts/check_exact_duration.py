"""Petits cas en durée : comparer le PLNE à une énumération indépendante."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from algo.model import Instance,Objective
from controle.plne import solve_plne
from controle.exact import exact

if __name__=='__main__':
    folder=ROOT/'results/time_objective/exact';folder.mkdir(parents=True,exist_ok=True)
    rows=[]
    for seed in range(10):
        rng=np.random.default_rng(5100+seed);n=3+seed%3
        xy=rng.uniform(0,25,(n+1,2));d=np.floor(10*np.sqrt(((xy[:,None,:]-xy[None,:,:])**2).sum(axis=2)))
        if seed==9:d[:]=0
        demand=np.r_[0,rng.integers(1,4,n)];service=np.r_[0,rng.integers(1,5,n)*10]
        early=np.r_[0,rng.integers(0,35,n)*10];late=np.full(n+1,2500.)
        ins=Instance(f'exact-duration-{seed}',xy,demand,service,early,late,d,
                     float(np.ceil(demand.sum()/2)+1),2,2500.)
        oracle=exact(ins,Objective.DURATION,max_clients=6)
        solved=solve_plne(ins,10,objective='duration')
        assert oracle['status']==solved['status']=='optimal'
        assert abs(oracle['score']/10-solved['cost'])<1e-6
        record=dict(instance=ins.name,n=n,optimum=oracle['score']/10,solver=solved,
                    data={name:getattr(ins,name).tolist() for name in ['xy','demand','service','early','late','travel']},
                    capacity=ins.capacity,vehicles=ins.vehicles,horizon=ins.horizon)
        (folder/(ins.name+'.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
        rows.append(dict(instance=ins.name,n=n,optimum=oracle['score']/10,returned=solved['cost'],
                         gap_pct=100*(solved['cost']/(oracle['score']/10)-1),calculation_s=solved['runtime_s']))
    import pandas as pd
    pd.DataFrame(rows).to_csv(folder/'summary.csv',index=False)
    print(pd.DataFrame(rows).to_string(index=False))
