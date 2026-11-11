"""Distance-only ALNS: regret repair, adaptive operators and annealing.

Fleet is an upper bound only. References are not imported or received.
All returned schedules are independently verified in original DIMACS units.
"""
from dataclasses import dataclass,asdict
import math,random,time
import numpy as np
from . import kernels as k
from .verify import verify


@dataclass(frozen=True)
class Settings:
    seconds:float=5.
    seed:int=0
    temperature_ratio:float=.02
    max_removed:int=40
    construction_attempts:int=12
    local_search:bool=True
    adaptive:bool=True
    annealing:bool=True
    iterations:int=1000000

    def __post_init__(self):
        if not math.isfinite(self.seconds) or self.seconds<=0:raise ValueError('Positive finite seconds required')
        if self.max_removed<1 or self.construction_attempts<1 or self.iterations<0:raise ValueError('Invalid work limits')
        if not math.isfinite(self.temperature_ratio) or self.temperature_ratio<0:raise ValueError('Invalid temperature')


def arrays(ins):
    return ins.travel,ins.distance,ins.demand,ins.service,ins.early,ins.late,ins.capacity,ins.horizon


def encode(routes,ins):
    a=np.zeros((min(ins.n,ins.vehicles)+1,ins.n+2),np.int64);lengths=np.zeros(len(a),np.int64)
    for i,route in enumerate(routes):a[i,:len(route)]=route;lengths[i]=len(route)
    return a,lengths


def decode(a,lengths):
    return [list(map(int,a[i,:n])) for i,n in enumerate(lengths) if n]


