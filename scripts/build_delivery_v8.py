"""One coherent assessed notebook/report, generated only after full catalog audit."""
from pathlib import Path
import hashlib, inspect, json, platform, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import nbformat
from scripts.analyze_catalog_v8 import analyze,BASE
from scripts.analyze_v7 import analyze as analyze_v7
from scripts.build_ils_v5_delivery import execute
from scripts.export_report import markdown_table
from algo.data import load
from algo.verify import verify
from scripts.editorial_math_review_v8 import GRAPH_TEXT, NOTATION_TEXT, graph_figure, prose_pass
from scripts.hgs_method_notes import HGS_DETAILS

FIG=ROOT/'livraison/catalog_v8_figures'


def image_cell(name,caption):
    cell=nbformat.v4.new_code_cell(f"display(Image(filename=str(ROOT/'livraison/catalog_v8_figures/{name}.png')))")
    cell.metadata['figure_captions']=[caption]
    return cell


def figures(df,cases,sizes):
    FIG.mkdir(parents=True,exist_ok=True)
    fig,ax=plt.subplots(figsize=(8,3.5))
    ax.bar(sizes.n.astype(str),sizes.mean_instance_gap,color='#0f766e')
    ax.axhline(6,color='#b45309',linestyle='--',label='Cible moyenne : 6 %')
    ax.axhline(5,color='#475569',linestyle=':',label='Repère : 5 %')
    ax.set(xlabel='Nombre de clients',ylabel='Gap moyen par instance (%)',title='Toutes les tailles du catalogue, sans sélection des résultats')
    ax.legend(fontsize=8);fig.tight_layout();fig.savefig(FIG/'sizes.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3.5))
    groups=[cases[cases.n.eq(n)].mean_gap.dropna().to_numpy() for n in sizes.n]
    ax.boxplot(groups,tick_labels=[str(n) for n in sizes.n],showmeans=True)
    ax.axhline(6,color='#b45309',linestyle='--')
    ax.set(xlabel='Nombre de clients',ylabel='Gap moyen de chaque instance (%)',title='Dispersion entre instances ; chaque point défavorable est conservé')
    fig.tight_layout();fig.savefig(FIG/'dispersion.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3.5))
    for n in sizes.n:
        values=np.sort(cases[cases.n.eq(n)].mean_gap.dropna())
        ax.step(values,np.arange(1,len(values)+1)/len(values),where='post',label=f'{n} clients')
    ax.axvline(6,color='#b45309',linestyle='--')
    ax.set(xlabel='Gap moyen par instance (%)',ylabel='Part cumulée des instances',title='Part du catalogue atteignant chaque niveau de qualité',ylim=(0,1.02))
    ax.legend(fontsize=8);fig.tight_layout();fig.savefig(FIG/'ecdf.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3.5))
    for n in sizes.n:
        g=df[df.n.eq(n)&df.valid]
        ax.scatter(g.total_s,g.gap_pct,label=f'{n} clients',s=14,alpha=.55)
    ax.axhline(6,color='#b45309',linestyle='--')
    ax.set(xlabel='Temps réel du pipeline, construction comprise (s)',ylabel='Gap de chaque essai (%)',title='Temps et qualité : budgets prédéfinis par taille')
    ax.legend(fontsize=7,ncol=2);fig.tight_layout();fig.savefig(FIG/'time_gap.png',dpi=160);plt.close(fig)
    heat=cases.pivot_table(index='family',columns='n',values='mean_gap',aggfunc='mean')
    fig,ax=plt.subplots(figsize=(7,3.7))
    im=ax.imshow(heat.to_numpy(),aspect='auto',cmap='YlOrRd',vmin=0)
    ax.set_xticks(np.arange(len(heat.columns)),[str(n) for n in heat.columns])
    ax.set_yticks(np.arange(len(heat.index)),heat.index)
    for i in range(len(heat.index)):
        for j in range(len(heat.columns)):
            ax.text(j,i,f'{heat.iloc[i,j]:.2f}',ha='center',va='center',fontsize=9)
    ax.set(xlabel='Nombre de clients',title='Gap moyen (%) par famille et par taille')
    fig.colorbar(im,ax=ax,label='Gap (%)');fig.tight_layout();fig.savefig(FIG/'families.png',dpi=160);plt.close(fig)


def illustration(name):
    path=BASE/'runs'/f'{name}_2101.json'
    r=json.loads(path.read_text(encoding='utf-8'))
    assert r['valid']
    ins=load(ROOT/'data/instances'/(name+'.vrp'))
    routes=r['result']['routes'];checked=verify(routes,ins)
    assert checked['valid']
    fig,(ax,gantt)=plt.subplots(1,2,figsize=(10,3.7))
    colors=plt.get_cmap('tab20')
    for i,route in enumerate(routes):
        points=ins.xy[[0,*route,0]]
        ax.plot(points[:,0],points[:,1],color=colors(i%20),linewidth=.8,alpha=.7)
    ax.scatter(ins.xy[1:,0],ins.xy[1:,1],s=8,color='#334155',zorder=3)
    ax.scatter(*ins.xy[0],marker='s',s=60,color='#dc2626',label='Dépôt',zorder=4)
    ax.set(title=f'{name} : {len(routes)} tournées',xlabel='Coordonnée x',ylabel='Coordonnée y');ax.legend(fontsize=7)
    for i,detail in enumerate(checked['routes'][:4]):
        previous=0.
        for stop in detail['schedule']:
            for start,end,color in [(previous,stop['arrival'],'#60a5fa'),(stop['arrival'],stop['start'],'#fbbf24'),(stop['start'],stop['finish'],'#10b981')]:
                if end>start:
                    gantt.broken_barh([(start/10,(end-start)/10)],(i-.32,.64),facecolors=color)
            previous=stop['finish']
        if detail['duration']>previous:
            gantt.broken_barh([(previous/10,(detail['duration']-previous)/10)],(i-.32,.64),facecolors='#60a5fa')
    gantt.set(yticks=list(range(min(4,len(routes)))),yticklabels=[f'Tournée {i+1}' for i in range(min(4,len(routes)))],
        xlabel='Temps (unités du benchmark)',title='Quatre premières tournées, graine 2101')
    from matplotlib.patches import Patch
    gantt.legend(handles=[Patch(color='#60a5fa',label='Trajet'),Patch(color='#fbbf24',label='Attente'),Patch(color='#10b981',label='Service')],fontsize=7)
    fig.tight_layout();fig.savefig(FIG/f'example_{name}.png',dpi=160);plt.close(fig)
    service=float(ins.service[1:].sum())
    assert abs(checked['duration']-checked['travel']-checked['waiting']-service)<1e-6
    return dict(instance=name,clients=ins.n,vehicles=len(routes),fleet_limit=ins.vehicles,
        distance=checked['distance']/10,bks=r['reference_distance'],gap=r['gap_pct'],
        duration=checked['duration']/10,travel=checked['travel']/10,
        waiting=checked['waiting']/10,service=service/10,
        max_load=max(d['load'] for d in checked['routes']),capacity=ins.capacity,
        latest_return=checked['makespan']/10,depot_closing=ins.horizon/10)


def main():
    df,cases,sizes,a=analyze()
    assert a['complete'] and a['executed']==472 and a['distinct_instances']==356
    _,paired_summary,paired_cases,paired_a=analyze_v7('continuation_120')
    pair=paired_summary.set_index('variant')
    own=pair.loc['baseline'];hybrid=pair.loc['hybrid_hgs'];gain=paired_a['comparisons'][0]
    all_scope=a['scopes']['catalog_356'];core=a['scopes']['core_116'];common=a['scopes']['common_seed_356']
    figures(df,cases,sizes)
    graph_figure(ROOT)
    examples=pd.DataFrame([illustration(n) for n in ['C101','R2_10_4']])
    examples.to_csv(BASE/'examples.csv',index=False)
    foundation=BASE/'foundation/Livrable_Final_CVRPTW.ipynb'
    if not foundation.exists():
        foundation.parent.mkdir(parents=True,exist_ok=True)
        foundation.write_bytes((ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb').read_bytes())
    old=nbformat.read(foundation,as_version=4)
    nb=nbformat.v4.new_notebook()
    nb.metadata['report_subtitle']='Solution hybride ILS–HGS — Modèle, améliorations et catalogue complet'
    def md(s):nb.cells.append(nbformat.v4.new_markdown_cell(s))
    header=f'''# Livrable final — Optimisation CVRPTW par une solution hybride ILS–HGS

**CESI — Algorithmique et optimisation — Modèle, implémentation et validation expérimentale**

## 1. Problème, contribution et résultat principal

Nous cherchons des tournées qui livrent chaque client une seule fois, respectent la capacité et les fenêtres horaires strictes, puis reviennent au dépôt avant sa fermeture. Pour comparer les solutions aux références DIMACS, l’objectif expérimental est la distance totale. Le nombre de véhicules constitue une borne maximale ; aucun véhicule supplémentaire ne permet de violer une contrainte.

Nous avons développé le constructeur, notre recherche locale itérée, les contrôles et leur intégration avec le moteur HGS de **PyVRP 0.12.2**, attribué à ses auteurs. Le HGS est une bibliothèque externe ; notre contribution porte sur la solution hybride, son code d’intégration, sa validation et son évaluation.

Le catalogue complet contient **356 instances**, de 100 à 1 000 clients. La campagne comprend **472 pipelines évalués**, dont **448 nouveaux** et **24 réutilisés avec leur temps intégralement compté**. La moyenne donnant le même poids à chaque instance est **{all_scope['mean_instance_gap']:.3f} %**. Le sous-ensemble demandé de **116 instances à 100 et 1 000 clients**, avec deux graines par instance, obtient **{core['mean_instance_gap']:.3f} %**.

La moyenne à 1 000 clients, les cas défavorables, la couverture et les temps sont détaillés dans les tableaux. Une moyenne sous un seuil ne signifie pas que chaque instance respecte ce seuil. Les différentes pondérations sont explicitement distinguées.

Le sujet initial évoque également la durée et le trafic variable. Notre périmètre est statique et symétrique : nous calculons durée, attente et service, mais optimisons ici la distance compatible avec les références. Le trafic variable, une garantie d’optimalité et les tailles supérieures à 1 000 clients ne sont pas démontrés.
'''
    md(header)
    nb.cells.append(nbformat.v4.new_code_cell("from pathlib import Path\nimport sys,json\nimport numpy as np\nimport pandas as pd\nfrom IPython.display import Image,display\nROOT=next(p for p in [Path.cwd(),*Path.cwd().parents] if (p/'algo/hybrid_reference.py').exists())\nif str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))\nfrom algo.data import load\nfrom algo.verify import verify\nfrom algo.optimized import solve,warmup\nfrom algo.profiles import production_settings\nwarmup()\nruns=pd.read_csv(ROOT/'results/catalog_v8/flat.csv')\nassert len(runs)==472\nassert runs.instance.nunique()==356"))
    md(GRAPH_TEXT)
    nb.cells.append(image_cell('graph_model','Modélisation du réseau en graphe orienté ; deux tournées réalisables sur un exemple pédagogique vérifié.'))
    md(NOTATION_TEXT)
    # Preserve the complete mathematical model and the real, explained Python
    # examples; replace obsolete campaign narratives with a single final study.
    nb.cells.extend(old.cells[2:13])
    md(f'''## 4.5. Hybridation retenue et attribution du moteur

Notre ILS produit une solution initiale de qualité, puis le HGS de PyVRP explore plusieurs solutions au sein d’une population, avec croisement et recherche locale. La solution ILS est transmise au moteur externe sans modifier demandes, capacité, fenêtres, distances, temps ni flotte. L’adaptateur refuse toute conversion qui arrondirait une donnée non entière.

Les recherches se partagent le budget à parts égales. À 1 000 clients : 60 s d’ILS puis 60 s de HGS. La construction et la préparation externe sont comptées en plus dans le temps réel. La graine du HGS vaut celle du pipeline + 10 000. Aucune BKS n’est transmise à un moteur.

Le moteur génétique utilise des pénalités pour explorer des états de travail éventuellement irréalisables. Ces états ne sont pas des solutions livrées. Notre contrôleur indépendant exige une couverture unique, les capacités, les débuts de service dans les fenêtres, la borne de flotte et le retour au dépôt avant de publier un résultat. La fin du HGS doit aussi conserver au moins la qualité de la solution ILS qui lui a été transmise.

L’intégration améliore surtout la diversification des affectations de clients. C’est une interprétation du fonctionnement : les mesures ci-dessous démontrent le gain de la combinaison, pas l’effet isolé de chaque mécanisme interne de PyVRP.

![Intégration et séparation des responsabilités](../livraison/ils_v7_figures/pipeline.png)

''')
    md(HGS_DETAILS)
    import algo.hybrid_reference as hybrid_module
    source=inspect.getsource(hybrid_module.solve)
    excerpt=source[source.index('    first = ils('):source.index('    elapsed = time.perf_counter()')]
    md('```python\n'+excerpt.rstrip()+'\n```\n\n**Lecture.** La première phase est notre ILS. La seconde appelle explicitement la bibliothèque externe avec les tournées obtenues. Le contrôle final protège les contraintes et l’incumbent. Les deux phases et leurs temps restent visibles dans le résultat.')
    md('''## 4.6. Registre des améliorations et décisions

Le développement a progressé par étapes : construire une solution réalisable, améliorer sa distance par ILS, tester les voisinages et les accélérations, puis intégrer un moteur génétique pour diversifier les affectations. Chaque modification a été évaluée sur un protocole identifié. Une modification correcte peut coûter davantage qu’elle ne rapporte ; nous distinguons donc les variantes retenues, les résultats négatifs et les expériences encore exploratoires.

| Modification | But et fonctionnement | Résultat observé | Décision |
|---|---|---|---|
| Groupes adaptatifs de tournées complètes et compilation Numba | Limiter le coût des mouvements et conserver les données originales | Base de l’ILS optimisée et de la première phase hybride | Retenu |
| Relocate, swap, 2-opt, 2-opt* et chaînes courtes | Modifier ordre et affectation, puis contrôler les tournées | Opérateurs de notre recherche locale | Retenus |
| Voisinage spatial et temporel, SWAP* dans notre ILS | Explorer des voisins et échanges plus riches | Pas de gain moyen confirmé au budget testé | Options expérimentales de l’ILS |
| RVND avec échanges de blocs et perturbations variables | Changer plus fortement la structure des tournées | Développement : 11,64 % contre 6,61 % pour la référence du même lot | Non retenu par défaut |
| Archive de tournées et partitionnement restreint | Recombiner des tournées réalisables par PLNE | Validation v5 : 10,355 % contre 10,127 % à 40 s ; pas de gain confirmé | Option, sans prétention d’optimalité globale |
| Cache exact des préfixes | Réévaluer seulement le suffixe modifié | Accélération dépendante des cas ; le gain de qualité n’est pas confirmé | Option testée différentiellement |
| Cache et groupes temporels combinés | Accélérer et choisir des groupes compatibles | Confirmation v6 : 6,164 % contre 6,065 % sur le même lot | Non retenu par défaut |
| Coût guidé et pénalités sur une trajectoire propre | Sortir des minima locaux sans changer le problème final | Coût guidé : 10,011 % contre 9,692 % sur trois cas ; variantes pénalisées irrégulières | Expériences conservées, non retenues |
| Construction puis HGS externe sans optimisation ILS | Ajouter une population génétique | Moyenne 6,624 % à 60 s ; un essai à 41,238 % | Initialisation insuffisante pour notre cible |
| Notre ILS puis HGS externe | Donner un point de départ amélioré à la population | Comparaison appariée à 120 s : 4,253 % contre 9,036 % | Combinaison recommandée et disponible |
| Couverture complète et contrôle indépendant | Vérifier la généralisation à toutes les tailles et publier chaque essai | Campagne finale de 472 pipelines sur 356 instances | Preuve expérimentale élargie ; aucun résultat défavorable retiré |

Les valeurs de lignes différentes ne s’interprètent pas comme un classement à budget égal : les lots et durées changent. Les protocoles et résultats complets v5, v6 et v7 sont conservés dans leurs annexes. Les archives cumulant de nombreuses trajectoires ne remplacent pas les résolutions de la campagne finale.

Les essais SWAP* de cette ligne concernent notre variante d’ILS. Le moteur externe PyVRP possède sa propre implémentation `SwapStar`, déjà activée dans la phase HGS retenue ; il s’agit de deux composants distincts.

Pour poursuivre ce suivi, le journal `docs/JOURNAL_EVOLUTION_ALGORITHME.md` associe à chaque changement son objectif, les paramètres modifiés, le lot, les graines, le budget, les mesures et la décision. Toute nouvelle modification de l’algorithme doit être accompagnée d’une nouvelle entrée et d’une expérience distincte ; une campagne figée n’est pas réécrite.
''')
    budget=pd.DataFrame([dict(clients=int(n),instances=56 if n==100 else 60,graines='2101 et 2102' if n in [100,1000] else '2101',
        recherche_totale_s=float(b),ILS_s=float(b)/2,HGS_s=float(b)/2) for n,b in sorted((int(k),v) for k,v in json.loads((BASE/'protocol.json').read_text())['budgets_by_clients'].items())])
    md('''## 5. Protocole final et définition des statistiques

### 5.1. Couverture, répétitions et budget

Les données et références proviennent de la révision figée `7474b068a8effa7f39448b241314b615c9271525` du dépôt PyVRP/Instances. Le format est lu par le projet ; VRPLIB désigne notamment une bibliothèque et des formats, tandis que Solomon et Gehring–Homberger sont les jeux d’instances. Il existe 56 cas Solomon à 100 clients et 60 cas par taille Gehring–Homberger de 200 à 1 000 clients, soit 356 cas distincts.

Les budgets ci-dessous sont fixés avant la campagne complète. Les six processus utilisent chacun un cœur et un seul thread. Les fonctions Numba sont préchauffées avant les mesures. Les temps réels comprennent les deux recherches, la construction et la préparation externe ; ils dépendent du matériel et ne sont pas des garanties de latence sur un autre ordinateur.

'''+markdown_table(budget)+r'''

Une répétition résout de nouveau la même instance avec une autre graine. Les 116 instances à 100 et 1 000 clients ont deux graines ; les tailles intermédiaires ont une graine de couverture. Nous ne calculons pas d’écart-type entre graines lorsqu’il n’existe qu’une observation.

Le nombre de clients décrit la taille d’un problème ; le nombre d’instances décrit des jeux de données différents ; le nombre d’essais décrit les résolutions avec leurs graines. Ainsi, une instance à 1 000 clients ne signifie pas 1 000 essais. Un pipeline final contient deux phases de recherche, et compte ici pour un essai complet.

Les 24 pipelines historiques réutilisés correspondent aux mêmes instances, paramètres, graines et deux phases de 60 s. Leurs composants de recherche ont les mêmes empreintes ; l’origine des fichiers et leur temps complet sont vérifiés. Ils ne sont pas comptés comme de nouveaux calculs. La campagne apporte 448 nouveaux pipelines. Les sorties sont conservées, même en cas d’échec.

### 5.2. Gap et moyenne générale

Pour une distance vérifiée D et la référence compatible B de la même instance :

$$g=100\frac{D-B}{B}.$$

Les distances suivent la convention DIMACS : chaque arc euclidien est tronqué à une décimale, par calcul entier `floor(10 × distance)` en interne. La même convention, les mêmes fenêtres, demandes et borne de flotte sont requises pour une comparaison. Une BKS est une meilleure solution connue, pas nécessairement un optimum prouvé. Dans notre objectif de distance seule, la flotte est bornée mais n’a pas de priorité lexicographique.

**Exemple pédagogique.** Une distance 1 040 face à une référence 1 000 donne un gap de 4 %. Deux instances à 0 % et 8 % donnent une moyenne de 4 %, bien que l’une dépasse 6 %. Cet exemple explique la formule ; il ne constitue pas une mesure de la campagne.

Pour une couverture entièrement réalisable, soit I le nombre d’instances et r_i le nombre de résultats réalisables pour l’instance i. Nous publions le gap moyen de cette instance puis une moyenne donnant le même poids à chaque instance :

$$\bar g_i=\frac{1}{r_i}\sum_{s=1}^{r_i}g_{i,s},\qquad \bar g_{instances}=\frac{1}{I}\sum_{i=1}^{I}\bar g_i.$$

Nous affichons aussi la moyenne de tous les essais :

$$\bar g_{essais}=\frac{\sum_i\sum_s g_{i,s}}{\sum_i r_i}.$$

Ces deux pondérations diffèrent ici, car certaines instances ont deux graines et d’autres une seule. La première évite de donner deux fois plus de poids à une instance répétée. La moyenne équilibrée par taille constitue encore une autre pondération et est identifiée séparément.

Les échecs restent dans le dénominateur du taux de faisabilité ; ils n’ont pas de gap de distance, et ne valent jamais zéro. En présence d’un échec, une moyenne sur les seuls résultats réalisables est conditionnelle et ne prouve pas la réussite sur tout le catalogue. Les tableaux précisent cette couverture.

Les écarts-types et boîtes à moustaches entre instances décrivent la difficulté du catalogue. Ils ne sont pas des intervalles de confiance sur de futures graines. Deux graines ne suffisent pas pour une conclusion statistique forte sur chaque cas ; une seule ne permet pas de mesurer la variance entre répétitions.
''')
    scope_rows=[]
    for label,key in [('Catalogue complet : poids égal par instance','catalog_356'),('100 et 1 000 clients, deux graines','core_116'),('Catalogue complet, seule graine commune 2101','common_seed_356')]:
        s=a['scopes'][key]
        scope_rows.append(dict(périmètre=label,instances=s['instances'],essais=s['attempts'],réalisables=s['valid'],
            échecs=s['failures'],gap_instances_pct=s['mean_instance_gap'],gap_essais_pct=s['mean_run_gap']))
    md('## 6. Résultats complets et interprétation\n\n### 6.1. Les deux périmètres demandés\n\n'+markdown_table(pd.DataFrame(scope_rows))+f'''\n\nLe bilan principal porte sur les **{all_scope['represented_instances']} instances représentées sur 356**. Sa moyenne est **{all_scope['mean_instance_gap']:.3f} %**, et non une moyenne calculée seulement sur les cas sous 5 ou 6 %. La moyenne brute des {all_scope['valid']} essais réalisables est {all_scope['mean_run_gap']:.3f} %. La vérification avec la seule graine commune 2101 donne {common['mean_instance_gap']:.3f} %, sans surreprésentation des cas répétés.

Le sous-ensemble 100/1 000 clients a une moyenne de **{core['mean_instance_gap']:.3f} %**. Il contient les 56 Solomon et les 60 grandes instances, sans sélection de familles. Les deux périmètres se recouvrent : leurs effectifs ne s’additionnent pas pour compter des instances distinctes.

Le changement de moyenne par rapport au bilan antérieur à 4,253 % ne constitue pas, à lui seul, une nouvelle amélioration algorithmique : le lot est élargi et contient des difficultés différentes. Le gain attribuable à la combinaison est étudié séparément dans la comparaison appariée de la section 6.3.

### 6.2. Décomposition par taille

'''+markdown_table(sizes[['n','instances','attempts','valid','failures','mean_instance_gap','worst_run_gap','runs_below_5','runs_below_6','mean_total_s']].rename(columns={'n':'clients','mean_instance_gap':'gap_moyen_pct','worst_run_gap':'pire_gap_pct','runs_below_5':'essais_sous_5','runs_below_6':'essais_sous_6','mean_total_s':'temps_moyen_s'}))+'''

Les tailles n’ont pas toutes le même budget. Ce tableau décrit le compromis retenu, pas un test à temps identique entre tailles. Les petites instances ne doivent pas masquer les cas difficiles à 1 000 clients : leur moyenne et leur pire essai sont toujours lus séparément.
''')
    nb.cells.append(nbformat.v4.new_code_cell(
        "valid=runs[runs.valid].copy()\n"
        "assert np.allclose(100*(valid.cost-valid.bks)/valid.bks,valid.gap_pct)\n"
        "macro=valid.groupby('instance').gap_pct.mean().mean()\n"
        f"assert np.isclose(macro,{all_scope['mean_instance_gap']!r})\n"
        "print('Vérification :',len(runs),'pipelines,',runs.instance.nunique(),'instances ; gap moyen par instance',round(macro,3),'%')"))
    nb.cells.append(image_cell('sizes','Gap moyen par taille sur toutes les instances ; les seuils ne servent pas à filtrer les résultats.'))
    nb.cells.append(image_cell('dispersion','Distribution des moyennes par instance ; valeurs extrêmes conservées.'))
    nb.cells.append(image_cell('families','Moyenne par famille et taille ; les différences reflètent la structure des instances.'))
    md('''**Lecture des graphiques.** La boîte représente les quartiles et la médiane ; le marqueur de moyenne et les valeurs extrêmes complètent la lecture. Une moyenne faible peut coexister avec un cas très défavorable. Les familles C regroupent les clients en amas, R les répartissent plus aléatoirement et RC combinent ces structures ; les catégories 1/2 correspondent à des configurations de fenêtres et d’horizon différentes.

La dispersion dépend de l’instance et, sur les tailles répétées, de la graine et de l’arrêt au temps. Nous ne prétendons pas que le seul nombre de clients explique le gap. La carte par familles rend visibles les difficultés que la moyenne générale résume imparfaitement.
''')
    nb.cells.append(image_cell('ecdf','Proportion cumulée d’instances atteignant chaque gap moyen ; tous les points sont inclus.'))
    nb.cells.append(image_cell('time_gap','Temps réels et gaps individuels ; compilation exclue, construction et préparation incluses.'))
    paired=paired_cases.pivot(index='instance',columns='variant',values='mean_gap')[['baseline','hybrid_hgs']].reset_index()
    paired.columns=['instance','ILS_60_puis_ILS_60_pct','ILS_60_puis_HGS_60_pct']
    md(f'''### 6.3. Quel gain provient de l’hybridation ?

Le catalogue complet mesure la couverture et la qualité finale. Pour attribuer un gain à la combinaison, nous utilisons une comparaison appariée séparée : douze instances à 1 000 clients, deux graines et une première phase ILS de 60 s commune. Chaque même résultat est ensuite poursuivi pendant 60 s par notre ILS ou par le HGS externe. Le temps de la première phase est facturé dans les deux branches, bien que le calcul ait été réutilisé.

{markdown_table(paired)}

La moyenne passe de **{own.mean_gap:.3f} %** pour ILS puis ILS à **{hybrid.mean_gap:.3f} %** pour ILS puis HGS, soit **{gain['improvement_pp']:.3f} points**. La combinaison gagne dans **{gain['wins']}/24** paires et régresse dans {gain['losses']}. Le temps réel moyen est {own.mean_total_s:.2f} s contre {hybrid.mean_total_s:.2f} s. La réduction relative du gap vaut {100*gain['improvement_pp']/own.mean_gap:.1f} % ; elle ne doit pas être confondue avec une réduction de la distance de ce même pourcentage.

L’intervalle exploratoire à 95 % par rééchantillonnage des douze instances est [{gain['instance_bootstrap95'][0]:.3f} ; {gain['instance_bootstrap95'][1]:.3f}] points. Ces cas étaient déjà étudiés et le budget de 120 s a été choisi après le diagnostic à 60 s : il s’agit d’une expérience de suivi, pas d’un test entièrement aveugle. Deux graines restent limitées.

La référence est elle aussi constituée de deux phases ; elle ne correspond pas à une ILS continue de 120 s. Les améliorations ne sont pas toutes attribuables au seul croisement : population, recherche locale et efficacité de l’implémentation externe interviennent ensemble. Une ablation interne du HGS n’a pas été exécutée.
''')
    cell=nbformat.v4.new_code_cell("display(Image(filename=str(ROOT/'livraison/ils_v7_figures/comparison_120.png')))")
    cell.metadata['figure_captions']=['Comparaison appariée des continuations à 120 s de recherche totale ; mêmes douze instances et deux graines.'];nb.cells.append(cell)
    md('''### 6.4. Deux résolutions expliquées : un cas structuré et un cas difficile

Nous fixons C101 et R2_10_4 avec la graine 2101 avant de lire les graphiques. Il ne s’agit pas de choisir la meilleure graine. Le premier illustre une résolution structurée à 100 clients ; le second conserve un cas difficile à 1 000 clients. Les cartes montrent toutes les tournées ; les Gantt montrent uniquement les quatre premières pour rester lisibles. Le contrôleur, lui, vérifie la solution complète.
'''+markdown_table(examples[['instance','clients','vehicles','distance','bks','gap']])+'''

Contrôles synthétiques des deux mêmes solutions :

'''+markdown_table(examples[['instance','max_load','capacity','latest_return','depot_closing','fleet_limit']])+'''

La charge maximale doit être au plus la capacité et le dernier retour au plus la fermeture du dépôt. Le respect de ces deux indicateurs ne remplace pas le contrôle de chaque fenêtre ni de la couverture. Les horaires détaillés de tous les clients sont enregistrés dans les JSON.
''')
    for name in ['C101','R2_10_4']:
        nb.cells.append(image_cell(f'example_{name}',f'{name}, graine 2101 : toutes les tournées et horaires des quatre premières ; résultat réellement exécuté.'))
    md('''**Distance et durée.** Sur chaque tournée, durée = trajets + attente + services, avec départ fixé à zéro. Le tableau suivant est recalculé par le vérificateur. La durée n’est pas utilisée à la place de la distance dans la formule du gap.
'''+markdown_table(examples[['instance','distance','duration','travel','waiting','service']]))
    worst=cases.sort_values('worst_gap',ascending=False).head(10)
    md('### 6.5. Les dix cas les plus défavorables\n\n'+markdown_table(worst[['instance','n','attempts','mean_gap','worst_gap','mean_total_s']])+'''

Ces lignes restent dans toutes les moyennes de leur périmètre. Une bonne moyenne générale ne résout pas automatiquement chaque famille. Le détail de l’ensemble des 356 instances, les graines, les distances, les flottes, les références et les temps est fourni dans `RESULTATS_CATALOGUE_V8.html` et les CSV associés.
''')
    md(f'''## 7. Reproduction, contrôles et traçabilité

Le code d’intégration se trouve dans `algo/hybrid_reference.py`, l’adaptateur entier dans `algo/external_reference.py`, notre ILS dans `algo/optimized.py` et `algo/iterated.py`, ses mouvements dans `algo/direct.py` et `algo/kernels.py`, et le contrôleur indépendant dans `algo/verify.py`. Les modules de recherche ne lisent jamais de fichier de référence. Les données d’entrée sont immuables.

Le protocole `results/catalog_v8/protocol.json` fige les budgets, graines, ordre aléatoire des tâches, versions de sources et référence des données. Le sous-dossier `source/` conserve le code effectivement exécuté. Les JSON `runs/` contiennent les solutions et mesures individuelles. `scripts/analyze_catalog_v8.py` revérifie les empreintes, les fichiers de référence, les tournées et les calculs ; il refuse une campagne incomplète pour la génération finale.

La reprise conserve les essais terminés et refuse de changer le protocole. Les 24 réutilisations ont une origine et une empreinte vérifiées ; elles ne sont ni des calculs neufs ni des recherches gratuites. Les erreurs techniques des essais préparatoires v7 restent archivées avec leurs messages. Aucun essai défavorable n’est transformé en valeur nulle.

```powershell
python -m pip install -r requirements-reference-v7.txt
python cli.py R2_10_3 --method ils_hgs --seconds 120 --seed 2101
python -m streamlit run web/app.py
python scripts/analyze_catalog_v8.py
python scripts/validate_delivery_v8.py
```

L’interface propose le profil **ILS + HGS (PyVRP)**. Le budget affiché est celui des deux recherches ; la construction et la préparation externe s’ajoutent au temps réel. Le profil ILS seul reste accessible comme référence. Les nouvelles campagnes locales restent séparées des résultats publiés. Les courbes du HGS ne disposent ici que de leurs points de début et de fin ; aucun historique interne n’est inventé.

Les tests couvrent les contraintes, les unités, l’immuabilité, les caches différentiels, les passages temporairement irréalisables des variantes, l’attribution externe, l’intégration CLI/web et les statistiques. Le reçu de validation final contient le nombre réel de tests et les empreintes des livrables. Les anciens reçus concernent leurs éditions historiques ; `livraison/VALIDATION.json` indique le justificatif courant.

## 8. Limites et conclusion

Le résultat final mesuré est **{all_scope['mean_instance_gap']:.3f} %** de gap moyen par instance sur le catalogue de 356 cas, et **{core['mean_instance_gap']:.3f} %** sur le lot de 116 cas à 100/1 000 clients. Ces valeurs dépendent du protocole, des budgets et des références figées. Les grandes instances ont leur propre bilan ; les pires cas restent visibles et ne sont pas masqués par les petites instances.

La comparaison appariée démontre un gain de la combinaison sur le lot étudié, avec une contribution externe explicitement attribuée. Elle ne démontre ni l’optimalité globale ni l’efficacité isolée de chaque opérateur du HGS. Une seule graine sur les tailles intermédiaires et deux sur les tailles extrêmes limitent l’analyse de la variabilité. Les mêmes cas ont parfois guidé des choix précédents : un jeu entièrement nouveau resterait utile.

Les principaux progrès sont l’initialisation par notre ILS, la diversification apportée par le HGS externe, le contrôle indépendant et l’élargissement de la preuve expérimentale. Les autres variantes restent documentées avec leurs échecs et leurs coûts. Les suites possibles sont davantage de répétitions, des ablations internes, un meilleur traitement des cas les plus difficiles et des évaluations à durée totale strictement identique entre méthodes. Le trafic variable, plus de 1 000 clients et l’optimisation de la durée constituent des limites explicites.

## Références

- Kool et al., *Hybrid Genetic Search for the Vehicle Routing Problem with Time Windows: a High-Performance Implementation* : https://wouterkool.github.io/pdf/paper-kool-hgs-vrptw.pdf
- PyVRP 0.12.2, moteur externe effectivement utilisé et licence MIT : https://github.com/PyVRP/PyVRP/tree/v0.12.2 ; https://github.com/PyVRP/PyVRP/blob/v0.12.2/LICENSE.md
- Données et références figées : https://github.com/PyVRP/Instances/tree/7474b068a8effa7f39448b241314b615c9271525/VRPTW
- VRPLIB, bibliothèque et formats : https://github.com/PyVRP/VRPLIB
- Vidal et al., informations de séquences et fenêtres : https://www.cirrelt.ca/documentstravail/cirrelt-2012-23.pdf

Les publications justifient les familles de méthodes ; leurs résultats numériques ne sont jamais attribués à notre projet. Les figures, tableaux et conclusions expérimentales du présent document proviennent des calculs et vérifications conservés dans notre dépôt.
''')
    nb=prose_pass(nb)
    execute(nb,ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb')
    markdown='\n\n'.join(c.source for c in nb.cells if c.cell_type=='markdown')
    (ROOT/'LIVRABLE_FINAL.md').write_text(markdown,encoding='utf-8')
    (ROOT/'docs/LIVRABLE_OPTIMISE_SOURCE.md').write_text(markdown,encoding='utf-8')
    df.to_csv(ROOT/'livraison/RESULTATS_CATALOGUE_V8.csv',index=False)
    cases.to_csv(ROOT/'livraison/INSTANCES_CATALOGUE_V8.csv',index=False)
    html='<meta charset="utf-8"><title>Catalogue CVRPTW complet</title><h1>356 instances : toutes les mesures</h1>'
    html+='<h2>Résumé par taille</h2>'+sizes.to_html(index=False,escape=True)
    html+='<h2>Toutes les instances, aucune sélection</h2>'+cases.to_html(index=False,escape=True)
    html+='<h2>Toutes les répétitions, y compris les échecs</h2>'+df.to_html(index=False,escape=True)
    (ROOT/'livraison/RESULTATS_CATALOGUE_V8.html').write_text(html,encoding='utf-8')
    from scripts.build_results_table_v8 import main as readable_table
    readable_table()
    print(json.dumps(dict(complete=True,instances=356,pipelines=472,means=a['scopes']),indent=2))


if __name__=='__main__':main()
