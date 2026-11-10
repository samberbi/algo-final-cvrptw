"""Build the new measured ILS/SA deliverable. Refuses an incomplete main study."""
from pathlib import Path
import json, platform, re, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import nbformat
import numpy as np
from nbconvert import HTMLExporter
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from scripts.ils_report_analysis import prepare,study_tables,OUT
from scripts.ils_figures import generate
from scripts.export_report import markdown_table


def table(frame, names=None):
    return markdown_table(frame.rename(columns=names or {}))


def main():
    df,summary,instances,sizes,records,payload=prepare()
    sens,scenarios,exact,exact_runs,constraints=study_tables()
    assert len(exact)==10 and len(exact_runs)==100 and sens.runs.sum()==144 and scenarios.runs.sum()==252
    worst=generate(df,summary,instances,sizes,records,sens,scenarios,exact,exact_runs)
    convergence=[]
    for record in records:
        if not record['valid']:continue
        trace=record['result']['trace'];budget=record['budget_s'];reference=record['reference_distance']
        at80=record['result']['initial_cost']
        for point in trace:
            if point['elapsed_s']<=.8*budget:at80=point['best']
        final=record['result']['cost']
        convergence.append(dict(n=record['n'],method=record['job']['method'],initial_gap=100*(record['result']['initial_cost']/reference-1),
            final_gap=100*(final/reference-1),last20_gain=100*(at80-final)/reference,late_improvement=final<at80-1e-8))
    import pandas as pd
    scaling_records=[json.loads(p.read_text(encoding='utf-8')) for p in (OUT/'scaling').glob('*.json') if p.name!='protocol.json']
    assert len(scaling_records)==36
    scaling=pd.DataFrame([dict(n=r['n'],method=r['method'],runtime=r['result']['runtime_s'],proposals=r['result']['iterations']) for r in scaling_records])
    assert scaling.proposals.eq(50000).all()
    scaling=scaling.groupby(['n','method']).agg(runs=('runtime','size'),mean_time=('runtime','mean'),std_time=('runtime','std'),max_time=('runtime','max')).reset_index()
    scaling.to_csv(OUT/'scaling.csv',index=False)
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(7.5,3.6))
    for method,g in scaling.groupby('method'):
        ax.errorbar(g.n,g.mean_time,yerr=g.std_time,marker='o',capsize=3,label='ILS' if method=='ils' else 'Recuit')
    ax.set(xlabel='Clients',ylabel='Temps moyen de l’appel (s)',title='50 000 propositions : moyenne ± écart-type, six essais par point')
    ax.set_xticks([100,200,1000]);ax.legend();fig.tight_layout();fig.savefig(ROOT/'livraison/ils_figures/scaling.png',dpi=170);plt.close(fig)
    convergence=pd.DataFrame(convergence).groupby(['n','method']).agg(initial_gap=('initial_gap','mean'),
        final_gap=('final_gap','mean'),last20_gain=('last20_gain','mean'),late_runs=('late_improvement','sum'),runs=('late_improvement','size')).reset_index()
    convergence.to_csv(OUT/'convergence.csv',index=False)
    df['family']=df.instance.str.extract(r'^((?:RC|C|R)[12])')
    families=df[df.n.eq(100)].groupby(['family','profile']).agg(mean_gap=('gap_pct','mean'),worst_gap=('gap_pct','max')).reset_index()
    families.to_csv(OUT/'families.csv',index=False)
    comparison=payload['comparison'];lo,hi=comparison['bootstrap_seed_block_95']
    def number(v):return f'{v:.3f}'.replace('.',',')
    model=(ROOT/'docs/MODELISATION_CVRPTW_CORRIGEE.md').read_text(encoding='utf-8')
    model=model.replace('### 1.4.','### 2.3.')
    model=model.split('**Rôle de l’approche exacte.**')[0] if '**Rôle de l’approche exacte.**' in model else model.split("**Rôle de l'approche exacte.**")[0]
    model+='**Rôle de l’approche exacte.** Le module `controle/plne.py` implémente cette formulation dans SciPy/HiGHS. Il est exécuté sur dix petits cas dans cette édition ; le tableau publie les statuts, bornes et temps. Les grandes instances sont traitées par ILS et recuit, sans prétendre les résoudre exactement.\n'
    paired=(f"Sur {comparison['paired_valid']} paires réalisables, l’ILS obtient une distance strictement inférieure dans "
        f"{comparison['ils_lower']} cas, identique dans {comparison['ties']} et supérieure dans {comparison['sa_lower']}. "
        f"La différence moyenne appariée ILS − recuit est {number(comparison['mean_difference_points'])} point de gap. "
        f"L’intervalle bootstrap à 95 % par blocs de graines est [{number(lo)} ; {number(hi)}] point. "
        "Cet intervalle mesure la variabilité des graines sur les 28 instances fixées, sans garantir le même classement sur de nouveaux problèmes.")
    labels={'profile':'Méthode','runs':'Essais','valides':'Réalisables','mean_gap':'Gap moyen (%)','median_gap':'Médiane (%)',
        'std_gap':'Écart-type (pt)','worst_gap':'Pire gap (%)','under7':'Sous 7 %','mean_search_s':'Recherche (s)',
        'mean_total_s':'Avec construction (s)','n':'Clients','instance':'Instance','time':'Recherche (s)','construction':'Construction (s)','total':'Total (s)'}
    certified=exact[exact.status.eq('optimal')]
    certified_runs=exact_runs[exact_runs.optimal_gap.notna()]
    exact_text=(f"HiGHS certifie {len(certified)} optimums sur les dix cas ; les autres lignes conservent leur statut exact. "
        "Une borne inférieure n’est pas une solution, et un incumbent à la limite de temps n’est pas un optimum prouvé. "
        f"Les gaps à l’optimum sont donc calculés uniquement pour les {len(certified_runs)} essais associés aux cas certifiés. ")
    for method,g in certified_runs.groupby('method'):
        exact_text+=f"Pour {method.upper()}, le gap moyen sur ces cas vaut {number(g.optimal_gap.mean())} %, avec un maximum de {number(g.optimal_gap.max())} %. "
    exact_text+='Ces petites instances vérifient la cohérence de la résolution et ne prédisent pas la difficulté des cas à 1 000 clients.'
    best_variant=sens.loc[sens.gap.idxmin(),'variant']
    sens_text=(f"La meilleure moyenne de cette étude exploratoire est obtenue par `{best_variant}`. "
        "Le tableau porte sur six autres instances de développement et trois graines par variante. "
        "Il ne démontre pas un réglage universel. La suppression de la recherche locale change le mécanisme de l’ILS, "
        "tandis que la température change l’acceptation du recuit. Le protocole principal a été figé avant l’observation de ces résultats ; il n’est pas réajusté après coup.")
    sens_by=sens.set_index('variant')
    sens_text+=(f" Sans recherche locale, le gap moyen ILS passe de {number(sens_by.loc['ils_base','gap'])} % à "
                f"{number(sens_by.loc['ils_without_local','gap'])} %. Ce contraste appuie le rôle de l’amélioration locale dans cette implémentation. "
                f"Une perturbation de huit mouvements donne {number(sens_by.loc['ils_large','gap'])} %, contre "
                f"{number(sens_by.loc['ils_small','gap'])} % pour un mouvement : davantage de perturbation ne donne pas automatiquement davantage de qualité à budget fixé.")
    statuses=constraints.groupby('status').size().to_dict()
    scenarios_text=(f"Les 252 observations se répartissent ainsi : {statuses}. "
        "Quand la capacité ou la flotte diminue, certaines demandes deviennent impossibles à répartir ; "
        "quand les fenêtres se resserrent, les insertions compatibles peuvent disparaître. "
        "Un échec de construction signifie seulement que le constructeur n’a rien trouvé avec ses douze essais. "
        "Le statut `proven_infeasible` n’est réservé qu’à une condition nécessaire effectivement violée. "
        "Les moyennes de distance et d’attente ne concernent que les solutions réalisables : leur population peut changer entre scénarios. "
        "Elles ne constituent donc pas, seules, une mesure causale de gain ni une preuve d’amélioration de la solution optimale.")
    scenarios_text+=' Le second panneau calcule la variation relative de distance obtenue par rapport au scénario original, pour les mêmes instance, graine et méthode, puis en prend la moyenne. Ce n’est pas un gap à l’optimum. Toutes ces variantes ont fourni un départ réalisable ; ce succès ne signifie pas que les tournées ou leur qualité restent identiques.'
    environment=json.loads((OUT/'environment.json').read_text(encoding='utf-8')) if (OUT/'environment.json').exists() else {'Python':platform.python_version(),'OS':platform.platform()}
    env=' ; '.join(f'{k} : {v}' for k,v in environment.items() if k!='Versions')+'. Les versions réellement utilisées sont consignées dans `results/revision_ils/environment.json`.\n\n'
    env+=table(pd.DataFrame(list(environment.get('Versions',{}).items()),columns=['Dépendance','Version']))
    tests_path=OUT/'test_validation.json'
    tests=json.loads(tests_path.read_text(encoding='utf-8')) if tests_path.exists() else None
    tests_text=(tests['summary'].strip() if tests else 'La suite de tests est exécutée avant la livraison ; son journal est fourni dans `results/revision_ils/tests.log`.')
    ils=summary[summary.profile.eq('ILS')].iloc[0];sa=summary[summary.profile.ne('ILS')].iloc[0]
    conclusion=(f"Sur les 28 instances fixées et les vingt graines retenues, l’ILS retourne {int(ils.valides)}/{int(ils.runs)} "
        f"solutions réalisables, avec un gap moyen de {number(ils.mean_gap)} %, contre {number(sa.mean_gap)} % pour le recuit. "
        f"Son pire gap est {number(ils.worst_gap)} % et {int(ils.under7)}/{int(ils.runs)} essais restent strictement sous 7 %. "
        "Ces valeurs décrivent notre code, les budgets choisis et ce benchmark connu. La comparaison appariée, les courbes de convergence et les tests de contraintes "
        "permettent d’en discuter les limites. Le travail suivant doit prioriser les cas les plus éloignés de leur référence et vérifier les pistes sur des instances non utilisées pour le développement.")
    by_size=sizes.set_index(['n','profile'])
    size_text=(f"Le classement dépend du périmètre : à 100 clients, le recuit a un gap moyen de {number(by_size.loc[(100,'Recuit simulé'),'mean_gap'])} %, "
        f"contre {number(by_size.loc[(100,'ILS'),'mean_gap'])} % pour l’ILS. À 1 000 clients, l’ILS atteint {number(by_size.loc[(1000,'ILS'),'mean_gap'])} %, "
        f"contre {number(by_size.loc[(1000,'Recuit simulé'),'mean_gap'])} % pour le recuit. L’avantage global ILS ne signifie donc pas une supériorité sur chaque taille. "
        "R1_10_1 reste difficile : ses vingt résultats ILS ne sont pas tous sous 7 %, et la moyenne ne doit pas masquer cette limite. "
        "Les vingt répétitions d’un même cas n’ajoutent pas vingt structures géographiques indépendantes.")
    substitutions=dict(MODEL=model,TESTS=tests_text,ENVIRONMENT=env,
        SUMMARY=table(summary[['profile','runs','valides','mean_gap','median_gap','worst_gap','under7']],labels),
        PAIRED_TEXT=paired,SIZES=table(sizes[['n','profile','runs','mean_gap','worst_gap','time','construction','total']],labels),
        INSTANCES100=table(instances[instances.n.eq(100)][['instance','profile','mean_gap','std_gap','worst_gap']],labels),
        LARGE=table(instances[instances.n.gt(100)][['instance','n','profile','mean_gap','std_gap','worst_gap']],labels),
        EXACT=table(exact,{'n':'Clients','seed':'Graine instance','status':'Statut PLNE','cost':'Incumbent','bound':'Borne inf.','time':'Temps (s)'}),
        EXACT_INTERPRETATION=exact_text,SENS=table(sens,{'variant':'Variante','runs':'Essais','valides':'Réalisables','gap':'Gap moyen (%)','worst':'Pire gap (%)'}),
        SENS_TEXT=sens_text,SCENARIOS=table(scenarios[['scenario','method','valides','distance_change_pct','duration_change_pct','waiting']],{'scenario':'Scénario','method':'Méthode','valides':'Réalisables /18','distance_change_pct':'Variation distance (%)','duration_change_pct':'Variation durée (%)','waiting':'Attente moyenne'}),
        SCENARIOS_TEXT=scenarios_text,CONCLUSION=conclusion,
        SIZE_TEXT=size_text,EXAMPLE=(f"Le run illustré est {worst['job']['instance']}, graine {worst['job']['seed']} : "
            f"distance {number(worst['result']['cost'])}, référence {number(worst['reference_distance'])}, "
            f"gap {number(worst['gap_pct'])} %. Il est choisi comme pire gap ILS à 100 clients, et non comme meilleur exemple esthétique."),
        SCALING=table(scaling,{'n':'Clients','method':'Méthode','runs':'Essais','mean_time':'Temps moyen (s)','std_time':'Écart-type (s)','max_time':'Temps maximal (s)'}),
        CONVERGENCE=table(convergence,{'n':'Clients','method':'Méthode','initial_gap':'Gap initial (%)','final_gap':'Gap final (%)','last20_gain':'Gain derniers 20 % (pt)','late_runs':'Records tardifs','runs':'Essais'}),
        FAMILIES=table(families,{'family':'Famille','profile':'Méthode','mean_gap':'Gap moyen (%)','worst_gap':'Pire gap (%)'}))
    text=(ROOT/'docs/LIVRABLE_ILS_SOURCE.md').read_text(encoding='utf-8')
    for key,value in substitutions.items():text=text.replace('{{'+key+'}}',value)
    assert not re.search(r'\{\{[A-Z_]+\}\}',text)
    setup="""from pathlib import Path
import sys, json
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'algo/data.py').exists())
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from IPython.display import display, Image, Markdown
from algo.data import load
from algo.solver import solve, Settings, construct, warmup
from algo.verify import verify
summary = json.loads((ROOT / 'results/revision_ils/summary.json').read_text(encoding='utf-8'))
assert summary['complete'] and summary['runs'] == 1120
print('Étude vérifiée :', summary['runs'], 'essais ;', summary['instances'], 'instances.')
warmup();
"""
    code={'setup':setup,
          'toy':"from algo.model import Instance\nimport numpy as np\ntoy = Instance('exemple', np.array([[0,0],[8,0],[4,3]]), np.array([0,2,3]), np.array([0,5,4]), np.array([0,15,0]), np.array([60,25,40]), np.array([[0,8,5],[8,0,5],[5,5,0]]), 6., 2, 60.)\nfor route in [[[1,2]], [[2,1]]]:\n    checked = verify(route, toy)\n    assert checked['valid']\n    print(route, ': distance', checked['distance'], '; durée', checked['duration'], '; attente', checked['waiting'])",
          'toy_exact':"from controle.plne import solve_plne\nsmall = load(ROOT / 'data/instances/C101.vrp').subset([1, 2])\n# Les dix vrais cas exacts sont sauvegardés ; ce lecteur ne relance pas le benchmark.\nimport pandas as pd\nexact_records = [json.loads(p.read_text()) for p in sorted((ROOT / 'results/revision_ils/studies/exact').glob('*.json'))]\ndisplay(pd.DataFrame([{'clients': r['n'], 'statut': r['exact']['status'], 'coût': r['exact']['cost'], 'borne': r['exact']['lower_bound']} for r in exact_records]))",
          'demo':"demo_instance = load(ROOT / 'data/instances/C101.vrp')\ninitial, info = construct(demo_instance, 777, 12)\nfor method in ['ils', 'sa']:\n    result = solve(demo_instance, Settings(method=method, seed=777, seconds=.2), initial)\n    assert verify(result['routes'], demo_instance)['valid']\n    print(method.upper(), ': distance =', result['cost'], '; réalisable ;', round(result['runtime_s'], 3), 's')"}
    # subset is not needed by the reader demonstration; keep notebook independent of a model method.
    code['toy_exact']=code['toy_exact'].replace("small = load(ROOT / 'data/instances/C101.vrp').subset([1, 2])\n",'')
    cells=[];md_parts=[]
    captions={'representation':'Données, tournées et contrôle indépendant','schedule':'Arrivée, attente et service',
        'validation':'Rôles du modèle, des résolutions exactes et des expériences','moves':'Voisinages sous contraintes',
        'ils':'Recherche locale itérée','sa':'Recuit simulé sur mouvements directs','temperature':'Acceptation et refroidissement',
        'dispersion':'Dispersion par taille et méthode','paired':'Comparaison appariée',
        'gaps_100':'Gaps à 100 clients','gaps_1000':'Gaps à 1 000 clients',
        'convergence_100':'Convergence à 100 clients','convergence_200':'Convergence à 200 clients','convergence_1000':'Convergence à 1 000 clients',
        'times':'Temps et qualité','scaling':'Temps sous un nombre fixé de propositions','sensitivity':'Sensibilité des réglages','constraints':'Effet des contraintes modifiées',
        'routes':'Tournées du cas illustré','windows':'Fenêtres et débuts de service'}
    chunks=re.split(r'<!-- EXEC:([a-zA-Z0-9_]+) -->',text)
    for i,chunk in enumerate(chunks):
        if i%2==0:
            if chunk.strip():cells.append(nbformat.v4.new_markdown_cell(chunk.strip()));md_parts.append(chunk.strip())
            continue
        if chunk.startswith('fig_'):
            name=re.sub(r'^(gaps|convergence)(\d+)$',r'\1_\2',chunk[4:]);source=f"display(Image(filename=str(ROOT / 'livraison/ils_figures/{name}.png')))"
            cell=nbformat.v4.new_code_cell(source);cell.metadata['figure_captions']=[captions[name]];cells.append(cell)
            md_parts.append(f'![{captions[name]}](livraison/ils_figures/{name}.png)')
        else:
            assert chunk in code,chunk
            cells.append(nbformat.v4.new_code_cell(code[chunk]))
            if chunk=='setup':md_parts.append('Résultats vérifiés à partir des fichiers JSON de la campagne complète.')
            elif chunk=='demo':md_parts.append('Démonstration courte : exécuter la cellule correspondante du notebook (0,2 s par méthode, hors construction).')
    nb=nbformat.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python (projet CVRPTW)','language':'python','name':'algo-ils'}})
    directory=ROOT/'.tools/kernels/algo-ils';directory.mkdir(parents=True,exist_ok=True)
    (directory/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Python (projet CVRPTW)','language':'python'}))
    manager=KernelManager(kernel_name='algo-ils',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(directory.parent)]))
    try:
        NotebookClient(nb,timeout=180,km=manager,resources={'metadata':{'path':str(ROOT)}}).execute()
    finally:
        if manager.has_kernel:manager.shutdown_kernel(now=True)
        manager.cleanup_resources()
    path=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb';nbformat.write(nb,path)
    (ROOT/'LIVRABLE_FINAL.md').write_text('\n\n'.join(md_parts)+'\n',encoding='utf-8')
    (ROOT/'docs/LIVRABLE_SOURCE.md').write_text(text,encoding='utf-8')
    # A system-site-packages venv does not inherit Anaconda's Jupyter data path.
    base_templates=Path(sys.base_prefix)/'share/jupyter/nbconvert/templates'
    kwargs={'extra_template_basedirs':[str(base_templates)],'extra_template_paths':[str(base_templates)]} if base_templates.exists() else {}
    html,_=HTMLExporter(**kwargs).from_notebook_node(nb)
    (ROOT/'livraison/RAPPORT_CVRPTW.html').write_text(html,encoding='utf-8')
    print('Notebook exécuté, Markdown et HTML reconstruits ;',len(cells),'cellules.')


if __name__=='__main__':main()
