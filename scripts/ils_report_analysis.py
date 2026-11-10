"""Recompute all report statistics from the new measured runs, no old pooling."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
from algo.data import load
from algo.verify import verify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/revision_ils'


def prepare(require_complete=True):
    protocol=json.loads((OUT/'protocol.json').read_text())
    if require_complete:
        for relative,expected in protocol['sources'].items():
            assert hashlib.sha256((OUT/'source'/relative).read_bytes()).hexdigest()==expected,relative
        assert hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest()==protocol['manifest_sha256']
    records=[];rows=[];instances={};hashes={}
    for path in sorted((OUT/'runs').glob('*.json')):
        item=json.loads(path.read_text());job=item['job'];result=item['result'];name=job['instance']
        valid=False;gap=None
        if result['status']=='feasible':
            if name not in instances:instances[name]=load(ROOT/'data/instances'/(name+'.vrp'))
            check=verify(result['routes'],instances[name]);assert check['valid']
            assert abs(check['distance']/10-result['cost'])<1e-6
            valid=True;gap=100*(result['cost']/job['reference_distance']-1)
            assert abs(gap-item['gap_pct'])<1e-8
        rows.append(dict(instance=name,n=job['n'],seed=job['seed'],method=job['method'],
                         profile='ILS' if job['method']=='ils' else 'Recuit simulé',valid=valid,status=result['status'],
                         gap_pct=gap,distance=result.get('cost'),reference_distance=job['reference_distance'],
                         runtime_s=result['runtime_s'],shared_initial_s=item.get('shared_initial',{}).get('seconds'),
                         total_s=item.get('total_with_shared_initial_s'),initial_cost=result.get('initial_cost'),
                         iterations=result.get('iterations',0),cycles=result.get('cycles',0),
                         valid_proposals=result.get('valid_proposals',0),budget_s=job['seconds']))
        records.append(item);hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    df=pd.DataFrame(rows)
    assert not df.duplicated(['instance','seed','method']).any()
    if require_complete:
        expected={(j['instance'],j['seed'],m) for j in protocol['jobs'] for m in protocol['methods']}
        assert set(zip(df.instance,df.seed,df.method))==expected
        for job in protocol['jobs']:
            pair=[r for r in records if r['job']['id']==job['id']]
            assert len(pair)==2 and pair[0]['initial_routes_sha256']==pair[1]['initial_routes_sha256']
            initial=json.loads((OUT/'initials'/f"{job['id']:04d}.json").read_text())
            initial_check=verify(initial['routes'],instances[job['instance']]);assert initial_check['valid']
            assert all(abs(r['result']['initial_cost']-initial_check['distance']/10)<1e-7 for r in pair)
            assert hashlib.sha256(json.dumps(initial['routes']).encode()).hexdigest()==pair[0]['initial_routes_sha256']
    summary=df.groupby('profile').agg(runs=('valid','size'),valides=('valid','sum'),
        mean_gap=('gap_pct','mean'),median_gap=('gap_pct','median'),std_gap=('gap_pct','std'),
        worst_gap=('gap_pct','max'),under7=('gap_pct',lambda s:int(s.lt(7).sum())),
        mean_search_s=('runtime_s','mean'),mean_total_s=('total_s','mean')).reset_index()
    per_instance=df.groupby(['instance','n','profile']).agg(runs=('valid','size'),valides=('valid','sum'),
        mean_gap=('gap_pct','mean'),std_gap=('gap_pct','std'),worst_gap=('gap_pct','max'),
        best_distance=('distance','min'),mean_time=('runtime_s','mean')).reset_index()
    per_size=df.groupby(['n','profile']).agg(runs=('valid','size'),valides=('valid','sum'),mean_gap=('gap_pct','mean'),
        worst_gap=('gap_pct','max'),time=('runtime_s','mean'),construction=('shared_initial_s','mean'),total=('total_s','mean')).reset_index()
    paired=df.pivot(index=['instance','seed'],columns='method',values='gap_pct').dropna()
    difference=paired['ils']-paired['sa']
    # Bootstrap seed blocks, preserving the fixed benchmark set and pairing.
    seed_means=difference.groupby('seed').mean().values
    rng=np.random.default_rng(20261110)
    samples=seed_means[rng.integers(0,len(seed_means),size=(10000,len(seed_means)))].mean(axis=1)
    ci=np.quantile(samples,[.025,.975]).tolist()
    comparison=dict(paired_valid=len(paired),ils_lower=int((difference < -1e-8).sum()),ties=int((difference.abs()<=1e-8).sum()),
                    sa_lower=int((difference>1e-8).sum()),mean_difference_points=float(difference.mean()),
                    bootstrap_seed_block_95=ci,scope='Uncertainty across random seeds on this fixed known benchmark, not new geographies')
    payload=dict(complete=len(df)==protocol['runs'],runs=len(df),instances=int(df.instance.nunique()),summary=summary.to_dict('records'),
                 comparison=comparison,source_files_sha256=hashes,protocol_sha256=hashlib.sha256((OUT/'protocol.json').read_bytes()).hexdigest())
    (OUT/'flat.json').write_text(df.to_json(orient='records',indent=2,force_ascii=False),encoding='utf-8')
    (OUT/'summary.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    index=[dict(name=r['job']['instance'],seed=r['job']['seed'],profile='ILS' if r['job']['method']=='ils' else 'Recuit simulé',
                id=r['job']['id'],file=f"{r['job']['id']:04d}_{r['job']['instance']}_{r['job']['seed']}_{r['job']['method']}.json")
           for r in records if r['valid']]
    (OUT/'simulation_index.json').write_text(json.dumps(index,ensure_ascii=False),encoding='utf-8')
    df.to_csv(OUT/'runs.csv',index=False)
    per_instance.to_csv(OUT/'instances.csv',index=False)
    return df,summary,per_instance,per_size,records,payload


def study_tables():
    root=OUT/'studies'
    sensitivity=[]
    refs={r['instance']:r['reference_distance'] for r in json.loads((ROOT/'data/manifest.json').read_text())['reference_instances']}
    for p in sorted((root/'sensitivity').glob('*.json')):
        r=json.loads(p.read_text());result=r['result'];valid=result['status']=='feasible'
        sensitivity.append(dict(variant=r['variant'],instance=r['instance'],seed=r['seed'],valid=valid,
                                gap=100*(result['cost']/refs[r['instance']]-1) if valid else None,
                                runtime=result['runtime_s']))
    sensitivity=pd.DataFrame(sensitivity)
    sens=sensitivity.groupby('variant').agg(runs=('valid','size'),valides=('valid','sum'),gap=('gap','mean'),worst=('gap','max')).reset_index()
    constraints=[]
    for p in sorted((root/'constraints').glob('*.json')):
        r=json.loads(p.read_text())
        for method,result in r['results'].items():
            valid=result['status']=='feasible';metrics=result.get('metrics',{})
            constraints.append(dict(scenario=r['scenario'],method=method,instance=r['instance'],seed=r['seed'],valid=valid,
                status=result['status'],distance=result.get('cost'),waiting=metrics.get('waiting',np.nan)/10,
                duration=metrics.get('duration',np.nan)/10,vehicles=result.get('vehicles'),runtime=result['runtime_s']))
    constraints=pd.DataFrame(constraints)
    baseline=constraints[constraints.scenario.eq('original')][['instance','seed','method','distance','duration']].rename(columns={'distance':'base_distance','duration':'base_duration'})
    constraints=constraints.merge(baseline,on=['instance','seed','method'],how='left',validate='many_to_one')
    constraints['distance_change_pct']=100*(constraints.distance/constraints.base_distance-1)
    constraints['duration_change_pct']=100*(constraints.duration/constraints.base_duration-1)
    scenarios=constraints.groupby(['scenario','method']).agg(runs=('valid','size'),valides=('valid','sum'),
                   distance=('distance','mean'),waiting=('waiting','mean'),duration=('duration','mean'),
                   distance_change_pct=('distance_change_pct','mean'),duration_change_pct=('duration_change_pct','mean')).reset_index()
    exact=[];exact_runs=[]
    for p in sorted((root/'exact').glob('*.json')):
        r=json.loads(p.read_text());e=r['exact']
        exact.append(dict(n=r['n'],seed=r['seed'],status=e['status'],cost=e['cost'],bound=e['lower_bound'],time=e['runtime_s']))
        for run in r['runs']:
            exact_runs.append(dict(n=r['n'],instance_seed=r['seed'],method=run['method'],seed=run['seed'],
                                   optimal_gap=run['optimal_gap'],valid=run['result']['status']=='feasible'))
    return sens,scenarios,pd.DataFrame(exact),pd.DataFrame(exact_runs),constraints
