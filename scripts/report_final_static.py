"""Tableaux reproductibles du pilote ; références jamais issues de nos résultats."""
from pathlib import Path
import argparse
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
import numpy as np
from scipy.sparse.csgraph import minimum_spanning_tree
from algo.static_small import load as load_small
from algo.data import load as load_full


def report(folder):
    folder=Path(folder).resolve()
    records=[json.loads(p.read_text(encoding='utf-8'))|{'source':p.relative_to(ROOT).as_posix()}
             for p in sorted((folder/'runs').glob('*.json'))]
    refs={}
    for record in records:
        result=record['result'];key=(record['instance'],record['n'])
        if record['method']=='ortools' and result.get('metrics',{}).get('valid'):
            old=refs.get(key)
            if old is None or result['cost']<old['result']['cost']:refs[key]=record
    rows=[]
    bounds={}
    for record in records:
        result=record['result'];m=result.get('metrics',{});ref=refs.get((record['instance'],record['n']))
        valid=bool(m.get('valid',False));cost=result.get('cost')
        reference_cost=ref['result']['cost'] if ref else None
        own=record['method']!='ortools'
        delta=100*(cost/reference_cost-1) if valid and ref and own else None
        public=record.get('public_plan_duration')
        key=(record['instance'],record['n'])
        if key not in bounds:
            name,n=key
            ins=(load_small(ROOT/f'data/static_small/n{n}'/(name+'.txt')) if n in [25,50]
                 else load_full(ROOT/'data/instances'/(name+'.vrp')))
            # +1 conserve les vrais arcs nuls ; un arbre contient exactement n arcs.
            shifted=np.array(ins.travel+1,copy=True);np.fill_diagonal(shifted,0)
            bounds[key]=(float(minimum_spanning_tree(shifted).sum())-ins.n+float(ins.service.sum()))/10
        lower=bounds[key]
        row={k:record[k] for k in ['instance','n','family','method','seed','budget_s','wall_s','cpu_s','source']}
        row.update(status=result['status'],valid=valid,vehicles=m.get('vehicles'),duration=cost,
            travel=m.get('travel',0)/10 if valid else None,waiting=m.get('waiting',0)/10 if valid else None,
            service=(m.get('duration',0)-m.get('travel',0)-m.get('waiting',0))/10 if valid else None,
            independent_reference=reference_cost,reference_status='Independent feasible OR-Tools, not proven optimum' if ref else 'Missing independent reference',
            reference_source=ref['source'] if ref else None,delta_independent_pct=delta,
            public_duration=public,delta_public_pct=100*(cost/public-1) if valid and public else None,
            partition_gain=result.get('partition_gain'),partition_columns=result.get('pool_columns'),
            own_ils_gain=result.get('own_ils_gain'),
            lower_bound=lower,lower_bound_kind='Service plus MST: valid but potentially weak',
            upper_bound_gap_pct=100*(cost/lower-1) if valid and lower>0 else None,
            certified_gap_pct=None,above_6=bool(delta>6) if delta is not None else None,
            cpu_above_120=record['cpu_s']>120,wall_overrun_s=max(0,record['wall_s']-record['budget_s']))
        rows.append(row)
    frame=pd.DataFrame(rows)
    frame.to_csv(folder/'RESULTATS.csv',index=False,encoding='utf-8-sig')
    stats=frame.groupby(['instance','n','method'],dropna=False).agg(
        attempts=('valid','size'),feasible=('valid','sum'),mean_duration=('duration','mean'),
        std_duration=('duration',lambda x:x.std(ddof=0)),best_duration=('duration','min'),
        mean_delta=('delta_independent_pct','mean'),worst_delta=('delta_independent_pct','max'),
        mean_wall_s=('wall_s','mean'),max_cpu_s=('cpu_s','max')).reset_index()
    stats.to_csv(folder/'STATISTIQUES.csv',index=False,encoding='utf-8-sig')
    summary=dict(resolutions=len(frame),instances=len(frame[['instance','n']].drop_duplicates()),
        feasible=int(frame.valid.sum()),failed=int((~frame.valid).sum()),
        independent_reference_instances=len(refs),signed_comparisons=int(frame.delta_independent_pct.notna().sum()),
        above_6=int(frame.above_6.eq(True).sum()),negative=int(frame.delta_independent_pct.lt(0).sum()),
        max_cpu_s=float(frame.cpu_s.max()),max_wall_s=float(frame.wall_s.max()),
        limitation='Small development pilot; OR-Tools is a feasible comparator, not a proven optimum. Search budgets and total runtimes differ explicitly. No global under-6 claim.')
    (folder/'BILAN.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)
    print(frame[['instance','n','method','seed','duration','independent_reference','delta_independent_pct','valid','wall_s']].to_string(index=False),flush=True)
    return frame,stats,summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);args=p.parse_args()
    report(ROOT/'results/final_static'/args.label)
