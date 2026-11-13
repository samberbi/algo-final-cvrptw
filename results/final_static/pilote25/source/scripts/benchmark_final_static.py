"""Petites campagnes statiques reprenables ; sauvegarde après chaque résolution."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from algo.data import load as load_full, reference
from algo.static_small import load as load_small
from algo.verify import verify
METHODS=['construction','ils','sa','pyvrp','hybrid','refined','refined_no_partition','ortools']


def evaluate(method,ins,seed,seconds,reference_seconds):
    from algo.duration import construct,solve,Settings
    if method=='construction':
        routes,info=construct(ins,seed)
        return dict(status='feasible' if routes is not None else 'not_found',routes=routes,construction=info,
                    attribution='Own regret-2 construction, best of 12 attempts by total duration')
    if method in ['ils','sa','hybrid']:
        return solve(ins,Settings(seconds=seconds,seed=seed,method=method))
    if method=='pyvrp':
        from algo.pyvrp_standalone_duration import solve as external
        return external(ins,seconds,seed)
    if method.startswith('refined'):
        from algo.refined_ablation import solve as refined
        return refined(ins,seed,seconds,partition=method=='refined')
    from algo.ortools_duration import solve as independent
    return independent(ins,reference_seconds,seed)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases',nargs='+',default=['C101:25','R101:25','RC201:25'])
    p.add_argument('--seeds',nargs='+',type=int,default=[4101])
    p.add_argument('--methods',nargs='+',choices=METHODS,default=METHODS)
    p.add_argument('--seconds',type=float,default=3)
    p.add_argument('--reference-seconds',type=float,default=10)
    p.add_argument('--label',required=True)
    args=p.parse_args()
    if args.seconds<=0 or args.reference_seconds<=0:p.error('Budgets positifs requis')
    if Path(args.label).name!=args.label or args.label in ['.','..']:p.error('Label simple requis')
    folder=ROOT/'results/final_static'/args.label;folder.mkdir(parents=True,exist_ok=True)
    (folder/'runs').mkdir(exist_ok=True)
    cases=[]
    for case in args.cases:
        name,n=case.split(':');n=int(n)
        path=(ROOT/f'data/static_small/n{n}'/(name+'.txt') if n in [25,50]
              else ROOT/'data/instances'/(name+'.vrp'))
        ins=load_small(path) if n in [25,50] else load_full(path)
        if ins.n!=n:raise ValueError('Taille annoncée incorrecte : '+case)
        cases.append((case,path,ins))
    config=vars(args)
    protocol_path=folder/'protocol.json'
    if protocol_path.exists():
        old=json.loads(protocol_path.read_text())
        if old['config']!=config:raise ValueError('Label déjà associé à un protocole différent')
        for rel,digest in old['sources'].items():
            if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=digest:
                raise ValueError('Code modifié depuis ce lot : nouveau label requis ('+rel+')')
    else:
        sources={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in list((ROOT/'algo').glob('*.py'))+[Path(__file__).resolve()]}
        protocol=dict(config=config,python=platform.python_version(),platform=platform.platform(),
            pyvrp=importlib.metadata.version('pyvrp'),ortools=importlib.metadata.version('ortools'),
            instance_hashes={case:hashlib.sha256(path.read_bytes()).hexdigest() for case,path,_ in cases},
            sources=sources,workers=1,reference='Independent OR-Tools feasible duration solution, not optimum',
            budget='Search seconds plus construction/setup for ILS/SA/hybrid/PyVRP; soft total seconds for refined; wall/CPU measured separately',
            exclusions='Warmup excluded from per-run timers; source validation and loading excluded; no BKS enters search')
        protocol_path.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
        source_folder=folder/'source'
        for rel in sources:
            target=source_folder/rel;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((ROOT/rel).read_bytes())
    # Préchauffage explicite, avant les chronomètres, pour chaque reprise.
    from algo.duration import warmup
    from algo.savings import savings_construct
    from algo.sequential import sequential_insert
    from algo.iterated import arrays
    warmup()
    small=load_small(ROOT/'data/static_small/n25/C101.txt')
    savings_construct(*arrays(small),small.vehicles,1,0.)
    sequential_insert(*arrays(small),small.vehicles,1,1.,.5,0)
    for case,path,ins in cases:
        for seed in args.seeds:
            for method in args.methods:
                target=folder/'runs'/f'{ins.name}_{ins.n}_{method}_{seed}.json'
                if target.exists():
                    print('Conservé : '+target.name,flush=True);continue
                started,cpu=time.perf_counter(),time.process_time()
                try:
                    result=evaluate(method,ins,seed,args.seconds,args.reference_seconds)
                    if result.get('routes') is not None:
                        metrics=verify(result['routes'],ins)
                        if not metrics['valid']:raise AssertionError(metrics['errors'])
                        result.update(metrics=metrics,cost=metrics['duration']/10)
                except Exception as error:
                    result=dict(status='error',routes=None,error=repr(error))
                record=dict(instance=ins.name,n=ins.n,family='RC' if ins.name.startswith('RC') else ins.name[0],
                    seed=seed,method=method,wall_s=time.perf_counter()-started,cpu_s=time.process_time()-cpu,
                    budget_s=args.reference_seconds if method=='ortools' else args.seconds,
                    result=result,reference_not_in_search=True)
                public=ROOT/'data/instances'/(ins.name+'.sol')
                if ins.n>=100 and public.exists():
                    routes,_=reference(public);checked=verify(routes,ins)
                    if checked['valid']:record['public_plan_duration']=checked['duration']/10
                target.write_text(json.dumps(record,indent=2,allow_nan=False),encoding='utf-8')
                print(f"{case} | {method} | graine {seed} | {result['status']} | "
                      f"durée {result.get('cost')} | {record['wall_s']:.3f} s | CPU {record['cpu_s']:.3f} s",flush=True)
    from scripts.report_final_static import report
    report(folder)


if __name__=='__main__':main()
