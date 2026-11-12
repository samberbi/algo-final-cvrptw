"""Compiled distance-only kernels, adapted from our existing implementation.
No vehicle penalty; fleet remains an upper bound. No external solver.
"""
import numpy as np
from numba import njit
TOL=1e-8

@njit(cache=True)
def route_eval(seq,length,travel,distance,demand,service,early,late,capacity,horizon):
    t=0.;cost=0.;load=0.;prev=0
    for p in range(length):
        i=seq[p];load+=demand[i]
        t=max(t+travel[prev,i],early[i])
        if t>late[i]+TOL or load>capacity+TOL:
            return False,0.,load
        t+=service[i];cost+=distance[prev,i];prev=i
    if length:
        t+=travel[prev,0];cost+=distance[prev,0]
    return t<=horizon+TOL,cost,load

@njit(cache=True)
def refresh(routes,lens,r,travel,distance,demand,service,early,late,capacity,horizon,depart,latest):
    L=lens[r];t=0.;prev=0;load=0.;cost=0.
    depart[r,0]=0.
    for p in range(L):
        i=routes[r,p];load+=demand[i]
        t=max(t+travel[prev,i],early[i])
        if t>late[i]+TOL or load>capacity+TOL:return False,0.,load
        t+=service[i];depart[r,p+1]=t;cost+=distance[prev,i];prev=i
    if L:
        t+=travel[prev,0];cost+=distance[prev,0]
    latest[r,L]=horizon;next_node=0;next_start=horizon
    for p in range(L-1,-1,-1):
        i=routes[r,p]
        latest[r,p]=min(late[i],next_start-service[i]-travel[i,next_node])
        next_node=i;next_start=latest[r,p]
    return t<=horizon+TOL,cost,load

@njit(cache=True)
def best_insert(routes,lens,r,c,travel,distance,demand,service,early,late,capacity,horizon,depart,latest,load,noise):
    if load+demand[c]>capacity+TOL:return 1e100,-1
    L=lens[r];best=1e100;position=-1;true_delta=1e100
    for p in range(L+1):
        prev=routes[r,p-1] if p else 0
        nxt=routes[r,p] if p<L else 0
        begin=max(depart[r,p]+travel[prev,c],early[c])
        if begin>late[c]+TOL:continue
        if begin+service[c]+travel[c,nxt]>latest[r,p]+TOL:continue
        delta=distance[prev,c]+distance[c,nxt]-distance[prev,nxt]
        ranking=delta*(1+noise*(2*np.random.random()-1)) if noise>0 else delta
        if ranking<best:
            best=ranking;position=p;true_delta=delta
    return true_delta,position

@njit(cache=True)
def insert_at(routes,lens,r,client,p):
    L=lens[r]
    for j in range(L,p,-1):routes[r,j]=routes[r,j-1]
    routes[r,p]=client;lens[r]+=1

@njit(cache=True)
def compact(routes,lens):
    at=0
    for r in range(len(lens)):
        if lens[r]:
            if r!=at:
                routes[at,:lens[r]]=routes[r,:lens[r]]
                lens[at]=lens[r]
            at+=1
    for r in range(at,len(lens)):lens[r]=0
    return at

@njit(cache=True)
def total(routes,lens,travel,distance,demand,service,early,late,capacity,horizon):
    count=0;cost=0.
    for r in range(len(lens)):
        if lens[r]:
            valid,d,_=route_eval(routes[r],lens[r],travel,distance,demand,service,early,late,capacity,horizon)
            if not valid:return -1,1e100
            count+=1;cost+=d
    return count,cost

