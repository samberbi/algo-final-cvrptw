"""Independent external performance ceiling on exactly the same integer matrices."""
import os
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import json,sys,multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import psutil
from algo.data import load
from algo.external_reference import solve
from web.experiments import atomic_json,read_json


def run(name):
    psutil.Process().cpu_affinity([[0,2,4][['C2_10_3','R2_10_3','RC2_10_4'].index(name)]])
    ins=load(ROOT/'data/instances'/(name+'.vrp'))
    result=solve(ins,20,2001)
    ref=next(r['reference_distance'] for r in read_json(ROOT/'data/manifest.json')['reference_instances'] if r['instance']==name)
    row=dict(instance=name,result=result,gap_pct=100*(result['cost']/ref-1) if result.get('cost') else None)
    atomic_json(ROOT/'results/optimization_v7/external_pilot'/(name+'.json'),row)
    return dict(instance=name,gap=row['gap_pct'],runtime_s=result['runtime_s'],engine=result['engine'])


if __name__=='__main__':
    with mp.get_context('spawn').Pool(3) as pool:
        for r in pool.imap_unordered(run,['C2_10_3','R2_10_3','RC2_10_4']):print(json.dumps(r),flush=True)
