"""Recompute CVRPTW metrics from every real run, checking frozen provenance."""
from pathlib import Path
import hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from algo.data import load
from algo.verify import verify
BASE=ROOT/'results/optimization_v6'


def analyze(label):
    folder=BASE/label
    protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
    for relative,expected in protocol['sources'].items():
        assert hashlib.sha256((folder/'source'/relative).read_bytes()).hexdigest()==expected,relative
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    assert hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest()==protocol['manifest_sha256']
    refs={r['instance']:r for r in manifest['reference_instances']}
    expected={(n,s,v) for n in protocol['instances'] for s in protocol['seeds'] for v in protocol['variants']}
    found=set(); cases={}; rows=[]; hashes={}; initial_hashes={}
    for path in sorted((folder/'runs').glob('*.json')):
        r=json.loads(path.read_text(encoding='utf-8'))
        key=r['instance'],r['seed'],r['variant']
        assert key in expected and key not in found
        found.add(key)
        name,seed,variant=key
        if r.get('valid'):
            identity=hashlib.sha256(json.dumps(r['initial_routes']).encode()).hexdigest()
            previous=initial_hashes.setdefault((name,seed),identity)
            assert previous==identity,'Different initial route lists'
        hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        row=dict(instance=name,seed=seed,profile=variant,n=refs[name]['n'],valid=r.get('valid',False),
                 status='feasible' if r.get('valid') else 'error',budget_s=r['budget_s'])
        if r.get('valid'):
            if name not in cases:
                file=ROOT/'data/instances'/(name+'.vrp')
                assert hashlib.sha256(file.read_bytes()).hexdigest()==manifest['files'][file.name]['sha256']
                cases[name]=load(file)
            ins=cases[name]
            checked=verify(r['result']['routes'],ins)
            initial=verify(r['initial_routes'],ins)
            assert checked['valid'] and initial['valid']
            distance=checked['distance']/10
            assert abs(distance-r['result']['cost'])<1e-7
            assert distance<=initial['distance']/10+1e-7
            reference=refs[name]['reference_distance']
            gap=100*(distance/reference-1)
            assert abs(gap-r['gap_pct'])<1e-7
            if protocol['initial_folder']:
                source=ROOT/r['construction']['source']
                assert hashlib.sha256(source.read_bytes()).hexdigest()==r['construction']['sha256']
            row.update(distance=distance,reference_distance=reference,gap_pct=gap,
                       vehicles=checked['vehicles'],initial_cost=initial['distance']/10,
                       runtime_s=r['result']['runtime_s'],total_s=r['total_s'],
                       cycles=r['result'].get('cycles',0),
                       proposals=r['result'].get('iterations',0),
                       previous_effort_s=r['construction'].get('previous_total_effort_s',0),
                       charged_total_s=r['total_s']+r['construction'].get('previous_total_effort_s',0))
        rows.append(row)
    assert found==expected,expected-found
    df=pd.DataFrame(rows)
    new_runs=len(df)
    reused_reference_runs=0
    if protocol.get('reference_label'):
        reference,_,_,_=analyze(protocol['reference_label'])
        reference=reference[reference.profile.eq('baseline')].copy()
        assert set(zip(reference.instance,reference.seed))==set(initial_hashes)
        for _,row in reference.iterrows():
            source=BASE/protocol['reference_label']/'runs'/f'{row.instance}_{int(row.seed)}_baseline.json'
            r=json.loads(source.read_text(encoding='utf-8'))
            assert hashlib.sha256(json.dumps(r['initial_routes']).encode()).hexdigest()==initial_hashes[(row.instance,int(row.seed))]
        reused_reference_runs=len(reference)
        reference['reused_reference']=True
        df['reused_reference']=False
        df=pd.concat([df,reference],ignore_index=True)
    assert df.valid.all(),'Failed runs retained in raw files; report their failure before any success-only mean'
    assert df.groupby(['instance','seed']).initial_cost.nunique().max()==1
    summary=df.groupby('profile').agg(runs=('valid','size'),feasible=('valid','sum'),
        mean_gap=('gap_pct','mean'),std_gap=('gap_pct','std'),median_gap=('gap_pct','median'),
        worst_gap=('gap_pct','max'),best_gap=('gap_pct','min'),
        under5=('gap_pct',lambda x:int((x<5).sum())),under6=('gap_pct',lambda x:int((x<6).sum())),
        under7=('gap_pct',lambda x:int((x<7).sum())),mean_search_s=('runtime_s','mean'),
        mean_total_s=('total_s','mean'),mean_cycles=('cycles','mean'),
        mean_proposals=('proposals','mean')).reset_index()
    cases=df.groupby(['instance','profile']).agg(mean_gap=('gap_pct','mean'),std_gap=('gap_pct','std'),
        best_gap=('gap_pct','min'),worst_gap=('gap_pct','max'),mean_distance=('distance','mean'),
        reference_distance=('reference_distance','first')).reset_index()
    paired=df.pivot(index=['instance','seed'],columns='profile',values='gap_pct')
    comparisons=[]
    for v in sorted(df.profile.unique()):
        if v=='baseline':continue
        delta=paired['baseline']-paired[v]
        percase=delta.groupby(level=0).mean().to_numpy()
        samples=np.random.default_rng(20261112).choice(percase,(10000,len(percase))).mean(axis=1)
        comparisons.append(dict(variant=v,improvement_pp=float(delta.mean()),wins=int((delta>1e-8).sum()),
                                losses=int((delta<-1e-8).sum()),
                                instance_bootstrap95=list(map(float,np.quantile(samples,[.025,.975])))))
    df.to_csv(folder/'flat.csv',index=False); summary.to_csv(folder/'summary.csv',index=False)
    cases.to_csv(folder/'instances.csv',index=False)
    paired.to_csv(folder/'paired.csv')
    payload=dict(runs=len(df),new_runs=new_runs,reused_reference_runs=reused_reference_runs,
                 instances=len(protocol['instances']),seeds=protocol['seeds'],
                 summary=summary.to_dict('records'),comparisons=comparisons,raw_sha256=hashes)
    (folder/'analysis.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    return df,summary,cases,payload


if __name__=='__main__':
    for label in sys.argv[1:] or ['development','validation','targeted_120']:
        _,summary,_,data=analyze(label)
        print(label);print(summary.to_string(index=False));print(json.dumps(data['comparisons']))
