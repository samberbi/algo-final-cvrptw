"""Continue one measured feasible JSON solution with all prior effort retained."""
from pathlib import Path
import argparse,hashlib,json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from algo.data import load
from algo.hgs_tuning import solve
from algo.verify import verify


if __name__=='__main__':
    p=argparse.ArgumentParser(description='Reprise HGS externe attribuée, depuis une solution complète')
    p.add_argument('input');p.add_argument('--instance');p.add_argument('--seconds',type=float,default=180.)
    p.add_argument('--neighbors',type=int,default=40);p.add_argument('--seed',type=int);p.add_argument('--output')
    a=p.parse_args();source=Path(a.input).resolve();prior=json.loads(source.read_text(encoding='utf-8'))
    name=a.instance or prior.get('instance')
    manifest=json.loads((ROOT/'data/manifest.json').read_text(encoding='utf-8'))
    if name not in {r['instance'] for r in manifest['reference_instances']}:p.error('Indiquer une instance du catalogue')
    old=prior.get('result',prior);ins=load(ROOT/'data/instances'/(name+'.vrp'))
    check=verify(old['routes'],ins)
    if not check['valid']:p.error('La solution initiale ne respecte pas les contraintes')
    seed=a.seed if a.seed is not None else prior.get('seed',0)+20000
    result=solve(ins,a.seconds,seed,old['routes'],a.neighbors)
    previous_time=prior.get('total_effort_s',prior.get('total_s',old.get('runtime_s')))
    if previous_time is None:raise ValueError('Le temps du calcul initial doit être renseigné')
    bks=next(r['reference_distance'] for r in manifest['reference_instances'] if r['instance']==name)
    record=dict(instance=name,seed=seed,source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        result=result,previous_cost=check['distance']/10,previous_total_s=previous_time,
        total_effort_s=previous_time+result['runtime_s'],reference_distance=bks,
        previous_gap=100*(check['distance']/10/bks-1),gap_pct=100*(result['cost']/bks-1),
        note='Extra-budget continuation, not a new cold solve')
    output=Path(a.output) if a.output else ROOT/'results/worst_v9/manual'/f'{time.time_ns()}_{name}.json'
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(dict(instance=name,before=record['previous_gap'],after=record['gap_pct'],
        additional_s=result['runtime_s'],total_s=record['total_effort_s'],output=str(output)),indent=2))
