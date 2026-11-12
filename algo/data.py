"""Pinned DIMACS instances; references belong only to the evaluator."""
from pathlib import Path
import numpy as np
import vrplib
from .model import Instance


def load(path):
    """Lit une instance VRPLIB et applique les unités DIMACS du projet.
    Distances : troncature à un dixième, stockée en unités entières ×10.
    Horaires et services sont aussi multipliés par 10 ; les demandes ne changent pas."""
    raw=vrplib.read_instance(str(path))
    xy=np.asarray(raw['node_coord'],dtype=float)
    distance=np.floor(10*np.asarray(raw['edge_weight'],dtype=float))
    windows=np.rint(10*np.asarray(raw['time_window'],dtype=float))
    service=np.asarray(raw.get('service_time',0),dtype=float)
    if service.ndim==0:service=np.full(len(xy),float(service))
    service=service*10;service[0]=0
    if list(raw['depot']) != [0]:raise ValueError('Single depot at index zero required')
    return Instance(Path(path).stem,xy,raw['demand'],service,windows[:,0],windows[:,1],
        distance,float(raw['capacity']),int(raw['vehicles']),float(windows[0,1]),
        metadata={'benchmark':'DIMACS distance-only','scale':10,'source':str(path)})


def reference(path):
    """Lit une solution de référence pour l’évaluation après résolution.
    Les tournées et le coût BKS ne sont pas transmis au moteur de recherche."""
    raw=vrplib.read_solution(str(path))
    return raw['routes'],float(raw['cost'])
