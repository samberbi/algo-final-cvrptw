"""Complète le livrable depuis les essais TD enregistrés, sans résolution."""
from pathlib import Path
import csv
import json
import statistics
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def content():
    folder = ROOT/'results/dabia2013/pilote_5s_3graines'
    rows = list(csv.DictReader((folder/'RESULTATS.csv').open(encoding='utf-8-sig')))
    assert len(rows) == 18 and all(r['valid'] == 'True' for r in rows)
    grouped = {}
    for row in rows:
        grouped.setdefault(row['instance'], []).append(row)
    # Figures construites uniquement à partir des traces et coûts réellement enregistrés.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figdir = ROOT/'livraison/duree_figures'
    names = list(grouped)
    fig, ax = plt.subplots(figsize=(9, 4))
    x = list(range(len(names)))
    initial = [float(grouped[n][0]['initial_duration']) for n in names]
    final = [statistics.mean(float(r['duration']) for r in grouped[n]) for n in names]
    ax.bar([i-.18 for i in x], initial, .36, label='Construction propre', color='#9eb8cb')
    ax.bar([i+.18 for i in x], final, .36, label='Après ILS temporel', color='#176b89')
    ax.set_xticks(x, names)
    ax.set_ylabel('Durée totale (u.t. du benchmark Dabia2013)')
    ax.set_title('Six instances à 25 clients — trois graines, budget souple de 5 s')
    ax.legend()
    fig.tight_layout();fig.savefig(figdir/'dabia_avant_apres.png', dpi=160);plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(11, 6))
    for ax, name in zip(axes.flat, names):
        for row in grouped[name]:
            record = json.loads((folder/f"{name}_{row['seed']}.json").read_text())
            trace = record['result']['trace']
            initial_cost = record['result']['initial_cost']
            ax.step([r['elapsed_s'] for r in trace]+[record['result']['runtime_s']],
                    [100*(r['best']/initial_cost-1) for r in trace]+[100*(record['result']['cost']/initial_cost-1)],
                    where='post', label=row['seed'], alpha=.75)
        ax.set_title(name);ax.set_xlabel('Temps de résolution (s)');ax.set_ylabel('Variation depuis construction (%)')
    axes.flat[0].legend(title='Graine', fontsize=7)
    fig.suptitle('Convergence de l’ILS temporel — trois graines par instance')
    fig.tight_layout();fig.savefig(figdir/'dabia_convergence.png', dpi=160);plt.close(fig)
    lines = ['| Instance | Clients | Graines | Durée moyenne (u.t. Dabia) | BKS Duration | Gap moyen (%) | Écart-type durée | CPU moyen (s) |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name, trials in grouped.items():
        durations = [float(r['duration']) for r in trials]
        lines.append(f"| {name} | 25 | {len(trials)} | {statistics.mean(durations):.6f} | "
                     f"{float(trials[0]['reference_duration']):.6f} | "
                     f"{statistics.mean(float(r['gap_duration_bks_pct']) for r in trials):+.6f} | "
                     f"{statistics.pstdev(durations):.6f} | {statistics.mean(float(r['total_cpu_s']) for r in trials):.3f} |")
    text = r'''### 6.13. Extension temporelle : pilote Dabia2013 à objectif compatible

**Pourquoi cette extension ?** Les fichiers de référence DIMACS des campagnes
précédentes optimisent les trajets. Leur durée recalculée permet une comparaison
descriptive, mais pas un gap à une BKS en durée. Nous conservons ces expériences
et ajoutons un pilote distinct, avec un objectif et des références temporels
compatibles. Aucun ancien pourcentage n'est renommé en nouveau gap.

**Données et périmètre.** Six instances de Dabia2013 à **25 clients** représentent
C1, C2, R1, R2, RC1 et RC2. Les 18 fichiers instance/fonctions temporelles/BKS
sont téléchargés sans modification depuis la révision
`331ec306b7908e0c9a264d1fc1341a938340ab79` de MAMUT-routing. Le manifeste conserve
les URL et empreintes SHA256. Il s'agit de dérivés temporels de Solomon, pas des
fichiers DIMACS statiques à 100 clients portant parfois le même nom. Les unités
de temps natives de Dabia sont conservées sans appliquer notre conversion
DIMACS par dix. Les durées brutes des deux jeux ne doivent pas être mélangées.

**Adaptation mathématique.** Le temps d'arrivée sur un arc est désormais une
fonction de son heure de départ :

$$
\alpha_{ij}(t)=t+\tau_{ij}(t).
$$

Pour une tournée $p=(v_1,\ldots,v_m)$ partant à $D_p$, les horaires sont :

$$
A_{v_1}=\alpha_{0v_1}(D_p),\quad
B_{v_j}=\max(A_{v_j},e_{v_j}),\quad
F_{v_j}=B_{v_j}+s_{v_j},
$$
$$
A_{v_{j+1}}=\alpha_{v_jv_{j+1}}(F_{v_j}),\quad
R_p=\alpha_{v_m0}(F_{v_m}).
$$

Les débuts de service respectent $B_i\le l_i$, les charges et la flotte restent
bornées, et le retour respecte la fermeture du dépôt. Le départ est cette fois
**une décision**, dans le domaine autorisé par les données. L'objectif devient :

$$
\boxed{\min T_{TD}=\sum_{p}(R_p-D_p)}
=T_{\mathrm{trajets}}+T_{\mathrm{attentes}}+T_{\mathrm{services}}.
$$

Ce changement est nécessaire pour respecter le benchmark. Il ne s'agit pas de
réétiqueter le modèle statique $\min\sum_kR_k$ à départs nuls. Le PLNE de la
section 2 reste un modèle **statique**, non un solveur exact de cette extension.
Les fonctions temporelles sont évaluées en double précision selon le contrat
canonique `td-fold/2`, avec prise en compte des changements de vitesse pendant
les trajets ; elles ne sont pas remplacées par une matrice de temps constants.

**Algorithme réellement exécuté et attribution.** Dans `algo/dabia.py`, notre
code effectue l'insertion séquentielle, la descente locale avec relocate, swap,
2-opt et 2-opt*, les perturbations/redémarrages ILS et la conservation de la
meilleure solution. Chaque ordre de tournée proposé est évalué avec son départ
optimal par **MAMUT-routing-lib 0.12.0**, bibliothèque externe également utilisée
comme contrôleur canonique final. Ce calcul d'horaire n'est pas présenté comme
une invention ou une implémentation personnelle. Ce pilote n'utilise **ni le
HGS statique PyVRP ni un nouveau solveur exact externe**. Un cache par instance
réutilise les évaluations de tournées identiques. L'acceptation locale exige une
amélioration supérieure à $10^{-8}$ unités ; cette tolérance de recherche ne
modifie ni les données ni le coût de validation du contrôleur.

**Vérification.** Les coûts de référence sont relus et vérifiés après la recherche,
jamais utilisés pour construire ou arrêter la solution. Une seconde simulation
avant reconstruit trajets, attentes et services à partir des départs retenus ;
elle utilise une tolérance diagnostique de $10^{-7}$ pour les arrondis. La
validation normative reste le contrôleur MAMUT sans epsilon. Les tests couvrent
aussi les doublons, clients absents, capacité, variations de trajet selon le
départ, conservation des clients par les mouvements et monotonie de l'archive.

**Protocole du pilote.** Après six résolutions préliminaires conservées, un second
lot de **18 résolutions enregistrées** couvre six instances et trois graines
(4101–4103), avec cinq secondes de budget souple par résolution. Cela représente
24 résolutions enregistrées au total sur ces deux lots, pas 24 instances. Le lot
ci-dessous est le second seulement. Les trois workers réduisent le délai du lot,
mais chaque CPU est mesuré dans le processus qui résout l'instance. Le chargement,
la construction, la recherche et la simulation finale sont comptés ; le
démarrage de l'interpréteur et le contrôle ultérieur du témoin sont exclus.

**Résultats mesurés.** Les 18 solutions sont réalisables et leur coût canonique
est exactement égal à celui de la BKS correspondante : gap moyen et maximal
**0 %**, sans valeur négative et sans plafonnement. Ce zéro est une égalité
effective des coûts canoniques de nos solutions et des références.
Les écarts-types sont nuls sur ces trois graines ; cela ne garantit pas la même
stabilité sur des instances plus grandes.

TABLE

Les CPU totaux observés ne dépassent pas **MAXCPU s**, et les temps écoulés
totaux ne dépassent pas **MAXWALL s**. Ces mesures respectent deux minutes sur
ce pilote ; ce n'est pas une garantie sur toute machine ou toute taille.

![Construction et ILS temporel sur les six instances du pilote.](../livraison/duree_figures/dabia_avant_apres.png)

**Lecture et intérêt.** Chaque paire de barres compare le coût construit et le
coût final moyen des trois graines, avec les unités propres à Dabia. Le service
reste obligatoire dans les deux coûts. C201 est déjà au coût de référence après
construction ; l'ILS ne lui apporte donc aucun gain mesuré. Sur R201, RC101 et
RC201, les baisses depuis la construction valent respectivement environ
17,50 %, 12,24 % et 12,36 %. Cette comparaison mesure l'apport de la recherche
combinée, pas l'effet isolé de chacun des quatre mouvements.

![Traces observées des trois graines pour chacune des six instances.](../livraison/duree_figures/dabia_convergence.png)

**Lecture et continuité.** Les courbes en escalier tracent uniquement les records
enregistrés, normalisés par le coût de construction, puis prolongés jusqu'au
temps réel de fin. Des courbes superposées sont possibles. Cette figure complète
le tableau final en montrant la progression de la recherche ; elle ne démontre
ni optimalité globale ni généralisation à 100 ou 1 000 clients.

**Statut des références et limites.** Les six fichiers indiquent historiquement
une preuve d'optimalité, mais C101, R201 et RC201 portent une note de réévaluation
du coût après le passage à `td-fold/2`, avec recertification encore en attente.
Nous conservons donc le libellé prudent **gap à une BKS Duration compatible**,
sans revendiquer six preuves nouvelles d'optimalité. Le contrôleur, ses versions
et les notes originales sont enregistrés. Ce pilote de développement ne couvre
que six instances choisies à 25 clients et ne remplace pas les campagnes statiques
à 100–1 000 clients. Aucun résultat à 50/100 clients Dabia ni à 1 000 clients
temporels n'a été exécuté dans cette étape. L'ablation des opérateurs et une
validation sur un lot non utilisé pour la mise au point restent à faire.

**Sources et reproduction.** Données :
[MAMUT Dabia2013](https://github.com/ANR-MAMUT/MAMUT-routing/tree/331ec306b7908e0c9a264d1fc1341a938340ab79/benchmarks/TDVRPTW/Dabia2013).
Méthodologie d'origine : Dabia et al. (2013) et Lera-Romero et al. (2020).
Contrôleur externe : [MAMUT-routing-lib](https://github.com/ANR-MAMUT/MAMUT-routing-lib),
version 0.12.0. Sources de nos essais, données, références et diagnostics sont
dans `results/dabia2013/` et `data/dabia2013/`.

Depuis le dossier du projet, environnement optionnel indépendant :

```powershell
py -3.12 -m venv .venv_dabia
.\.venv_dabia\Scripts\python.exe -m pip install -r requirements-dabia.txt
.\.venv_dabia\Scripts\python.exe -m pytest tests/test_dabia.py -q
.\.venv_dabia\Scripts\python.exe scripts/validate_dabia.py
.\.venv_dabia\Scripts\python.exe scripts/benchmark_dabia.py --instances R201 --seconds 5 --label demo_dabia
```

La dernière commande affiche directement le coût, la BKS en durée, le gap signé,
le CPU et le temps réel. Chaque relance crée un dossier numéroté si nécessaire.
Les anciennes commandes `test_instances.py` continuent à résoudre le modèle
statique ; leur écart au témoin ne devient pas un gap Dabia.
'''
    return text.replace('TABLE', '\n'.join(lines)).replace('MAXCPU',f"{max(float(r['total_cpu_s']) for r in rows):.3f}").replace('MAXWALL',f"{max(float(r['total_wall_s']) for r in rows):.3f}")


def augment(nb):
    import nbformat
    nb.cells = [c for c in nb.cells if not c.metadata.get('dabia_extension')]
    cell = nbformat.v4.new_markdown_cell(content())
    cell.metadata['dabia_extension'] = True
    index = next(i for i,c in enumerate(nb.cells) if c.cell_type == 'markdown' and c.source.startswith('## 7.'))
    nb.cells.insert(index, cell)
    for c in nb.cells:
        if c.cell_type == 'markdown' and c.source.startswith('# Livrable final'):
            marker = '\n\n**Extension Dabia2013 validée**'
            c.source = c.source.split(marker)[0]+marker+' : un pilote distinct à 25 clients minimise la durée complète avec trajets dépendant de l’heure et départs optimisés. Voir section 6.13. Les résultats statiques à 100–1 000 clients restent conservés, avec leurs écarts aux témoins réévalués ; ils ne sont pas renommés en gaps temporels certifiés.'
        if c.cell_type == 'markdown' and c.source.startswith('## 7.'):
            marker = '\n\n**Bilan de l’extension temporelle.**'
            c.source = c.source.split(marker)[0]+marker+' Le pilote de la section 6.13 ajoute une évaluation à BKS Duration compatible : 18/18 solutions réalisables, au coût des BKS sur six instances à 25 clients et trois graines. Les 16 tests spécifiques passent. Le modèle statique, ses comparaisons et ses limites restent distincts. Le passage temporel à 50/100 clients et au-delà, ainsi que la recertification signalée dans certaines références, ne sont pas présentés comme achevés.'
    return nb


def main():
    # La mission finale impose des trajets fixes : ne plus modifier le notebook.
    text='# Exploration TD — hors périmètre du modèle statique confirmé\n\n'+content()
    (ROOT/'docs/EXTENSION_DABIA2013.md').write_text(text,encoding='utf-8')
    print('Archive exploratoire TD actualisée ; notebook statique inchangé.')


if __name__ == '__main__':
    main()
