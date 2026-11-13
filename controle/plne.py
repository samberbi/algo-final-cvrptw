"""Actual CVRPTW mixed-integer model solved by SciPy/HiGHS, for small cases.

Same assignment, arc, time and artificial-flow constraints as the report.
An incumbent is not called optimal unless HiGHS proves optimality.
"""
import math
import time
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix
from algo.verify import verify


def solve_plne(ins,seconds=10.,objective='duration'):
    if objective not in ('distance','duration'):raise ValueError('Choose distance or duration')
    if not math.isfinite(seconds) or seconds<=0:raise ValueError('Positive time limit required')
    if ins.n>30:raise ValueError('The explicit PLNE is reserved for at most 30 clients')
    started=time.perf_counter();n=ins.n;K=min(ins.vehicles,n);o=0;r=n+1
    C=list(range(1,n+1));vehicles=range(K)
    A=[(o,j) for j in C]+[(i,j) for i in C for j in C if i!=j]+[(i,r) for i in C]
    metric=objective
    index={};lower=[];upper=[];integrality=[];objective=[]
    def variable(key,lo=0.,hi=math.inf,integer=0,cost=0.):
        index[key]=len(lower);lower.append(lo);upper.append(hi);integrality.append(integer);objective.append(cost)
    for k in vehicles:
        variable(('u',k),hi=1,integer=1)
        variable(('R',k),hi=ins.horizon,cost=int(metric=='duration'))
        for i in C:variable(('y',i,k),hi=1,integer=1)
        for i,j in A:
            variable(('x',i,j,k),hi=1,integer=1,cost=float(ins.distance[i,0 if j==r else j]) if metric=='distance' else 0.)
            variable(('f',i,j,k),hi=0 if j==r else n)
    for i in C:variable(('t',i),lo=float(ins.early[i]),hi=float(ins.late[i]))
    if not n:return dict(status='optimal',routes=[],cost=0.,lower_bound=0.,runtime_s=time.perf_counter()-started)
    rows=[];cols=[];values=[];lo=[];hi=[]
    def constraint(terms,l=-math.inf,h=math.inf):
        row=len(lo)
        for key,value in terms:
            rows.append(row);cols.append(index[key]);values.append(float(value))
        lo.append(l);hi.append(h)
    M=float(ins.horizon+ins.service.max()+ins.travel.max())
    for i in C:
        constraint([(('y',i,k),1) for k in vehicles],1,1)
    for k in vehicles:
        for i in C:
            constraint([(('x',a,b,k),1) for a,b in A if a==i]+[(('y',i,k),-1)],0,0)
            constraint([(('x',a,b,k),1) for a,b in A if b==i]+[(('y',i,k),-1)],0,0)
        constraint([(('x',0,j,k),1) for j in C]+[(('u',k),-1)],0,0)
        constraint([(('x',i,r,k),1) for i in C]+[(('u',k),-1)],0,0)
        constraint([(('y',i,k),ins.demand[i]) for i in C]+[(('u',k),-ins.capacity)],h=0)
        constraint([(('R',k),1),(('u',k),-ins.horizon)],h=0)
        for j in C:
            constraint([(('t',j),1),(('x',0,j,k),-M)],l=float(ins.travel[0,j])-M)
        for i in C:
            for j in C:
                if i!=j:constraint([(('t',j),1),(('t',i),-1),(('x',i,j,k),-M)],l=float(ins.service[i]+ins.travel[i,j])-M)
            ret=float(ins.service[i]+ins.travel[i,0])
            constraint([(('R',k),1),(('t',i),-1),(('x',i,r,k),-M)],l=ret-M)
            # En durée, minimiser la somme des R rend cette borne supérieure
            # redondante à l'optimum. La borne inférieure et R <= H*u restent.
            # Le mode historique distance garde l'égalité explicite du retour.
            if metric == 'distance':
                constraint([(('R',k),1),(('t',i),-1),(('x',i,r,k),M)],h=ret+M)
            constraint([(('f',a,b,k),1) for a,b in A if b==i]+
                       [(('f',a,b,k),-1) for a,b in A if a==i]+[(('y',i,k),-1)],0,0)
        constraint([(('f',0,j,k),1) for j in C]+[(('y',i,k),-1) for i in C],0,0)
        for i,j in A:constraint([(('f',i,j,k),1),(('x',i,j,k),-n)],h=0)
    matrix=coo_matrix((values,(rows,cols)),shape=(len(lo),len(index))).tocsc()
    result=milp(np.array(objective),integrality=np.array(integrality),bounds=Bounds(lower,upper),
                constraints=LinearConstraint(matrix,lo,hi),options={'time_limit':seconds,'mip_rel_gap':0.})
    record=dict(status={0:'optimal',1:'time_limit',2:'proven_infeasible',3:'unbounded',4:'error'}.get(result.status,'error'),
                solver_status=int(result.status),message=result.message,runtime_s=time.perf_counter()-started,
                variables=len(index),constraints=len(lo),routes=None,cost=None,
                lower_bound=float(result.mip_dual_bound)/10 if getattr(result,'mip_dual_bound',None) is not None else None,
                mip_gap=float(result.mip_gap) if getattr(result,'mip_gap',None) is not None else None)
    if result.x is not None:
        routes=[]
        for k in vehicles:
            if result.x[index['u',k]]<.5:continue
            current=o;route=[]
            for _ in range(n+1):
                nxt=[j for i,j in A if i==current and result.x[index['x',i,j,k]]>.5]
                if len(nxt)!=1:raise AssertionError('Invalid exact arc solution')
                if nxt[0]==r:break
                route.append(nxt[0]);current=nxt[0]
            routes.append(route)
        checked=verify(routes,ins)
        if not checked['valid']:raise AssertionError(checked)
        record.update(routes=routes,cost=checked[metric]/10,metrics=checked,objective=metric)
        assert abs(record['cost']-result.fun/10)<1e-5
    return record
