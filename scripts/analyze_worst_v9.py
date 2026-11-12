"""Audit measured hard-case trials; no missing run can be treated as a success."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from algo.data import load,reference
from algo.verify import verify

BASE=ROOT/'results/worst_v9'


def recovery(label='recovery180'):
    folder=BASE/label;p=json.loads((folder/'protocol.json').read_text())
    for name,sha in p['sources'].items():
        assert hashlib.sha256((folder/'source'/name.replace('\\','/')).read_bytes()).hexdigest()==sha
    records=[]
    for path in sorted((folder/'runs').glob('*.json')):
        r=json.loads(path.read_text());assert r['complete']
        source=ROOT/r['source'].replace('\\','/')
        assert r['source'] in p['origins']
        assert hashlib.sha256(source.read_bytes()).hexdigest()==r['source_sha256']==p['origins'][r['source']]
        prior=json.loads(source.read_text());assert prior['valid']
        assert (prior['instance'],prior['seed'])==(r['instance'],r['seed'])
        assert abs(r['previous_gap']-prior['gap_pct'])<1e-7
        assert r['valid'],r.get('error')
        ins=load(ROOT/'data/instances'/(r['instance']+'.vrp'))
        check=verify(r['result']['routes'],ins)
        assert check['valid'] and abs(check['distance']/10-r['result']['cost'])<1e-7
        assert r['result']['cost']<=prior['result']['cost']+1e-7
        assert abs(r['gap_pct']-100*(r['result']['cost']/r['reference_distance']-1))<1e-7
        assert abs(r['total_effort_s']-r['previous_total_s']-r['additional_runtime_s'])<1e-6
        assert abs(r['additional_runtime_s']-r['result']['runtime_s'])<1e-6
        records.append(dict(instance=r['instance'],seed=r['seed'],before=r['previous_gap'],
            after=r['gap_pct'],old_cost=r['previous_cost'],new_cost=r['result']['cost'],
            vehicles=check['vehicles'],source=path.relative_to(ROOT).as_posix(),
            previous_total_s=r['previous_total_s'],additional_s=r['additional_runtime_s'],
            total_s=r['total_effort_s']))
    assert len(records)==len(p['origins'])
    data=pd.DataFrame(records)
    data.to_csv(folder/'summary.csv',index=False)
    return data


def archive():
    from scripts.analyze_catalog_v8 import summary
    updates=recovery()
    baseline=pd.read_csv(ROOT/'results/catalog_v8/flat.csv')
    selected=baseline[baseline.valid&baseline.gap_pct.ge(7)]
    assert set(zip(selected.instance,selected.seed))==set(zip(updates.instance,updates.seed))
    d=baseline.copy().set_index(['instance','seed'])
    d['baseline_gap_pct']=d.gap_pct;d['baseline_cost']=d.cost;d['baseline_total_s']=d.total_s
    d['extra_runtime_s']=0.;d['recovery_source']=''
    for row in updates.itertuples():
        key=(row.instance,row.seed)
        assert abs(d.at[key,'gap_pct']-row.before)<1e-7
        assert abs(d.at[key,'total_s']-row.previous_total_s)<1e-6
        d.at[key,'gap_pct']=row.after;d.at[key,'cost']=row.new_cost;d.at[key,'vehicles']=row.vehicles
        d.at[key,'total_s']=row.total_s;d.at[key,'extra_runtime_s']=row.additional_s
        d.at[key,'recovery_source']=row.source
    d=d.reset_index();out=BASE/'updated_archive';out.mkdir(exist_ok=True)
    d.to_csv(out/'flat.csv',index=False)
    cases=d.groupby(['instance','n'],as_index=False).agg(attempts=('valid','size'),valid=('valid','sum'),
        mean_gap=('gap_pct','mean'),worst_gap=('gap_pct','max'),mean_total_s=('total_s','mean'),
        baseline_mean_gap=('baseline_gap_pct','mean'))
    cases.to_csv(out/'instances.csv',index=False)
    info=dict(scope='Mixed-budget archive after ten targeted continuations; not a new 120s catalog',
        attempts=len(d),instances=d.instance.nunique(),changed_trials=len(updates),
        baseline_max=float(baseline.gap_pct.max()),maximum=float(d.gap_pct.max()),
        additional_seconds=float(updates.additional_s.sum()),all_observed_under7=bool(d.gap_pct.lt(7).all()),
        summary=summary(d),large_summary=summary(d[d.n.eq(1000)]))
    (out/'analysis.json').write_text(json.dumps(info,indent=2))
    return d,cases,info


def restarts():
    folder=BASE/'restarts360';p=json.loads((folder/'protocol.json').read_text())
    for name,sha in p['sources'].items():
        assert hashlib.sha256((folder/'source'/name.replace('\\','/')).read_bytes()).hexdigest()==sha
    records=[]
    for path in sorted((folder/'runs').glob('*.json')):
        r=json.loads(path.read_text());assert r['complete'] and r['valid'],r.get('error')
        ins=load(ROOT/'data/instances'/(r['instance']+'.vrp'))
        check=verify(r['result']['routes'],ins)
        assert check['valid'] and abs(check['distance']/10-r['result']['cost'])<1e-7
        assert r['result']['cost']<=min(c['cost'] for c in r['components'])+1e-7
        assert len(r['components'])==(1 if r['strategy']=='long' else 3)
        assert sum(c['search_budget_s'] for c in r['components'])==360.
        for component in r['components']:
            verified=verify(component['routes'],ins)
            assert verified['valid'] and abs(verified['distance']/10-component['cost'])<1e-7
        assert abs(r['total_s']-sum(c['runtime_s'] for c in r['components'])-r['pool_preparation_s']-r['result']['runtime_s'])<1e-6
        assert abs(r['gap_pct']-100*(r['result']['cost']/r['reference_distance']-1))<1e-7
        records.append(dict(instance=r['instance'],strategy=r['strategy'],
            before_pool=r['best_input_gap'],gap_pct=r['gap_pct'],
            pool_gain_pp=r['best_input_gap']-r['gap_pct'],total_s=r['total_s']))
    assert len(records)==6 and {(r['instance'],r['strategy']) for r in records}=={
        (n,s) for n in p['instances'] for s in p['strategies']}
    df=pd.DataFrame(records);df.to_csv(folder/'flat.csv',index=False)
    return df


def analyze(label):
    folder=BASE/label;p=json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
    for name,sha in p['sources'].items():
        assert hashlib.sha256((folder/'source'/name.replace('\\','/')).read_bytes()).hexdigest()==sha
    assert hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest()==p['manifest_sha256']
    expected={(n,s,v) for n in p['instances'] for s in p['seeds'] for v in p['variants']}
    seen=set();rows=[];cache={}
    for path in sorted((folder/'runs').glob('*.json')):
        r=json.loads(path.read_text());key=(r['instance'],r['seed'],r['variant'])
        assert r['complete'] and key in expected and key not in seen;seen.add(key)
        if r['instance'] not in cache:
            ins=load(ROOT/'data/instances'/(r['instance']+'.vrp'))
            routes,bks=reference(ROOT/'data/instances'/(r['instance']+'.sol'))
            check=verify(routes,ins);assert check['valid'] and abs(check['distance']/10-bks)<1e-7
            cache[r['instance']]=(ins,bks)
        ins,bks=cache[r['instance']]
        row=dict(instance=r['instance'],seed=r['seed'],variant=r['variant'],valid=r['valid'],
            gap_pct=None,cost=None,vehicles=None,total_s=r.get('total_s'),
            source=path.relative_to(ROOT).as_posix(),error=r.get('error',''))
        if r['valid']:
            checked=verify(r['result']['routes'],ins);assert checked['valid']
            cost=checked['distance']/10;gap=100*(cost/bks-1)
            assert abs(cost-r['result']['cost'])<1e-7 and abs(gap-r['gap_pct'])<1e-7
            assert cost<=r['first_phase']['cost']+1e-7
            assert r['search_budget_s']==sum(p['variants'][r['variant']][:2])
            assert abs(r['total_s']-r['construction']['seconds']-r['first_phase']['runtime_s']-r['result']['runtime_s'])<1e-6
            trace=r['result']['trace']
            assert all(b['best']<=a['best']+1e-6 for a,b in zip(trace,trace[1:]))
            row.update(gap_pct=gap,cost=cost,vehicles=checked['vehicles'],iterations=r['result']['iterations'])
        rows.append(row)
    assert seen==expected,(label,len(seen),len(expected))
    df=pd.DataFrame(rows)
    summary=df.groupby('variant',as_index=False).agg(runs=('valid','size'),valid=('valid','sum'),
        mean_gap=('gap_pct','mean'),worst_gap=('gap_pct','max'),mean_total_s=('total_s','mean'))
    summary['under7']=summary.variant.map(df[df.valid&df.gap_pct.lt(7)].groupby('variant').size()).fillna(0).astype(int)
    pairs=df[df.valid].pivot(index=['instance','seed'],columns='variant',values='gap_pct')
    comparisons=[]
    if 'split60' in pairs:
        for v in p['variants']:
            if v=='split60' or v not in pairs:continue
            pair=pairs[['split60',v]].dropna();delta=pair.split60-pair[v]
            comparisons.append(dict(variant=v,pairs=len(pair),mean_gain_pp=float(delta.mean()),
                wins=int((delta>1e-8).sum()),losses=int((delta<-1e-8).sum())))
    df.to_csv(folder/'flat.csv',index=False);summary.to_csv(folder/'summary.csv',index=False)
    (folder/'analysis.json').write_text(json.dumps(dict(complete=True,runs=len(df),comparisons=comparisons,
        scope='Post-hoc difficult cases, new seeds, equal 120s search; all runs retained'),indent=2))
    return df,summary,comparisons


if __name__=='__main__':
    for label in sys.argv[1:]:
        _,summary,comparisons=analyze(label)
        print(label);print(summary.to_string(index=False));print(json.dumps(comparisons))
