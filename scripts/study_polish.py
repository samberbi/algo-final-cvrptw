# HISTORICAL ALNS experiment: never pool with results/revision_ils.
"""Equal-time paired pilot on six observed difficult large trajectories."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import json,hashlib,psutil
from algo.data import load
from algo.legacy_alns import solve,Settings,warmup
from ameliorations.decomposition import polish


def main():
    psutil.Process().cpu_affinity([8])
    out=ROOT/'results/polish_pilot';out.mkdir(exist_ok=True)
    pp=out/'protocol.json'
    if not pp.exists():
        rows=[json.loads(p.read_text()) for p in (ROOT/'results/campaign/runs').glob('*.json')]
        rows=[r for r in rows if r['job']['n']==1000 and r['result']['status']=='feasible']
        worst=sorted(rows,key=lambda r:r['gap_pct'],reverse=True)
        selected=[];names=set()
        for r in worst:
            if r['job']['instance'] in names:continue
            selected.append(r['job']['id']);names.add(r['job']['instance'])
            if len(selected)==6:break
        pp.write_text(json.dumps(dict(selected_job_ids=selected,seconds=5.,seed=606,
            selection='six worst distinct 1000-client instances observed before pilot; explicitly post-hoc',
            method_sha256=hashlib.sha256((ROOT/'ameliorations/decomposition.py').read_bytes()).hexdigest()),indent=2))
    protocol=json.loads(pp.read_text());warmup()
    records={r['job']['id']:r for r in [json.loads(p.read_text()) for p in (ROOT/'results/campaign/runs').glob('*.json')]}
    output=out/'runs.jsonl';done={(r['id'],r['method']) for r in map(json.loads,output.read_text().splitlines())} if output.exists() else set()
    for i,job_id in enumerate(protocol['selected_job_ids']):
        base=records[job_id];job=base['job'];ins=load(ROOT/'data/instances'/(job['instance']+'.vrp'))
        for method in (['global','decomposition'] if i%2==0 else ['decomposition','global']):
            if (job_id,method) in done:continue
            if method=='global':result=solve(ins,Settings(seconds=5.,seed=606),base['result']['routes'])
            else:result=polish(ins,base['result']['routes'],5.,606)
            gap=100*(result['cost']/job['reference_distance']-1)
            row=dict(id=job_id,instance=job['instance'],method=method,initial_gap_pct=base['gap_pct'],gap_pct=gap,result=result)
            with output.open('a') as f:f.write(json.dumps(row)+'\n')
            print(job['instance'],method,'gap',gap,flush=True)


if __name__=='__main__':main()
