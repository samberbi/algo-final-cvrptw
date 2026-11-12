"""Parallel Clarke-Wright savings: an additional initial constructor only."""
import numpy as np
from numba import njit
from .kernels import route_eval,compact


@njit(cache=True)
def savings_construct(travel,distance,demand,service,early,late,capacity,horizon,
                      fleet,seed,noise=0.):
    np.random.seed(seed)
    n=len(demand)-1
    routes=np.zeros((n+1,n+2),np.int64)
    lengths=np.zeros(n+1,np.int64)
    owner=np.arange(n+1,dtype=np.int64)-1
    loads=np.zeros(n+1)
    for client in range(1,n+1):
        routes[client-1,0]=client;lengths[client-1]=1;loads[client-1]=demand[client]
    count=n*(n-1)//2
    first=np.empty(count,np.int64);second=np.empty(count,np.int64);values=np.empty(count)
    at=0
    for i in range(1,n+1):
        for j in range(i+1,n+1):
            first[at]=i;second[at]=j
            values[at]=(distance[0,i]+distance[0,j]-distance[i,j])*(1+noise*(np.random.random()-.5))
            at+=1
    order=np.argsort(values)
    candidate=np.empty(n+2,np.int64);reverse=np.empty(n+2,np.int64)
    for index in range(count-1,-1,-1):
        pair=order[index];i=first[pair];j=second[pair]
        a=owner[i];b=owner[j]
        if a==b or loads[a]+loads[b]>capacity+1e-8:continue
        la=lengths[a];lb=lengths[b]
        if i!=routes[a,0] and i!=routes[a,la-1]:continue
        if j!=routes[b,0] and j!=routes[b,lb-1]:continue
        if distance[0,i]+distance[0,j]-distance[i,j]<=1e-9:continue
        for p in range(la):candidate[p]=routes[a,p] if routes[a,la-1]==i else routes[a,la-1-p]
        for p in range(lb):candidate[la+p]=routes[b,p] if routes[b,0]==j else routes[b,lb-1-p]
        length=la+lb
        feasible,_,_=route_eval(candidate,length,travel,distance,demand,service,early,late,capacity,horizon)
        if not feasible:
            for p in range(length):reverse[p]=candidate[length-1-p]
            feasible,_,_=route_eval(reverse,length,travel,distance,demand,service,early,late,capacity,horizon)
            if not feasible:continue
            candidate[:length]=reverse[:length]
        routes[a,:length]=candidate[:length];lengths[a]=length;lengths[b]=0;loads[a]+=loads[b];loads[b]=0
        for p in range(length):owner[routes[a,p]]=a
    used=compact(routes,lengths)
    if used>fleet:return routes,lengths,False
    for r in range(used):
        feasible,_,_=route_eval(routes[r],lengths[r],travel,distance,demand,service,early,late,capacity,horizon)
        if not feasible:return routes,lengths,False
    return routes,lengths,True
