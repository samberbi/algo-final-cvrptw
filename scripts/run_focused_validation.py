"""Fresh 80-run study fixed by instance identifiers, with full coverage separate.

Known instances: this is a new repeated measurement, not an unseen test set.
Never import or execute the comparison project's code or stored solutions.
"""
import os
for variable in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS']:
    os.environ[variable]='1'
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import json,hashlib,time,multiprocessing as mp,psutil,traceback
from algo.data import load
from algo.solver import solve,Settings,warmup
from algo.verify import verify
from ameliorations.decomposition import polish


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def initialize():
    psutil.Process().cpu_affinity([[0,2,4,6][(mp.current_process()._identity[0]-1)%4]])
    warmup()


def execute(job):
    path=ROOT/'results/focused/runs'/f'{job["id"]:03d}_{job["instance"]}_{job["seed"]}.json'
    if path.exists():
        record=json.loads(path.read_text());assert record['job']==job
        return record['result']['status']
    start=time.perf_counter()
    try:
        ins=load(ROOT/'data/instances'/(job['instance']+'.vrp'))
        result=solve(ins,Settings(seconds=job['seconds'],seed=job['seed']))
        base_cost=result.get('cost');base_time=result['runtime_s'];stages=[]
        if result['status']=='feasible' and ins.n>=400:
            for offset in ([600000,700000] if ins.n==1000 else [600000]):
                improved=polish(ins,result['routes'],5.,job['seed']+offset)
                stages.append(dict(cost=improved['cost'],runtime_s=improved['runtime_s']))
                trace=result['trace']+[dict(iteration=result['iterations'],elapsed_s=result['runtime_s']+v['elapsed_s'],
                    best=v['best'],phase='intensification') for v in improved['trace']]
                result=dict(result,routes=improved['routes'],cost=improved['cost'],vehicles=improved['vehicles'],
                    trace=trace,runtime_s=result['runtime_s']+improved['runtime_s'])
        if result['status']=='feasible':
            checked=verify(result['routes'],ins);assert checked['valid']
            assert abs(result['cost']-checked['distance']/10)<1e-6
            result['metrics']={k:v for k,v in checked.items() if k!='routes'}
        gap=100*(result['cost']/job['reference_distance']-1) if result['status']=='feasible' else None
        record=dict(job=job,result=result,gap_pct=gap,from_zero=True,base_cost=base_cost,base_runtime_s=base_time,
            stages=stages,total_budget_s=job['seconds']+(10. if job['n']==1000 else 0.),
            cpu_affinity=psutil.Process().cpu_affinity())
    except Exception as exc:
        record=dict(job=job,from_zero=True,gap_pct=None,base_cost=None,base_runtime_s=None,stages=[],
            result=dict(status='error',reason=repr(exc),traceback=traceback.format_exc(),runtime_s=time.perf_counter()-start))
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(record));temp.replace(path)
    return record['result']['status']


def main():
    out=ROOT/'results/focused';(out/'runs').mkdir(parents=True,exist_ok=True)
    refs={r['instance']:r for r in json.loads((ROOT/'data/manifest.json').read_text())['reference_instances']}
    selection=[(f'{family}{i:02}',seed) for family in ['C1','C2','R1','R2','RC1','RC2'] for i in [1,2,3,4] for seed in [11,22,33]]
    selection += [(name,11) for name in ['C1_2_1','R1_2_1']]
    selection += [(name,seed) for name in ['C1_10_1','R1_10_1'] for seed in [11,22,33]]
    jobs=[dict(id=i,instance=name,n=refs[name]['n'],seed=seed,reference_distance=refs[name]['reference_distance'],
        seconds={100:5.,200:6.,1000:15.}[refs[name]['n']]) for i,(name,seed) in enumerate(selection)]
    assert len(jobs)==80 and len({j['instance'] for j in jobs})==28
    protocol=dict(jobs=jobs,runs=80,instances=28,from_zero=True,
        selection='four first identifiers per Solomon family, first C1/R1 at 200 and 1000; fixed before this fresh campaign',
        prior_exposure='known instances already inspected; illustrative validation, not a blind holdout',
        objective='DIMACS distance only; file fleet maximum',workers=4,cpu_affinities=[0,2,4,6],
        nominal_budgets='5 s at 100, 6 s at 200, 15+5+5 s at 1000; warmup and loading separate',
        data_manifest_sha256=sha(ROOT/'data/manifest.json'),
        sources={str(p.relative_to(ROOT)):sha(p) for p in [*sorted((ROOT/'algo').glob('*.py')),ROOT/'ameliorations/decomposition.py']})
    pp=out/'protocol.json'
    if pp.exists():assert json.loads(pp.read_text())==protocol
    else:pp.write_text(json.dumps(protocol,indent=2))
    counts={};started=time.perf_counter()
    with mp.get_context('spawn').Pool(4,initializer=initialize) as pool:
        for i,status in enumerate(pool.imap_unordered(execute,jobs,chunksize=1),1):
            counts[status]=counts.get(status,0)+1
            progress=dict(completed=i,expected=80,complete=i==80,statuses=counts,elapsed_s=time.perf_counter()-started)
            (out/'progress.json').write_text(json.dumps(progress,indent=2))
            if i%8==0:print(i,'/80',counts,flush=True)


if __name__=='__main__':main()
