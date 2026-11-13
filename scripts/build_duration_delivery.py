"""Construit le livrable en durée à partir de résolutions réellement exécutées."""
from pathlib import Path
import inspect,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import nbformat
from scripts.analyze_duration import analyze,BASE
from algo.duration_kernels import route_eval
from scripts.figure_explanations import EXPLANATIONS
from matplotlib.patches import Patch

FIG=ROOT/'livraison/duree_figures'
COLORS={'ils':'#2563a6','sa':'#cc7b23','hybrid':'#128475'}
LABELS={'ils':'ILS durée','sa':'Recuit durée','hybrid':'ILS durée + HGS'}


def table(frame):
    d=frame.copy()
    for col in d:
        if pd.api.types.is_float_dtype(d[col]):
            d[col]=d[col].map(lambda v:'—' if pd.isna(v) else f'{v:.3f}'.replace('.',','))
    return d.to_markdown(index=False)


def save(fig,name):
    fig.tight_layout();fig.savefig(FIG/(name+'.png'),dpi=160,bbox_inches='tight');plt.close(fig)


def figures(df,cases,sizes,repeated,info):
    FIG.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(9,3))
    xy={0:(0,0),1:(2,1),2:(2,-1)}
    for i,(x,y) in xy.items():ax.scatter(x,y,s=800,color='#dce9f5' if i else '#afd9cf');ax.text(x,y,str(i),ha='center',va='center')
    for i,j,label in [(0,1,'8'),(0,2,'5'),(1,2,'5')]:
        a,b=xy[i],xy[j];ax.plot([a[0],b[0]],[a[1],b[1]],color='#71849a',zorder=0)
        ax.text((a[0]+b[0])/2+.08,(a[1]+b[1])/2,label,bbox=dict(facecolor='white',edgecolor='none'))
    ax.text(2.7,.75,'Client 1 : service 5 ; fenêtre [15,25]')
    ax.text(2.7,-.25,'Client 2 : service 4 ; fenêtre [0,40]')
    ax.text(2.7,-.85,'Dépôt 0 ; capacité 6 ; demandes 2 et 3')
    ax.set_xlim(-.5,7.8);ax.set_ylim(-1.5,1.6);ax.axis('off')
    ax.set_title('Même trajet total : 18 ; durées différentes selon les attentes')
    save(fig,'graphe')
    fig,ax=plt.subplots(figsize=(9,2.8))
    segments=[[(0,8,'Trajet'),(8,7,'Attente'),(15,5,'Service'),(20,5,'Trajet'),(25,4,'Service'),(29,5,'Trajet')],
              [(0,5,'Trajet'),(5,4,'Service'),(9,5,'Trajet'),(14,1,'Attente'),(15,5,'Service'),(20,8,'Trajet')]]
    color={'Trajet':'#64748b','Attente':'#d6942c','Service':'#128475'}
    for i,parts in enumerate(segments):
        for start,length,kind in parts:ax.barh(i,length,left=start,color=color[kind],height=.5)
    ax.set_yticks([0,1],['0 → 1 → 2 → 0 : durée 34','0 → 2 → 1 → 0 : durée 28'])
    ax.set_xlabel('Temps depuis le départ fixé à zéro (u.t.)')
    ax.legend(handles=[Patch(facecolor=value,label=kind) for kind,value in color.items()],
              ncols=3,loc='upper right');save(fig,'attentes')
    fig,ax=plt.subplots(figsize=(10,2));ax.axis('off')
    for i,text in enumerate(['Construction\nregret-2 : sélection en durée','Notre ILS en durée\n5 s de recherche','HGS externe PyVRP\n5 s ; départ fixé à 0','Contrôle indépendant\net mesures séparées']):
        ax.text(.12+i*.25,.5,text,ha='center',va='center',transform=ax.transAxes,
                bbox=dict(boxstyle='round,pad=.6',facecolor='#e5f0ed',edgecolor='#7b9d94'),fontsize=9)
        if i<3:ax.annotate('',xy=(.24+i*.25,.5),xytext=(.22+i*.25,.5),xycoords='axes fraction',arrowprops=dict(arrowstyle='->'))
    save(fig,'pipeline')
    grouped=df[df.core & df.valid].groupby('n').agg(initial=('initial_duration','mean'),final=('duration','mean'))
    fig,ax=plt.subplots(figsize=(9,3.5));x=np.arange(len(grouped))
    ax.bar(x-.18,grouped.initial,.35,label='Construction');ax.bar(x+.18,grouped.final,.35,label='Après hybride',color=COLORS['hybrid'])
    ax.set_xticks(x,grouped.index);ax.set_xlabel('Nombre de clients');ax.set_ylabel('Durée cumulée moyenne (u.t.)');ax.legend();save(fig,'avant_apres')
    fig,ax=plt.subplots(figsize=(9,3.5));bottom=np.zeros(len(sizes))
    for column,label,color in [('mean_travel','Trajets','#64748b'),('mean_waiting','Attentes','#d6942c'),('mean_service','Services','#128475')]:
        ax.bar(np.arange(len(sizes)),sizes[column],bottom=bottom,label=label,color=color);bottom+=sizes[column].to_numpy()
    ax.set_xticks(np.arange(len(sizes)),sizes.n);ax.set_ylabel('Durée moyenne par instance (u.t.)');ax.set_xlabel('Clients');ax.legend();save(fig,'composition')
    fig,ax=plt.subplots(figsize=(9,3.5));groups=[cases[cases.n.eq(n)].mean_delta_reference_pct for n in sizes.n]
    ax.boxplot(groups,tick_labels=sizes.n.tolist(),showmeans=True)
    ax.axhline(0,color='#b45309',ls='--');ax.set_xlabel('Clients — une observation par instance')
    ax.set_ylabel('Écart au plan témoin (%)');save(fig,'distribution')
    fig,ax=plt.subplots(figsize=(9,3.5));ax.hist(cases.mean_delta_reference_pct,bins=25,color=COLORS['hybrid'],edgecolor='white')
    ax.axvline(cases.mean_delta_reference_pct.mean(),label='Moyenne',color='#cc7b23')
    ax.axvline(cases.mean_delta_reference_pct.median(),label='Médiane',color='#2563a6',ls='--')
    ax.set_xlabel('Écart moyen au plan témoin par instance (%)');ax.set_ylabel('Effectif : instances');ax.legend();save(fig,'histogramme')
    fig,axes=plt.subplots(1,3,figsize=(12,3.8))
    for ax,name in zip(axes,['C101','R202','R2_10_8']):
        sub=repeated[repeated.instance.eq(name)&repeated.valid]
        ax.boxplot([sub[sub.method.eq(m)].duration for m in COLORS],tick_labels=['ILS','Recuit','Hybride'],showmeans=True)
        ax.set_title(name+' — 20 graines/méthode');ax.set_ylabel('Durée (u.t.)')
    save(fig,'repetitions')
    fig,axes=plt.subplots(1,3,figsize=(12,3.5))
    for ax,name in zip(axes,['C101','R202','R2_10_8']):
        values=repeated[repeated.instance.eq(name)&repeated.method.eq('hybrid')&repeated.valid].duration
        ax.hist(values,bins='auto',color=COLORS['hybrid'],edgecolor='white');ax.set_title(name+' — hybride, 20 essais')
        ax.set_xlabel('Durée (u.t.)');ax.set_ylabel('Effectif')
    save(fig,'histogrammes_repetitions')
    pairs=pd.read_csv(BASE/'regression.csv');reg=info['regression']
    fig,ax=plt.subplots(figsize=(8,4));ax.scatter(pairs.initial_duration,pairs.duration,alpha=.7)
    xs=np.linspace(pairs.initial_duration.min(),pairs.initial_duration.max(),100)
    ax.plot(xs,reg['slope']*xs+reg['intercept'],color='#b45309',label=f"r={reg['pearson']:.3f} ; R²={reg['r2']:.3f}")
    ax.set_xlabel('Durée initiale (u.t.)');ax.set_ylabel('Durée finale (u.t.)');ax.legend();save(fig,'regression')
    fig,axes=plt.subplots(1,3,figsize=(12,3.8))
    for ax,name in zip(axes,['C101','R202','R2_10_8']):
        sub=repeated[repeated.instance.eq(name)&repeated.valid]
        end=max(json.loads((ROOT/r.source).read_text())['result']['runtime_s']-json.loads((ROOT/r.source).read_text())['result']['construction_s'] for r in sub.itertuples())
        grid=np.linspace(0,end,150)
        for method in COLORS:
            curves=[];final=[]
            for row in sub[sub.method.eq(method)].itertuples():
                result=json.loads((ROOT/row.source).read_text())['result'];offset=result['construction_s']
                points=sorted((max(0.,p['elapsed_s']-offset),p['best']) for p in result['trace'])
                times=np.array([p[0] for p in points]);values=np.minimum.accumulate([p[1] for p in points])
                indices=np.maximum(0,np.searchsorted(times,grid,side='right')-1)
                curves.append(np.asarray(values)[indices]);final.append(result['cost'])
            a=np.array(curves);mean=a.mean(axis=0);sd=a.std(axis=0,ddof=0)
            assert np.isclose(mean[-1],np.mean(final))
            ax.plot(grid,mean,label=LABELS[method],color=COLORS[method]);ax.fill_between(grid,mean-sd,mean+sd,alpha=.12,color=COLORS[method])
        ax.set_title(name);ax.set_xlabel('Temps après construction (s)');ax.set_ylabel('Durée cumulée (u.t.)')
    axes[-1].legend(fontsize=7);save(fig,'convergence')


