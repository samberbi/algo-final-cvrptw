"""Vérification numérique ciblée, sans déclarer un faux optimum compatible."""
from pathlib import Path
from dataclasses import replace
import csv
import json
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import vrplib
import numpy as np
from algo.static_small import load
from algo.ortools_duration import solve
from algo.verify import verify
from algo.data import reference,load as load_full


def main():
    out=ROOT/'results/final_static/reference_audit';out.mkdir(parents=True,exist_ok=True)
    targets={'C101':(2624.01,3),'C105':(2530.20,3),'C106':(2630.01,3),
             'C201':(3195.27,2),'R101':(1295.01,8)}
    rows=[]
    for name,(published,fleet) in targets.items():
        path=ROOT/'data/static_small/n25'/(name+'.txt')
        ins=load(path)
        result=solve(ins,seconds=3,seed=4101)
        assert result['status']=='feasible'
        raw=vrplib.read_instance(path,instance_format='solomon')
        full=replace(ins,travel=10*np.asarray(raw['edge_weight']),distance=10*np.asarray(raw['edge_weight']))
        checked=verify(result['routes'],full)
        row=dict(instance=name,n=25,published_cost=published,published_vehicles=fleet,
            obtained_dimacs_cost=result['cost'],repriced_full_precision=checked['duration']/10,
            full_precision_feasible=checked['valid'],obtained_vehicles=len(result['routes']),
            difference_full_precision=checked['duration']/10-published,
            status='Published starred optimum; direct gap withheld: timing integrality/rounding/route proof not fully established')
        (out/(name+'_25.json')).write_text(json.dumps(dict(comparison=row,result=result,full_precision_check=checked),indent=2))
        rows.append(row)
    # C101 à 100 : coût d'une tournée publiée, sans attribuer de preuve au tableau 3.
    name='C101';path=ROOT/'data/instances/C101.vrp'
    ins=load_full(path);raw=vrplib.read_instance(path)
    full=replace(ins,travel=10*np.asarray(raw['edge_weight']),distance=10*np.asarray(raw['edge_weight']))
    routes,_=reference(ROOT/'data/instances/C101.sol')
    checked=verify(routes,full)
    rows.append(dict(instance=name,n=100,published_cost=9828.94,published_vehicles=10,
        obtained_dimacs_cost=verify(routes,ins)['duration']/10,repriced_full_precision=checked['duration']/10,
        full_precision_feasible=checked['valid'],obtained_vehicles=len(routes),
        difference_full_precision=checked['duration']/10-9828.94,
        status='Published heuristic value, not treated as certified optimum'))
    with (out/'PHONIN_VERIFICATION.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
