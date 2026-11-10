"""Build the original narrative from exactly the frozen 1,000 attempts."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import json,re,hashlib,time,xml.etree.ElementTree as ET
import numpy as np,pandas as pd,nbformat as nbf,psutil
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from scripts.figures import diagrams,measured,save
from algo.data import load
from algo.verify import verify


def table(df):
    def format_cell(v):
        if isinstance(v,(float,np.floating)):
            if pd.isna(v):return '—'
            return ('0,000' if abs(v)<.0005 else f'{v:.3f}'.replace('.',','))
        return str(v).replace('|',' / ').replace('\n',' ')
    rows=['| '+' | '.join(map(str,df.columns))+' |','| '+' | '.join(['---']*len(df.columns))+' |']
    rows+=['| '+' | '.join(format_cell(v) for v in row)+' |' for row in df.itertuples(index=False,name=None)]
    return '\n'.join(rows)


def family(name):
    return name.split('_')[0] if '_' in name else name[:-2]


def prepare():
    print('Waiting for all largest-instance continuations before publication...',flush=True)
    while True:
        try:
            largest_progress=json.loads((ROOT/'results/largest_v2/progress.json').read_text())
            if largest_progress['complete']:break
        except (FileNotFoundError,json.JSONDecodeError):pass
        time.sleep(2)
    out=ROOT/'results/report';out.mkdir(exist_ok=True)
    figures=out/'figures';diagrams(figures)
    protocol=json.loads((ROOT/'results/campaign/protocol.json').read_text())
    manifest_path=ROOT/'data/manifest.json'
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest()==protocol['dataset_sha256']
    data_manifest=json.loads(manifest_path.read_text())
    for name,info in data_manifest['files'].items():
        assert hashlib.sha256((ROOT/'data/instances'/name).read_bytes()).hexdigest()==info['sha256'],name
    for name,sha in protocol['source_sha256'].items():
        assert hashlib.sha256((ROOT/'algo'/name).read_bytes()).hexdigest()==sha,name
    final_protocol=json.loads((ROOT/'results/final/protocol.json').read_text())
    assert hashlib.sha256((ROOT/'ameliorations/decomposition.py').read_bytes()).hexdigest()==final_protocol['method_sha256']
    records=[json.loads(p.read_text()) for p in sorted((ROOT/'results/final/runs').glob('*.json'))]
    largest_protocol=json.loads((ROOT/'results/largest_v2/protocol.json').read_text())
    assert largest_protocol['method_sha256']==final_protocol['method_sha256']
    largest={r['job']['id']:r for r in [json.loads(p.read_text()) for p in (ROOT/'results/largest_v2/runs').glob('*.json')]}
    assert len(largest)==largest_protocol['expected'] and all(r['job']['n']==1000 for r in largest.values())
    records=[largest.get(r['job']['id'],r) for r in records]
    assert len(records)==1000 and len({r['job']['id'] for r in records})==1000
    assert {r['job']['id'] for r in records}==set(range(1000))
    declared={j['id']:j for j in protocol['jobs']}
    flat=[]
    for row in records:
        j=row['job'];r=row['result'];assert declared[j['id']]==j
        assert hashlib.sha256((ROOT/row['base_file']).read_bytes()).hexdigest()==row['base_file_sha256']
        if j['n']==1000:
            assert hashlib.sha256((ROOT/row['previous_stage_file']).read_bytes()).hexdigest()==row['previous_stage_sha256']
        if r['status']=='feasible':
            ins=load(ROOT/'data/instances'/(j['instance']+'.vrp'))
            checked=verify(r['routes'],ins);assert checked['valid'],j
            assert abs(r['cost']-checked['distance']/10)<1e-6
            gap=100*(r['cost']/j['reference_distance']-1)
            assert abs(gap-row['gap_pct'])<1e-8
        flat.append(dict(id=j['id'],instance=j['instance'],family=family(j['instance']),n=j['n'],seed=j['seed'],
            status=r['status'],distance=r.get('cost'),reference_distance=j['reference_distance'],gap_pct=row['gap_pct'],
            vehicles=r.get('vehicles'),fleet_limit=j['fleet_limit'],budget_s=j['seconds'],
            runtime_s=r['runtime_s'],cpu_s=r.get('cpu_s'),iterations=r.get('iterations',0),
            initial_gap_pct=row['initial_gap_pct'],base_runtime_s=row['base_runtime_s'],
            continuation_runtime_s=row['continuation_runtime_s'],total_budget_s=row['total_budget_s']))
    df=pd.DataFrame(flat);df.to_csv(out/'mille_executions.csv',index=False)
    web=df[['instance','n','seed','status','distance','reference_distance','gap_pct','vehicles','fleet_limit','runtime_s']].copy()
    web.columns=['Instance','Clients','Graine','Statut','Distance','BKS','Gap (%)','Véhicules','Maximum véhicules','Temps cumulé (s)']
    html_table=web.to_html(index=False,table_id='runs',na_rep='—',float_format=lambda v:f'{v:.3f}')
    html='''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Les 1 000 exécutions CVRPTW</title>
<style>body{font:15px system-ui;margin:30px;color:#203246}input{padding:10px;min-width:320px}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:8px;border-bottom:1px solid #ddd;text-align:right}th{position:sticky;top:0;background:#e5edf3}tr:hover{background:#edf4f9}td:first-child,th:first-child{text-align:left}</style>
<h1>Les 1 000 exécutions CVRPTW</h1><p>Distance DIMACS, flotte maximale respectée. Les temps incluent la continuation lorsqu'elle s'applique. Un tiret ne signifie pas un gap nul.</p>
<label>Filtrer : <input id="filter" placeholder="Instance, taille, graine ou statut"></label><p id="count">1 000 lignes</p>'''+html_table+'''
<script>const rows=[...document.querySelectorAll('#runs tbody tr')];document.querySelector('#filter').addEventListener('input',e=>{const q=e.target.value.toLowerCase();let n=0;rows.forEach(r=>{const ok=r.textContent.toLowerCase().includes(q);r.hidden=!ok;if(ok)n++;});document.querySelector('#count').textContent=n+' lignes affichées sur 1 000';});</script></html>'''
    (ROOT/'livraison/MILLE_EXECUTIONS.html').write_text(html,encoding='utf-8')
    instances=df.groupby(['instance','family','n'],sort=True).agg(runs=('id','size'),
        valid=('status',lambda s:int(s.eq('feasible').sum())),mean_gap_pct=('gap_pct','mean'),max_gap_pct=('gap_pct','max'),
        min_gap_pct=('gap_pct','min'),std_gap_pct=('gap_pct','std'),mean_distance=('distance','mean'),
        reference_distance=('reference_distance','first'),mean_time_s=('runtime_s','mean'),
        min_vehicles=('vehicles','min'),max_vehicles=('vehicles','max'),fleet_limit=('fleet_limit','first')).reset_index()
    assert len(instances)==356
    instances.to_csv(out/'toutes_les_instances.csv',index=False)
    df[(df.status!='feasible')|df.gap_pct.ge(7)].to_csv(out/'essais_hors_cible.csv',index=False)
    valid=df[df.status=='feasible'];gaps=valid.gap_pct
    macro=float(instances.mean_gap_pct.mean())
    rng=np.random.default_rng(20261109)
    means=instances.mean_gap_pct.dropna().values
    bootstrap=means[rng.integers(0,len(means),size=(10000,len(means)))].mean(axis=1)
    ci=np.quantile(bootstrap,[.025,.975])
    size=df.groupby('n').agg(essais=('id','size'),valides=('status',lambda s:int(s.eq('feasible').sum())),
        sous7=('gap_pct',lambda s:int(s.lt(7).sum())),gap_moy=('gap_pct','mean'),gap_max=('gap_pct','max'),
        temps_moy=('runtime_s','mean'),temps_max=('runtime_s','max')).reset_index()
    size.to_csv(out/'bilan_par_taille.csv',index=False)
    examples=measured(figures,df,instances,records)
    worst100=examples[0]
    map_instance(worst100,figures)
    summary=dict(attempts=1000,instances=356,valid=len(valid),below7=int(gaps.lt(7).sum()),below5=int(gaps.lt(5).sum()),
        mean_gap=float(gaps.mean()),macro_mean_gap=macro,median=float(gaps.median()),std=float(gaps.std()),
        maximum=float(gaps.max()),bootstrap_macro_ci95=ci.tolist(),
        raw_files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'results/campaign/runs').glob('*.json'))},
        derived_files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'results/final/runs').glob('*.json'))})
    summary['largest_files_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'results/largest_v2/runs').glob('*.json'))}
    before_after=pd.DataFrame([
        ['Initial',int(df.initial_gap_pct.notna().sum()),float(df.initial_gap_pct.mean()),float(df.initial_gap_pct.max()),int(df.initial_gap_pct.lt(7).sum()),float(df.base_runtime_s.mean())],
        ['Après intensification',len(valid),float(gaps.mean()),float(gaps.max()),int(gaps.lt(7).sum()),float(df.runtime_s.mean())]],
        columns=['État','Valides','Gap moy. (%)','Pire gap (%)','Sous 7 %','Temps cumulé moy. (s)'])
    before_after.to_csv(out/'avant_apres.csv',index=False)
    (out/'validation.json').write_text(json.dumps(summary,indent=2))
    test_suite=ET.parse(ROOT/'results/tests.xml').getroot().find('testsuite')
    assert test_suite.get('failures')=='0' and test_suite.get('errors')=='0'
    global_frame=pd.DataFrame([
        ['Exécutions réalisables',f'{len(valid)} / 1000'],['Gap moyen par exécution (%)',float(gaps.mean())],
        ['Gap moyen à poids égal par instance (%)',macro],['Médiane (%)',float(gaps.median())],
        ['Premier quartile Q1 (%)',float(gaps.quantile(.25))],['Troisième quartile Q3 (%)',float(gaps.quantile(.75))],
        ['Écart interquartile (points)',float(gaps.quantile(.75)-gaps.quantile(.25))],
        ['Écart-type (points de pourcentage)',float(gaps.std())],['Pire gap (%)',float(gaps.max())],
        ['Solutions réalisables sous 7 %',f'{int(gaps.lt(7).sum())} / 1000'],
        ['Solutions réalisables sous 5 %',f'{int(gaps.lt(5).sum())} / 1000']],columns=['Indicateur','Résultat'])
    display_size=size.rename(columns={'n':'Clients','essais':'Essais','valides':'Valides','sous7':'Sous 7 %',
        'gap_moy':'Gap moy. (%)','gap_max':'Pire gap (%)','temps_moy':'Temps moy. (s)','temps_max':'Temps max. (s)'})
    representatives=instances[instances.instance.isin([f'{f}{i:02}' for f in ['C1','C2','R1','R2','RC1','RC2'] for i in [1,2]])]
    representatives=representatives[['instance','runs','mean_gap_pct','max_gap_pct','mean_time_s']]
    representatives.columns=['Instance','Essais','Gap moy. (%)','Pire gap (%)','Temps moy. (s)']
    sensitivity=pd.DataFrame([dict(instance=r['instance'],seed=r['seed'],method=r['method'],
        status=r['result']['status'],gap=r['gap_pct']) for r in map(json.loads,(ROOT/'results/sensitivity/runs.jsonl').read_text().splitlines())])
    assert len(sensitivity)==72
    st=sensitivity.groupby('method').agg(essais=('gap','size'),valides=('status',lambda s:int(s.eq('feasible').sum())),
        gap_moy=('gap','mean'),gap_max=('gap','max')).reset_index()
    st.to_csv(out/'sensibilite.csv',index=False)
    st['method']=st['method'].map({'reference':'Réglage initial','sans_adaptation':'Sans adaptation',
        'sans_recuit':'Sans recuit','temperature_basse':'Température initiale basse',
        'temperature_haute':'Température initiale haute','petits_retraits':'Retraits limités à dix clients'})
    st.columns=['Variante','Essais','Valides','Gap moy. (%)','Pire gap (%)']
    polish_pilot=pd.DataFrame([dict(instance=r['instance'],method=r['method'],initial=r['initial_gap_pct'],gap=r['gap_pct'])
        for r in map(json.loads,(ROOT/'results/polish_pilot/runs.jsonl').read_text().splitlines())])
    assert len(polish_pilot)==12
    paired=polish_pilot.pivot(index='instance',columns='method',values='gap').reset_index()
    paired=paired[['instance','global','decomposition']]
    paired.columns=['Instance','Continuation globale (%)','Groupes de tournées (%)']
    paired.to_csv(out/'pilote_intensification.csv',index=False)
    duration=pd.DataFrame(json.loads((ROOT/'results/duration/runs.json').read_text()))
    assert len(duration)==36
    dur=duration.groupby(['instance','objective']).agg(duration=('duration','mean'),waiting=('waiting','mean'),
        travel=('travel','mean'),service=('service','mean')).unstack('objective')
    dt=pd.DataFrame({'Instance':dur.index,'Durée mode distance':dur[('duration','distance')].values,
        'Durée mode durée':dur[('duration','duration')].values,
        'Attente mode durée':dur[('waiting','duration')].values,
        'Trajet mode durée':dur[('travel','duration')].values,'Service':dur[('service','duration')].values})
    dt['Variation durée (%)']=100*(dt['Durée mode durée']/dt['Durée mode distance']-1)
    dt.to_csv(out/'objectif_duree.csv',index=False)
    n1000=size[size.n==1000].iloc[0]
    family_means=instances.groupby('family').mean_gap_pct.mean().sort_values()
    easiest,hardest=family_means.index[0],family_means.index[-1]
    interpretation=(f'Le gap moyen sur les {len(valid)} recherches réalisables est de {gaps.mean():.3f} %, '
        f'avec un maximum de {gaps.max():.3f} %. À 1 000 clients, {int(n1000.sous7)} essais sur {int(n1000.essais)} '
        f'sont sous 7 %. Les boîtes montrent la médiane (trait), les quartiles, la moyenne et les valeurs extrêmes. '
        f'Un point isolé n’est pas supprimé : il signale une exécution à expliquer. '
        f'Le bootstrap à poids égal par instance donne un intervalle descriptif de [{ci[0]:.3f} ; {ci[1]:.3f}] % '
        f'pour la moyenne. Il ne couvre pas une population universelle de problèmes ; les variantes d’une famille '
        f'partagent des structures et les budgets changent avec la taille. '
        f'La famille {hardest} présente la moyenne par instance la plus élevée ({family_means.iloc[-1]:.3f} %), '
        f'et {easiest} la plus faible ({family_means.iloc[0]:.3f} %). Cette association ne prouve pas '
        f'un effet isolé des fenêtres ou de la géographie : plusieurs caractéristiques changent ensemble.')
    cases=' '.join(f"Sur {r['job']['instance']}, graine {r['job']['seed']}, le pire essai affiché de sa taille atteint {r['gap_pct']:.3f} %." for r in examples)
    cases+=' Les courbes relient les observations enregistrées du meilleur coût ; elles ne montrent pas toutes les solutions courantes. La carte est une illustration, pas une preuve de respect des fenêtres.'
    environment=json.loads((ROOT/'results/environment.json').read_text())
    environment_text=(f"Les mesures sont issues de {environment['platform']}, sur {environment.get('cpu_model',environment['processor'])}, "
        f"avec {environment['physical_cores']} cœurs physiques et environ {environment['ram_gib']:.1f} Gio de mémoire. "
        f"Python {environment['python'].split()[0]}, NumPy {environment['direct_versions']['numpy']}, "
        f"Numba {environment['direct_versions']['numba']} et VRPLIB {environment['direct_versions']['vrplib']} sont utilisés. "
        f"Les versions et le placement des processus figurent dans les fichiers d'environnement et de protocole.")
    replacements={'{{ENVIRONMENT}}':environment_text,
        '{{TEST_RESULTS}}':f"Le rapport de tests contient **{test_suite.get('tests')} tests réussis**, sans erreur ni échec.",
        '{{GLOBAL_RESULTS}}':table(global_frame),'{{SIZE_RESULTS}}':table(display_size),
        '{{BEFORE_AFTER}}':table(before_after),
        '{{RESULT_INTERPRETATION}}':interpretation,'{{REPRESENTATIVE_RESULTS}}':table(representatives),
        '{{CASE_INTERPRETATION}}':cases,'{{SENSITIVITY_RESULTS}}':table(st),
        '{{POLISH_PILOT}}':table(paired),'{{DURATION_RESULTS}}':table(dt),
        '{{CONCLUSION}}':f"Sur les mille résolutions prévues, {len(valid)} solutions sont réalisables et {int(gaps.lt(7).sum())} ont un gap inférieur à 7 %. Le gap moyen est {gaps.mean():.3f} %, le pire {gaps.max():.3f} %. Ces valeurs décrivent le protocole DIMACS et les budgets publiés ; elles ne constituent pas une garantie pour chaque nouvelle instance."}
    full=instances[['instance','n','runs','valid','reference_distance','mean_gap_pct','max_gap_pct','mean_time_s']].copy()
    full.columns=['Instance','Clients','Essais','Valides','Référence','Gap moy. (%)','Pire gap (%)','Temps moy. (s)']
    (ROOT/'livraison/ANNEXE_INSTANCES.md').write_text('# Annexe — Les 356 instances, sans exclusion\n\n'+table(full)+'\n\nLe détail des mille résolutions est dans `results/report/mille_executions.csv`. Les échecs de faisabilité restent dans les effectifs ; aucun gap nul ne leur est attribué.\n',encoding='utf-8')
    from scripts.focused_report import prepare_focus
    focus_replacements,focused=prepare_focus(ROOT,out,figures,size,table,map_instance)
    replacements.update(focus_replacements)
    summary['focused']=focused
    return replacements,summary


def map_instance(row,figures):
    import matplotlib.pyplot as plt
    ins=load(ROOT/'data/instances'/(row['job']['instance']+'.vrp'))
    fig,ax=plt.subplots(figsize=(7,5.5))
    for route in row['result']['routes']:
        seq=[0]+route+[0];ax.plot(ins.xy[seq,0],ins.xy[seq,1],marker='.',linewidth=.8)
    ax.scatter(*ins.xy[0],marker='s',s=80,c='black',zorder=10,label='Dépôt')
    ax.set_title(f"Pire essai à 100 clients : {row['job']['instance']} — {row['gap_pct']:.2f} %")
    ax.set_aspect('equal');ax.legend();save(fig,figures/'routes.png')
    schedule=verify(row['result']['routes'],ins)['routes'][0]['schedule']
    fig,ax=plt.subplots(figsize=(9,3.8))
    for i,stop in enumerate(schedule[:8]):
        client=stop['client'];arrive=stop['arrival']/10;begin=stop['start']/10;service=ins.service[client]/10
        ax.plot([ins.early[client]/10,ins.late[client]/10],[i,i],color='#bac8d0',linewidth=7,alpha=.6)
        if begin>arrive:ax.plot([arrive,begin],[i,i],color='#e0a54a',linewidth=4)
        ax.plot([begin,begin+service],[i,i],color='#398a63',linewidth=4)
        ax.scatter([begin],[i],color='#224d6a',s=20,zorder=5)
    ax.set_yticks(range(min(8,len(schedule))),[str(s['client']) for s in schedule[:8]])
    ax.set(xlabel='Temps',ylabel='Client',title='Débuts de service (points), fenêtres (gris), attente (orange), service (vert)')
    ax.invert_yaxis();save(fig,figures/'route_schedule.png')


CODE={
'setup':'''from pathlib import Path
import sys,json,inspect
ROOT=Path.cwd()
sys.path.insert(0,str(ROOT))
from IPython.display import display,Image
from algo.solver import solve,Settings,warmup
from algo.data import load
from algo.verify import verify
from algo import kernels
FIG=ROOT/'results/report/figures'
progress=json.loads((ROOT/'results/final/progress.json').read_text())
assert progress['complete'] and progress['completed']==1000
focus=json.loads((ROOT/'results/focused/progress.json').read_text())
assert focus['complete'] and focus['completed']==80
print('Étude principale : 80 nouveaux essais sur 28 instances. Extension : 1 000 trajectoires sur 356 instances.')''',
'representation':"display(Image(filename=str(FIG/'representation.png')))",
'mini_example':'''import numpy as np,pandas as pd
from algo.model import Instance
toy=Instance('exemple',np.array([[0,0],[8,0],[4,3]]),np.array([0,2,3]),
    np.array([0,5,4]),np.array([0,15,0]),np.array([60,25,40]),
    np.array([[0,8,5],[8,0,5],[5,5,0]]),6.,2,60.)
display(pd.DataFrame({'Client':[1,2],'Demande':[2,3],'Service':[5,4],
    'Ouverture':[15,0],'Fermeture':[25,40]}))
display(pd.DataFrame(toy.distance,index=['Dépôt','Client 1','Client 2'],columns=['Dépôt','Client 1','Client 2']).rename_axis('Depuis / vers').reset_index())
examples=[]
for route in [[1,2],[2,1]]:
    v=verify([route],toy)
    assert v['valid']
    examples.append({'Ordre':str(route),'Charge':sum(toy.demand[route]),'Distance':v['distance'],
        'Trajet':v['travel'],'Attente':v['waiting'],'Service':9,'Durée':v['duration']})
display(pd.DataFrame(examples))''',
'small_exact':'''from controle.exact import exact
from algo.model import Objective
oracle_distance=exact(toy,Objective.DISTANCE)
oracle_duration=exact(toy,Objective.DURATION)
assert oracle_distance['status']==oracle_duration['status']=='optimal'
assert oracle_distance['score']==18 and oracle_duration['score']==28
print('Optimum exact de l’exemple : distance',oracle_distance['score'],'; durée',oracle_duration['score'])''',
'schedule_example':"display(Image(filename=str(FIG/'schedule.png')))",
'algorithm_diagram':"display(Image(filename=str(FIG/'algorithm.png')))",
'repair_diagram':"display(Image(filename=str(FIG/'repair.png')))",
'moves_diagram':"display(Image(filename=str(FIG/'moves.png')))",
'acceptance_diagram':"display(Image(filename=str(FIG/'acceptance.png')))",
'budget_diagram':"display(Image(filename=str(FIG/'budgets.png')))",
'individual_runs':'''runs=pd.read_csv(ROOT/'results/report/etude_principale_80.csv')
assert len(runs)==80
display(runs[['instance','n','seed','status','distance','reference_distance','gap_pct','runtime_s']].head(12))
print('Extrait : 12 lignes sur 80. Les CSV et les tableaux HTML conservent les lots complets séparément.')''',
'source_excerpt':"print(inspect.getsource(kernels.best_insert.py_func))",
'results_figures':"display(Image(filename=str(FIG/'gaps.png')))\ndisplay(Image(filename=str(FIG/'families.png')))\ndisplay(Image(filename=str(FIG/'scaling.png')))",
'convergence_and_map':"display(Image(filename=str(FIG/'convergence.png')))\ndisplay(Image(filename=str(FIG/'routes.png')))\ndisplay(Image(filename=str(FIG/'route_schedule.png')))",
}

CAPTIONS={
    'representation':['Données, représentation des tournées et évaluation indépendante.'],
    'schedule_example':['Exemple illustratif : attente avant ouverture et début de service dans la fenêtre.'],
    'algorithm_diagram':['Boucle ALNS : construire, retirer, réparer, accepter et protéger le meilleur résultat.'],
    'repair_diagram':['Exemple de retrait et réparation ; la réserve doit être entièrement réinsérée.'],
    'moves_diagram':['Relocate, swap et 2-opt* : illustrations de modifications de tournées.'],
    'acceptance_diagram':['Probabilités théoriques du recuit pour plusieurs températures illustratives.'],
    'budget_diagram':['Budgets nominaux initiaux et cumulés ; les temps réels sont publiés séparément.'],
    'results_figures':['Vingt-quatre cas à 100 clients : moyenne et étendue minimum–maximum des trois graines.',
        'Variabilité par famille : douze exécutions par famille à 100 clients.',
        'Temps réels cumulés et propositions de la phase initiale ; budgets variables selon la taille.'],
    'convergence_and_map':['Historique observé et état final des pires essais affichés, sans sélection favorable.',
        'Tournées du pire essai à 100 clients ; le dépôt est représenté par un carré.',
        'Extrait des horaires de sa première tournée : les points indiquent les débuts de service.']}


def main():
    if 8 in psutil.Process().cpu_affinity():psutil.Process().cpu_affinity([8])
    replacements,summary=prepare()
    source=(ROOT/'docs/LIVRABLE_SOURCE.md').read_text(encoding='utf-8')
    for key,value in replacements.items():source=source.replace(key,value)
    assert '{{' not in source
    cells=[]
    for i,part in enumerate(re.split(r'<!-- EXEC:(\w+) -->',source)):
        if i%2:
            cell=nbf.v4.new_code_cell(CODE[part]);cell.metadata['include_code_in_report']=part=='source_excerpt'
            cell.metadata['figure_captions']=CAPTIONS.get(part,[])
            cells.append(cell)
        elif part.strip():cells.append(nbf.v4.new_markdown_cell(part.strip()))
    cells.append(nbf.v4.new_markdown_cell('### Contrôle exécutable court\n\nCe contrôle de fonctionnement est distinct des mille recherches de la campagne.'))
    cells.append(nbf.v4.new_code_cell("startup=warmup()\ninstance=load(ROOT/'data/instances/C101.vrp')\ndemo=solve(instance,Settings(seconds=.2,seed=9999))\nassert demo['status']=='feasible' and verify(demo['routes'],instance)['valid']\nprint('Contrôle réalisable ; distance :',demo['cost'],'; véhicules :',demo['vehicles'])"))
    nb=nbf.v4.new_notebook(cells=cells)
    nb.metadata['kernelspec']=dict(name='algo-final',display_name='ALGO FINAL (Python)',language='python')
    kernel_dir=ROOT/'.tools/kernels';spec=kernel_dir/'algo-final';spec.mkdir(parents=True,exist_ok=True)
    (spec/'kernel.json').write_text(json.dumps(dict(argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
        display_name='ALGO FINAL (Python)',language='python')))
    manager=KernelManager(kernel_name='algo-final',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel_dir)]))
    try:NotebookClient(nb,timeout=180,km=manager,resources={'metadata':{'path':str(ROOT)}}).execute()
    finally:
        if manager.has_kernel:manager.shutdown_kernel(now=True)
        manager.cleanup_resources()
    nbf.validate(nb)
    notebook=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb';nbf.write(nb,notebook)
    from nbconvert import HTMLExporter
    html,_=HTMLExporter().from_notebook_node(nb)
    notebook.with_suffix('.html').write_text(html,encoding='utf-8')
    (ROOT/'LIVRABLE_FINAL.md').write_text(re.sub(r'<!-- EXEC:\w+ -->','*Figure ou code exécuté dans le Notebook.*',source),encoding='utf-8')
    summary.update(notebook_sha256=hashlib.sha256(notebook.read_bytes()).hexdigest(),executed_code_cells=sum(c.cell_type=='code' for c in nb.cells))
    (ROOT/'results/report/validation.json').write_text(json.dumps(summary,indent=2))
    print({k:v for k,v in summary.items() if k not in ['raw_files_sha256','derived_files_sha256','largest_files_sha256','focused']})
    print('Primary study:',{k:v for k,v in summary['focused'].items() if k!='raw_files_sha256'})


if __name__=='__main__':main()
