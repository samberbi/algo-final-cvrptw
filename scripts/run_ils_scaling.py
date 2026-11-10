"""Supplementary fixed-proposal timing; separate from the frozen main campaign."""
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):os.environ[name]='1'
from pathlib import Path
import sys,json,random,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import psutil
from algo.data import load
from algo.solver import solve,Settings,warmup
from algo.verify import verify
from web.experiments import atomic_json,read_json


def main():
    out=ROOT/'results/revision_ils/scaling';out.mkdir(exist_ok=True)
    psutil.Process().cpu_affinity([psutil.Process().cpu_affinity()[4]])
    protocol=dict(instances=['C101','R101','C1_2_1','R1_2_1','C1_10_1','R1_10_1'],seeds=[101,102,103],
        methods=['ils','sa'],proposals=50000,safety_seconds=30.,cpu_affinity=psutil.Process().cpu_affinity(),
        scope='Fixed proposal count within each method, local-search internal evaluations not counted; instances differ in structure',
        construction='Reuse the frozen common starts, recorded separately',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if (out/'protocol.json').exists():assert read_json(out/'protocol.json')==protocol
    else:atomic_json(out/'protocol.json',protocol)
    jobs=[(n,s,m) for n in protocol['instances'] for s in protocol['seeds'] for m in protocol['methods']]
    random.Random(847).shuffle(jobs);warmup()
    for name,seed,method in jobs:
        target=out/f'{name}_{seed}_{method}.json'
        if target.exists():continue
        initial=next(read_json(p) for p in (out.parent/'initials').glob('*.json') if (lambda j:j['instance']==name and j['seed']==seed)(read_json(p)['job']))
        ins=load(ROOT/'data/instances'/(name+'.vrp'))
        result=solve(ins,Settings(method=method,seconds=30.,iterations=50000,seed=seed),initial['routes'])
        assert verify(result['routes'],ins)['valid'] and result['iterations']==50000
        atomic_json(target,dict(instance=name,n=ins.n,seed=seed,method=method,result=result,initial=initial['info']))
    print('Fixed-proposal study complete:',len(jobs),'runs')


if __name__=='__main__':main()
