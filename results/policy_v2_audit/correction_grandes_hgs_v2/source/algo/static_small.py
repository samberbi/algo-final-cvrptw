"""Chargement des sous-instances officielles au même contrat statique que le projet."""
from pathlib import Path
import numpy as np
import vrplib
from .model import Instance


def load(path):
    raw=vrplib.read_instance(path,instance_format='solomon')
    xy=np.asarray(raw['node_coord'],dtype=float)
    travel=np.floor(10*np.asarray(raw['edge_weight'],dtype=float))
    windows=np.rint(10*np.asarray(raw['time_window'],dtype=float))
    service=10*np.asarray(raw['service_time'],dtype=float);service[0]=0
    return Instance(Path(path).stem,xy,raw['demand'],service,windows[:,0],windows[:,1],
        travel,float(raw['capacity']),int(raw['vehicles']),float(windows[0,1]),
        metadata={'source':str(path),'benchmark':'Solomon static subinstance',
                  'convention':'DIMACS truncated tenths, fixed symmetric times, departure zero','scale':10})
