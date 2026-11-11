"""Solve without reading a BKS; references belong to reporting scripts only."""
from pathlib import Path
import argparse,json,time
from algo.data import load
from algo.solver import solve,Settings,warmup,production_settings
from algo.verify import verify


def main():
    p=argparse.ArgumentParser(description='CVRPTW : distance DIMACS, capacité et fenêtres strictes')
    p.add_argument('instance',help='Nom fourni, par exemple R202 ou R1_10_1, ou chemin .vrp')
    p.add_argument('--seconds',type=float,default=10.)
    p.add_argument('--seed',type=int,default=11)
    p.add_argument('--method', choices=['ils','sa'], default='ils')
    p.add_argument('--objective',choices=['distance'],default='distance')
    p.add_argument('--intensify',action='store_true',help='Ajoute cinq secondes dès 400 clients et une seconde passe à 1 000')
    p.add_argument('--output',default='results/solution.json')
    a=p.parse_args();root=Path(__file__).resolve().parent
    if a.intensify and a.objective!='distance':p.error('Intensification réservée à la distance')
    path=Path(a.instance)
    if not path.is_file():path=root/'data/instances'/(a.instance+'.vrp')
    ins=load(path);startup=warmup()
    result=solve(ins,production_settings(method=a.method,seconds=a.seconds,seed=a.seed))
    if a.intensify and ins.n>=400 and result['status']=='feasible':
        from ameliorations.decomposition import polish
        result['stages']=[]
        for offset in ([600000,700000] if ins.n==1000 else [600000]):
            improved=polish(ins,result['routes'],5.,a.seed+offset)
            result['stages'].append(dict(cost=improved['cost'],runtime_s=improved['runtime_s']))
            result.update(routes=improved['routes'],cost=improved['cost'],vehicles=improved['vehicles'],
                runtime_s=result['runtime_s']+improved['runtime_s'],metrics=verify(improved['routes'],ins))
    result['warmup_seconds']=startup
    target=root/a.output;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2))
    print(result['status'],'coût',result.get('cost'),'temps',round(result['runtime_s'],3),'s')
    print(target)


if __name__=='__main__':main()
