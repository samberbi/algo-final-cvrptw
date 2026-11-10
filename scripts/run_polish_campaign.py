# HISTORICAL ALNS experiment: never pool with results/revision_ils.
"""Five-second post-hoc intensification on every >=400-client trajectory.

The original 1,000 attempts remain immutable. Derived files retain the base
hash, cumulative time, stage budget and method hash. No BKS enters the search.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import concurrent.futures as cf,multiprocessing as mp,psutil,json,time,os,hashlib
from algo.data import load
from algo.legacy_alns import warmup
from algo.verify import verify
from ameliorations.decomposition import polish


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def initialize():
    index=mp.current_process()._identity[0]-1
    psutil.Process().cpu_affinity([[8,10][index%2]])
    warmup()


def execute(filename):
    base_path=Path(filename);row=json.loads(base_path.read_text());job=row['job'];old=row['result']
    target=ROOT/'results/final/runs'/base_path.name
    if target.exists():return
    result=old;gap=row['gap_pct'];extra=0.
    if job['n']>=400 and old['status']=='feasible':
        ins=load(ROOT/'data/instances'/(job['instance']+'.vrp'))
        continued=polish(ins,old['routes'],5.,job['seed']+600000)
        checked=verify(continued['routes'],ins);assert checked['valid']
        assert continued['cost']<=old['cost']+1e-8
        extra=continued['runtime_s']
        trace=list(old['trace'])+[dict(iteration=old['iterations'],elapsed_s=old['runtime_s']+v['elapsed_s'],
            best=v['best'],phase='route_intensification') for v in continued['trace']]
        result=dict(old,routes=continued['routes'],cost=continued['cost'],vehicles=continued['vehicles'],
            runtime_s=old['runtime_s']+extra,cpu_s=None,
            metrics={k:v for k,v in checked.items() if k!='routes'},trace=trace,
            intensification_attempts=continued['attempts'],intensification_improvements=continued['improvements'])
        gap=100*(result['cost']/job['reference_distance']-1)
    derived=dict(row,result=result,gap_pct=gap,initial_gap_pct=row['gap_pct'],initial_cost=old.get('cost'),
        base_runtime_s=old['runtime_s'],continuation_runtime_s=extra,
        total_budget_s=job['seconds']+(5. if job['n']>=400 else 0.),
        base_file_sha256=digest(base_path),base_file='results/campaign/runs/'+base_path.name,
        continued_from_own_solution=True,continuation_cpu_affinity=psutil.Process().cpu_affinity())
    temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(derived),encoding='utf-8');temporary.replace(target)


def main():
    out=ROOT/'results/final';(out/'runs').mkdir(parents=True,exist_ok=True)
    protocol=dict(expected_trajectories=1000,initial_protocol_sha256=digest(ROOT/'results/campaign/protocol.json'),
        additional_seconds=5.,eligible_sizes=[400,600,800,1000],
        selection='post-hoc after six difficult observed cases; 5 paired wins, 1 loss; not independent validation',
        method_sha256=digest(ROOT/'ameliorations/decomposition.py'),workers=2,cpu_affinities=[8,10],
        concurrency='postprocessing may run on other physical cores while initial workers continue; shared thermal/cache resources',
        budget_rule='initial size-dependent budget plus five seconds for every >=400 case, not conditioned on BKS gap')
    pp=out/'protocol.json'
    if pp.exists():assert json.loads(pp.read_text())==protocol
    else:pp.write_text(json.dumps(protocol,indent=2))
    queued=set();futures={};start=time.perf_counter()
    with cf.ProcessPoolExecutor(max_workers=2,mp_context=mp.get_context('spawn'),initializer=initialize) as pool:
        while True:
            finished={p.name for p in (out/'runs').glob('*.json')}
            progress=dict(completed=len(finished),expected=1000,complete=len(finished)==1000,elapsed_s=time.perf_counter()-start)
            (out/'progress.json').write_text(json.dumps(progress,indent=2))
            if len(finished)==1000:break
            files=[p for p in sorted((ROOT/'results/campaign/runs').glob('*.json')) if p.name not in finished and p.name not in queued]
            for p in files[:max(0,2-len(futures))]:
                queued.add(p.name);futures[pool.submit(execute,str(p))]=p.name
            if futures:
                done,_=cf.wait(futures,timeout=1.,return_when=cf.FIRST_COMPLETED)
                for f in done:
                    name=futures.pop(f);f.result()
                    if len(finished)%20==0:print('Derived trajectories',len(finished)+1,'/1000',flush=True)
            else:time.sleep(1.)
    print('All 1000 trajectories and all stage times retained.',flush=True)


if __name__=='__main__':main()
