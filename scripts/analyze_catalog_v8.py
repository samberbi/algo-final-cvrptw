"""Full-catalog audit and explicit instance-weighted versus run-weighted gaps."""
from pathlib import Path
import hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from algo.data import load,reference
from algo.verify import verify

BASE=ROOT/'results/catalog_v8'


def summary(frame):
    """Do not turn failures into zero gaps or give repeated cases extra weight."""
    good=frame[frame.valid].copy()
    per=good.groupby('instance').gap_pct.mean()
    return dict(instances=int(frame.instance.nunique()),attempts=len(frame),valid=len(good),
        failures=int((~frame.valid).sum()),represented_instances=len(per),
        feasible_rate=float(frame.valid.mean()),mean_instance_gap=float(per.mean()) if len(per) else None,
        mean_run_gap=float(good.gap_pct.mean()) if len(good) else None,
        std_instance_gap=float(per.std(ddof=1)) if len(per)>1 else None,
        best_run_gap=float(good.gap_pct.min()) if len(good) else None,
        worst_run_gap=float(good.gap_pct.max()) if len(good) else None,
        runs_below_5=int((good.gap_pct<5).sum()),runs_below_6=int((good.gap_pct<6).sum()),
        instances_mean_below_6=int((per<6).sum()),
        mean_total_s=float(good.total_s.mean()) if len(good) else None)


def analyze(require_complete=True):
    protocol=json.loads((BASE/'protocol.json').read_text(encoding='utf-8'))
    manifest=json.loads((ROOT/'data/manifest.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest()==protocol['manifest_sha256']
    for name,sha in protocol['sources'].items():
        assert hashlib.sha256((BASE/'source'/name.replace('\\','/')).read_bytes()).hexdigest()==sha
    expected={(name,seed) for name,n,seed in protocol['job_order']}
    paths=sorted((BASE/'runs').glob('*.json'))
    rows=[];seen=set();last_name=None;checked_refs={}
    for path in paths:
        r=json.loads(path.read_text(encoding='utf-8'))
        key=(r['instance'],r['seed'])
        assert key in expected and key not in seen and r['complete']
        seen.add(key)
        name=r['instance']
        if name!=last_name:
            for suffix in ['.vrp','.sol']:
                p=ROOT/'data/instances'/(name+suffix)
                assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['files'][name+suffix]['sha256']
            ins=load(ROOT/'data/instances'/(name+'.vrp'))
            routes,bks=reference(ROOT/'data/instances'/(name+'.sol'))
            control=verify(routes,ins)
            assert control['valid'] and abs(control['distance']/10-bks)<1e-7
            checked_refs[name]=bks
            last_name=name
        row=dict(instance=name,n=ins.n,family=name.split('_')[0] if '_' in name else name.rstrip('0123456789')+name.lstrip('RC')[:1],
            seed=r['seed'],valid=r['valid'],reused=r['reused'],search_budget_s=r['search_budget_s'],
            total_s=r.get('total_s'),newly_executed_s=r.get('newly_executed_s'),
            reference_vehicles=control['vehicles'],fleet_limit=ins.vehicles,
            bks=bks,cost=None,vehicles=None,gap_pct=None,error=r.get('error',''),
            source=path.relative_to(ROOT).as_posix())
        if r['reused']:
            p=ROOT/r['origin'].replace('\\','/');assert hashlib.sha256(p.read_bytes()).hexdigest()==r['origin_sha256']
            prior=json.loads(p.read_text(encoding='utf-8'))
            assert prior['instance']==name and prior['seed']==r['seed']
            assert prior['result']['routes']==r['result']['routes']
            assert abs(prior['total_s']-r['total_s'])<1e-6
        if r['valid']:
            checked=verify(r['result']['routes'],ins)
            assert checked['valid'] and abs(checked['distance']/10-r['result']['cost'])<1e-7
            gap=100*(checked['distance']/10/bks-1)
            assert abs(gap-r['gap_pct'])<1e-7 and abs(r['reference_distance']-bks)<1e-7
            assert len(r['result']['components'])==2
            assert 'not by us' in r['result']['attribution']
            row.update(cost=checked['distance']/10,vehicles=checked['vehicles'],gap_pct=gap)
        else:
            assert r.get('error') or r.get('result',{}).get('status')!='feasible'
        rows.append(row)
    if require_complete:
        assert seen==expected,(len(seen),len(expected))
    df=pd.DataFrame(rows)
    assert not df.empty
    # Normalize the six Solomon family identifiers without changing any data.
    df['family']=df.instance.str.extract(r'^(RC[12]|C[12]|R[12])',expand=False)
    per=df.groupby(['instance','n','family'],as_index=False).agg(
        attempts=('valid','size'),valid=('valid','sum'),mean_gap=('gap_pct','mean'),
        std_gap=('gap_pct','std'),best_gap=('gap_pct','min'),worst_gap=('gap_pct','max'),
        bks=('bks','first'),mean_distance=('cost','mean'),best_distance=('cost','min'),mean_total_s=('total_s','mean'))
    assert np.allclose(100*(per.mean_distance.to_numpy(dtype=float)/per.bks.to_numpy(dtype=float)-1),
                       per.mean_gap.to_numpy(dtype=float),equal_nan=True)
    groups=[]
    for n,g in df.groupby('n'):
        groups.append(dict(n=int(n),**summary(g)))
    sizes=pd.DataFrame(groups)
    scopes=dict(catalog_356=summary(df),core_116=summary(df[df.n.isin([100,1000])]),
                common_seed_356=summary(df[df.seed.eq(2101)]))
    scopes['catalog_356']['balanced_size_gap']=float(sizes.mean_instance_gap.mean())
    core_sizes=sizes[sizes.n.isin([100,1000])]
    scopes['core_116']['balanced_size_gap']=float(core_sizes.mean_instance_gap.mean())
    analysis=dict(complete=seen==expected,planned=472,executed=len(df),
        new_pipelines=int((~df.reused).sum()),reused_pipelines=int(df.reused.sum()),
        distinct_instances=int(df.instance.nunique()),reference_revision=protocol['reference_revision'],
        scopes=scopes,total_new_runtime_s=float(df.newly_executed_s.sum()),
        total_charged_runtime_s=float(df.total_s.sum()),
        definitions=dict(primary_mean='Average of per-instance means; each instance weight 1',
            run_mean='Average of all valid pipeline gaps, which weights repeated instances more',
            size_balanced='Average of size-group means; a different weighting',
            failures='Counted separately; no artificial zero gap and no claim of full coverage if any fail',
            uncertainty='One seed on intermediate sizes; two seeds on 100/1000; dispersion is not a confidence interval'))
    df.to_csv(BASE/'flat.csv',index=False)
    per.to_csv(BASE/'instances.csv',index=False)
    sizes.to_csv(BASE/'sizes.csv',index=False)
    (BASE/'analysis.json').write_text(json.dumps(analysis,indent=2,allow_nan=False),encoding='utf-8')
    return df,per,sizes,analysis


if __name__=='__main__':
    _,_,sizes,analysis=analyze('--partial' not in sys.argv)
    print(json.dumps(analysis,indent=2))
    print(sizes.to_string(index=False))
