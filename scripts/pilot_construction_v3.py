"""Additional construction calibration; never replace the v2 validation."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS']:os.environ[key]='1'
from pathlib import Path
import sys,json,time,multiprocessing as mp,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import psutil
from algo.data import load
from algo.iterated import construct,arrays,decode,Settings as CoreSettings,solve as core_solve
from algo.optimized import solve,Settings,warmup
from algo.sequential import sequential_insert
from algo.verify import verify
from algo import kernels

OUT=ROOT/'results/optimization_v3/construction_development'
CPUS=[]


def init(cpus):
    psutil.Process().cpu_affinity([cpus[(mp.current_process()._identity[0]-1)%len(cpus)]])
    warmup()
    ins=load(ROOT/'data/instances/C101.vrp')
    sequential_insert(*arrays(ins),ins.vehicles,1,1.,.2,0)


def execute(name):
    ins=load(ROOT/'data/instances'/(name+'.vrp'))
    ref=next(r['reference_distance'] for r in json.loads((ROOT/'data/manifest.json').read_text())['reference_instances'] if r['instance']==name)
    rows=[];initial,info=construct(ins,951,12)
    best=verify(initial,ins)['distance']/10;best_routes=initial
    rows.append(dict(label='regret12',cost=best,seconds=info['seconds']))
    for saving,time_weight,policy in [(1.,0.,0),(2.,0.,0),(1.,.2,0),(2.,.2,0),(1.,0.,1),(1.,.2,1)]:
        start=time.perf_counter()
        encoded,lengths,success=sequential_insert(*arrays(ins),ins.vehicles,951,saving,time_weight,policy)
        routes=decode(encoded,lengths) if success else None
        if routes is not None:
            checked=verify(routes,ins);assert checked['valid'];cost=checked['distance']/10
        else:cost=None
        rows.append(dict(label=f'seq_{saving}_{time_weight}_{policy}',cost=cost,seconds=time.perf_counter()-start))
        if cost is not None and cost<best:best=cost;best_routes=routes
    result=solve(ins,Settings(seconds=25.,seed=951,group_size=240,adaptive_groups=True),best_routes)
    item=dict(instance=name,reference_distance=ref,construction=rows,best_initial=best,
              initial_routes=best_routes,result=result,gap_pct=100*(result['cost']/ref-1))
    (OUT/(name+'.json')).write_text(json.dumps(item),encoding='utf-8')
    return dict(instance=name,old_start_gap=100*(rows[0]['cost']/ref-1),new_start_gap=100*(best/ref-1),final_gap=item['gap_pct'])


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    names=[f'{f}_10_2' for f in ['C1','C2','R1','R2','RC1','RC2']]
    (OUT/'protocol.json').write_text(json.dumps(dict(names=names,seed=951,search_seconds=25,role='Further development after v2 broad validation revealed weak generalization; v2 validation remains fully published',source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'algo').glob('*.py')})))
    cpus=psutil.Process().cpu_affinity()[::2][-2:]
    with mp.get_context('spawn').Pool(2,initializer=init,initargs=(cpus,)) as pool:
        for item in pool.imap_unordered(execute,names):print(json.dumps(item),flush=True)