@njit(cache=True)
def repair_fast(routes,lens,limit,travel,distance,demand,service,early,late,capacity,horizon,regret,noise,seed):
    np.random.seed(seed)
    n=len(demand)-1;rows=len(lens)
    pending=np.ones(n+1,np.bool_);pending[0]=False
    depart=np.zeros((rows,n+2));latest=np.zeros((rows,n+2));loads=np.zeros(rows)
    costs=np.full((n+1,rows),1e100);positions=np.full((n+1,rows),-1,np.int64)
    for r in range(rows):
        valid,_,load=refresh(routes,lens,r,travel,distance,demand,service,early,late,capacity,horizon,depart,latest)
        if not valid or r>=limit:
            lens[r]=0
            refresh(routes,lens,r,travel,distance,demand,service,early,late,capacity,horizon,depart,latest)
            loads[r]=0.
        else:
            loads[r]=load
            for p in range(lens[r]):pending[routes[r,p]]=False
    W=0.  # Distance only: opening a legal vehicle has no fixed penalty.
    for c in range(1,n+1):
        if pending[c]:
            for r in range(limit):
                costs[c,r],positions[c,r]=best_insert(routes,lens,r,c,travel,distance,demand,service,early,late,capacity,horizon,depart,latest,loads[r],noise)
    left=0
    for c in range(1,n+1):left+=int(pending[c])
    while left:
        first_empty=-1
        for r in range(limit):
            if lens[r]==0:first_empty=r;break
        chosen=-1;chosen_r=-1;chosen_p=-1;priority=-1;best_regret=-1e100;best_greedy=1e100
        for c in range(1,n+1):
            if not pending[c]:continue
            values=np.full(3,1e100);route_best=-1;pos_best=-1;alternatives=0
            for r in range(limit):
                if lens[r]==0 and r!=first_empty:continue
                if positions[c,r]<0:continue
                alternatives+=1
                val=costs[c,r]+(W if lens[r]==0 else 0.)
                if val<values[0]:
                    values[2]=values[1];values[1]=values[0];values[0]=val
                    route_best=r;pos_best=positions[c,r]
                elif val<values[1]:values[2]=values[1];values[1]=val
                elif val<values[2]:values[2]=val
            if alternatives==0:continue
            if regret==1:
                value=values[0]*(1+noise*(np.random.random()-.5))
                if value<best_greedy:
                    best_greedy=value;chosen=c;chosen_r=route_best;chosen_p=pos_best
            else:
                scarcity=max(0,regret-alternatives)
                gap=0.
                for j in range(1,min(regret,alternatives)):gap+=values[j]-values[0]
                gap*=1+noise*(np.random.random()-.5)
                if scarcity>priority or (scarcity==priority and gap>best_regret):
                    priority=scarcity;best_regret=gap;chosen=c;chosen_r=route_best;chosen_p=pos_best
        if chosen<0:return False
        insert_at(routes,lens,chosen_r,chosen,chosen_p)
        valid,_,loads[chosen_r]=refresh(routes,lens,chosen_r,travel,distance,demand,service,early,late,capacity,horizon,depart,latest)
        if not valid:return False
        pending[chosen]=False;left-=1
        for c in range(1,n+1):
            if pending[c]:
                costs[c,chosen_r],positions[c,chosen_r]=best_insert(routes,lens,chosen_r,c,travel,distance,demand,service,early,late,capacity,horizon,depart,latest,loads[chosen_r],noise)
    compact(routes,lens)
    return True

