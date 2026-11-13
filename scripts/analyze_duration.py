"""Statistiques descriptives en durée, sans inventer de BKS temporelle."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from scipy.sparse.csgraph import minimum_spanning_tree
from algo.data import load,reference
from algo.verify import verify

BASE=ROOT/'results/time_objective/catalogue'
QUANTILES=[.025,.1,.25,.3,.5,.7,.75,.9,.975]


def describe(series):
    """Convention descriptive : variance/covariance divisées par N, quantiles linéaires."""
    s=pd.Series(series).dropna();q=s.quantile(QUANTILES)
    modes=s.mode().tolist()
    mode='aucun mode distinct' if len(s) and s.value_counts().max()==1 else (';'.join(map(str,modes)) if len(modes)<=5 else f'{len(modes)} modes ex aequo')
    return dict(n=len(s),mean=s.mean(),median=s.median(),mode=mode,
                variance=s.var(ddof=0),std=s.std(ddof=0),minimum=s.min(),maximum=s.max(),
                range=s.max()-s.min(),iqr=q.loc[.75]-q.loc[.25],
                **{f'q{v:g}':float(q.loc[v]) for v in QUANTILES})


def analyze(require_complete=True):
    protocol=json.loads((BASE/'protocol.json').read_text())
    assert protocol['objective']=='sum_route_duration' and protocol['departures']==0
    assert hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest()==protocol['manifest_sha256']
    for name,sha in protocol['sources'].items():
        assert hashlib.sha256((BASE/'source'/name.replace('\\','/')).read_bytes()).hexdigest()==sha,name
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    expected={(j[0],j[1],j[2]) for j in protocol['jobs']}
    seen=set();rows=[];cache={}
    for path in sorted((BASE/'runs').glob('*.json')):
        r=json.loads(path.read_text());key=(r['instance'],r['seed'],r['method'])
        assert r['complete'] and key in expected and key not in seen;seen.add(key)
        assert r['objective']=='sum_route_duration' and r['reference_kind']=='duration_of_distance_BKS_plan'
        name=r['instance']
        if name not in cache:
            for ext in ['.vrp','.sol']:
                p=ROOT/'data/instances'/(name+ext)
                assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['files'][p.name]['sha256']
            ins=load(ROOT/'data/instances'/(name+'.vrp'))
            ref_routes,ref_distance=reference(ROOT/'data/instances'/(name+'.sol'))
            checked=verify(ref_routes,ins)
            assert checked['valid'] and abs(checked['distance']/10-ref_distance)<1e-7
            # +1 traite correctement les vrais arcs de temps nul, ignorés sinon par SciPy.
            shifted=np.array(ins.travel+1,copy=True);np.fill_diagonal(shifted,0.)
            mst=minimum_spanning_tree(shifted).sum()-ins.n
            lower=(float(mst)+float(ins.service.sum()))/10
            cache[name]=(ins,checked['duration']/10,lower)
        ins,ref_time,lower=cache[name]
        row=dict(instance=name,n=ins.n,seed=r['seed'],method=r['method'],core=r['core'],
                 valid=r['valid'],budget_s=r['budget_s'],total_s=r['total_s'],
                 reference_duration=ref_time,lower_bound=lower,error=r.get('error',''),
                 source=path.relative_to(ROOT).as_posix())
        if r['valid']:
            result=r['result'];control=verify(result['routes'],ins)
            value=control['duration']/10
            assert control['valid'] and abs(value-r['duration'])<1e-7
            assert abs(value-result['cost'])<1e-7 and result['objective']=='duration'
            assert value+1e-7>=lower and value<=r['initial_duration']+1e-7
            assert abs(value-r['travel']-r['waiting']-r['service'])<1e-7
            assert abs(ref_time-r['reference_duration'])<1e-7
            delta=100*(value/ref_time-1)
            assert abs(delta-r['delta_reference_pct'])<1e-7
            trace=result['trace'];assert all(b['best']<=a['best']+1e-6 for a,b in zip(trace,trace[1:]))
            row.update(duration=value,initial_duration=r['initial_duration'],travel=r['travel'],
                       waiting=r['waiting'],service=r['service'],makespan=r['makespan'],vehicles=r['vehicles'],
                       delta_reference_pct=delta,gain_initial_pct=r['gain_initial_pct'],
                       gap_bound_pct=100*(value/lower-1) if lower>0 else None,
                       first_phase_duration=result['components'][0]['cost'])
        rows.append(row)
    if require_complete:assert seen==expected,(len(seen),len(expected))
    df=pd.DataFrame(rows);core=df[df.core].copy();good=core[core.valid]
    cases=core.groupby(['instance','n'],as_index=False).agg(
        attempts=('valid','size'),valid=('valid','sum'),mean_duration=('duration','mean'),
        median_duration=('duration','median'),std_duration=('duration',lambda x:x.std(ddof=0) if len(x)>1 else np.nan),
        reference_duration=('reference_duration','first'),lower_bound=('lower_bound','first'),
        mean_delta_reference_pct=('delta_reference_pct','mean'),mean_gain_initial_pct=('gain_initial_pct','mean'),
        mean_travel=('travel','mean'),mean_waiting=('waiting','mean'),mean_service=('service','mean'),
        mean_calculation_s=('total_s','mean'),mean_gap_bound_pct=('gap_bound_pct','mean'))
    sizes=cases.groupby('n',as_index=False).agg(instances=('instance','size'),attempts=('attempts','sum'),
        feasible=('valid','sum'),mean_duration=('mean_duration','mean'),
        mean_delta_reference_pct=('mean_delta_reference_pct','mean'),mean_gain_initial_pct=('mean_gain_initial_pct','mean'),
        mean_calculation_s=('mean_calculation_s','mean'),mean_travel=('mean_travel','mean'),
        mean_waiting=('mean_waiting','mean'),mean_service=('mean_service','mean'))
    repeated=df[df.instance.isin(['C101','R202','R2_10_8']) & df.seed.between(4101,4120)].copy()
    if require_complete:
        assert len(core)==472 and len(cases)==356 and len(df)==646 and len(repeated)==180
        assert repeated.groupby(['instance','method']).size().eq(20).all()
        starts=repeated.groupby(['instance','seed']).initial_duration.agg(lambda x:x.max()-x.min())
        assert starts.abs().max()<1e-7,'Comparisons must share the same construction value'
    descriptions=[]
    for (name,method),group in repeated[repeated.valid].groupby(['instance','method']):
        for metric in ['duration','waiting','total_s','delta_reference_pct']:
            descriptions.append(dict(instance=name,method=method,metric=metric,**describe(group[metric])))
    descriptive=pd.DataFrame(descriptions)
    # Une observation par instance, même taille et même graine : éviter les pseudo-répétitions.
    pairs=good[good.n.eq(1000)&good.seed.eq(4101)].copy()
    x=pairs.initial_duration.to_numpy();y=pairs.duration.to_numpy()
    covariance=float(np.mean((x-x.mean())*(y-y.mean())))
    slope=covariance/float(np.var(x));intercept=float(y.mean()-slope*x.mean())
    fitted=slope*x+intercept;r=float(np.corrcoef(x,y)[0,1])
    sct=float(((y-y.mean())**2).sum());sce=float(((y-fitted)**2).sum());scr=float(((fitted-y.mean())**2).sum())
    assert np.isclose(sct,scr+sce) and np.isclose(1-sce/sct,r*r)
    regression=dict(n=len(pairs),x='initial_duration',y='duration',covariance=covariance,
                    pearson=r,slope=slope,intercept=intercept,r2=1-sce/sct,SCT=sct,SCR=scr,SCE=sce,
                    scope='60 distinct 1000-client instances; seed 4101; 10s search; descriptive, not causal')
    pairs['fitted']=fitted
    for name,frame in [('flat',df),('core',core),('instances',cases),('sizes',sizes),
                       ('repetitions',repeated),('descriptive',descriptive),('regression',pairs)]:
        frame.to_csv(BASE/(name+'.csv'),index=False)
    info=dict(complete=seen==expected,runs=len(df),core_runs=len(core),instances=len(cases),
              feasible=int(df.valid.sum()),failed=int((~df.valid).sum()),repetition_runs=len(repeated),
              mean_instance_delta_reference_pct=float(cases.mean_delta_reference_pct.mean()),
              mean_instance_gain_initial_pct=float(cases.mean_gain_initial_pct.mean()),
              reference_kind='Duration of distance-BKS plans; no known time optimum',
              mean_calculation_s=float(good.total_s.mean()),regression=regression,
              duration_population=describe(cases.mean_duration),delta_population=describe(cases.mean_delta_reference_pct))
    (BASE/'analysis.json').write_text(json.dumps(info,indent=2,allow_nan=False),encoding='utf-8')
    return df,cases,sizes,repeated,descriptive,info


if __name__=='__main__':
    *_,info=analyze('--partial' not in sys.argv)
    print(json.dumps(info,indent=2))
