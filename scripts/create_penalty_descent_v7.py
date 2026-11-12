"""Derive an auditable penalty-aware descent from our existing four move types."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

HEADER='''"""Complete-state penalized descent; keep a separate feasible distance archive."""
import numpy as np
from numba import njit
from .kernels import compact
from .penalty_hybrid import route_penalties
TOL=1e-8

@njit(cache=True)
def augmented(seq,length,travel,distance,demand,service,early,late,capacity,horizon,wc,wt):
    d,c,t=route_penalties(seq,length,travel,distance,demand,service,early,late,capacity,horizon)
    return d+wc*c+wt*t

@njit(cache=True)
'''


if __name__=='__main__':
    source=(ROOT/'algo/kernels.py').read_text(encoding='utf-8-sig')
    body=source[source.index('def local_search('):]
    body=body.replace('def local_search(','def descent(',1)
    body=body.replace('seed,enabled):','seed,enabled,capacity_weight,time_weight):',1)
    body=body.replace('    old=np.zeros(len(lens));load=np.zeros(len(lens))',
        '    old=np.zeros(len(lens));load=np.zeros(len(lens))\n    roads=np.zeros(len(lens));excess=np.zeros(len(lens));warps=np.zeros(len(lens))\n    ba,bl=routes.copy(),lens.copy();best_feasible=np.inf')
    body=body.replace('valid,old[r],load[r]=route_eval(routes[r],lens[r],travel,distance,demand,service,early,late,capacity,horizon)',
        'roads[r],excess[r],warps[r]=route_penalties(routes[r],lens[r],travel,distance,demand,service,early,late,capacity,horizon)\n            old[r]=roads[r]+capacity_weight*excess[r]+time_weight*warps[r]')
    body=body.replace('        changed=False','        if excess.sum()<=TOL and warps.sum()<=TOL and roads.sum()<best_feasible-1e-8:\n            best_feasible=roads.sum();ba,bl=routes.copy(),lens.copy()\n        changed=False')
    body=body.replace('                        if load[b]+chainload>capacity+TOL:continue','')
    body=body.replace('if enabled[1] and a!=b and load[a]-demand[i]+demand[j]<=capacity+TOL and load[b]-demand[j]+demand[i]<=capacity+TOL:',
                      'if enabled[1] and a!=b:')
    body=body.replace('if not eliminate and delta>=-1e-9:continue',
        'if delta>=-1e-9 and old[a]-roads[a]+old[b]-roads[b]<=TOL:continue')
    body=body.replace('if delta<-1e-9:', 'if delta<-1e-9 or old[a]-roads[a]+old[b]-roads[b]>TOL:')
    body=body.replace('if delta<-1e-9 or eliminate:', 'if delta<-1e-9 or old[a]-roads[a]+old[b]-roads[b]>TOL:')
    for seq,length,oldvars,newvar in [('tmp','La-size','va,_,_','ca'),('tmp2','Lb+size','vb,_,_','cb'),
        ('tmp','La','va,_,_','ca'),('tmp2','Lb','vb,_,_','cb'),('tmp','La','valid,_,_','ca'),
        ('tmp','l1','va,_,_','ca'),('tmp2','l2','vb,_,_','cb')]:
        old=f'{oldvars}=route_eval({seq},{length},travel,distance,demand,service,early,late,capacity,horizon)'
        new=f'{newvar}=augmented({seq},{length},travel,distance,demand,service,early,late,capacity,horizon,capacity_weight,time_weight)'
        body=body.replace(old,new)
    body=body.replace('if va and vb:', 'if ca+cb<old[a]+old[b]-1e-8:')
    body=body.replace('if valid:routes[a,:La]=tmp[:La];changed=True', 'if ca<old[a]-1e-8:routes[a,:La]=tmp[:La];changed=True')
    ending='''    for r in range(len(lens)):
        roads[r],excess[r],warps[r]=route_penalties(routes[r],lens[r],travel,distance,demand,service,early,late,capacity,horizon)
    if excess.sum()<=TOL and warps.sum()<=TOL and roads.sum()<best_feasible-1e-8:
        best_feasible=roads.sum();ba,bl=routes.copy(),lens.copy()
    compact(routes,lens)
    return changes,tested,ba,bl,best_feasible
'''
    body=body.replace('    compact(routes,lens)\n    return changes,tested',ending)
    assert 'route_eval(' not in body and 'va and vb' not in body
    assert 'load[b]+chainload>capacity' not in body
    (ROOT/'algo/penalty_descent.py').write_text(HEADER+body,encoding='utf-8')
