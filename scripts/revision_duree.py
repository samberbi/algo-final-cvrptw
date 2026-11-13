"""Compléments ciblés du livrable : pédagogie, audit exhaustif et temps réel.

Ne relance aucune résolution et ne remplace aucun résultat de campagne.
Les solutions des essais locaux sont contrôlées avant leur présentation séparée.
"""
from pathlib import Path
import inspect
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nbformat
import pandas as pd
from algo import duration
from algo.data import load, reference
from algo.verify import verify

OUT = ROOT / 'results/time_objective/revision_duree'
FIG = ROOT / 'livraison/duree_figures'


def table(frame):
    from scripts.build_duration_delivery import table as render
    return render(frame)


def marked(text, key):
    cell = nbformat.v4.new_markdown_cell(text)
    cell.metadata['revision_duree'] = key
    return cell


def insert_before(nb, heading, cells):
    index = next(i for i, c in enumerate(nb.cells)
                 if c.cell_type == 'markdown' and heading in c.source)
    if not nb.cells[index].source.startswith(heading):
        source = nb.cells[index].source
        split = source.index(heading)
        before = nbformat.v4.new_markdown_cell(source[:split].rstrip())
        after = nbformat.v4.new_markdown_cell(source[split:])
        nb.cells[index:index+1] = [before, after]
        index += 1
    nb.cells[index:index] = cells


