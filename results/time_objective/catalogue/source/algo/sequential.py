"""Solomon-style sequential insertion, used only for initial construction."""
import numpy as np
from numba import njit
from .kernels import refresh,insert_at


@njit(cache=True)
def sequential_insert(travel,distance,demand,service,early,late,capacity,horizon,
                      fleet,seed,saving_weight,time_weight,seed_policy):
    """Build complete feasible tours; never called during a search iteration.

    A route starts with a far or urgent customer. Its next customer maximizes
    depot saving minus insertion cost. Latest-start caches enforce all windows.
    """
    np.random.seed(seed)
    n=len(demand)-1
    routes=np.zeros((min(fleet,n)+1,n+2),np.int64)
    lengths=np.zeros(len(routes),np.int64)
    pending=np.ones(n+1,np.bool_);pending[0]=False
    depart=np.zeros((1,n+2));latest=np.zeros((1,n+2))
    one=np.zeros((1,n+2),np.int64);one_length=np.zeros(1,np.int64)
    left=n;vehicle=0
    while left:
        if vehicle>=fleet or vehicle>=n:return routes,lengths,False
        chosen=-1;priority=-1e100
        for client in range(1,n+1):
            if not pending[client]:continue
            if demand[client]>capacity:continue
            begin=max(travel[0,client],early[client])
            if begin>late[client] or begin+service[client]+travel[client,0]>horizon:continue
            rank=distance[0,client] if seed_policy==0 else -late[client]+.05*distance[0,client]
            rank*=1+.1*(np.random.random()-.5)
            if rank>priority:chosen=client;priority=rank
        if chosen<0:return routes,lengths,False
        one_length[0]=1;one[0,0]=chosen;pending[chosen]=False;left-=1
        while left:
            valid,_,load=refresh(one,one_length,0,travel,distance,demand,service,early,late,capacity,horizon,depart,latest)
            if not valid:return routes,lengths,False
            length=one_length[0];winner=-1;winner_position=-1;winner_score=-1e100
            for client in range(1,n+1):
                if not pending[client] or load+demand[client]>capacity+1e-8:continue
                best=1e100;best_position=-1
                for position in range(length+1):
                    previous=one[0,position-1] if position else 0
                    following=one[0,position] if position<length else 0
                    begin=max(depart[0,position]+travel[previous,client],early[client])
                    if begin>late[client]+1e-8:continue
                    arrive_next=begin+service[client]+travel[client,following]
                    if arrive_next>latest[0,position]+1e-8:continue
                    delta=distance[previous,client]+distance[client,following]-distance[previous,following]
                    delay=0.
                    if position<length:
                        old_start=depart[0,position+1]-service[following]
                        delay=max(arrive_next,early[following])-old_start
                    rank=(1-time_weight)*delta+time_weight*delay
                    if rank<best:best=rank;best_position=position
                if best_position<0:continue
                score=(saving_weight*distance[0,client]-best)*(1+.05*(np.random.random()-.5))
                if score>winner_score:winner=client;winner_position=best_position;winner_score=score
            if winner<0:break
            insert_at(one,one_length,0,winner,winner_position)
            pending[winner]=False;left-=1
        routes[vehicle,:one_length[0]]=one[0,:one_length[0]]
        lengths[vehicle]=one_length[0];vehicle+=1
    return routes,lengths,True
