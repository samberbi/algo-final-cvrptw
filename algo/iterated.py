"""ILS and direct-move SA for strict CVRPTW; reference-free search."""
from dataclasses import dataclass,asdict
import math,random,time
import numpy as np
from . import kernels as k
from .direct import walk
from .verify import verify


@dataclass(frozen=True)
class Settings:
    seconds:float=5.
    seed:int=0
    method:str='ils'
    temperature_ratio:float=.02
    perturbation_strength:int=4
    acceptance_tolerance:float=.005
    construction_attempts:int=12
    local_search:bool=True
    iterations:int=1000000000
    neighbor_count:int=24

    def __post_init__(self):
        if not math.isfinite(self.seconds) or self.seconds<=0:raise ValueError('Positive finite seconds required')
        if self.method not in ('ils','sa'):raise ValueError('Choose ils or sa')
        if min(self.perturbation_strength,self.construction_attempts,self.neighbor_count)<1 or self.iterations<0:raise ValueError('Invalid work limits')
        if not math.isfinite(self.temperature_ratio) or self.temperature_ratio<0:raise ValueError('Invalid temperature')
        if not math.isfinite(self.acceptance_tolerance) or not 0<=self.acceptance_tolerance<=.2:raise ValueError('Invalid tolerance')


def arrays(ins):
    return ins.travel,ins.distance,ins.demand,ins.service,ins.early,ins.late,ins.capacity,ins.horizon


def encode(routes,ins):
    a=np.zeros((min(ins.n,ins.vehicles)+1,ins.n+2),np.int64);l=np.zeros(len(a),np.int64)
    for i,r in enumerate(routes):a[i,:len(r)]=r;l[i]=len(r)
    return a,l


def decode(a,l):
    return [list(map(int,a[i,:n])) for i,n in enumerate(l) if n]


def construct(ins,seed=0,attempts=12):
    start=time.perf_counter();rng=random.Random(seed);best=math.inf;routes=None
    for attempt in range(attempts):
        a,l=encode([],ins)
        if k.repair_fast(a,l,len(l)-1,*arrays(ins),2,0. if attempt==0 else .2,rng.randrange(2**31)):
            count,cost=k.total(a,l,*arrays(ins))
            if count>=0 and cost<best:best=cost;routes=decode(a,l)
    return routes,dict(seconds=time.perf_counter()-start,attempts=attempts,cost=best/10 if routes is not None else None)


def solve(ins,settings=None,initial=None):
    cfg=settings or Settings();start=time.perf_counter();cpu_start=time.process_time();deadline=start+cfg.seconds
    result=dict(status='not_found',routes=None,method=cfg.method,objective='distance',seed=cfg.seed,settings=asdict(cfg),trace=[])
    impossible=ins.proven_impossible()
    if impossible:return dict(result,status='proven_infeasible',reason=impossible,runtime_s=time.perf_counter()-start)
    construction_s=0.
    if initial is None:
        initial,info=construct(ins,cfg.seed,cfg.construction_attempts);construction_s=info['seconds']
    if initial is None:return dict(result,reason='construction failed',runtime_s=time.perf_counter()-start)
    if not verify(initial,ins)['valid']:raise ValueError('Invalid initial solution')
    a,l=encode(initial,ins);args=arrays(ins);rng=random.Random(cfg.seed)
    current=k.total(a,l,*args)[1];initial_cost=current;ba,bl,best=a.copy(),l.copy(),current
    neighbors=np.argsort(ins.distance,axis=1)[:,1:min(ins.n+1,cfg.neighbor_count+1)].astype(np.int64)
    enabled=np.ones(4,np.bool_);accepted=valid=improved=proposals=cycles=0;operators=np.zeros(4,np.int64)
    t0=max(1e-9,cfg.temperature_ratio*max(initial_cost,1.));next_log=0.;last_improvement=0
    def log():
        elapsed=time.perf_counter()-start
        result['trace'].append(dict(iteration=proposals,cycle=cycles,elapsed_s=elapsed,best=best/10,current=current/10,
            temperature=t0*(.005**min(1.,elapsed/cfg.seconds))/10 if cfg.method=='sa' else None))
    log()
    while proposals<cfg.iterations and time.perf_counter()<deadline:
        cycles+=1
        if cfg.method=='sa':
            steps=min(256,cfg.iterations-proposals);temp=t0*(.005**min(1.,(time.perf_counter()-start)/cfg.seconds))
            current,wa,wl,value,nv,na,ni,ops,attempts=walk(a,l,len(l)-1,*args,neighbors,steps,rng.randrange(2**31),temp,1)
            proposals+=attempts;valid+=nv;accepted+=na;operators+=ops
        else:
            work,wl=a.copy(),l.copy()
            for _ in range(cfg.perturbation_strength):
                if proposals>=cfg.iterations or time.perf_counter()>=deadline:break
                steps=min(64,cfg.iterations-proposals)
                _,_,_,_,nv,na,_,ops,attempts=walk(work,wl,len(wl)-1,*args,neighbors,steps,rng.randrange(2**31),1.,0)
                proposals+=attempts;valid+=nv;operators+=ops
            if cfg.local_search and time.perf_counter()<deadline:
                k.local_search(work,wl,*args,neighbors,10,2,rng.randrange(2**31),enabled)
            value=k.total(work,wl,*args)[1];wa=work
            if value<=best*(1+cfg.acceptance_tolerance)+1e-8:a,l,current=work,wl,value;accepted+=1
        if value<best-1e-8:ba,bl,best=wa.copy(),wl.copy(),value;improved+=1;last_improvement=cycles
        if cfg.method=='ils' and cycles-last_improvement>=100:a,l,current=ba.copy(),bl.copy(),best;last_improvement=cycles
        elapsed=time.perf_counter()-start
        if elapsed>=next_log:log();next_log=elapsed+max(.025,cfg.seconds/100)
    routes=decode(ba,bl);checked=verify(routes,ins)
    if not checked['valid'] or abs(checked['distance']-best)>1e-6:raise AssertionError(checked)
    log()
    return dict(result,status='feasible',routes=routes,cost=best/10,initial_cost=initial_cost/10,vehicles=checked['vehicles'],metrics=checked,
        runtime_s=time.perf_counter()-start,cpu_s=time.process_time()-cpu_start,construction_s=construction_s,
        iterations=proposals,cycles=cycles,accepted=accepted,valid_proposals=valid,improved=improved,operators=operators.tolist())


def warmup():
    from .model import Instance
    xy=np.array([[0,0],[3,0],[6,0],[0,3]],float);d=np.floor(10*np.hypot(xy[:,0,None]-xy[None,:,0],xy[:,1,None]-xy[None,:,1]))
    ins=Instance('warmup',xy,np.array([0,1,1,1]),np.zeros(4),np.zeros(4),np.full(4,1000.),d,3.,3,1000.)
    start=time.perf_counter();initial,_=construct(ins,0,1)
    for method in ('ils','sa'):solve(ins,Settings(seconds=.01,method=method,iterations=20),initial)
    # Compile local search even if compilation consumed the short first call.
    a,l=encode(initial,ins);neighbors=np.argsort(d,axis=1)[:,1:].astype(np.int64)
    k.local_search(a,l,*arrays(ins),neighbors,2,2,0,np.ones(4,np.bool_))
    return time.perf_counter()-start
