"""Second fixed five-second pass on every 1,000-client trajectory only.

Triggered by size, never by a BKS threshold. Previous states stay immutable.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import concurrent.futures as cf,multiprocessing as mp,psutil,json,time,hashlib
from algo.data import load
from algo.solver import warmup
from algo.verify import verify
from ameliorations.decomposition import polish


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def initialize():
    psutil.Process().cpu_affinity([[0,2][(mp.current_process()._identity[0]-1)%2]])
    warmup()


def execute(filename):
    path=Path(filename);row=json.loads(path.read_text());j=row['job'];old=row['result']
    target=ROOT/'results/largest/runs'/path.name
    if target.exists():return
    result=old;extra=0.;gap=row['gap_pct']
    if old['status']=='feasible':
        ins=load(ROOT/'data/instances'/(j['instance']+'.vrp'))
        r=polish(ins,old['routes'],5.,j['seed']+700000)
        v=verify(r['routes'],ins);assert v['valid'] and r['cost']<=old['cost']+1e-8
        extra=r['runtime_s']
        trace=old['trace']+[dict(iteration=old['iterations'],elapsed_s=old['runtime_s']+t['elapsed_s'],best=t['best'],phase='largest_second_pass') for t in r['trace']]
        result=dict(old,routes=r['routes'],cost=r['cost'],vehicles=r['vehicles'],runtime_s=old['runtime_s']+extra,
            metrics={k:v for k,v in v.items() if k!='routes'},trace=trace,
            largest_extra_attempts=r['attempts'],largest_extra_improvements=r['improvements'])
        gap=100*(r['cost']/j['reference_distance']-1)
    record=dict(row,result=result,gap_pct=gap,second_pass_runtime_s=extra,
        continuation_runtime_s=row['continuation_runtime_s']+extra,total_budget_s=row['total_budget_s']+5.,
        previous_stage_file='results/final/runs/'+path.name,previous_stage_sha256=sha(path),
        largest_cpu_affinity=psutil.Process().cpu_affinity())
    temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(record));temporary.replace(target)


def main():
    out=ROOT/'results/largest';(out/'runs').mkdir(parents=True,exist_ok=True)
    initial=json.loads((ROOT/'results/campaign/protocol.json').read_text())
    expected=sum(j['n']==1000 for j in initial['jobs'])
    protocol=dict(expected=expected,size=1000,additional_seconds=5.,total_nominal_seconds=25.,
        rule='all 1000-client trajectories, no BKS-based stopping or seed selection',
        reason='initial full-screen mean at 1000 clients was 10.0025%; extra size-based effort chosen after observation',
        method_sha256=sha(ROOT/'ameliorations/decomposition.py'),cpu_affinities=[0,2],workers=2)
    pp=out/'protocol.json'
    if pp.exists():assert json.loads(pp.read_text())==protocol
    else:pp.write_text(json.dumps(protocol,indent=2))
    queued=set();futures={};start=time.perf_counter()
    with cf.ProcessPoolExecutor(max_workers=2,mp_context=mp.get_context('spawn'),initializer=initialize) as pool:
        while True:
            finished={p.name for p in (out/'runs').glob('*.json')}
            (out/'progress.json').write_text(json.dumps(dict(completed=len(finished),expected=expected,
                complete=len(finished)==expected,elapsed_s=time.perf_counter()-start),indent=2))
            if len(finished)==expected:break
            files=[p for p in sorted((ROOT/'results/final/runs').glob('*.json'))
                   if p.name not in finished and p.name not in queued and '_10_' in p.name]
            for p in files[:max(0,2-len(futures))]:queued.add(p.name);futures[pool.submit(execute,str(p))]=p.name
            if futures:
                done,_=cf.wait(futures,timeout=1.,return_when=cf.FIRST_COMPLETED)
                for f in done:futures.pop(f);f.result()
            else:time.sleep(1)
    print('All',expected,'largest trajectories received the fixed second pass.',flush=True)


if __name__=='__main__':main()
