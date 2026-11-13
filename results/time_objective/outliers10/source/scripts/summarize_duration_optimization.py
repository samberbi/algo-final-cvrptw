"""Revalide les solutions ciblées et documente l'avant/après sans réécrire l'historique."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
import nbformat
from algo.data import load,reference
from algo.verify import verify


def summarize():
    folder=ROOT/'results/time_objective/outliers10'
    protocol=json.loads((folder/'protocol.json').read_text())
    expected={(name,seed) for name,seed in protocol['jobs']}
    base={}
    for path in (folder/'runs').glob('*.json'):
        r=json.loads(path.read_text());base[r['instance'],r['seed']]=(r,path)
    assert set(base)==expected,'Targeted batch incomplete'
    all_records=dict(base)
    for tag in ['outliers_hgs30','outliers_hgs120']:
        parent_folder=ROOT/'results/time_objective'/tag
        if not (parent_folder/'protocol.json').exists():continue
        p=json.loads((parent_folder/'protocol.json').read_text())
        for name,seed in p['jobs']:
            path=parent_folder/'runs'/f'{name}_{seed}.json'
            if not path.exists():continue
            r=json.loads(path.read_text())
            if r['valid'] and r['delta_pct'] <= all_records[name,seed][0].get('delta_pct',float('inf'))+1e-7:
                all_records[name,seed]=(r,path)
    rows=[];cache={}
    for key,(r,path) in sorted(all_records.items()):
        initial=base[key][0]
        if key[0] not in cache:
            ins=load(ROOT/'data/instances'/(key[0]+'.vrp'))
            rr,_=reference(ROOT/'data/instances'/(key[0]+'.sol'))
            ref=verify(rr,ins);assert ref['valid'];cache[key[0]]=(ins,ref)
        ins,ref=cache[key[0]]
        if r['valid']:
            check=verify(r['result']['routes'],ins)
            delta=100*(check['duration']/ref['duration']-1)
            assert check['valid'] and abs(delta-r['delta_pct'])<1e-7
            assert abs(check['duration']/10-r['duration'])<1e-7
        else:delta=None
        rows.append(dict(instance=r['instance'],n=ins.n,seed=r['seed'],valid=r['valid'],
            baseline_pct=initial['baseline_delta_pct'],first_variant_pct=initial.get('delta_pct'),
            final_pct=delta,first_runtime_s=initial['runtime_s'],cumulative_runtime_s=r['runtime_s'],
            source=path.relative_to(ROOT).as_posix()))
    runs=pd.DataFrame(rows)
    cases=runs.groupby(['instance','n'],as_index=False).agg(runs=('seed','size'),valid=('valid','sum'),
        before_mean_pct=('baseline_pct','mean'),first_mean_pct=('first_variant_pct','mean'),
        after_mean_pct=('final_pct','mean'),worst_after_pct=('final_pct','max'),
        mean_cumulative_s=('cumulative_runtime_s','mean'))
    runs.to_csv(folder/'AVANT_APRES_ESSAIS.csv',index=False)
    cases.to_csv(folder/'AVANT_APRES_INSTANCES.csv',index=False)
    from scripts.build_duration_delivery import table
    text='''### 6.9. Optimisation ciblée des dépassements en durée

**Périmètre.** Les 23 instances dépassant +6 % en moyenne et trois autres ayant un essai individuel au-dessus de +6 % ont été sélectionnées après l'audit initial. Les 26 instances représentent 43 couples instance–graine. Cette sélection est une mise au point sur les difficultés observées, pas un nouveau test indépendant sur tout le catalogue.

**Modifications réellement exécutées.** Le prototype `algo/duration_refine.py` compare des constructions Clarke–Wright et insertion séquentielle, puis les améliore avec la recherche locale externe de PyVRP 0.12.2. Les voisinages spatiaux et temporels sont élargis de 40 à 60, 80 et 120 clients. Jusqu'à quatre départs diversifient les constructions. Le réservoir de tournées est maintenant évalué en **durée** : un partitionnement choisit des tournées déjà réalisables en couvrant chaque client exactement une fois, sous la borne de flotte. Le mode historique distance reste explicite et les tests vérifient que deux ordres de même distance sont correctement départagés selon leurs attentes.

**Objectif et validité.** Les départs restent fixés à zéro et le coût reste la somme des trajets, attentes et services. Aucune référence n'est transmise au solveur. Chaque résultat final est contrôlé indépendamment sur les données originales. Une optimalité éventuelle du partitionnement concerne uniquement les tournées disponibles dans le réservoir, pas le CVRPTW complet.

**Budgets.** Le premier prototype demande au plus dix secondes de calcul au total, après préchauffage ; les appels natifs terminent avant d'être contrôlés, donc le temps observé et tout dépassement sont conservés. Les essais encore au-dessus du seuil peuvent être prolongés par le HGS en durée. Dans ce cas, le temps cumulé inclut intégralement la construction et la recherche du premier prototype, plus la continuation et sa préparation. Ces essais plus longs sont identifiés ; ils ne sont pas présentés comme des résultats à dix secondes. La campagne initiale allouait dix secondes à la recherche seule, avec construction ajoutée : les deux conventions restent visibles.

**Résultats par instance.** Les colonnes avant/après utilisent les mêmes graines disponibles. Le pire essai est affiché pour ne pas masquer un dépassement par une moyenne favorable.

'''+table(cases.rename(columns={'instance':'Instance','n':'Clients','runs':'Essais','valid':'Réalisables',
    'before_mean_pct':'Avant moyen (%)','first_mean_pct':'Prototype moyen (%)','after_mean_pct':'Après moyen (%)',
    'worst_after_pct':'Pire après (%)','mean_cumulative_s':'Calcul cumulé moyen (s)'}))
    above=int(runs.final_pct.gt(6).sum());failed=int((~runs.valid).sum())
    text+=f'''\n\nSur ce lot ciblé, **{len(runs)-above-failed}/{len(runs)} essais sont réalisables et au plus à +6 %**, {above} essais restent au-dessus et {failed} essais sont en échec. La moyenne après optimisation est calculée sur chaque instance du lot ; les valeurs individuelles et les chemins des solutions sont conservés dans `results/time_objective/outliers10/AVANT_APRES_ESSAIS.csv`.

**Portée.** Les valeurs précédentes des 646 résolutions ne sont pas remplacées. Ce tableau documente une nouvelle variante sur les cas ciblés et ne constitue ni une nouvelle moyenne indépendante des 356 instances, ni une preuve de gap à un optimum temporel. Le seuil porte toujours sur la durée du plan témoin réévalué. Les valeurs négatives, les temps supplémentaires et les dépassements éventuels sont conservés.'''
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ordered=cases.sort_values('before_mean_pct')
    y=range(len(ordered))
    fig,ax=plt.subplots(figsize=(9,8))
    ax.hlines(y,ordered.after_mean_pct,ordered.before_mean_pct,color='#b8c0ca')
    ax.scatter(ordered.before_mean_pct,y,label='Avant : moyenne des mêmes graines',color='#b45309',s=24)
    ax.scatter(ordered.after_mean_pct,y,label='Après : moyenne des mêmes graines',color='#128475',s=24)
    ax.axvline(6,color='#b45309',linestyle='--',label='Seuil +6 % au plan témoin')
    ax.set(yticks=list(y),yticklabels=ordered.instance,xlabel='Écart de durée au plan témoin (%)')
    ax.legend(fontsize=8);fig.tight_layout()
    fig.savefig(ROOT/'livraison/duree_figures/optimisation_ciblee.png',dpi=160);plt.close(fig)
    text+='''

![Évolution des écarts moyens des 26 instances ciblées, sur les mêmes graines.](../livraison/duree_figures/optimisation_ciblee.png)

**Lecture du graphique.** Chaque ligne représente une instance du lot ciblé. Le point orange indique son écart moyen avant modification, le point vert son écart moyen après les recherches réellement exécutées. Le segment relie les mêmes graines avant et après ; un déplacement vers la gauche signifie une diminution de durée. La ligne pointillée matérialise le seuil de +6 % par rapport au plan témoin réévalué. Les éventuelles continuations plus longues participent au point final ; leur temps cumulé figure dans le tableau.

**Intérêt et continuité.** Après l'audit des dépassements, ce graphique rend visible le progrès et permet de repérer les cas restant proches du seuil. Il complète le tableau sans remplacer la colonne du pire essai : un point moyen sous la ligne ne suffirait pas à valider toutes les graines. Il concerne les 26 instances sélectionnées, et non l'ensemble du catalogue ni un optimum temporel connu.'''
    test_path=folder/'tests.xml'
    if test_path.exists():
        import xml.etree.ElementTree as ET
        tests=ET.parse(test_path).getroot()
        failures=len(list(tests.iter('failure')))+len(list(tests.iter('error')))
        skipped=len(list(tests.iter('skipped')))
        passed=len(list(tests.iter('testcase')))-skipped-failures
        text+=f'\n\n**Vérification du code.** La suite complète exécutée après ajout du prototype compte {passed} tests réussis, {failures} échecs et {skipped} tests ignorés. Le détail est conservé dans `results/time_objective/outliers10/tests.xml`. Les tests comprennent notamment la sélection en durée lorsque les distances sont identiques, la faisabilité du prototype et les contrôles historiques de non-régression.'
    pool_gains=[]
    for r,_ in base.values():
        step=r.get('result',{}).get('recombination')
        if step:
            pool_gains.append(float(step['initial_cost'])-float(step['cost']))
    if pool_gains:
        text+=f'''\n\n**Diagnostic du partitionnement.** Sur {len(pool_gains)} appels au réservoir, {sum(g>1e-7 for g in pool_gains)} améliorent directement la durée de l'archive avant la dernière recherche locale. Le plus grand gain de cette étape vaut {max(pool_gains):.1f} unités de durée. Ce diagnostic compare l'entrée et la sortie de l'étape dans les traces ; il ne remplace pas une étude d'ablation complète à budget identique.'''
    (ROOT/'docs/OPTIMISATION_DUREE_CIBLEE.md').write_text(text+'\n',encoding='utf-8')
    return text,dict(instances=len(cases),runs=len(runs),above_6=above,failed=failed,
        worst_pct=float(runs.final_pct.max()),mean_instance_pct=float(cases.after_mean_pct.mean()))


def add_to_notebook(nb):
    from scripts.revision_duree import insert_before,marked
    text,info=summarize()
    nb.cells=[c for c in nb.cells if c.metadata.get('revision_duree')!='optimisation']
    insert_before(nb,'## 7.',[marked(text,'optimisation')])
    return info


def main():
    from scripts.revision_duree import write_markdown
    path=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb'
    nb=nbformat.read(path,as_version=4)
    info=add_to_notebook(nb)
    nbformat.validate(nb);nbformat.write(nb,path);write_markdown(nb)
    print(json.dumps(info,indent=2))


if __name__=='__main__':main()
