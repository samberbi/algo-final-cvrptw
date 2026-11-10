"""Exactly 1,000 predeclared fresh solves across all 356 DIMACS instances.

Four single-threaded workers have separate CPU affinities. This is a new
parallel-throughput protocol, not comparable in runtime to old sequential lots.
Raw attempts, including failures, remain saved. Resume never replaces a run.
"""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS']:
    os.environ[name]='1'
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import hashlib,json,multiprocessing as mp,random,time,traceback
import psutil
from algo.data import load
from algo.solver import Settings,solve,warmup
from algo.verify import verify


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def initialize(cpus):
    index=mp.current_process()._identity[0]-1
    psutil.Process().cpu_affinity([cpus[index%len(cpus)]])
    startup=warmup()
    print('Worker',os.getpid(),'CPU',psutil.Process().cpu_affinity(),'warmup',round(startup,3),flush=True)


def execute(job):
    path=ROOT/'results/campaign/runs'/f'{job["id"]:04d}_{job["instance"]}_{job["seed"]}.json'
    if path.exists():
        previous=json.loads(path.read_text());assert previous['job']==job
        return previous['job']['id'],previous['result']['status'],True
    start=time.perf_counter()
    try:
        ins=load(ROOT/'data/instances'/(job['instance']+'.vrp'))
        result=solve(ins,Settings(seconds=job['seconds'],seed=job['seed']))
        if result['status']=='feasible':
            checked=verify(result['routes'],ins);assert checked['valid']
            assert abs(result['cost']-checked['distance']/10)<1e-7
            result['metrics']={k:v for k,v in checked.items() if k!='routes'}
        gap=100*(result['cost']/job['reference_distance']-1) if result['status']=='feasible' else None
    except Exception as exc:
        result=dict(status='error',reason=repr(exc),traceback=traceback.format_exc(),runtime_s=time.perf_counter()-start,routes=None)
        gap=None
    record=dict(job=job,result=result,gap_pct=gap,wall_with_loading_s=time.perf_counter()-start,
        pid=os.getpid(),cpu_affinity=psutil.Process().cpu_affinity(),from_zero=True)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(record),encoding='utf-8');temporary.replace(path)
    return job['id'],result['status'],False


def main():
    out=ROOT/'results/campaign';(out/'runs').mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    refs=manifest['reference_instances'];assert len(refs)==356
    # Two seeds everywhere; a deterministic random subset receives a third seed.
    # 356*2 + 288 = 1000. This selection is fixed before observing the campaign.
    order=sorted(r['instance'] for r in refs);random.Random(20261109).shuffle(order)
    third=set(order[:288]);jobs=[]
    budgets={100:5.,200:6.,400:8.,600:10.,800:12.,1000:15.}
    for ref in sorted(refs,key=lambda r:(r['n'],r['instance'])):
        for seed in ([11,22,33] if ref['instance'] in third else [11,22]):
            jobs.append(dict(id=len(jobs),instance=ref['instance'],n=ref['n'],seed=seed,
                seconds=budgets[ref['n']],reference_distance=ref['reference_distance'],
                fleet_limit=ref['fleet_limit']))
    assert len(jobs)==1000
    random.Random(8611).shuffle(jobs)
    available=psutil.Process().cpu_affinity();cpus=[c for c in [0,2,4,6] if c in available]
    if not cpus:cpus=available[:1]
    protocol=dict(total_runs=1000,instances=356,seeds=[11,22,33],minimum_repetitions=2,third_seed_instances=sorted(third),
        jobs=jobs,objective='distance only; original file fleet upper bound; DIMACS tenths',
        budgets_s=budgets,workers=len(cpus),single_cpu_affinities=cpus,
        timing='wall-clock search including construction, per-worker warmup and loading separate; parallel single-core workers',
        throughput_caveat='Shared caches, thermal limits and OS load remain; no timing superiority claim against sequential reports',
        prior_exposure='Six named development cases and pilot cases already known; coverage study, not entirely unseen geography',
        dataset_sha256=digest(ROOT/'data/manifest.json'),
        source_sha256={p.name:digest(p) for p in sorted((ROOT/'algo').glob('*.py'))})
    pp=out/'protocol.json'
    if pp.exists():assert json.loads(pp.read_text())==json.loads(json.dumps(protocol)),'Frozen protocol changed'
    else:pp.write_text(json.dumps(protocol,indent=2))
    print('Frozen jobs:',len(jobs),'Workers:',len(cpus),'Total nominal search seconds:',sum(j['seconds'] for j in jobs),flush=True)
    started=time.perf_counter();count=0;statuses={}
    with mp.get_context('spawn').Pool(len(cpus),initializer=initialize,initargs=(cpus,)) as pool:
        for job_id,status,reused in pool.imap_unordered(execute,jobs,chunksize=1):
            count+=1;statuses[status]=statuses.get(status,0)+1
            progress=dict(completed=count,expected=1000,statuses=statuses,elapsed_s=time.perf_counter()-started,complete=count==1000)
            (out/'progress.json').write_text(json.dumps(progress,indent=2))
            if count%10==0:print('Completed',count,'/1000',statuses,'wall',round(progress['elapsed_s'],1),flush=True)
    print('Finished all 1000 predeclared attempts.',flush=True)


if __name__=='__main__':main()