def main():
    df,cases,sizes,repeated,descriptive,info=analyze()
    figures(df,cases,sizes,repeated,info)
    model=(ROOT/'docs/MODELE_DUREE.md').read_text(encoding='utf-8')
    nb=nbformat.v4.new_notebook();nb.metadata['report_subtitle']='Durée totale — Modélisation, ILS–HGS et statistique descriptive'
    def md(s):nb.cells.append(nbformat.v4.new_markdown_cell(s.strip()))
    def code(s):nb.cells.append(nbformat.v4.new_code_cell(s))
    def img(name,caption):
        cell=nbformat.v4.new_code_cell(f"display(Image(filename=str(ROOT/'livraison/duree_figures/{name}.png')))")
        cell.metadata['figure_captions']=[caption];nb.cells.append(cell)
        explanation=nbformat.v4.new_markdown_cell(EXPLANATIONS[name])
        explanation.metadata['explains_figure']=name
        nb.cells.append(explanation)
    md('''# Livrable final — CVRPTW : minimisation de la durée totale

**CESI — Algorithmique et optimisation — 13 novembre 2026**

Nous cherchons des tournées livrant chaque client exactement une fois, respectant la capacité, les fenêtres strictes et la fermeture du dépôt. Notre objectif est la **somme des durées des tournées**, avec trajets, attentes et services, pour des départs fixés à zéro. Le temps d’exécution du solveur est mesuré séparément.

La méthode associe notre constructeur et notre ILS à un HGS externe fourni par **PyVRP 0.12.2**, explicitement attribué à ses auteurs. Les expériences utilisent les données Solomon et Gehring–Homberger, sans les modifier. Les temps de trajet restent statiques ; la prise en compte d’un trafic dépendant de l’heure demeure une extension non démontrée.

Le rapport présente successivement le problème, sa formulation, l’algorithme, le protocole, les statistiques descriptives et les limites. Les fichiers individuels permettent de vérifier les solutions et les calculs.
''')
    code("from pathlib import Path\nimport sys,json\nimport numpy as np\nimport pandas as pd\nfrom IPython.display import display,Image\nROOT=next(p for p in [Path.cwd(),*Path.cwd().parents] if (p/'algo/duration.py').exists())\nif str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))\nfrom scripts.analyze_duration import analyze\nruns,cases,sizes,repetitions,descriptive,analysis=analyze()\nassert len(runs)==646 and len(cases)==356\nassert runs.valid.all()\nprint('646 résolutions en durée ; 356 instances ; toutes réalisables.')")
    md('''## 1. Du réseau routier à la durée d’une tournée

Le dépôt et les clients forment les sommets d’un graphe orienté ; un arc représente un trajet possible. Les temps de trajet sont $c_{ij}$, les demandes $q_i$, les services $s_i$ et les fenêtres $[e_i,l_i]$. Une solution est une liste de tournées ; le dépôt 0 est implicite au départ et au retour.

Deux ordres de visite peuvent parcourir la même distance et produire des attentes différentes. Sur l’exemple suivant, le trajet total vaut 18 et les services totalisent 9 dans les deux cas. L’attente vaut 7 dans l’ordre 1 puis 2, contre 1 dans l’autre : les durées sont 34 et 28. Le deuxième ordre est meilleur pour notre objectif.
''')
    img('graphe','Temps symétriques : chaque trait représente les deux arcs de sens opposés. Cet exemple pédagogique ne constitue pas un benchmark.')
    img('attentes','Attente, service et trajet sont distincts. À trajet total égal, la durée peut changer.')
    code("from algo.model import Instance\nfrom algo.verify import verify\nm=np.array([[0,80,50],[80,0,50],[50,50,0]],float)\ntoy=Instance('exemple',np.zeros((3,2)),np.array([0,2,3]),np.array([0,50,40]),np.array([0,150,0]),np.array([600,250,400]),m,6.,1,600.)\nfor route in [[[1,2]],[[2,1]]]:\n    v=verify(route,toy)\n    assert v['valid']\n    print(route,'trajets',v['travel']/10,'attente',v['waiting']/10,'services',toy.service.sum()/10,'durée',v['duration']/10)")
    md(model)
    md('''## 3. Complexité et vérification du modèle

Le problème généralise le TSP : avec un seul véhicule, des fenêtres larges, des services nuls et une capacité non bloquante, minimiser la durée revient à minimiser le coût d’un circuit du TSP. Cette réduction est polynomiale : l’optimisation est NP-difficile. Les contraintes de temps et de capacité rendent l’exploration pratique plus exigeante ; elles ne donnent pas une garantie d’optimalité à une métaheuristique.

Le PLNE de `controle/plne.py` est réellement résolu par HiGHS avec le coût placé sur les variables de retour $R_k$. Sur dix petits cas de 3 à 5 clients, nous comparons son résultat à une énumération indépendante des tournées et partitions. Les deux méthodes prouvent les mêmes optimums en durée. Un cas comprend des arcs nuls pour vérifier que le flot empêche les cycles isolés.
''')
    md(table(pd.read_csv(ROOT/'results/time_objective/exact/summary.csv')))
    md('Ces dix cas contrôlent la formulation ; ils ne démontrent pas l’optimalité des solutions à 100–1 000 clients.')
    md(r'''## 4. Algorithme et lien avec le code

### 4.1. Construire, perturber, intensifier et conserver le meilleur

Le constructeur utilise des insertions regret-2 respectant capacité et horaires. Les surcoûts de trajet guident les positions ; parmi douze constructions complètes, la meilleure est sélectionnée selon sa **durée réelle**. La construction est mesurée et ajoutée au temps total.

Notre ILS copie la solution courante, tente quatre perturbations réalisables, puis une descente locale échantillonnée et bornée. Les mouvements sont relocate, swap, inversion 2-opt et échange de fins de tournées 2-opt*. Chaque mouvement recalcule les horaires complets des tournées touchées : une économie d’arcs ne suffit pas à prouver une amélioration de durée.

La candidate est acceptée si sa durée reste dans une tolérance de 0,5 % autour du record. Toute amélioration stricte met à jour une copie de l’archive. Après cent cycles sans record, la recherche repart de cette archive. Le budget mural est contrôlé entre les blocs de mouvements ; un bloc commencé peut légèrement dépasser la limite, et le temps réel est publié.

Le recuit utilise les mêmes mouvements et le même évaluateur temporel. Une hausse de durée $\Delta>0$ peut être acceptée avec $\exp(-\Delta/\theta)$ ; la température décroît géométriquement avec le temps consommé. L’archive réalisable reste distincte de l’état courant.

### 4.2. Évaluer effectivement la durée

`route_eval` reçoit une tournée, les matrices, demandes, services et fenêtres ; il renvoie la faisabilité, la durée et la charge. La ligne `max` compte l’attente ; la dernière addition compte le retour au dépôt. Les unités internes sont des dixièmes ; les sorties affichées sont divisées par dix.
''')
    md('```python\n'+inspect.getsource(route_eval.py_func).strip()+'\n```')
    md('''### 4.3. Hybridation avec un moteur externe

Le profil hybride transmet le résultat de notre ILS au HGS de PyVRP 0.12.2, sans lire de référence et sans modifier les contraintes. Le HGS maintient une population de solutions, sélectionne des parents par tournois, effectue un croisement SREX et applique une recherche locale comprenant notamment SwapStar. Des états de travail pénalisés peuvent être explorés ; seules des solutions finales réalisables sont conservées.

Le coût du véhicule est configuré avec `unit_distance_cost=0`, `unit_duration_cost=1` et `start_late=0`. Ce dernier paramètre fixe le départ à zéro : décaler le départ pour masquer l’attente ne correspondrait pas au modèle. Le coût retourné est confronté à la somme des durées recalculées par notre contrôleur indépendant.

Le partage évalué est 5 s d’ILS puis 5 s de HGS. Ce réglage constitue une base expérimentale pour l’objectif durée ; une configuration performante en distance n’est pas automatiquement validée en durée.
''')
    img('pipeline','La recherche se partage dix secondes ; construction et préparation externe s’ajoutent au temps de calcul total.')
    md('''### 4.4. Modifications et vérifications

| Modification | Motif | Vérification |
|---|---|---|
| Objectif PLNE sur les retours $R_k$ | Minimiser la durée cumulée | Concordance de dix optimums avec une énumération indépendante |
| Évaluateur temporel des mouvements | Inclure attente, service et retour | Deux ordres de même trajet mais de durées 34/28 sont distingués |
| Sélection initiale et archive en durée | Éviter une acceptation restée en distance | Coûts confrontés à `verify`, archive non dégradée |
| HGS : coût durée et départ fixé | Aligner le moteur externe sur le modèle | Test d’une attente obligatoire que le départ ne peut masquer |
| Nouvelles références temporelles | Éviter de renommer les gaps distance | Tournées de référence réévaluées, qualification explicite |
| Nouvelle campagne et statistique descriptive | Mesurer l’effet réel de la méthode | Données individuelles, graines, sources figées et effectifs conservés |

L’implémentation propre de l’ILS, les adaptateurs et la vérification sont dans le projet ; le moteur génétique externe appartient à PyVRP. Les commentaires du code expliquent les fonctions et les points sensibles.
''')
    md(r'''## 5. Protocole et références des benchmarks en durée

Nous utilisons les 56 Solomon à 100 clients et les 300 Gehring–Homberger de 200, 400, 600, 800 et 1 000 clients : **356 instances**. Les matrices de temps conservent la convention des fichiers DIMACS : arcs euclidiens tronqués à une décimale, horaires et services à la même échelle. Les durées sont exprimées en unités du benchmark, pas en minutes réelles démontrées.

La campagne de couverture comporte **472 pipelines hybrides** : une graine sur toutes les instances, une seconde à 100/1 000 clients. Le lot de stabilité compare ILS, recuit et hybride sur C101, R202 et R2_10_8, avec **20 graines par couple instance/méthode**, soit 180 résolutions. Six résolutions hybrides appartiennent déjà à la couverture : le total distinct est **646**, pas 652. Toutes sont exécutées pour l’objectif durée.

Chaque méthode dispose de dix secondes de recherche. Construction et préparation externe sont comptées en plus ; la compilation est préchauffée séparément. Les essais sont répartis sur six processus à une affinité CPU enregistrée, avec les bibliothèques de calcul limitées à un thread. Graines, ordre, versions et sources exécutées sont figés dans le protocole.

Les trois cas répétés représentent un cas groupé, un cas aléatoire et une grande instance historiquement difficile. Ce choix ne rend pas le lot représentatif de toutes les situations. Les méthodes reçoivent la même construction pour une même instance et graine ; celle-ci est effectivement recalculée et facturée dans chaque résolution.

### 5.1. Ce que signifie la référence

Les fichiers `.sol` DIMACS donnent des tournées de référence sélectionnées pour la **distance**. Nous recalculons leur durée, avec les mêmes services, fenêtres et départs à zéro. Ce plan est un **témoin réalisable**, dont l’optimalité en durée n’est pas établie. Son utilisation n’introduit pas de connaissance dans le solveur : il est lu après la résolution.

L’écart au témoin est :

$$E=100\frac{T_{\mathrm{obtenu}}-T_{\mathrm{témoin}}}{T_{\mathrm{témoin}}}.$$

Un écart négatif signifie que la solution est plus courte en durée que ce témoin ; cela ne signifie pas qu’un optimum a été battu. Nous ne présentons pas cet indicateur comme un gap à une BKS temporelle. Les anciens pourcentages calculés en distance ne qualifient pas l’objectif actuel.

### 5.2. Borne inférieure et véritable gap

Pour les petits cas, une preuve d’optimalité permet un véritable gap $100(T/T^*-1)$. Pour les grandes instances, nous utilisons aussi une borne simple :

$$L=\sum_i s_i+\operatorname{MST}(G,c)\le T^*.$$

L’union des tournées rejoint le dépôt et tous les clients ; son temps de trajet est au moins celui d’un arbre couvrant minimal. L’attente est non négative et les services sont obligatoires. Ainsi $100(T/L-1)$ borne supérieurement le gap à l’optimum, mais peut être très pessimiste. Il ne s’agit pas d’une BKS. Les trois notions — optimum prouvé, borne inférieure et plan témoin — restent séparées dans les tableaux.
''')
    md('## 6. Résultats et statistique descriptive\n\n### 6.1. Couverture, qualité temporelle et temps de calcul')
    md(f"Les {info['runs']} résolutions comprennent {info['feasible']} solutions réalisables et {info['failed']} échecs. Le tableau de couverture donne le même poids à chaque instance après moyenne de ses graines disponibles. L’écart moyen au plan témoin vaut **{info['mean_instance_delta_reference_pct']:.3f} %** et le gain moyen depuis la construction **{info['mean_instance_gain_initial_pct']:.3f} %**. Ces deux indicateurs ont des références différentes.")
    shown=sizes[['n','instances','attempts','feasible','mean_duration','mean_delta_reference_pct','mean_gain_initial_pct','mean_calculation_s']].rename(columns={'n':'Clients','instances':'Instances','attempts':'Essais','feasible':'Réalisables','mean_duration':'Durée (u.t.)','mean_delta_reference_pct':'Écart témoin (%)','mean_gain_initial_pct':'Gain initial (%)','mean_calculation_s':'Calcul (s)'})
    md(table(shown))
    md('Les moyennes favorables ne suppriment pas les cas difficiles. Voici les six instances dont la durée moyenne dépasse le plus celle du plan témoin ; elles restent dans tous les tableaux de leur périmètre.')
    worst=cases.nlargest(6,'mean_delta_reference_pct')[['instance','n','mean_duration','reference_duration','mean_delta_reference_pct','mean_calculation_s']]
    md(table(worst))
    worst_run=df.loc[df.delta_reference_pct.idxmax()]
    md(f"Le pire essai individuel est {worst_run.instance}, graine {int(worst_run.seed)} : **{worst_run.delta_reference_pct:+.3f} %** au témoin. Il ne doit pas être confondu avec une moyenne d’instance.")
    md('Ces écarts positifs montrent une marge d’amélioration au budget de dix secondes. Ils ne sont ni cachés par la moyenne générale ni transformés en zéros. Le témoin reste une solution réalisable et non un optimum démontré en durée.')
    img('avant_apres','Durées avant/après à dix secondes de recherche. Les moyennes par taille ne sont pas une preuve de complexité asymptotique.')
    img('composition','Décomposition des durées finales : trajets, attentes et services ; ces derniers sont constants pour une instance.')
    md('''### 6.2. Population, variables et données tabulaires

Une ligne d’essai représente une instance, une graine, une méthode et un budget. Le nom de l’instance et la méthode sont qualitatifs ; le nombre de clients est discret ; durée, attente et temps de calcul sont quantitatifs ; la faisabilité est booléenne. Une graine sert à identifier une exécution, pas à expliquer causalement sa performance.

Les cases manquantes des indicateurs de qualité d’un échec ne valent jamais zéro. La colonne d’erreur est normalement vide pour une réussite. Nous contrôlons les colonnes indispensables sur les essais réalisables avant de calculer les statistiques.
''')
    code("cols=['instance','seed','method','n','valid','duration','reference_duration','total_s']\ndisplay(runs[cols].head())\ndisplay(runs[cols].dtypes.to_frame('type'))\ndisplay(runs[cols].isna().sum().to_frame('manquants'))\nassert runs.loc[runs.valid,['duration','reference_duration','total_s']].notna().all().all()\n# Synthèse de 356 moyennes d’instance, avec même poids par instance.\nz=cases[['mean_duration','mean_waiting','mean_calculation_s']]\nauto=z.describe()\nauto.loc['std']=z.std(ddof=0)  # Harmoniser la convention descriptive N.\ndisplay(auto)")
    md(r'''### 6.3. Position, dispersion et quantiles

Pour N valeurs observées, la moyenne est $\bar x=N^{-1}\sum x_i$. La médiane partage la série ordonnée en deux moitiés ; elle est moins sensible que la moyenne aux valeurs élevées. Le mode est une valeur la plus fréquente ; pour une série continue sans répétition, il peut ne pas y avoir de mode distinct utile.

Nous employons la variance descriptive $v=N^{-1}\sum(x_i-\bar x)^2$ et l’écart-type $\sigma=\sqrt v$, avec `ddof=0`. La variance corrigée divisée par N−1 répondrait à une autre convention et n’est pas mélangée ici. L’étendue vaut maximum moins minimum ; l’IQR vaut $Q_3-Q_1$. Les quantiles sont calculés par interpolation linéaire Pandas, convention annoncée pour rendre les résultats reproductibles.

Les tableaux suivants portent sur les **vingt répétitions d’une même instance et méthode**. Les colonnes détaillées, y compris les quantiles 2,5 %, 10 %, 30 %, 70 %, 90 % et 97,5 %, sont conservées en CSV.
''')
    small=descriptive[descriptive.metric.eq('duration')][['instance','method','n','mean','median','std','minimum','q0.25','q0.75','maximum','iqr']].copy()
    small['method']=small.method.map(LABELS);md(table(small))
    examples=descriptive[descriptive.metric.eq('duration') & descriptive.method.eq('hybrid')].set_index('instance')
    c=examples.loc['C101'];r=examples.loc['R2_10_8']
    md(f"Sur C101, les vingt résultats hybrides ont une moyenne de {c['mean']:.3f} et une médiane de {c['median']:.3f} u.t., avec un écart-type de {c['std']:.3f}. Cette stabilité observée ne garantit pas tous les essais futurs. Sur R2_10_8, la moyenne vaut {r['mean']:.3f} contre une médiane de {r['median']:.3f} u.t. ; l’histogramme permet de lire l’influence des durées les plus élevées.")
    code("# Une fiche complète, verticale pour garder la lecture lisible.\nfiche=descriptive.query(\"instance == 'R2_10_8' and method == 'hybrid' and metric == 'duration'\")\ndisplay(fiche.drop(columns=['instance','method','metric']).T.rename(columns={fiche.index[0]:'valeur'}))\nx=repetitions.query(\"instance == 'R2_10_8' and method == 'hybrid'\").duration\nprint('variance N :',x.var(ddof=0),'écart-type :',x.std(ddof=0))\ndisplay(x.quantile([.025,.1,.3,.7,.9,.975]).to_frame('durée'))")
    img('repetitions','Chaque boîte porte sur 20 graines à budget identique. Une boîte réduite à un trait correspond à des valeurs identiques.')
    img('histogrammes_repetitions','Histogrammes de durées du profil hybride, 20 répétitions par cas ; les classes décrivent les fréquences observées.')
    md('''La boîte contient les observations entre Q1 et Q3 et son trait central est la médiane ; le marqueur représente la moyenne. Les moustaches atteignent les dernières observations dans les bornes Q1−1,5 IQR et Q3+1,5 IQR. Les autres points sont potentiellement atypiques : ils ne sont pas supprimés.

Une moyenne supérieure à la médiane peut signaler l’influence de grandes valeurs, mais l’interprétation doit être confrontée à l’histogramme. Une série constante n’a pas une dispersion normale non dégénérée. Avec vingt valeurs et des contraintes produisant des plateaux, nous ne supposons pas automatiquement une loi normale et n’appliquons pas les probabilités d’une gaussienne sans justification.

Les graphiques globaux suivants représentent les moyennes de **356 instances différentes**. Ils décrivent l’hétérogénéité du catalogue et ne remplacent pas l’étude entre graines d’un même cas.
''')
    img('distribution','Boîtes par taille : une moyenne par instance ; la ligne zéro correspond au plan témoin, pas à un optimum temporel.')
    img('histogramme','Distribution des écarts moyens d’instance au témoin. Les valeurs défavorables et négatives sont conservées.')
    md(r'''### 6.4. Covariance, corrélation et moindres carrés

Pour éviter de confondre l’effet du budget et de la taille, cette étude utilise une observation par instance à 1 000 clients, la graine 4101 et dix secondes de recherche : 60 couples. X est la durée de construction et Y la durée finale du profil hybride.

$$\operatorname{Cov}(X,Y)=N^{-1}\sum_i(x_i-\bar x)(y_i-\bar y),\quad r=\frac{\operatorname{Cov}(X,Y)}{\sigma_X\sigma_Y}.$$

La droite $\widehat y=ax+b$ minimise $\sum_i(y_i-ax_i-b)^2$, avec $a=\operatorname{Cov}(X,Y)/v_X$ et $b=\bar y-a\bar x$. La pente mesure l’association observée des durées ; l’interception ne s’interprète pas comme une durée réelle à extrapoler hors des données.
''')
    reg=info['regression'];md(f"Les calculs donnent **r = {reg['pearson']:.4f}**, **a = {reg['slope']:.4f}**, **b = {reg['intercept']:.4f}** et **R² = {reg['r2']:.4f}**. Ils décrivent ce lot, sans démontrer un effet causal du moteur ni une garantie prédictive sur une instance nouvelle.")
    code("p=pd.read_csv(ROOT/'results/time_objective/catalogue/regression.csv')\nx=p.initial_duration.to_numpy();y=p.duration.to_numpy()\ncov=np.mean((x-x.mean())*(y-y.mean()))\nassert np.isclose(cov,np.cov(x,y,ddof=0)[0,1])\nr=cov/(x.std(ddof=0)*y.std(ddof=0))\na=cov/x.var(ddof=0);b=y.mean()-a*x.mean()\na_np,b_np=np.linalg.lstsq(np.c_[x,np.ones(len(x))],y,rcond=None)[0]\nassert np.allclose([a,b],[a_np,b_np])\nassert np.isclose(r,np.corrcoef(x,y)[0,1])\nyp=a*x+b\nSCT=((y-y.mean())**2).sum();SCR=((yp-y.mean())**2).sum();SCE=((y-yp)**2).sum()\nR2=1-SCE/SCT\nassert np.isclose(SCT,SCR+SCE) and np.isclose(R2,r*r)\nprint('Covariance',cov,'Pearson',r,'a',a,'b',b,'R²',R2)\nprint('SCT',SCT,'SCR',SCR,'SCE',SCE)")
    img('regression','Moindres carrés sur 60 instances, même taille, graine et budget. Une difficulté commune peut expliquer l’association.')
    md(r'''La décomposition SCT = SCR + SCE sépare la variabilité totale, la part associée à la droite ajustée et les résidus. Avec une interception, $R^2=1-\mathrm{SCE}/\mathrm{SCT}=r^2$ en régression linéaire simple. Un R² élevé ne signifie pas que la méthode a causé cette proportion d’amélioration.

### 6.5. Convergence et comparaison des méthodes

Nous alignons les traces sur le temps après construction. Chaque trace est une fonction en escalier du meilleur coût connu ; après l’arrêt d’un essai, sa dernière valeur est conservée jusqu’à l’horizon commun. La fin de la courbe moyenne est vérifiée contre la moyenne des durées finales du même lot. La zone représente ± un écart-type descriptif entre graines, et non un intervalle de confiance.
''')
    img('convergence','Convergence moyenne et dispersion de 20 graines par méthode/cas. Le temps de construction reste compté dans les tableaux de calcul total.')
    comp=repeated.groupby(['instance','method'],as_index=False).agg(runs=('valid','size'),feasible=('valid','sum'),
        duration=('duration','mean'),std=('duration',lambda x:x.std(ddof=0)),mean_calculation_s=('total_s','mean'),delta=('delta_reference_pct','mean'))
    comp['method']=comp.method.map(LABELS);md(table(comp))
    md('Sur ce lot de vingt graines par cas, l’hybride présente la durée moyenne la plus faible pour les trois cas. Les distributions se recouvrent, notamment sur la grande instance : cette observation descriptive ne constitue pas un test de significativité ni une preuve de supériorité sur tout le catalogue.')
    md('''Ces moyennes et dispersions comparent des méthodes à effort de recherche égal. Nous ne retenons pas seulement le meilleur essai ; un mécanisme plus complexe peut régresser sur un cas. Les trois cas ont été choisis pour leur contraste et ne permettent pas une conclusion universelle de supériorité.

## 7. Reproduction, limites et conclusion

Le changement porte sur le modèle, le coût des mouvements, l’acceptation, l’archive, le HGS et les mesures. Une simple substitution du mot « distance » par « temps » aurait laissé le solveur optimiser le mauvais critère. Les cas de test distinguent explicitement ces deux objectifs.

La campagne montre le comportement observé en durée sur les 356 instances et la stabilité sur trois cas répétés. Les limites restent : temps de trajet statiques, tailles plafonnées à 1 000 clients, budget de dix secondes, peu de graines sur la couverture globale et absence d’optimum temporel officiel pour les grandes instances. La borne MST peut être faible. Les services constants peuvent réduire les pourcentages relatifs sans prouver que les trajets et attentes sont proches de leurs meilleurs niveaux : leur décomposition doit accompagner les résultats.

Les fichiers `results/time_objective/catalogue/runs/` contiennent les solutions, temps et traces. Le protocole et les sources effectivement exécutées sont conservés. `scripts/analyze_duration.py` recalcule les contraintes, les références et les statistiques ; `scripts/valider_duree.py` contrôle la remise. Le notebook recalcule les analyses et exemples, sans relancer les 646 résolutions.

```powershell
python -m pip install -r requirements.txt
python cli.py C101 --method ils_hgs --seconds 10 --seed 4101
python -m streamlit run web/app.py
python scripts/analyze_duration.py
python scripts/valider_duree.py
python -m pytest tests -q --junitxml=livraison/TESTS.xml
```

L’objectif de la CLI est la durée par défaut. Les routines historiques en distance restent explicites pour les contrôles de non-régression ; leurs anciens résultats ne sont pas utilisés comme des benchmarks temporels.

## Références

- Sujet CESI, *Algorithmique et optimisation*, énoncé : minimisation de la durée totale d’une tournée ; extension annoncée au trafic horaire.
- Support CESI, *Corbeille d’exercices — Statistiques descriptives*, exercices 1–8 : indicateurs, quantiles, covariance/Pearson, moindres carrés, R² et représentations.
- [PyVRP, code source version 0.12.2](https://github.com/PyVRP/PyVRP/tree/v0.12.2) : moteur HGS externe, durée, fenêtres et paramètres de véhicules.
- [Documentation PyVRP : temps et durées](https://pyvrp.org/notebooks/duration_constraints.html) ; les propriétés utilisées sont également vérifiées dans la version 0.12.2 installée.
- [Règles officielles DIMACS VRPTW](https://dimacs.rutgers.edu/programs/implementation-challenges/vehicle-routing/implementation-challenge-vehicle-routing/vrp-with-time-windows) : objectif de référence en distance, flotte maximale et convention des arcs.
- [Données PyVRP/Instances](https://github.com/PyVRP/Instances), révision figée dans `data/manifest.json`.
''')
    from scripts.revision_duree import augment
    augment(nb,df,cases,sizes)
    from scripts.add_algorithm_theory import add_to_notebook as add_theory
    add_theory(nb)
    sensitivity_protocol=ROOT/'results/time_objective/sensitivity_controlled/protocol.json'
    if sensitivity_protocol.exists():
        sensitivity_jobs=json.loads(sensitivity_protocol.read_text())['jobs']
        if all((sensitivity_protocol.parent/'runs'/f'{name}_{seed}_{config}.json').exists()
               for name,seed,config in sensitivity_jobs):
            from scripts.reporting_completion import harmonize
            harmonize(nb)
    target=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb';nbformat.write(nb,target)
    text_parts=[]
    import re
    for c in nb.cells:
        if c.cell_type=='markdown':text_parts.append(c.source.replace('(../livraison/','(livraison/'))
        elif c.metadata.get('figure_captions'):
            name=re.search(r"livraison/duree_figures/([^']+)",c.source).group(1)
            text_parts.append('!['+c.metadata['figure_captions'][0]+'](livraison/duree_figures/'+name+')')
    text='\n\n'.join(text_parts)
    (ROOT/'LIVRABLE_FINAL.md').write_text(text,encoding='utf-8')
    from scripts.revision_duree import write_markdown
    write_markdown(nb)
    df.to_csv(ROOT/'livraison/RESULTATS_DUREE.csv',index=False)
    cases.to_csv(ROOT/'livraison/INSTANCES_DUREE.csv',index=False)
    descriptive.to_csv(ROOT/'livraison/STATISTIQUES_DESCRIPTIVES_DUREE.csv',index=False)
    page='''<!doctype html><html lang="fr"><meta charset="utf-8"><title>CVRPTW — tous les résultats en durée</title>
<style>body{font:15px Arial;margin:28px;color:#14233a}table{border-collapse:collapse;font-size:12px}td,th{padding:6px;border:1px solid #ddd}th{background:#e6f1ed}input{padding:10px;width:360px;max-width:90%}section{overflow:auto;max-height:75vh;margin-bottom:30px}thead{position:sticky;top:0}</style>
<h1>CVRPTW — résultats en durée</h1><p>356 instances ; 646 résolutions distinctes. Départs à zéro : trajets + attentes + services. Calcul en secondes, durée en unités du benchmark.</p>
<p>La référence est la durée recalculée d’un plan BKS distance, sans preuve d’optimalité en temps. Un écart négatif est possible. La borne MST est une borne inférieure, distincte du plan témoin.</p>
<label>Filtrer une instance ou une méthode : <input id="filter" placeholder="R2_10_8, hybrid…"></label>'''
    page+='<h2>Couverture : 356 instances, 472 essais hybrides</h2><section>'+cases.to_html(index=False,escape=True)+'</section>'
    page+='<h2>Tous les 646 essais, comparaisons comprises</h2><section>'+df.to_html(index=False,escape=True)+'</section>'
    page+='''<script>document.getElementById('filter').addEventListener('input',function(){const s=this.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>{r.style.display=r.textContent.toLowerCase().includes(s)?'':'none';});});</script></html>'''
    (ROOT/'livraison/RESULTATS_DUREE.html').write_text(page,encoding='utf-8')
    from scripts.prepare_soutenance import main as prepare_soutenance
    prepare_soutenance()
    print('Duration notebook built from executed data:',info['runs'],'runs')


if __name__=='__main__':main()
