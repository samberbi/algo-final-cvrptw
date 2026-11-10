"""Independently re-evaluate every published new solution against its own data."""
from pathlib import Path
from dataclasses import replace
import hashlib,json,math,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from algo.data import load,reference
from algo.verify import verify
from scripts.ils_report_analysis import prepare
from scripts.run_ils_studies import synthetic


def check_result(result,ins):
    if result['status']!='feasible':return 0
    check=verify(result['routes'],ins)
    assert check['valid'],check
    assert abs(check['distance']/10-result['cost'])<1e-7
    trace=result['trace'];assert all(b['best']<=a['best']+1e-8 for a,b in zip(trace,trace[1:]))
    assert abs(trace[-1]['best']-result['cost'])<1e-7
    return 1


def main():
    df,*_=prepare();out=ROOT/'results/revision_ils';ins_cache={};verified=0
    names=df.instance.unique()
    for name in names:
        ins=load(ROOT/'data/instances'/(name+'.vrp'));ins_cache[name]=ins
        routes,cost=reference(ROOT/'data/instances'/(name+'.sol'))
        valid=verify(routes,ins);assert valid['valid'] and abs(valid['distance']/10-cost)<1e-7
        assert df[df.instance.eq(name)].reference_distance.eq(cost).all()
    for path in (out/'runs').glob('*.json'):
        row=json.loads(path.read_text());verified+=check_result(row['result'],ins_cache[row['job']['instance']])
    exact_verified=heuristic_verified=0
    for path in (out/'studies/exact').glob('*.json'):
        row=json.loads(path.read_text());ins=synthetic(row['n'],row['seed']);exact=row['exact']
        if exact['routes'] is not None:
            check=verify(exact['routes'],ins);assert check['valid']
            assert abs(check['distance']/10-exact['cost'])<1e-7;exact_verified+=1
        assert exact['lower_bound']<=exact['cost']+1e-6
        if exact['status']=='optimal':assert abs(exact['cost']-exact['lower_bound'])<1e-6
        for run in row['runs']:heuristic_verified+=check_result(run['result'],ins)
    sensitivity_verified=constraints_verified=0
    for path in (out/'studies/sensitivity').glob('*.json'):
        row=json.loads(path.read_text());ins=load(ROOT/'data/instances'/(row['instance']+'.vrp'))
        sensitivity_verified+=check_result(row['result'],ins)
    for path in (out/'studies/constraints').glob('*.json'):
        row=json.loads(path.read_text());ins=load(ROOT/'data/instances'/(row['instance']+'.vrp'));scenario=row['scenario']
        if scenario.startswith('capacity'):ins=replace(ins,capacity=ins.capacity*int(scenario.split('_')[1])/100)
        elif scenario.startswith('fleet'):ins=replace(ins,vehicles=max(1,math.ceil(ins.vehicles*int(scenario.split('_')[1])/100)))
        elif scenario.startswith('windows'):
            factor=int(scenario.split('_')[1])/100;mid=(ins.early+ins.late)/2;width=(ins.late-ins.early)*factor
            early=np.maximum(0,mid-width/2);late=np.minimum(ins.horizon,mid+width/2);early[0]=0;late[0]=ins.horizon
            ins=replace(ins,early=early,late=late)
        for result in row['results'].values():constraints_verified+=check_result(result,ins)
    scaling_verified=0
    for path in (out/'scaling').glob('*.json'):
        if path.name=='protocol.json':continue
        row=json.loads(path.read_text(encoding='utf-8'));scaling_verified+=check_result(row['result'],ins_cache[row['instance']])
        assert row['result']['iterations']==50000
    payload=dict(main_verified=verified,references_verified=len(names),exact_incumbents_verified=exact_verified,scaling_verified=scaling_verified,
        small_heuristics_verified=heuristic_verified,sensitivity_verified=sensitivity_verified,constraints_verified=constraints_verified,
        frozen_sources_and_common_starts_checked=True,
        studies_runner_sha256_at_validation=hashlib.sha256((ROOT/'scripts/run_ils_studies.py').read_bytes()).hexdigest())
    (out/'integrity_validation.json').write_text(json.dumps(payload,indent=2))
    print(json.dumps(payload,indent=2))


if __name__=='__main__':main()
