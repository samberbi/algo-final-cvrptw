"""Additional declared development on difficult long-route families."""
import os
for key in ['OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
from pathlib import Path
import sys,json,multiprocessing as mp,time,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import psutil
from algo.data import load
from algo.iterated import construct
from algo.optimized import solve,Settings,warmup
from algo.precondition import descend
from algo.verify import verify
OUT=ROOT/'results/optimization_v3/descent_development'


def init(cpus):
    psutil.Process().cpu_affinity([cpus[(mp.current_process()._identity[0]-1)%len(cpus)]])
    warmup()


def execute(job):
    name,swap=job;ins=load(ROOT/'data/instances'/(name+'.vrp'))
    initial,info=construct(ins,952,12)
    before=verify(initial,ins)['distance']/10
    prepared=descend(ins,initial,6.25,952,swap)
    remaining=max(.01,25-prepared['runtime_s'])
    result=solve(ins,Settings(seconds=remaining,seed=952,group_size=240,adaptive_groups=True),prepared['routes'])
    ref=next(r['reference_distance'] for r in json.loads((ROOT/'data/manifest.json').read_text())['reference_instances'] if r['instance']==name)
    item=dict(instance=name,swap=swap,initial_cost=before,precondition=prepared,result=result,gap_pct=100*(result['cost']/ref-1),time=prepared['runtime_s']+result['runtime_s'])
    (OUT/f'{name}_{int(swap)}.json').write_text(json.dumps(item),encoding='utf-8')
    return dict(instance=name,swap=swap,pre_gap=100*(prepared['cost']/ref-1),final_gap=item['gap_pct'],seconds=item['time'])


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    jobs=[(name,flag) for name in ['C2_10_2','R2_10_2','RC2_10_2'] for flag in [False,True]]
    (OUT/'protocol.json').write_text(json.dumps(dict(jobs=jobs,seed=952,total_budget=25,precondition_max_s=6.25,role='Additional development after v2 coverage; no validation data tuning',source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'algo').glob('*.py')})))
    with mp.get_context('spawn').Pool(2,initializer=init,initargs=(psutil.Process().cpu_affinity()[::2][-2:],)) as pool:
        for item in pool.imap_unordered(execute,jobs):print(json.dumps(item),flush=True)
