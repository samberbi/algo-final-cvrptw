"""Prolonge seulement les nouveaux essais encore au-dessus du seuil.

Le temps de la solution de départ est inclus dans le cumul. Budget et sélection
sont explicitement différents d'une campagne indépendante à dix secondes.
"""
from pathlib import Path
import argparse,hashlib,json,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
from algo.data import load,reference
from algo.verify import verify
from algo.hgs_tuning import solve


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',default='outliers10')
    p.add_argument('--tag',default='outliers_hgs30');p.add_argument('--seconds',type=float,default=30)
    p.add_argument('--neighbors',type=int,default=80)
    p.add_argument('--threshold',type=float,default=6.)
    p.add_argument('--seed-offset',type=int,default=30000)
    args=p.parse_args()
    source=ROOT/'results/time_objective'/args.source
    output=ROOT/'results/time_objective'/args.tag;(output/'runs').mkdir(parents=True,exist_ok=True)
    jobs=pd.read_csv(source/'summary.csv')
    jobs=jobs[jobs.valid & jobs.delta_pct.gt(args.threshold)]
    protocol=dict(objective='duration',departures=0,additional_search_s=args.seconds,neighbors=args.neighbors,
                  parent_campaign=args.source,selection=f'Parent trials with delta > +{args.threshold}%',
                  seed_offset=args.seed_offset,
                  jobs=[(r.instance,int(r.seed)) for r in jobs.itertuples()],scope='Targeted continuation; cumulative time reported')
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    # Une nouvelle campagne conserve sa propre version des sources ; les
    # instantanés des campagnes précédentes ne sont jamais remplacés.
    for source_path in [*sorted((ROOT/'algo').glob('*.py')),Path(__file__)]:
        relative=source_path.relative_to(ROOT)
        frozen=output/'source'/relative
        frozen.parent.mkdir(parents=True,exist_ok=True)
        if not frozen.exists():frozen.write_bytes(source_path.read_bytes())
    rows=[]
    for job in jobs.itertuples():
        path=output/'runs'/f'{job.instance}_{job.seed}.json'
        if path.exists():record=json.loads(path.read_text())
        else:
            parent_path=source/'runs'/path.name;parent=json.loads(parent_path.read_text())
            start=time.perf_counter()
            try:
                ins=load(ROOT/'data/instances'/(job.instance+'.vrp'))
                result=solve(ins,args.seconds,int(job.seed)+args.seed_offset,parent['result']['routes'],args.neighbors,objective='duration')
                checked=verify(result['routes'],ins);assert checked['valid']
                refs,_=reference(ROOT/'data/instances'/(job.instance+'.sol'))
                ref=verify(refs,ins);assert ref['valid']
                elapsed=result['runtime_s']
                record=dict(instance=job.instance,n=int(job.n),seed=int(job.seed),valid=True,
                    baseline_delta_pct=float(job.baseline_delta_pct),parent_delta_pct=float(job.delta_pct),
                    delta_pct=100*(checked['duration']/ref['duration']-1),duration=checked['duration']/10,
                    reference_duration=ref['duration']/10,additional_runtime_s=elapsed,
                    runtime_s=float(parent['runtime_s'])+elapsed,result=result,
                    parent_source=parent_path.relative_to(ROOT).as_posix(),scope='Targeted continuation; includes parent computation time')
            except Exception:
                record=dict(instance=job.instance,n=int(job.n),seed=int(job.seed),valid=False,
                    error=traceback.format_exc(),runtime_s=float(parent['runtime_s'])+time.perf_counter()-start,
                    parent_source=parent_path.relative_to(ROOT).as_posix())
            path.write_text(json.dumps(record,indent=2),encoding='utf-8')
        row={k:v for k,v in record.items() if k!='result'};rows.append(row)
        pd.DataFrame(rows).to_csv(output/'summary.csv',index=False)
        print({k:row.get(k) for k in ['instance','seed','valid','parent_delta_pct','delta_pct','runtime_s']},flush=True)
    if not len(jobs):print(f'No parent trial exceeds +{args.threshold}%.',flush=True)


if __name__=='__main__':main()
