"""Separate exact validation, parameter sensitivity and one-factor scenarios."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):os.environ[key]='1'
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dataclasses import replace
import json,math,random,time
import numpy as np
import psutil
from algo.model import Instance
from algo.data import load
from algo.solver import solve,Settings,construct,warmup
from algo.verify import verify
from controle.plne import solve_plne
from web.experiments import atomic_json,read_json

OUT=ROOT/'results/revision_ils/studies'
NAMES=['C105','C205','R105','R205','RC105','RC205']


def synthetic(n,seed):
    rng=np.random.default_rng(seed);xy=np.vstack(([25.,25.],rng.uniform(0,50,(n,2))))
    d=np.floor(10*np.hypot(xy[:,0,None]-xy[None,:,0],xy[:,1,None]-xy[None,:,1]))
    q=np.r_[0,rng.integers(1,4,n)];service=np.r_[0,np.full(n,20.)]
    routes=[];route=[];loadq=0
    for i in range(1,n+1):
        if loadq+q[i]>12:routes.append(route);route=[];loadq=0
        route.append(i);loadq+=q[i]
    if route:routes.append(route)
    early=np.zeros(n+1);late=np.zeros(n+1);ends=[]
    for route in routes:
        t=0.;prev=0
        for i in route:
            arrival=t+d[prev,i];early[i]=max(0,arrival-rng.integers(0,80));late[i]=arrival+300
            t=max(arrival,early[i])+service[i];prev=i
        ends.append(t+d[prev,0])
    H=max(max(ends)+300,late.max());late[0]=H
    return Instance(f'small_{n}_{seed}',xy,q,service,early,late,d,12.,len(routes)+1,H)


def main():
    allowed=psutil.Process().cpu_affinity();psutil.Process().cpu_affinity([allowed[min(8,len(allowed)-1)]])
    OUT.mkdir(parents=True,exist_ok=True);warmup()
    # Protocol is written before the first measurement. All cases are reported.
    configs={'ils_base':{},'ils_small':{'perturbation_strength':1},'ils_large':{'perturbation_strength':8},
             'ils_strict':{'acceptance_tolerance':0.},'ils_without_local':{'local_search':False},
             'sa_cold':{'method':'sa','temperature_ratio':.005},'sa_base':{'method':'sa'},
             'sa_hot':{'method':'sa','temperature_ratio':.05}}
    scenarios=['original','capacity_80','capacity_120','windows_70','windows_130','fleet_80','fleet_120']
    protocol=dict(development_instances=NAMES,seeds=[801,802,803],seconds=2.,sensitivity=configs,
                  scenarios=scenarios,one_factor_at_a_time=True,modified_instances_have_no_BKS=True,
                  exact_sizes=[4,6,8,10,12],exact_seeds=[11,22],exact_limit_s=8.,
                  exact_heuristic_seeds=[301,302,303,304,305],exact_heuristic_seconds=.2,
                  scope='Post-main-protocol diagnostics; do not retroactively tune the main campaign',
                  cpu_affinity=psutil.Process().cpu_affinity())
    p=OUT/'protocol.json'
    if p.exists():assert read_json(p)==protocol
    else:atomic_json(p,protocol)
    for n in protocol['exact_sizes']:
        for seed in protocol['exact_seeds']:
            target=OUT/'exact'/f'{n}_{seed}.json'
            if target.exists():continue
            ins=synthetic(n,seed);exact=solve_plne(ins,8.);runs=[]
            for s in protocol['exact_heuristic_seeds']:
                initial,info=construct(ins,s,12)
                for method in ('ils','sa'):
                    result=solve(ins,Settings(seconds=.2,seed=s,method=method),initial)
                    runs.append(dict(method=method,seed=s,result=result,
                        optimal_gap=100*(result['cost']/exact['cost']-1) if exact['status']=='optimal' and exact['cost']>0 else None))
            atomic_json(target,dict(n=n,seed=seed,exact=exact,runs=runs))
            print('Exact',n,seed,exact['status'],flush=True)
    jobs=[(name,seed,label) for name in NAMES for seed in protocol['seeds'] for label in configs]
    random.Random(812).shuffle(jobs)
    cache={}
    for number,(name,seed,label) in enumerate(jobs):
        target=OUT/'sensitivity'/f'{name}_{seed}_{label}.json'
        if target.exists():continue
        ins=load(ROOT/'data/instances'/(name+'.vrp'))
        if (name,seed) not in cache:cache[name,seed]=construct(ins,seed,12)
        initial,info=cache[name,seed]
        cfg=replace(Settings(seconds=2.,seed=seed),**configs[label]);result=solve(ins,cfg,initial)
        atomic_json(target,dict(instance=name,seed=seed,variant=label,result=result,initial=info))
        if number%12==0:print('Sensitivity',number+1,'/',len(jobs),flush=True)
    jobs=[(name,seed,scenario) for name in NAMES for seed in protocol['seeds'] for scenario in scenarios]
    random.Random(813).shuffle(jobs)
    for number,(name,seed,scenario) in enumerate(jobs):
        target=OUT/'constraints'/f'{name}_{seed}_{scenario}.json'
        if target.exists():continue
        original=load(ROOT/'data/instances'/(name+'.vrp'));ins=original
        if scenario.startswith('capacity'):ins=replace(ins,capacity=ins.capacity*int(scenario.split('_')[1])/100)
        elif scenario.startswith('fleet'):ins=replace(ins,vehicles=max(1,math.ceil(ins.vehicles*int(scenario.split('_')[1])/100)))
        elif scenario.startswith('windows'):
            factor=int(scenario.split('_')[1])/100;mid=(ins.early+ins.late)/2;width=(ins.late-ins.early)*factor
            e=np.maximum(0,mid-width/2);l=np.minimum(ins.horizon,mid+width/2);e[0]=0;l[0]=ins.horizon
            ins=replace(ins,early=e,late=l)
        results={};start=time.perf_counter()
        if ins.proven_impossible():initial=None;info=dict(seconds=0.,reason=ins.proven_impossible())
        else:initial,info=construct(ins,seed,12)
        for method in ('ils','sa'):
            if initial is None:
                result=dict(status='proven_infeasible' if ins.proven_impossible() else 'not_found',reason=info.get('reason','construction failed'),routes=None,runtime_s=0.)
            else:result=solve(ins,Settings(seconds=2.,seed=seed,method=method),initial)
            results[method]=result
        atomic_json(target,dict(instance=name,seed=seed,scenario=scenario,modified=scenario!='original',
                               capacity=ins.capacity,fleet=ins.vehicles,initial=info,results=results))
        if number%12==0:print('Constraints',number+1,'/',len(jobs),flush=True)
    atomic_json(OUT/'complete.json',dict(complete=True,exact=10,sensitivity=len(configs)*6*3,constraints=7*6*3*2))
    print('Studies complete',flush=True)


if __name__=='__main__':main()
