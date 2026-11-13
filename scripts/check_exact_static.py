"""Une tentative MILP limitée : garde aussi les bornes et absences d'incumbent."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from algo.static_small import load
from controle.plne import solve_plne


def main():
    p=argparse.ArgumentParser();p.add_argument('--instance',default='C101')
    p.add_argument('--seconds',type=float,default=10.);args=p.parse_args()
    target=ROOT/f'results/final_static/exact/{args.instance}_25_{args.seconds:g}s.json'
    if target.exists():raise SystemExit('Résultat conservé : '+str(target))
    path=ROOT/'data/static_small/n25'/(args.instance+'.txt')
    result=solve_plne(load(path),args.seconds,'duration')
    record=dict(instance=args.instance,n=25,budget_s=args.seconds,
        objective='sum returns, departures zero, DIMACS tenths',result=result,
        input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        model_sha256=hashlib.sha256((ROOT/'controle/plne.py').read_bytes()).hexdigest())
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['routes','metrics']},indent=2))


if __name__=='__main__':main()