def solve(ins,settings=None,initial=None):
    cfg=settings or Settings();start=time.perf_counter();cpu_start=time.process_time();deadline=start+cfg.seconds
    rng=random.Random(cfg.seed);args=arrays(ins)
    result=dict(status='not_found',routes=None,objective='distance',seed=cfg.seed,settings=asdict(cfg),trace=[])
    if ins.proven_impossible():
        return dict(result,status='proven_infeasible',reason=ins.proven_impossible(),runtime_s=time.perf_counter()-start,cpu_s=time.process_time()-cpu_start)
    if initial is not None and not verify(initial,ins)['valid']:raise ValueError('Invalid initial solution')
    best_cost=math.inf;ba=bl=None
    attempts=0
    for attempt in range(1 if initial is not None else cfg.construction_attempts):
        if attempt and time.perf_counter()>start+cfg.seconds*.25:break
        a,l=encode(initial or [],ins);attempts+=1
        success=True if initial is not None else k.repair_fast(a,l,len(l)-1,*args,2,0. if attempt==0 else .2,rng.randrange(2**31))
        count,cost=k.total(a,l,*args) if success else (-1,math.inf)
        if count>=0 and cost<best_cost:best_cost=cost;ba,bl=a.copy(),l.copy()
    if ba is None:
        return dict(result,reason='construction failed',runtime_s=time.perf_counter()-start,cpu_s=time.process_time()-cpu_start)
    initial_cost=best_cost;construction_s=time.perf_counter()-start
    a,l=ba.copy(),bl.copy();current=best_cost
    neighbors=np.argsort(ins.distance,axis=1)[:,1:min(ins.n+1,25)].astype(np.int64)
    enabled=np.ones(4,np.bool_)
    def local(work,wl,moves=10):
        if not cfg.local_search or time.perf_counter()>=deadline:return work,wl
        candidate,cl=work.copy(),wl.copy()
        k.local_search(candidate,cl,*args,neighbors,moves,2,rng.randrange(2**31),enabled)
        before=k.total(work,wl,*args);after=k.total(candidate,cl,*args)
        if after[0]>=0 and after[1]<before[1]-1e-8:return candidate,cl
        return work,wl
    a,l=local(a,l,50);current=k.total(a,l,*args)[1]
    if current<best_cost:ba,bl,best_cost=a.copy(),l.copy(),current
    weights=np.ones(6);selected=np.zeros(6,np.int64);accepted=improved=failed=0
    t0=max(1e-9,cfg.temperature_ratio*max(initial_cost,1.));last=0
    result['trace'].append(dict(iteration=0,elapsed_s=time.perf_counter()-start,best=best_cost/10,current=current/10,temperature=t0/10))
    iteration=-1;completed=0;temperature=t0
    for iteration in range(cfg.iterations):
        if time.perf_counter()>=deadline:break
        completed+=1
        progress=min(1.,(time.perf_counter()-start)/cfg.seconds)
        temperature=t0*(.005**progress)
        op=rng.choices(range(6),weights=weights if cfg.adaptive else None,k=1)[0]
        selected[op]+=1;work,wl=a.copy(),l.copy()
        if rng.random()<.12:
            nonempty=[i for i,n in enumerate(wl[:-1]) if n]
            wl[rng.choice(nonempty)]=0
        else:
            count=rng.randint(1,min(ins.n,cfg.max_removed,max(2,int(.35*ins.n))))
            k.destroy_fast(work,wl,*args[:6],ins.horizon,ins.capacity,count/max(1,ins.n),op,rng.randrange(2**31))
        good=k.repair_fast(work,wl,len(wl)-1,*args,rng.choice((2,3)),.2 if rng.random()<.3 else 0.,rng.randrange(2**31))
        reward=.05
        if good:
            if iteration%5==0:work,wl=local(work,wl)
            vehicles,value=k.total(work,wl,*args)
            if vehicles<0:raise AssertionError('Repair returned invalid routes')
            delta=value-current
            take=delta<=0 or (cfg.annealing and rng.random()<math.exp(-min(745.,delta/max(temperature,1e-12))))
            if take:
                reward=1. if value<current-1e-8 else .2;a,l,current=work,wl,value;accepted+=1
            if value<best_cost-1e-8:
                ba,bl,best_cost=work.copy(),wl.copy(),value;reward=5.;improved+=1;last=iteration
        else:failed+=1
        if cfg.adaptive:weights[op]=.9*weights[op]+.1*reward
        if iteration-last>=200:
            a,l,current=ba.copy(),bl.copy(),best_cost;last=iteration
        if iteration%50==0:
            result['trace'].append(dict(iteration=iteration+1,elapsed_s=time.perf_counter()-start,best=best_cost/10,current=current/10,temperature=temperature/10))
    routes=decode(ba,bl);checked=verify(routes,ins)
    if not checked['valid'] or abs(checked['distance']-best_cost)>1e-6:raise AssertionError(checked)
    result['trace'].append(dict(iteration=completed,elapsed_s=time.perf_counter()-start,best=best_cost/10,current=current/10,temperature=temperature/10))
    return dict(result,status='feasible',routes=routes,cost=best_cost/10,initial_cost=initial_cost/10,
        vehicles=checked['vehicles'],metrics=checked,runtime_s=time.perf_counter()-start,cpu_s=time.process_time()-cpu_start,
        construction_s=construction_s,construction_attempts=attempts,iterations=completed,
        accepted=accepted,improved=improved,failed_repairs=failed,
        operators=[dict(id=i,selected=int(selected[i]),weight=float(weights[i])) for i in range(6)])


def warmup():
    from .model import Instance
    xy=np.array([[0,0],[3,0],[6,0],[0,3]],float)
    distance=np.floor(10*np.hypot(xy[:,0,None]-xy[None,:,0],xy[:,1,None]-xy[None,:,1]))
    ins=Instance('warmup',xy,np.array([0,1,1,1]),np.zeros(4),np.zeros(4),np.full(4,1000.),distance,3.,3,1000.)
    start=time.perf_counter();args=arrays(ins)
    a,l=encode([[1],[2],[3]],ins)
    k.repair_fast(a,l,len(l)-1,*args,2,0.,1)
    k.destroy_fast(a,l,*args[:6],ins.horizon,ins.capacity,.3,0,1)
    k.repair_fast(a,l,len(l)-1,*args,3,.2,1)
    neighbors=np.argsort(ins.distance,axis=1)[:,1:].astype(np.int64)
    k.local_search(a,l,*args,neighbors,5,2,1,np.ones(4,np.bool_))
    k.total(a,l,*args)
    return time.perf_counter()-start
