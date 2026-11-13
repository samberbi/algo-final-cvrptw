"""Campagne ciblée : construction + intensification + partitionnement en durée.

Périmètre sélectionné sur les résultats antérieurs : mise au point, pas test
indépendant. Les témoins sont lus seulement après la résolution de chaque cas.
"""
from pathlib import Path
import argparse,hashlib,json,os,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
from algo.data import load,reference
from algo.verify import verify
from algo.duration_refine import solve
from algo.iterated import arrays
from algo.savings import savings_construct
from algo.sequential import sequential_insert


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=float,default=10)
    parser.add_argument('--tag',default='outliers10');args=parser.parse_args()
    out=ROOT/'results/time_objective'/args.tag
    (out/'runs').mkdir(parents=True,exist_ok=True)
    core=pd.read_csv(ROOT/'results/time_objective/catalogue/core.csv')
    cases=pd.read_csv(ROOT/'results/time_objective/catalogue/instances.csv')
    selected=set(cases.loc[cases.mean_delta_reference_pct.gt(6),'instance'])
    selected.update(core.loc[core.delta_reference_pct.gt(6),'instance'])
    jobs=core[core.instance.isin(selected)].sort_values(['instance','seed'])
    hashes={}
    for name in ['duration_refine','route_pool','savings','sequential','iterated','hgs_tuning','verify','data','model']:
        p=ROOT/'algo'/(name+'.py');dest=out/'source/algo'/p.name
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
        hashes['algo/'+p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    protocol=dict(objective='sum_route_duration',departures=0,reference_kind='duration_of_distance_BKS_plan',
                  selection='Instances with mean OR individual coverage run above +6% in the prior catalogue',
                  requested_total_s=args.seconds,jobs=[(r.instance,int(r.seed)) for r in jobs.itertuples()],
                  sources=hashes,scope='Targeted development, not independent validation',workers=1)
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    warm=load(ROOT/'data/instances/C101.vrp')
    savings_construct(*arrays(warm),warm.vehicles,0,0.)
    sequential_insert(*arrays(warm),warm.vehicles,0,1.,.5,0)
    print(f'{len(jobs)} runs on {len(selected)} instances; total requested {args.seconds}s/run',flush=True)
    rows=[]
    for job in jobs.itertuples():
        path=out/'runs'/f'{job.instance}_{job.seed}.json'
        if path.exists():
            record=json.loads(path.read_text())
        else:
            start=time.perf_counter()
            try:
                ins=load(ROOT/'data/instances'/(job.instance+'.vrp'))
                result=solve(ins,int(job.seed),args.seconds)
                control=verify(result['routes'],ins) if result['routes'] else {'valid':False}
                refs,_=reference(ROOT/'data/instances'/(job.instance+'.sol'))
                ref=verify(refs,ins);assert ref['valid']
                value=control['duration']/10 if control['valid'] else None
                record=dict(instance=job.instance,n=int(job.n),seed=int(job.seed),valid=control['valid'],
                    baseline_delta_pct=float(job.delta_reference_pct),reference_duration=ref['duration']/10,
                    duration=value,delta_pct=100*(value/(ref['duration']/10)-1) if value is not None else None,
                    runtime_s=result['runtime_s'],requested_total_s=args.seconds,result=result,
                    scope='Targeted tuning; not substituted into the original catalogue')
            except Exception:
                record=dict(instance=job.instance,n=int(job.n),seed=int(job.seed),valid=False,
                    error=traceback.format_exc(),runtime_s=time.perf_counter()-start,
                    baseline_delta_pct=float(job.delta_reference_pct))
            path.write_text(json.dumps(record,indent=2),encoding='utf-8')
        row={k:v for k,v in record.items() if k not in ['result']}
        rows.append(row)
        pd.DataFrame(rows).to_csv(out/'summary.csv',index=False)
        print({k:row.get(k) for k in ['instance','seed','valid','baseline_delta_pct','delta_pct','runtime_s']},flush=True)
    print('Complete. Failures and regressions are preserved.',flush=True)


if __name__=='__main__':main()
