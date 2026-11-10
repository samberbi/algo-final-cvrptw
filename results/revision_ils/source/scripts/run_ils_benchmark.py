"""Predeclared paired ILS/SA campaign, common initial routes, separate outputs."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):
    os.environ[key]='1'
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse,hashlib,json,multiprocessing as mp,random,time,traceback
import psutil
from algo.data import load
from algo.solver import construct,solve,Settings,warmup
from algo.verify import verify
from web.experiments import atomic_json,read_json

OUT=ROOT/'results/revision_ils'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def initialize(cpus):
    psutil.Process().cpu_affinity([cpus[(mp.current_process()._identity[0]-1)%len(cpus)]])
    warmup()


def execute(job):
    targets={m:OUT/'runs'/f"{job['id']:04d}_{job['instance']}_{job['seed']}_{m}.json" for m in ('ils','sa')}
    if all(p.exists() for p in targets.values()):return job['id']
    ins=load(ROOT/'data/instances'/(job['instance']+'.vrp'))
    initial_path=OUT/'initials'/f"{job['id']:04d}.json"
    if initial_path.exists():
        shared=read_json(initial_path);initial,info=shared['routes'],shared['info']
    else:
        initial,info=construct(ins,job['seed'],12)
        atomic_json(initial_path,dict(job=job,routes=initial,info=info))
    order=['ils','sa'];random.Random(9371+job['id']).shuffle(order)
    for method in order:
        if targets[method].exists():continue
        try:
            if initial is None:
                result=dict(status='not_found',method=method,routes=None,reason='Common initial construction failed',runtime_s=0.)
            else:
                result=solve(ins,Settings(method=method,seconds=job['seconds'],seed=job['seed']),initial)
            valid=False;gap=None
            if result['status']=='feasible':
                check=verify(result['routes'],ins)
                assert check['valid'] and abs(check['distance']/10-result['cost'])<1e-7
                valid=True;gap=100*(result['cost']/job['reference_distance']-1)
            record=dict(job=dict(job,method=method,profile='ILS' if method=='ils' else 'Recuit simulé'),
                        result=result,valid=valid,gap_pct=gap,reference_distance=job['reference_distance'],
                        shared_initial=info,initial_routes_sha256=hashlib.sha256(json.dumps(initial).encode()).hexdigest(),
                        method_order=order,cpu_affinity=psutil.Process().cpu_affinity(),n=ins.n,
                        budget_s=job['seconds'],total_with_shared_initial_s=result['runtime_s']+info['seconds'])
        except Exception as exc:
            record=dict(job=dict(job,method=method),valid=False,gap_pct=None,n=ins.n,
                        result=dict(status='error',reason=str(exc),traceback=traceback.format_exc(),runtime_s=0.))
        atomic_json(targets[method],record)
    return job['id']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args();(OUT/'runs').mkdir(parents=True,exist_ok=True)
    refs={r['instance']:r for r in read_json(ROOT/'data/manifest.json')['reference_instances']}
    names=[f'{f}{i:02}' for f in ('C1','C2','R1','R2','RC1','RC2') for i in range(1,5)]
    names+=['C1_2_1','R1_2_1','C1_10_1','R1_10_1']
    budgets={100:5.,200:6.,1000:25.}
    jobs=[dict(id=i,instance=n,seed=seed,n=refs[n]['n'],seconds=budgets[refs[n]['n']],
               reference_distance=refs[n]['reference_distance'])
          for i,(n,seed) in enumerate((n,s) for n in names for s in range(101,121))]
    allowed=psutil.Process().cpu_affinity();cpus=allowed[::2][:args.workers]
    protocol=dict(instances=names,seeds=list(range(101,121)),pairs=len(jobs),runs=2*len(jobs),jobs=jobs,
                  methods=['ils','sa'],objective='DIMACS total distance, strict CVRPTW, fleet upper bound',
                  shared_initial='12 regret-2 constructions once per pair; same routes supplied to both methods',
                  timing='Equal improvement budgets, initial construction recorded separately; atomic operations may overrun',
                  parallelism=dict(workers=len(cpus),cpu_affinities=cpus,shared_resources=True),
                  prior_exposure='Known instances; implementation pilots already observed; not a blind holdout',
                  sources={str(p.relative_to(ROOT)):digest(p) for p in [*sorted((ROOT/'algo').glob('*.py')),Path(__file__).resolve()]},
                  manifest_sha256=digest(ROOT/'data/manifest.json'))
    pp=OUT/'protocol.json'
    if pp.exists():assert read_json(pp)==protocol,'Frozen protocol mismatch'
    else:
        atomic_json(pp,protocol)
        import shutil
        for rel in protocol['sources']:
            target=OUT/'source'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,target)
    order=jobs[:];random.Random(20261110).shuffle(order);start=time.perf_counter();done=0
    print('Frozen:',len(names),'instances,',len(jobs)*2,'runs,',len(cpus),'workers',flush=True)
    with mp.get_context('spawn').Pool(len(cpus),initializer=initialize,initargs=(cpus,)) as pool:
        for pair in pool.imap_unordered(execute,order,chunksize=1):
            done+=1
            atomic_json(OUT/'progress.json',dict(completed_pairs=done,total_pairs=len(jobs),complete=done==len(jobs),elapsed_s=time.perf_counter()-start))
            if done%10==0:print(done,'/',len(jobs),'pairs',round(time.perf_counter()-start,1),'s',flush=True)
    print('Complete',flush=True)


if __name__=='__main__':main()