@njit(cache=True)
def local_search(routes,lens,travel,distance,demand,service,early,late,capacity,horizon,neighbors,max_moves,chains,seed,enabled):
    np.random.seed(seed)
    n=len(demand)-1;changes=0;tested=0
    old=np.zeros(len(lens));load=np.zeros(len(lens))
    owner=np.full(n+1,-1,np.int64);where=np.zeros(n+1,np.int64)
    tmp=np.empty(n+2,np.int64);tmp2=np.empty(n+2,np.int64)
    for iteration in range(max_moves):
        for r in range(len(lens)):
            valid,old[r],load[r]=route_eval(routes[r],lens[r],travel,distance,demand,service,early,late,capacity,horizon)
            for p in range(lens[r]):owner[routes[r,p]]=r;where[routes[r,p]]=p
        changed=False
        offset=np.random.randint(max(1,n))
        for ii in range(n):
            i=1+(ii+offset)%n;a=owner[i]
            if a<0:continue
            p=where[i];La=lens[a]
            for nn in range(neighbors.shape[1]):
                j=neighbors[i,nn]
                if j==0 or j==i:continue
                b=owner[j]
                if b<0:continue
                q=where[j];Lb=lens[b]
                # Relocate (and optional chains) into a different route.
                if enabled[0] and a!=b:
                    for size in range(1,chains+1):
                        if p+size>La:break
                        chainload=0.
                        for z in range(size):chainload+=demand[routes[a,p+z]]
                        if load[b]+chainload>capacity+TOL:continue
                        pre=routes[a,p-1] if p else 0;end=routes[a,p+size] if p+size<La else 0
                        gain=distance[pre,end]-distance[pre,i]-distance[routes[a,p+size-1],end]
                        for pos in range(q,min(Lb,q+1)+1):
                            prev=routes[b,pos-1] if pos else 0;nxt=routes[b,pos] if pos<Lb else 0
                            delta=gain+distance[prev,i]+distance[routes[a,p+size-1],nxt]-distance[prev,nxt]
                            eliminate=False  # No lexicographic fleet priority.
                            if not eliminate and delta>=-1e-9:continue
                            z=0
                            for k in range(La):
                                if k<p or k>=p+size:tmp[z]=routes[a,k];z+=1
                            for k in range(pos):tmp2[k]=routes[b,k]
                            for k in range(size):tmp2[pos+k]=routes[a,p+k]
                            for k in range(pos,Lb):tmp2[k+size]=routes[b,k]
                            tested+=1
                            va,_,_=route_eval(tmp,La-size,travel,distance,demand,service,early,late,capacity,horizon)
                            vb,_,_=route_eval(tmp2,Lb+size,travel,distance,demand,service,early,late,capacity,horizon)
                            if va and vb:
                                routes[a,:La-size]=tmp[:La-size];lens[a]=La-size
                                routes[b,:Lb+size]=tmp2[:Lb+size];lens[b]=Lb+size
                                changed=True;break
                        if changed:break
                if changed:break
                # Swap between distinct routes.
                if enabled[1] and a!=b and load[a]-demand[i]+demand[j]<=capacity+TOL and load[b]-demand[j]+demand[i]<=capacity+TOL:
                    prev=routes[a,p-1] if p else 0;nxt=routes[a,p+1] if p+1<La else 0
                    prev2=routes[b,q-1] if q else 0;nxt2=routes[b,q+1] if q+1<Lb else 0
                    delta=distance[prev,j]+distance[j,nxt]-distance[prev,i]-distance[i,nxt]+distance[prev2,i]+distance[i,nxt2]-distance[prev2,j]-distance[j,nxt2]
                    if delta<-1e-9:
                        tmp[:La]=routes[a,:La];tmp2[:Lb]=routes[b,:Lb];tmp[p]=j;tmp2[q]=i
                        tested+=1
                        va,_,_=route_eval(tmp,La,travel,distance,demand,service,early,late,capacity,horizon)
                        vb,_,_=route_eval(tmp2,Lb,travel,distance,demand,service,early,late,capacity,horizon)
                        if va and vb:
                            routes[a,p]=j;routes[b,q]=i;changed=True
                if changed:break
                # Intra-route 2-opt; symmetric DISTANCE is an explicit data invariant.
                if enabled[2] and a==b and p<q:
                    prev=routes[a,p-1] if p else 0;nxt=routes[a,q+1] if q+1<La else 0
                    delta=distance[prev,j]+distance[i,nxt]-distance[prev,i]-distance[j,nxt]
                    if delta<-1e-9:
                        tmp[:La]=routes[a,:La]
                        for k in range(q-p+1):tmp[p+k]=routes[a,q-k]
                        tested+=1
                        valid,_,_=route_eval(tmp,La,travel,distance,demand,service,early,late,capacity,horizon)
                        if valid:routes[a,:La]=tmp[:La];changed=True
                if changed:break
                # 2-opt*: exchange tails at the selected positions.
                if enabled[3] and a!=b:
                    prev=routes[a,p-1] if p else 0;prev2=routes[b,q-1] if q else 0
                    delta=distance[prev,j]+distance[prev2,i]-distance[prev,i]-distance[prev2,j]
                    eliminate=False  # No lexicographic fleet priority.
                    if delta<-1e-9 or eliminate:
                        l1=p+Lb-q;l2=q+La-p
                        tmp[:p]=routes[a,:p];tmp[p:l1]=routes[b,q:Lb]
                        tmp2[:q]=routes[b,:q];tmp2[q:l2]=routes[a,p:La]
                        tested+=1
                        va,_,_=route_eval(tmp,l1,travel,distance,demand,service,early,late,capacity,horizon)
                        vb,_,_=route_eval(tmp2,l2,travel,distance,demand,service,early,late,capacity,horizon)
                        if va and vb:
                            routes[a,:l1]=tmp[:l1];routes[b,:l2]=tmp2[:l2];lens[a]=l1;lens[b]=l2;changed=True
                if changed:break
            if changed:break
        if not changed:break
        changes+=1
    compact(routes,lens)
    return changes,tested