def route_figure(name, record, path):
    """Carte complète et horaires d'une tournée réelle du même essai."""
    ins = load(ROOT / 'data/instances' / (name + '.vrp'))
    checked = verify(record['result']['routes'], ins)
    assert checked['valid']
    routes = record['result']['routes']
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    # Choisir la tournée à plus forte attente sans masquer le critère de sélection.
    index = max(range(len(routes)), key=lambda i: checked['routes'][i]['waiting'])
    route = routes[index]
    for other in routes:
        nodes = [0, *other, 0]
        axes[0].plot(ins.xy[nodes, 0], ins.xy[nodes, 1], linewidth=.5, color='#b8c0ca', alpha=.5)
    nodes = [0, *route, 0]
    axes[0].plot(ins.xy[nodes, 0], ins.xy[nodes, 1], linewidth=1.5, color='#176b89', label='Tournée détaillée à droite')
    axes[0].scatter(*ins.xy[0], marker='s', color='black', label='Dépôt', zorder=3)
    axes[0].set(title=f'{name} : {len(routes)} tournées', xlabel='Coordonnée x', ylabel='Coordonnée y')
    axes[0].legend(fontsize=8)
    clock = 0.
    previous = 0
    colors = {'Trajet': '#64748b', 'Attente': '#d6942c', 'Service': '#128475'}
    for position, client in enumerate(route):
        travel = ins.travel[previous, client]
        arrival = clock + travel
        begin = max(arrival, ins.early[client])
        for left, width, kind in [(clock, travel, 'Trajet'), (arrival, begin-arrival, 'Attente'),
                                  (begin, ins.service[client], 'Service')]:
            axes[1].barh(0, width/10, left=left/10, color=colors[kind], height=.4)
        # Quelques repères seulement : tous les identifiants se chevaucheraient à 1 000 clients.
        if position % max(1, len(route)//5) == 0:
            axes[1].annotate(str(client), (begin/10, .26), fontsize=8, ha='center')
        clock = begin + ins.service[client]
        previous = client
    axes[1].barh(0, ins.travel[previous, 0]/10, left=clock/10, color=colors['Trajet'], height=.4)
    from matplotlib.patches import Patch
    axes[1].legend(handles=[Patch(facecolor=c, label=k) for k,c in colors.items()], fontsize=8,
                   loc='lower center',bbox_to_anchor=(.5,1.01),ncols=3)
    axes[1].set(title=f'Tournée {index+1} · {len(route)} clients · attente maximale de cet essai',
                xlabel='Temps depuis le départ à zéro (u.t.)', yticks=[],ylim=(-.4,.4))
    axes[1].set_title(axes[1].get_title(),pad=40,fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return index + 1, checked['routes'][index]['waiting']/10


def augment(nb, runs, cases, sizes):
    """Ajoute des sections identifiées sans toucher aux cellules de calcul existantes."""
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    nb.cells = [c for c in nb.cells if not c.metadata.get('revision_duree')]
    # Le modèle lu par le notebook reste aligné sur son fichier de référence.
    for cell in nb.cells:
        if cell.cell_type == 'markdown' and cell.source.startswith('## 2. Modélisation'):
            cell.source = (ROOT/'docs/MODELE_DUREE.md').read_text(encoding='utf-8').strip()
        if cell.cell_type == 'markdown' and cell.source.startswith('### 4.4.') and 'Simplification de C7' not in cell.source:
            marker='\n\nL’implémentation propre'
            rows='''
| Simplification de C7 pour l'objectif durée | Retirer uniquement une borne supérieure redondante | Dix optimums exacts conservés ; fermeture du dépôt maintenue |
| Audit exhaustif des écarts temporels | Contrôler le seuil par essai et par instance | 646 solutions et 356 témoins revalidés ; dépassements listés en section 6.7 |
| Constructions alternatives et intensification locale | Réduire les mauvaises durées de départ | Essais exploratoires séparés, solutions revalidées et régressions conservées |
| Carte, horaires et temps d'exécution | Relier représentation, objectif et coût de calcul | Figures issues des mêmes résultats enregistrés et commentées individuellement |'''
            assert marker in cell.source
            cell.source=cell.source.replace(marker,rows+marker)

    core = runs[runs.core].copy()
    checked_runs = runs.copy()
    checked_runs['au_plus_6_pct'] = checked_runs.valid & checked_runs.delta_reference_pct.le(6.)
    checked_runs.to_csv(OUT/'TOUS_LES_ESSAIS_DUREE.csv', index=False)
    checked_cases = cases.copy()
    checked_cases['moyenne_au_plus_6_pct'] = checked_cases.mean_delta_reference_pct.le(6.)
    checked_cases.to_csv(OUT/'TOUTES_LES_INSTANCES_DUREE.csv', index=False)
    worst = checked_cases[~checked_cases.moyenne_au_plus_6_pct].sort_values('mean_delta_reference_pct', ascending=False)
    worst.to_csv(OUT/'INSTANCES_AU_DESSUS_DE_6.csv', index=False)
    counts=[]
    for n, group in core.groupby('n'):
        local_cases=cases[cases.n.eq(n)]
        counts.append({'Clients':int(n), 'Instances':len(local_cases),
                       'Instances > 6 % (moyenne)':int(local_cases.mean_delta_reference_pct.gt(6).sum()),
                       'Essais hybrides':len(group),
                       'Essais > 6 %':int(group.delta_reference_pct.gt(6).sum()),
                       'Pire écart essai (%)':group.delta_reference_pct.max()})
    summary=pd.DataFrame(counts)
    summary.to_csv(OUT/'BILAN_SEUIL_6.csv',index=False)

    # Extraits copiés des fonctions réellement utilisées, sans pseudo-code renommé.
    construct=inspect.getsource(duration.construct)
    solve=inspect.getsource(duration.solve)
    fragment=solve[solve.index('    own_seconds ='):solve.index('    final =')]
    from algo.duration_moves import walk
    walk_source=inspect.getsource(walk.py_func)
    fragment_walk=walk_source[walk_source.index('        delta ='):walk_source.index('        accepted += 1')]
    pedagogy='''### 4.5. Suivre les données dans les fonctions réelles

Une solution est une liste de listes : `[[1, 2]]` représente dépôt → 1 → 2 → dépôt. `encode` la convertit en une matrice de clients et un tableau de longueurs pour les boucles compilées ; `decode` reconstruit la liste. Ces deux représentations décrivent les mêmes tournées, sans ajouter le dépôt dans les listes de clients.

**Construire (`construct`).** L'entrée est une instance et une graine ; la sortie contient les tournées retenues et le temps de construction. Les insertions utilisent les trajets pour guider la construction, mais les solutions complètes sont comparées selon leur durée indépendante, attentes comprises. L'extrait suivant est la fonction réelle de `algo/duration.py`.

```python
'''+construct.strip()+'''
```

**Enchaîner les recherches (`solve`).** À partir de la solution construite, cette partie réelle de la fonction répartit le budget et transmet les tournées de l'ILS au HGS externe. Elle n'utilise pas le plan de référence pour chercher une solution.

```python
'''+fragment.rstrip()+'''
```

**Accepter un mouvement (`walk`).** Après avoir recalculé les durées et vérifié les tournées touchées, `ca` et `cb` sont leurs nouvelles durées, et `costs` contient les anciennes. Le delta est donc la variation de durée complète, et non une simple économie de deux arcs. En mode perturbation, une hausse réalisable est possible ; en mode recherche, une baisse est acceptée, et le recuit peut accepter une hausse selon sa température. Extrait réel de `algo/duration_moves.py` :

```python
'''+fragment_walk.rstrip()+'''
```

**Exemple avant/après.** Dans l'exemple des deux clients, remplacer `[1, 2]` par `[2, 1]` fait passer la durée de 34 à 28 : le delta affiché est −6 (−60 dans les unités internes). Le trajet reste 18, les services restent 9 et l'attente passe de 7 à 1. La solution candidate doit toujours respecter les fenêtres et la capacité avant son acceptation. Un changement d'ordre n'est donc utile que si son évaluation temporelle complète le confirme.

**Lien avec la version précédente.** Les principes construction → perturbation → intensification → validation sont conservés. En revanche, la campagne en durée a mesuré une descente échantillonnée plus simple et un budget de dix secondes. Les performances de l'ancien moteur avancé en distance ne constituent pas une mesure du même moteur en durée. Restaurer ses mécanismes exige d'adapter aussi les filtres, les coûts et les acceptations ; renommer uniquement la fonction objectif ne suffirait pas.'''
    insert_before(nb,'## 5.',[marked(pedagogy,'pedagogie')])

    runtime='''### 6.6. Taille des instances et temps d'exécution réel

Le temps de calcul est une seconde mesure, distincte de la durée des tournées minimisée. Pour toutes les tailles, le budget de recherche est dix secondes ; le calcul total comprend en plus la construction et la préparation. Nous utilisons les temps effectivement enregistrés et donnons le même poids à chaque instance après moyenne de ses graines.

'''+table(sizes[['n','instances','mean_calculation_s']].rename(columns={'n':'Clients','instances':'Instances','mean_calculation_s':'Calcul total moyen (s)'}))
    fig,ax=plt.subplots(figsize=(8,4))
    ax.plot(sizes.n,sizes.mean_calculation_s,'o-',label='Calcul total moyen observé')
    ax.axhline(10,color='#b45309',linestyle='--',label='Budget de recherche fixé')
    ax.set(xlabel='Nombre de clients',ylabel='Temps de calcul (secondes)',ylim=(9,15.5))
    ax.legend();fig.tight_layout();fig.savefig(FIG/'taille_temps.png',dpi=160);plt.close(fig)
    runtime+='''

![Temps de calcul total selon la taille, pour dix secondes de recherche.](../livraison/duree_figures/taille_temps.png)

**Lecture et intérêt.** Les points représentent le calcul total moyen par taille, et la ligne pointillée le budget de recherche commun. Le total passe de 10,04 s à 100 clients à 14,28 s à 1 000 clients. Ce surplus renseigne sur le coût pratique de construction et de préparation ; il montre pourquoi « dix secondes de recherche » ne signifie pas « dix secondes du lancement au résultat ». Après les courbes de qualité pendant la recherche, ce graphique complète le compromis qualité–temps par le coût réellement attendu par l'utilisateur.

**Limite.** Puisque l'arrêt de la recherche dépend d'un budget fixé, ces points ne permettent pas de déduire une complexité asymptotique. Il faudrait aussi chronométrer une quantité de travail identique, comme un nombre de mouvements, pour étudier intrinsèquement le passage à l'échelle.'''

    audit=r'''### 6.7. Vérification exhaustive des écarts et du seuil de 6 %

Nous avons recalculé les horaires et contraintes de chacune des 646 solutions enregistrées et des 356 plans témoins, sur les fichiers originaux vérifiés par empreinte. Les durées sont comparées aux coûts enregistrés et chaque écart est recalculé par $100(T/T_{\mathrm{témoin}}-1)$. Les 646 solutions sont réalisables. Les tableaux exhaustifs `TOUS_LES_ESSAIS_DUREE.csv` et `TOUTES_LES_INSTANCES_DUREE.csv` sont dans `results/time_objective/revision_duree/` ; ils conservent aussi le budget, le temps réel et le chemin du résultat source.

Le seuil est appliqué à l'écart signé : « au plus +6 % » signifie ne pas dépasser la durée du témoin de plus de 6 %. Une valeur négative importante n'est pas un échec de ce critère. Ce critère ne certifie pas une proximité de 6 % avec l'optimum temporel inconnu. Le bilan suivant porte uniquement sur les 472 essais hybrides de couverture ; les répétitions des autres méthodes restent dans le CSV de tous les essais.

'''+table(summary)+f'''

**Bilan du catalogue mesuré : {len(worst)} instances sur 356 dépassent +6 % en moyenne.** Une moyenne globale favorable n'annule pas ces dépassements ; la liste complète figure dans `INSTANCES_AU_DESSUS_DE_6.csv`. Les cas suivants sont ceux à améliorer, sans retirer leurs essais du bilan :

'''+table(worst[['instance','n','attempts','mean_delta_reference_pct','mean_calculation_s']])

    local_rows=[]
    retained=OUT/'essais_locaux';retained.mkdir(exist_ok=True)
    paths=sorted(retained.glob('*.json')) or sorted((ROOT/'results/local/multistart_duration').glob('*.json'))
    for path in paths:
        r=json.loads(path.read_text(encoding='utf-8'))
        ins=load(ROOT/'data/instances'/(r['instance']+'.vrp'))
        control=verify(r['routes'],ins)
        ref_routes,_=reference(ROOT/'data/instances'/(r['instance']+'.sol'))
        ref=verify(ref_routes,ins)
        assert control['valid'] and ref['valid']
        value=control['duration']/10
        delta=100*(control['duration']/ref['duration']-1)
        assert abs(value-r['duration'])<1e-7 and abs(delta-r['gap_duration_reference_pct'])<1e-7
        archived=retained/path.name
        archived.write_text(json.dumps(r,indent=2),encoding='utf-8')
        old=core[core.instance.eq(r['instance']) & core.seed.eq(r['seed'])]
        if len(old)!=1:continue
        local_rows.append({'Instance':r['instance'],'Graine':r['seed'],
                           'Écart campagne (%)':float(old.iloc[0].delta_reference_pct),
                           'Écart essai local (%)':delta,'Durée locale':value,
                           'Calcul local (s)':r['calculation_s'],'Réalisable':True,
                           'source':archived.relative_to(ROOT).as_posix()})
    local=pd.DataFrame(local_rows)
    if len(local):
        local.to_csv(OUT/'OPTIMISATIONS_LOCALES_SEPAREES.csv',index=False)
        audit+='''

**Optimisations exploratoires, distinctes de la campagne.** Nous avons testé des départs Clarke–Wright et insertion séquentielle, sélectionnés en durée, suivis de la recherche locale externe de PyVRP avec des voisinages de 40, 60, 80 puis 120 clients. Quatre départs sont essayés dans cette variante. Les données et contraintes restent identiques, et chaque solution ci-dessous est revalidée indépendamment.

'''+table(local.drop(columns=['source']))+'''

Ces paramètres ont été explorés sur des cas déjà identifiés comme difficiles : ce sont des résultats de mise au point, pas une validation indépendante ni une nouvelle moyenne sur 356 instances. Les temps locaux sont mesurés après préchauffage ; ils concernent le calcul de chaque variante, sans absorber le coût des expériences exploratoires antérieures. Sur C1_10_6, les deux écarts sont 6,28 % et 5,86 %, soit 6,07 % en moyenne. Les quatre départs n'ont pas amélioré les résultats du premier essai renforcé sur ce cas ; le temps supplémentaire n'apporte donc pas ici de gain mesurable. Les résultats initiaux et locaux restent dans des colonnes et fichiers distincts.'''

    illustrations='''### 6.8. Relier une solution réelle à sa carte et à ses horaires

Les schémas suivants reprennent deux solutions de la campagne, avec la graine 4101 et la méthode hybride. Ils ne proviennent pas des essais locaux d'optimisation et n'introduisent aucune résolution supplémentaire. C101 illustre un cas groupé stable ; R2_10_8 fournit le contraste avec une grande instance plus variable.
'''
    for name in ['C101','R2_10_8']:
        r=json.loads((ROOT/f'results/time_objective/catalogue/runs/{name}_4101_hybrid.json').read_text())
        number,waiting=route_figure(name,r,FIG/(name+'_carte_horaires.png'))
        illustrations+=f'''

![{name} : carte complète et détail horaire d'une tournée du même essai.](../livraison/duree_figures/{name}_carte_horaires.png)

**Lecture de {name}.** À gauche, les lignes relient les visites dans leur ordre réel et reviennent au dépôt carré ; cette vue situe toutes les tournées. La tournée en bleu est celle détaillée à droite : la tournée {number}, choisie car son attente est maximale dans cet essai ({waiting:.1f} u.t.). Dans le diagramme horaire, le gris correspond aux trajets, l'orange aux attentes et le vert aux services ; quelques numéros de clients donnent des repères sans superposer tous les identifiants. Tous les segments de cette tournée sont conservés. Les axes spatiaux de la carte et l'axe temporel du diagramme ont donc des significations différentes.

**Intérêt et lien avec les statistiques.** La carte explique l'organisation des trajets ; le diagramme montre pourquoi cette organisation doit aussi être évaluée dans le temps. Ensemble, ils relient la représentation en graphe du début aux durées mesurées dans les tableaux. Cette solution individuelle aide à comprendre le fonctionnement, mais la stabilité et la qualité générale doivent rester évaluées à partir des répétitions et du catalogue complet.
'''
    insert_before(nb,'## 7.',[marked(runtime,'temps'),marked(audit,'audit'),marked(illustrations,'illustrations')])
    # Les expériences ciblées restent une section séparée du bilan historique.
    protocol_path=ROOT/'results/time_objective/outliers10/protocol.json'
    if protocol_path.exists():
        jobs=json.loads(protocol_path.read_text())['jobs']
        if all((protocol_path.parent/'runs'/f'{name}_{seed}.json').exists() for name,seed in jobs):
            from scripts.summarize_duration_optimization import add_to_notebook
            add_to_notebook(nb)
    return {'instances':len(cases),'runs':len(runs),'instances_above_6':len(worst),
            'core_runs_above_6':int(core.delta_reference_pct.gt(6).sum()),'local_checked':len(local_rows)}


def write_markdown(nb):
    parts=[]
    for cell in nb.cells:
        if cell.cell_type=='markdown':
            parts.append(cell.source.replace('(../livraison/','(livraison/'))
        elif cell.metadata.get('figure_captions'):
            name=re.search(r"livraison/duree_figures/([^']+)",cell.source).group(1)
            parts.append('!['+cell.metadata['figure_captions'][0]+'](livraison/duree_figures/'+name+')')
    (ROOT/'LIVRABLE_FINAL.md').write_text('\n\n'.join(parts)+'\n',encoding='utf-8')
    journal=next(c.source for c in nb.cells if c.cell_type=='markdown' and c.source.startswith('### 4.4.'))
    if any(c.metadata.get('revision_duree')=='optimisation' for c in nb.cells):
        journal+='\n\n## Complément : optimisation ciblée en durée\n\nLe profil `duration_refined` ajoute plusieurs constructions, une recherche locale externe PyVRP à voisinages progressifs et un réservoir de tournées évalué en durée. Les essais encore défavorables reçoivent une continuation HGS identifiée, avec le temps précédent inclus. Les résultats individuels, les budgets et les limites sont détaillés dans [OPTIMISATION_DUREE_CIBLEE.md](OPTIMISATION_DUREE_CIBLEE.md). La campagne initiale reste inchangée.\n'
    if any(c.metadata.get('reporting_completion') for c in nb.cells):
        journal+='\n\n## Compléments expérimentaux et rédactionnels\n\nLes sections 6.10 et 6.11 ajoutent une [sensibilité contrôlée](SENSIBILITE_CONTROLEE_DUREE.md) du profil ILS–HGS et une [analyse des scénarios](ANALYSE_SCENARIOS_DUREE.md) sur le catalogue initial. Le contexte métier, la réduction TSP, les fenêtres par objet/client, le départ à zéro et les budgets sont explicités. Cette passe ne modifie pas les opérateurs, le profil par défaut ou les meilleures tournées conservées.\n'
    if any(c.metadata.get('cpu_completion') for c in nb.cells):
        journal+='\n\n## Réduction du temps CPU\n\nLe profil renforcé réutilise désormais les voisins calculés sur une même instance immuable et évite les transferts identiques vers le moteur. Le tri stable et les préfixes sont vérifiés contre PyVRP. La [section CPU et parallélisme](TEMPS_CPU_ET_PARALLELISME.md) rapporte les mesures avant/après à travail et coûts identiques, puis les résultats sur un, deux et quatre processus. Le calcul du CPU inclut tous les workers. Aucun ancien temps écoulé n’est renommé en temps CPU ; les meilleurs résultats historiques restent conservés.\n'
    (ROOT/'docs/JOURNAL_EVOLUTION_ALGORITHME.md').write_text('# Évolution vers l’objectif durée\n\n'+journal.rstrip()+'\n',encoding='utf-8')


def main():
    from scripts.analyze_duration import analyze
    runs,cases,sizes,*_=analyze()
    target=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb'
    nb=nbformat.read(target,as_version=4)
    original_codes=[c.source for c in nb.cells if c.cell_type=='code']
    result=augment(nb,runs,cases,sizes)
    assert original_codes==[c.source for c in nb.cells if c.cell_type=='code']
    nbformat.validate(nb);nbformat.write(nb,target)
    write_markdown(nb)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
