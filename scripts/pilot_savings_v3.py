"""Declared constructor pilot on the development families; no held-out tuning."""
import os
for key in ['OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
from pathlib import Path
import sys,json,multiprocessing as mp,time,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import psutil
from algo.data import load
from algo.iterated import arrays,decode,construct
from algo.optimized import solve,Settings,warmup
from algo.savings import savings_construct
from algo.verify import verify
OUT=ROOT/'results/optimization_v3/savings_development'


def init(cpus):
    psutil.Process().cpu_affinity([cpus[(mp.current_process()._identity[0]-1)%len(cpus)]])
    warmup();ins=load(ROOT/'data/instances/C101.vrp')
    savings_construct(*arrays(ins),ins.vehicles,1,0.)


def execute(name):
    ins=load(ROOT/'data/instances'/(name+'.vrp'))
    initial,info=construct(ins,953,12);best_routes=initial;best=verify(initial,ins)['distance']/10
    old=best;trials=[]
    for noise in [0.,.05,.15]:
        start=time.perf_counter()
        encoded,lengths,success=savings_construct(*arrays(ins),ins.vehicles,953,noise)
        routes=decode(encoded,lengths) if success else None
        cost=verify(routes,ins)['distance']/10 if routes is not None else None
        if routes is not None:assert verify(routes,ins)['valid']
        trials.append(dict(noise=noise,cost=cost,runtime_s=time.perf_counter()-start))
        if cost is not None and cost<best:best=cost;best_routes=routes
    result=solve(ins,Settings(seconds=25.,seed=953,group_size=240,adaptive_groups=True),best_routes)
    ref=next(r['reference_distance'] for r in json.loads((ROOT/'data/manifest.json').read_text())['reference_instances'] if r['instance']==name)
    item=dict(instance=name,old_start=old,new_start=best,initial_routes=best_routes,trials=trials,result=result,gap_pct=100*(result['cost']/ref-1))
    (OUT/(name+'.json')).write_text(json.dumps(item),encoding='utf-8')
    return dict(instance=name,old_start_gap=100*(old/ref-1),new_start_gap=100*(best/ref-1),final_gap=item['gap_pct'])


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True);names=[f'{f}_10_2' for f in ['C1','C2','R1','R2','RC1','RC2']]
    (OUT/'protocol.json').write_text(json.dumps(dict(names=names,seed=953,noises=[0.,.05,.15],search_seconds=25,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'algo').glob('*.py')},role='Development only; added after weak v2 generalization, v2 results are kept')))
    with mp.get_context('spawn').Pool(2,initializer=init,initargs=(psutil.Process().cpu_affinity()[::2][-2:],)) as pool:
        for item in pool.imap_unordered(execute,names):print(json.dumps(item),flush=True)
