"""Pinned DIMACS instances; references belong only to the evaluator."""
from pathlib import Path
import numpy as np
import vrplib
from .model import Instance


def load(path):
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
    raw=vrplib.read_solution(str(path))
    return raw['routes'],float(raw['cost'])
