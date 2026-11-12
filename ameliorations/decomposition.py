"""Distance-only search in groups of incumbent routes, original data preserved."""
import time,random
import numpy as np
from algo.model import Instance
from algo.solver import solve,Settings
from algo.verify import verify


def polish(ins,initial,seconds=5.,seed=2026):
    checked=verify(initial,ins)
    if not checked['valid']:raise ValueError('Invalid initial tours')
    if seconds<=0:raise ValueError('Positive time budget required')
    start=time.perf_counter();deadline=start+seconds;rng=random.Random(seed)
    routes=[list(r) for r in initial];best=checked['distance'];initial_cost=best
    attempts=improvements=0;trace=[]
    while routes and time.perf_counter()<deadline:
        centers=np.array([ins.xy[r].mean(axis=0) for r in routes])
        pivot=rng.randrange(len(routes));order=np.argsort(np.linalg.norm(centers-centers[pivot],axis=1))
        group=[];count=0
        for i in order:
            if group and count+len(routes[i])>120:continue
            group.append(int(i));count+=len(routes[i])
            if len(group)>=12:break
        mapping=[0]+[c for i in group for c in routes[i]];inverse={c:i for i,c in enumerate(mapping)}
        ids=np.array(mapping);remaining_fleet=ins.vehicles-(len(routes)-len(group))
        fleet_limit=min(remaining_fleet,len(group)+3,len(ids)-1)
        sub=Instance('induced_routes',ins.xy[ids],ins.demand[ids],ins.service[ids],ins.early[ids],ins.late[ids],
            ins.travel[np.ix_(ids,ids)],ins.capacity,fleet_limit,ins.horizon,ins.distance[np.ix_(ids,ids)])
        local=[[inverse[c] for c in routes[i]] for i in group]
        remaining=deadline-time.perf_counter()
        if remaining<=0:break
        result=solve(sub,Settings(seconds=min(.2,remaining),seed=rng.randrange(2**31)),local)
        attempts+=1
        if result['status']!='feasible':continue
        proposal=[r for i,r in enumerate(routes) if i not in group]+[[mapping[c] for c in r] for r in result['routes']]
        v=verify(proposal,ins)
        if not v['valid']:raise AssertionError(v['errors'])
        if v['distance']<best-1e-8:
            routes=proposal;best=v['distance'];improvements+=1
            trace.append(dict(elapsed_s=time.perf_counter()-start,best=best/10))
    v=verify(routes,ins);assert v['valid'] and best<=initial_cost+1e-8
    return dict(status='feasible',routes=routes,cost=best/10,vehicles=v['vehicles'],
        initial_cost=initial_cost/10,runtime_s=time.perf_counter()-start,
        attempts=attempts,improvements=improvements,trace=trace)
