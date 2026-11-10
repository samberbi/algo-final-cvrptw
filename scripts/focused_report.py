"""Pedagogical primary study, with the full thousand-run extension explicit."""
from pathlib import Path
import json,hashlib,shutil
import numpy as np,pandas as pd
import matplotlib.pyplot as plt
from algo.data import load
from algo.verify import verify
from scripts.figures import measured,save


def prepare_focus(root,out,figures,coverage_size,table,map_instance):
    protocol=json.loads((root/'results/focused/protocol.json').read_text())
    for name,digest in protocol['sources'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
    records=[json.loads(p.read_text()) for p in sorted((root/'results/focused/runs').glob('*.json'))]
    assert len(records)==80 and len({r['job']['id'] for r in records})==80
    declared={j['id']:j for j in protocol['jobs']};flat=[]
    for row in records:
        j=row['job'];r=row['result'];assert declared[j['id']]==j and row['from_zero']
        if r['status']=='feasible':
            v=verify(r['routes'],load(root/'data/instances'/(j['instance']+'.vrp')))
            assert v['valid'] and abs(v['distance']/10-r['cost'])<1e-7
        flat.append(dict(instance=j['instance'],family=j['instance'].split('_')[0] if '_' in j['instance'] else j['instance'][:-2],
            n=j['n'],seed=j['seed'],status=r['status'],reference_distance=j['reference_distance'],distance=r.get('cost'),
            gap_pct=row['gap_pct'],runtime_s=r['runtime_s'],iterations=r.get('iterations',0),vehicles=r.get('vehicles'),
            initial_gap_pct=100*(row['base_cost']/j['reference_distance']-1) if row['base_cost'] is not None else None,
            base_runtime_s=row['base_runtime_s']))
    df=pd.DataFrame(flat);df.to_csv(out/'etude_principale_80.csv',index=False)
    html=df[['instance','n','seed','status','reference_distance','distance','gap_pct','runtime_s']].to_html(index=False,na_rep='—',float_format=lambda v:f'{v:.4f}')
    (root/'livraison/ETUDE_80_EXECUTIONS.html').write_text('<!doctype html><meta charset="utf-8"><title>80 nouveaux essais CVRPTW</title><h1>Étude principale : 80 nouvelles résolutions</h1><p>Les deux lots restent distincts : cette page contient les 80 nouveaux essais, le tableau MILLE_EXECUTIONS.html conserve l’extension.</p>'+html,encoding='utf-8')
    instances=df.groupby(['instance','family','n']).agg(runs=('seed','size'),valid=('status',lambda s:int(s.eq('feasible').sum())),
        mean_gap_pct=('gap_pct','mean'),max_gap_pct=('gap_pct','max'),min_gap_pct=('gap_pct','min'),
        std_gap_pct=('gap_pct','std'),mean_time_s=('runtime_s','mean'),reference_distance=('reference_distance','first'),
        best_distance=('distance','min')).reset_index()
    instances.to_csv(out/'etude_principale_instances.csv',index=False)
    broad=out/'coverage_figures';broad.mkdir(exist_ok=True)
    for p in figures.glob('*.png'):shutil.copy2(p,broad/p.name)
    examples=measured(figures,df,instances,records);map_instance(examples[0],figures)
    small=instances[instances.n==100].sort_values(['family','instance'])
    fig,ax=plt.subplots(figsize=(11,3.8));x=np.arange(len(small));mean=small.mean_gap_pct.values
    ax.bar(x,mean,yerr=np.array([mean-small.min_gap_pct.values,small.max_gap_pct.values-mean]),capsize=2,color='#347e94')
    ax.axhline(7,color='#bf5b42',ls='--',label='7 %');ax.set_xticks(x,small.instance,rotation=60,ha='right')
    ax.set(ylabel='Gap DIMACS (%)',title='24 instances à 100 clients : moyenne et étendue min–max sur trois graines')
    ax.legend();save(fig,figures/'gaps.png')
    fig,ax=plt.subplots(figsize=(8,3.5));families=['C1','C2','R1','R2','RC1','RC2']
    ax.boxplot([df[(df.n==100)&df.family.eq(f)].gap_pct.dropna().values for f in families],tick_labels=families,showmeans=True)
    ax.set(ylabel='Gap DIMACS (%)',title='Dispersion par famille : quatre instances et trois graines, soit douze essais')
    ax.axhline(7,color='#bf5b42',ls='--');save(fig,figures/'families.png')
    valid=df[df.status.eq('feasible')];gaps=valid.gap_pct
    sizes=df.groupby('n').agg(essais=('seed','size'),valides=('status',lambda s:int(s.eq('feasible').sum())),
        sous7=('gap_pct',lambda s:int(s.lt(7).sum())),mean=('gap_pct','mean'),max=('gap_pct','max'),time=('runtime_s','mean')).reset_index()
    sizes.columns=['Clients','Essais','Valides','Sous 7 %','Gap moy. (%)','Pire gap (%)','Temps moy. (s)']
    stats=pd.DataFrame([['Solutions réalisables',f'{len(valid)} /80'],['Gap moyen par exécution (%)',float(gaps.mean())],
        ['Moyenne à poids égal par instance (%)',float(instances.mean_gap_pct.mean())],['Médiane (%)',float(gaps.median())],
        ['Écart-type (points)',float(gaps.std())],['Pire gap (%)',float(gaps.max())],
        ['Essais sous 7 %',f'{int(gaps.lt(7).sum())} /80']],columns=['Indicateur','Résultat'])
    before=pd.DataFrame([['Recherche initiale',float(df.initial_gap_pct.mean()),float(df.initial_gap_pct.max()),float(df.base_runtime_s.mean())],
        ['Profil final',float(gaps.mean()),float(gaps.max()),float(df.runtime_s.mean())]],
        columns=['État','Gap moy. (%)','Pire gap (%)','Temps cumulé moy. (s)'])
    present=small[['instance','reference_distance','best_distance','mean_gap_pct','max_gap_pct','mean_time_s']].copy()
    present.columns=['Instance','Référence','Meilleur coût','Gap moy. (%)','Pire gap (%)','Temps moy. (s)']
    largest=instances[instances.n.gt(100)][['instance','n','runs','mean_gap_pct','max_gap_pct','mean_time_s']].copy()
    largest.columns=['Instance','Clients','Essais','Gap moy. (%)','Pire gap (%)','Temps moy. (s)']
    v=dict(runs=80,instances=28,valid=len(valid),mean_gap=float(gaps.mean()),maximum=float(gaps.max()),below7=int(gaps.lt(7).sum()),
        raw_files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'results/focused/runs').glob('*.json'))})
    (root/'results/focused/validation.json').write_text(json.dumps(v,indent=2))
    interpretation=(f'Les {len(valid)} solutions réalisables du lot principal ont un gap moyen de {gaps.mean():.3f} % '
        f'et un pire gap de {gaps.max():.3f} %. {int(gaps.lt(7).sum())} essais sur 80 sont strictement sous 7 %. '
        f'Les barres à 100 clients indiquent la moyenne et le minimum–maximum des trois graines ; '
        f'les boîtes comparent les douze exécutions de chaque famille. Les budgets différents selon la taille '
        f'empêchent d’attribuer toute variation de temps à la seule taille.')
    cases=' '.join(f"Le pire essai affiché à {r['job']['n']} clients est {r['job']['instance']}, graine {r['job']['seed']}, à {r['gap_pct']:.3f} %." for r in examples)
    cases+=' La carte représente le cas difficile à 100 clients ; les horaires sont contrôlés par le vérificateur, pas par le dessin.'
    ext=coverage_size.rename(columns={'n':'Clients','essais':'Essais','valides':'Valides','sous7':'Sous 7 %',
        'gap_moy':'Gap moy. (%)','gap_max':'Pire gap (%)','temps_moy':'Temps moy. (s)','temps_max':'Temps max. (s)'})
    replacements={'{{GLOBAL_RESULTS}}':table(stats),'{{SIZE_RESULTS}}':table(sizes),'{{BEFORE_AFTER}}':table(before),
        '{{REPRESENTATIVE_RESULTS}}':table(present),'{{LARGE_FOCUS_RESULTS}}':table(largest),
        '{{RESULT_INTERPRETATION}}':interpretation,'{{CASE_INTERPRETATION}}':cases,'{{COVERAGE_RESULTS}}':table(ext),
        '{{CONCLUSION}}':f"Le lot principal fournit {len(valid)} solutions réalisables sur 80, avec un gap moyen de {gaps.mean():.3f} % et un maximum de {gaps.max():.3f} %. L’extension à 356 instances et mille trajectoires reste présentée séparément : elle révèle des difficultés supplémentaires et empêche de généraliser les résultats du lot principal à tout le jeu."}
    return replacements,v
