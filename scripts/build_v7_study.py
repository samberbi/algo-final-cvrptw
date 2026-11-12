"""Build the measured large-instance study, retaining unsuccessful hypotheses."""
from pathlib import Path
import json
import importlib.metadata
import platform
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import nbformat
from scripts.analyze_v7 import analyze, BASE
from scripts.build_ils_v5_delivery import execute
from scripts.export_report import markdown_table

LABELS = dict(baseline='ILS propre', external_warm='Construction propre + HGS externe',
              external_cold='HGS externe, départ libre', gls='ILS et coût guidé',
              penalty='Exploration pénalisée', penalty_hot='Pénalités, température forte',
              penalty_ils='ILS pénalisée', intensive_ils='ILS pénalisée approfondie')
LABELS['hybrid_hgs'] = 'ILS propre 60 s + HGS externe 60 s'


def main():
    import psutil
    environment = dict(recorded_after_campaign=True, python=platform.python_version(),
        platform=platform.platform(), physical_cores=psutil.cpu_count(logical=False),
        logical_cores=psutil.cpu_count(logical=True), measured_workers=6, threads_per_worker=1,
        versions={p:importlib.metadata.version(p) for p in ['numpy','scipy','numba','pyvrp','pandas','pytest']})
    (BASE/'environment.json').write_text(json.dumps(environment, indent=2), encoding='utf-8')
    development = []
    for label in ['development', 'development_descent', 'development_intensive']:
        df, summary, _, _ = analyze(label)
        summary.insert(0, 'campaign', label)
        development.append(summary)
    dev = pd.concat(development, ignore_index=True)
    runs, summary, cases, analysis = analyze('confirmation_external')
    assert len(runs) == 48 and runs.valid.all()
    final_runs, final_summary, final_cases, final_analysis = analyze('continuation_120')
    all_runs = []
    for label in ['development', 'development_descent', 'development_intensive', 'confirmation_external', 'continuation_120']:
        frame = pd.read_csv(BASE/label/'flat.csv')
        frame.insert(0, 'campaign', label)
        all_runs.append(frame)
    pd.concat(all_runs, ignore_index=True).to_csv(ROOT/'livraison/RESULTATS_ILS_V7.csv', index=False)
    table = cases.pivot(index='instance', columns='variant', values='mean_gap')
    table = table[['baseline', 'external_warm']]
    table.columns = ['ILS propre : gap moyen (%)', 'HGS externe : gap moyen (%)']
    table.to_csv(BASE/'confirmation_external/comparison_by_instance.csv')
    figdir = ROOT/'livraison/ils_v7_figures'
    figdir.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(table))
    ax.plot(x, table.iloc[:, 0], 'o-', label='ILS propre')
    ax.plot(x, table.iloc[:, 1], 's-', label='Construction propre + HGS externe')
    ax.axhline(6, color='#b45309', linestyle='--', label='Cible moyenne : 6 %')
    ax.set_xticks(x, table.index, rotation=55, ha='right')
    ax.set(ylabel='Gap moyen à la BKS (%)', title='Douze instances de 1 000 clients, deux graines par méthode')
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(figdir/'comparison.png', dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 3.5))
    order = ['baseline', 'external_warm']
    ax.boxplot([runs.loc[runs.variant.eq(v), 'gap_pct'].to_numpy() for v in order],
               tick_labels=['ILS propre (24 essais)', 'HGS externe (24 essais)'], showmeans=True)
    ax.axhline(6, linestyle='--', color='#b45309')
    ax.set(ylabel='Gap à la BKS (%)', title='Dispersion de tous les essais, sans sélection du meilleur')
    fig.tight_layout(); fig.savefig(figdir/'distribution.png', dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 3.5))
    for v in order:
        r = runs[runs.variant.eq(v)]
        ax.scatter(r.total_s, r.gap_pct, label=LABELS[v], alpha=.8)
    ax.axhline(6, linestyle='--', color='#b45309')
    ax.set(xlabel='Temps réel : construction + moteur (s)', ylabel='Gap (%)',
           title='Même plafond de recherche, préparations comptées séparément')
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(figdir/'time_gap.png', dpi=160); plt.close(fig)
    own = summary.set_index('variant').loc['baseline']
    ext = summary.set_index('variant').loc['external_warm']
    comparison = analysis['comparisons'][0]
    achieved = ext.mean_gap < 6
    decision = dict(own_default_changed=False, external_is_our_implementation=False,
        external_mean_below_6=bool(achieved), own_mean_below_6=bool(own.mean_gap < 6),
        scope='12 fixed previously studied 1000-client cases, two new seeds, 60s search plus measured construction/setup',
        academic_adoption='External engine authorized by the user; attributed component, available as an optional hybrid')
    (BASE/'decision.json').write_text(json.dumps(decision, indent=2), encoding='utf-8')
    shown = summary.copy()
    shown['variant'] = shown.variant.map(LABELS)
    development_table = dev.copy()
    development_table['variant'] = development_table.variant.map(LABELS)
    text = f'''# Recherche d’amélioration sur les grandes instances CVRPTW

## Conclusion mesurée et statut

Sur les douze instances historiques à 1 000 clients, avec deux nouvelles graines et 60 secondes de recherche, notre ILS obtient **{own.mean_gap:.3f} %** de gap moyen. Le comparateur **construction propre puis HGS externe PyVRP 0.12.2** obtient **{ext.mean_gap:.3f} %**, avec {int(ext.valid)}/24 solutions finales réalisables. La cible moyenne de 6 % est {'atteinte par ce comparateur' if achieved else 'encore manquée par ce comparateur'}. Le pire essai externe reste à **{ext.worst_gap:.3f} %** : une moyenne sous 6 % ne signifie pas que tous les essais sont sous 6 %.

Le moteur par défaut et le livrable évalué restent notre ILS. PyVRP est une bibliothèque externe, et sa recherche génétique n’est pas notre implémentation. L’utilisateur a confirmé que le moteur externe est autorisé ; il reste explicitement attribué à PyVRP. La construction propre utilisée ici est une initialisation par insertion ; aucune phase d’optimisation ILS ne précède le HGS dans cette campagne.

## Problème, unités et calcul du gap

Le problème conserve la capacité, les fenêtres strictes sur le début de service, l’attente autorisée, la couverture exactement une fois, le retour au dépôt et la borne de flotte. La distance seule est minimisée selon la convention DIMACS : chaque arc vaut floor(10 × distance euclidienne) en interne. Les temps de trajet et les fenêtres utilisent la même échelle. Le moteur ne lit aucune BKS.

Après résolution, le vérificateur indépendant recalcule la distance D et toutes les contraintes sur les données originales. Pour une référence compatible B : **gap = 100 × (D − B) / B**. Une BKS est la meilleure solution connue, pas une preuve d’optimalité. Notre comparaison utilise les fichiers .sol du jeu figé et vérifie aussi ces solutions. La flotte est ici une contrainte maximale, pas le premier objectif : il ne faut pas mélanger cette comparaison avec la référence SINTEF hiérarchique.

La moyenne est la moyenne arithmétique des 24 gaps de chaque méthode, soit deux essais pour chacune des douze instances. Toutes les instances ont donc le même poids. Aucun seuil de gap ne sert à sélectionner les résultats. Les distances et les flottes de chaque exécution figurent dans le CSV complet.

## Hypothèses réellement implémentées dans notre code

1. **Coût guidé** (`algo/guided.py`) : des pénalités d’arcs fréquemment présents modifient seulement le coût de recherche. Les temps de trajet et contraintes restent inchangés. Seule la distance originale classe l’archive finale.
2. **Exploration pénalisée** (`algo/penalty_hybrid.py`) : les mouvements atomiques conservent tous les clients et la borne de flotte. Les états de travail peuvent dépasser la capacité ou les horaires. L’objectif de travail est F = D + wQ × excès de charge + wT × décalage temporel. Une arrivée tardive accumule un décalage puis ramène l’horloge à la borne de fin ; un décalage nul correspond à l’absence de violation temporelle. L’archive finale accepte exclusivement les états réalisables sur les contraintes originales.
3. **Descente pénalisée** (`algo/penalty_descent.py`, `algo/penalty_ils.py`) : relocate, swap, 2-opt et 2-opt* sont évalués sur ce coût de travail. Les poids sont adaptés à la fréquence des états réalisables. Les raccourcis fondés sur la seule distance sont utilisés seulement lorsque les routes concernées sont déjà réalisables.
4. **ILS pénalisée approfondie** (`algo/intensive_ils.py`) : quatre à douze perturbations acceptées au maximum, puis une descente jusqu’à un optimum local, en continuant la descente lorsqu’un bloc de 300 mouvements est épuisé. Cette variante corrige les perturbations trop longues de la première tentative.

Ces variantes sont des expériences distinctes. Les tests confirment la validité de leur archive et l’intégrité des données ; ils ne démontrent pas leur performance. Les gains observés sont insuffisamment réguliers pour remplacer le moteur courant.

## Développement : gains et régressions

Trois instances difficiles séparées de la confirmation : C2_10_8, R2_10_8 et RC2_10_8. Les deux premières campagnes utilisent la graine 2002 ; la troisième utilise 2003. Chaque campagne réexécute sa référence. Même une graine identique peut produire des résultats différents sous un arrêt au temps, puisque le nombre d’itérations dépend de l’exécution. Il faut comparer les méthodes dans leur campagne, sans choisir la référence la plus favorable a posteriori.

{markdown_table(development_table)}

Les trois échecs du premier départ libre externe sont des erreurs techniques de l’adaptateur lors de la récupération de sa version, après le calcul. Ils sont conservés avec leur traceback et ne sont ni des instances infaisables ni des résultats à gap nul. L’erreur a été corrigée puis trois nouveaux essais ont été exécutés sous un nouveau protocole. Les anciens essais n’ont pas été écrasés. Leur durée totale n’avait pas été enregistrée ; elle n’est pas remplacée par zéro.

## Confirmation sur les douze grandes instances

Les familles C1, C2, R1, R2, RC1 et RC2 sont représentées par les suffixes 3 et 4. Graines 2101 et 2102 ; 24 résolutions par méthode ; plafond de recherche de 60 s ; six processus, un cœur physique par processus et un seul thread. La même construction déterministe est utilisée pour chaque paire instance–graine. La préparation externe et la construction sont mesurées, la compilation est préchauffée hors budget. Les temps ne doivent pas être assimilés à ceux d’un ordinateur différent.

{markdown_table(shown)}

L’écart-type global mélange les différences entre instances et les variations entre graines. Il ne mesure donc pas uniquement l’aléa de l’algorithme. Les écarts-types par instance, fondés ici sur seulement deux valeurs, restent très incertains.

{markdown_table(table.reset_index())}

Le gain moyen apparié est **{comparison['improvement_pp']:.3f} points**. L’intervalle exploratoire à 95 % par rééchantillonnage des douze instances est [{comparison['instance_bootstrap95'][0]:.3f} ; {comparison['instance_bootstrap95'][1]:.3f}] points. Deux graines par instance restent limitées. Ces douze cas étaient déjà étudiés dans les campagnes précédentes : c’est une confirmation sur le lot difficile, pas une évaluation indépendante sur toutes les 60 instances à 1 000 clients.

![Comparaison par instance](../livraison/ils_v7_figures/comparison.png)

![Dispersion des 48 essais](../livraison/ils_v7_figures/distribution.png)

![Temps réels et qualité](../livraison/ils_v7_figures/time_gap.png)

## Ce que la référence externe nous apprend

L’article de Kool et ses coauteurs présente une recherche génétique hybride pour le VRPTW avec capacité et objectif de distance DIMACS. Elle combine population diversifiée, croisement de tournées, amélioration locale et pénalités de capacité/temps. Notre interprétation est que la diversification structurelle et l’efficacité de la recherche locale expliquent une partie de l’écart ; nos essais ne permettent pas d’isoler causalement chaque mécanisme.

Notre diagnostic pour la suite : une population diversifiée ou une recombinaison de tournées peut aider à changer la répartition des clients, mais ajouter des pénalités à une trajectoire unique n’a pas suffi dans nos essais. Une implémentation propre de ces mécanismes demanderait une nouvelle phase de développement et de validation. Les concaténations de segments temporels restent une piste d’accélération ; elles ne sont pas présentées comme déjà implémentées ici.

## Reproduire et lire les résultats

`results/optimization_v7/confirmation_external/protocol.json` fige les instances, graines, budgets, ordre des tâches et empreintes du code. Le sous-dossier `source/` conserve les sources réellement exécutées. `runs/` contient chaque solution complète, ses mesures et sa graine. `flat.csv`, `instances.csv`, `summary.csv` et `analysis.json` sont recalculables par `python scripts/analyze_v7.py confirmation_external`.

Le notebook `notebooks/Recherche_1000_clients_V7.ipynb` est exécuté sur ces données, sans relancer secrètement les recherches. `livraison/RESULTATS_ILS_V7.csv` rassemble les 81 essais des quatre campagnes, dont trois échecs techniques. Le pilote antérieur de trois départs libres à 20 s reste un diagnostic séparé dans `external_pilot/` : il n’entre dans aucune moyenne de confirmation.

Pour une référence manuelle explicite : `python scripts/run_external_reference.py R2_10_3 --seconds 60 --seed 2101 --our-construction`. Installer auparavant les dépendances facultatives avec `python -m pip install -r requirements-reference-v7.txt`. Cette commande ne change pas l’ILS par défaut.

## Sources et attribution

- Kool et al., *Hybrid Genetic Search for the Vehicle Routing Problem with Time Windows: a High-Performance Implementation* : https://wouterkool.github.io/pdf/paper-kool-hgs-vrptw.pdf
- Source de PyVRP **0.12.2** réellement utilisée, fondée sur `GeneticAlgorithm` : https://github.com/PyVRP/PyVRP/blob/v0.12.2/pyvrp/solve.py
- Licence MIT et auteurs de la bibliothèque : https://github.com/PyVRP/PyVRP/blob/v0.12.2/LICENSE.md
- Voudouris et Tsang, principe général du coût guidé, étudié dans cet article pour le voyageur de commerce : https://www.sciencedirect.com/science/article/pii/S037722179800099X . Il ne constitue pas une preuve de gain pour notre CVRPTW.

La version externe est épinglée : les versions récentes de PyVRP ont une architecture différente et ne doivent pas être confondues avec ce HGS 0.12.2.
'''
    assert len(final_runs) == 48 and final_runs.valid.all()
    final_own = final_summary.set_index('variant').loc['baseline']
    final_ext = final_summary.set_index('variant').loc['hybrid_hgs']
    final_table = final_cases.pivot(index='instance', columns='variant', values='mean_gap')[['baseline', 'hybrid_hgs']]
    final_table.columns = ['ILS 60 s + ILS 60 s (%)', 'ILS 60 s + HGS externe 60 s (%)']
    final_table.to_csv(BASE/'continuation_120/comparison_by_instance.csv')
    final_shown = final_summary.copy()
    final_shown['variant'] = final_shown.variant.map(LABELS)
    final_shown.loc[final_shown.variant.eq('ILS propre'), 'variant'] = 'ILS propre 60 s + ILS propre 60 s'
    fig, ax = plt.subplots(figsize=(11, 2.1))
    ax.set(xlim=(0, 4), ylim=(0, 1)); ax.axis('off')
    for i, (label, color) in enumerate([
        ('Construction propre\n(capacité et horaires)', '#dbeafe'),
        ('Notre ILS\n60 secondes', '#dbeafe'),
        ('HGS externe PyVRP\n60 secondes', '#ffedd5'),
        ('Vérification indépendante\npuis calcul du gap', '#dcfce7')]):
        ax.text(i+.47, .5, label, ha='center', va='center', fontsize=9,
                bbox=dict(boxstyle='round,pad=.55', facecolor=color, edgecolor='#64748b'))
        if i < 3:
            ax.annotate('', xy=(i+1.07, .5), xytext=(i+.89, .5), arrowprops=dict(arrowstyle='->', color='#334155'))
    fig.tight_layout(); fig.savefig(figdir/'pipeline.png', dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(final_table))
    ax.plot(x, final_table.iloc[:, 0], 'o-', label='ILS 60 s + ILS 60 s')
    ax.plot(x, final_table.iloc[:, 1], 's-', label='ILS 60 s + HGS externe 60 s')
    ax.axhline(6, color='#b45309', linestyle='--', label='Cible moyenne : 6 %')
    ax.set_xticks(x, final_table.index, rotation=55, ha='right')
    ax.set(ylabel='Gap moyen à la BKS (%)', title='Pipelines à 120 s de recherche totale, douze cas × deux graines')
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(figdir/'comparison_120.png', dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.boxplot([final_runs.loc[final_runs.variant.eq(v), 'gap_pct'].to_numpy() for v in ['baseline', 'hybrid_hgs']],
               tick_labels=['ILS puis ILS (24 essais)', 'ILS puis HGS externe (24 essais)'], showmeans=True)
    ax.axhline(6, linestyle='--', color='#b45309')
    ax.set(ylabel='Gap à la BKS (%)', title='Tous les résultats des pipelines de 120 s, sans filtrage')
    fig.tight_layout(); fig.savefig(figdir/'distribution_120.png', dpi=160); plt.close(fig)
    headline = f'''\n\n**Bilan des pipelines de 120 s : {final_own.mean_gap:.3f} % pour deux phases ILS ; {final_ext.mean_gap:.3f} % pour ILS puis HGS externe.** La cible moyenne de 6 % est {'atteinte' if final_ext.mean_gap < 6 else 'manquée'} par cette seconde combinaison sur les douze cas étudiés et deux graines. Cette combinaison comprend une bibliothèque externe, explicitement attribuée ; elle ne remplace pas automatiquement la métaheuristique évaluée.\n'''
    text = text.replace('# Recherche d’amélioration sur les grandes instances CVRPTW', '# Recherche d’amélioration sur les grandes instances CVRPTW'+headline, 1)
    text = text.replace('les 81 essais des quatre campagnes', 'les 129 exécutions des cinq campagnes')
    gain = final_analysis['comparisons'][0]
    text += f'''\n\n## Complément décisif : ILS puis moteur génétique externe\n\nL’essai naïf à 60 s a révélé une régression majeure : sur R1_10_3, graine 2101, le moteur externe a conservé la construction initiale à 41,238 %. Cette valeur n’est pas supprimée. Le démarrage réalisable ne garantit pas une bonne initialisation, et une minute n’a pas suffi à ce moteur pour la corriger sur ce cas.\n\nNous réutilisons donc les **24 sorties ILS réellement calculées pendant 60 s** dans la campagne précédente. À partir de chaque même sortie, deux nouvelles branches sont exécutées : ILS pendant 60 s, ou HGS externe pendant 60 s. La graine de seconde phase est la graine initiale + 10 000 pour les deux branches. Les deux pipelines sont ainsi facturés à 120 s de recherche, avec la même construction et leurs préparations effectives. Les 24 préfixes sont réutilisés, pas recalculés : la nouvelle campagne exécute **48 secondes phases**. Les branches partagent leur première phase ; elles sont appariées et ne doivent pas être traitées comme deux expériences indépendantes.\n\n{markdown_table(final_shown)}\n\n{markdown_table(final_table.reset_index())}\n\nLe gain apparié moyen est {gain['improvement_pp']:.3f} points, avec un intervalle exploratoire par instances [{gain['instance_bootstrap95'][0]:.3f} ; {gain['instance_bootstrap95'][1]:.3f}]. Le pipeline hybride atteint un gap inférieur à 6 % dans **{int(final_ext.below_6)}/24** essais, avec un pire résultat de **{final_ext.worst_gap:.3f} %**. Sa durée totale moyenne mesurée est **{final_ext.mean_total_s:.2f} s**, et non 60 s.\n\n![Comparaison des pipelines de 120 s](../livraison/ils_v7_figures/comparison_120.png)\n\n![Dispersion des pipelines de 120 s](../livraison/ils_v7_figures/distribution_120.png)\n\nCette construction du protocole garantit une comparaison de deux continuations à effort nominal égal. Elle ne représente pas une ILS continue lancée une seule fois pendant 120 s : l’ILS de référence est elle aussi relancée depuis l’archive à mi-parcours. Le budget a été augmenté après le diagnostic à 60 s ; ce complément est donc une expérience de suivi, pas une confirmation indépendante. Les données, objectifs, contraintes et références n’ont pas changé.\n\n**Décision :** rendre disponible la combinaison ILS–HGS en option dans la CLI et l’interface web, avec attribution explicite du composant externe. La combinaison ILS–HGS est une option technique mesurée, pas un HGS que nous aurions nous-mêmes codé. Les essais négatifs, les 48 premières comparaisons et les trois erreurs techniques restent dans le tableau complet.\n'''
    text += '\nLa combinaison optionnelle est accessible dans `algo/hybrid_reference.py`. Pour la relancer depuis une construction neuve : `python scripts/run_hybrid_reference.py R2_10_3 --search-seconds 120 --seed 2101`. Le temps réel inclut la construction et la préparation externe en plus des deux parts de recherche ; le préchauffage est affiché séparément. Le pilote à 20 s et les essais manuels ne sont pas inclus dans les 129 exécutions des cinq campagnes.\n'
    text += '\nNotre contribution est le développement de l’intégration hybride, de l’initialisation, de l’ILS, du protocole et de la validation. Le moteur HGS est celui de PyVRP, attribué à ses auteurs. Le profil `ILS + HGS (PyVRP)` est disponible dans l’interface web, et la CLI principale accepte `--method ils_hgs --seconds 120`. Pour ce profil, les 120 secondes sont partagées entre les deux recherches ; la construction et la préparation externe sont comptées en plus dans le temps réel. La phase HGS ne collecte pas ici sa convergence interne : seuls ses points de début et de fin sont affichés.\n'
    text += '\n![Notre initialisation et ILS, moteur externe attribué, puis vérification](../livraison/ils_v7_figures/pipeline.png)\n'
    decision.update(external_mean_below_6=bool(final_ext.mean_gap < 6),
                    own_mean_below_6=bool(final_own.mean_gap < 6),
                    primary_campaign='continuation_120',
                    naive_60s_external_mean=float(ext.mean_gap),
                    scope='12 fixed previously studied 1000-client cases, two seeds; 60s ILS prefix and matched 60s continuation; construction/setup charged')
    (BASE/'decision.json').write_text(json.dumps(decision, indent=2), encoding='utf-8')
    (ROOT/'docs/RECHERCHE_GRANDES_INSTANCES_V7.md').write_text(text, encoding='utf-8')
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_markdown_cell(text.replace('../livraison/', '../livraison/')),
        nbformat.v4.new_code_cell("from pathlib import Path\nimport pandas as pd\nimport matplotlib.pyplot as plt\nroot = Path.cwd()\nif not (root / 'data/manifest.json').exists():\n    root = root.parent\nfolder = root / 'results/optimization_v7/confirmation_external'\nruns = pd.read_csv(folder / 'flat.csv')\nassert len(runs) == 48 and runs.valid.all()\ndisplay(pd.read_csv(folder / 'summary.csv'))"),
        nbformat.v4.new_markdown_cell('## Toutes les distances, flottes et graines de confirmation'),
        nbformat.v4.new_code_cell("display(runs[['instance', 'seed', 'variant', 'bks', 'cost', 'vehicles', 'gap_pct', 'total_s']].sort_values(['instance', 'seed', 'variant']))"),
        nbformat.v4.new_markdown_cell('## Recalcul indépendant du gap et de sa moyenne'),
        nbformat.v4.new_code_cell("import numpy as np\nrecomputed = 100 * (runs.cost - runs.bks) / runs.bks\nassert np.allclose(recomputed, runs.gap_pct)\ndisplay(runs.groupby('variant').gap_pct.agg(['count', 'mean', 'std', 'min', 'max']))\nfor variant, values in runs.groupby('variant'):\n    assert len(values) == 24\n    assert np.isclose(values.gap_pct.mean(), values.groupby('instance').gap_pct.mean().mean())"),
        nbformat.v4.new_code_cell("from IPython.display import Image, display\nfor name in ['comparison', 'distribution', 'time_gap']:\n    display(Image(filename=str(root / 'livraison/ils_v7_figures' / (name + '.png'))))")]
    nb.cells += [nbformat.v4.new_markdown_cell('## Résultats des pipelines : les deux phases et tout leur coût'),
        nbformat.v4.new_code_cell("final = pd.read_csv(root / 'results/optimization_v7/continuation_120/flat.csv')\nassert len(final) == 48 and final.valid.all()\nassert np.allclose(final.total_s, final.reused_prefix_s + final.newly_executed_s)\ndisplay(final.groupby('variant').agg(essais=('gap_pct', 'size'), gap_moyen=('gap_pct', 'mean'), ecart_type=('gap_pct', 'std'), pire=('gap_pct', 'max'), temps_total=('total_s', 'mean')))\ndisplay(final[['instance', 'seed', 'variant', 'bks', 'cost', 'vehicles', 'gap_pct', 'total_s']].sort_values(['instance','seed','variant']))\nfor name in ['comparison_120','distribution_120']:\n    display(Image(filename=str(root / 'livraison/ils_v7_figures' / (name + '.png'))))")]
    execute(nb, ROOT/'notebooks/Recherche_1000_clients_V7.ipynb')
    html = pd.concat(all_runs, ignore_index=True).to_html(index=False, escape=True)
    (ROOT/'livraison/RESULTATS_ILS_V7.html').write_text('<meta charset="utf-8"><h1>Expériences v7 : tous les essais</h1>'+html, encoding='utf-8')
    note = f'''\n\n## Recherche v7 sur les grandes instances\n\nLa [nouvelle étude](docs/RECHERCHE_GRANDES_INSTANCES_V7.md) et son [notebook exécuté](notebooks/Recherche_1000_clients_V7.ipynb) comparent notre ILS à un **moteur externe identifié**, PyVRP 0.12.2 HGS. Sur douze instances de 1 000 clients et deux nouvelles graines, à 60 secondes de recherche, les gaps moyens sont {own.mean_gap:.3f} % pour notre ILS et {ext.mean_gap:.3f} % pour la construction propre suivie du moteur externe. Les 48 solutions de confirmation sont réalisables. Le pire gap externe reste {ext.worst_gap:.3f} %.\n\nLes variantes propres à coût guidé et pénalités sont documentées avec leurs régressions. L’ILS par défaut et le livrable évalué v6 restent en place : les résultats externes ne sont pas attribués à notre implémentation. [Tous les essais v7](livraison/RESULTATS_ILS_V7.html), [CSV](livraison/RESULTATS_ILS_V7.csv).\n'''
    note += f'\nLe suivi à **120 s de recherche totale** compare deux phases ILS à ILS puis HGS externe : **{final_own.mean_gap:.3f} % contre {final_ext.mean_gap:.3f} %**, sur les mêmes 24 paires. Les préfixes sont réutilisés et tout leur temps est facturé dans chaque pipeline. La combinaison comporte un moteur externe ; elle reste une option de recherche distincte du livrable évalué. Commande : `python scripts/run_hybrid_reference.py R2_10_3 --search-seconds 120 --seed 2101`.\n'
    readme = ROOT/'README.md'
    before = readme.read_text(encoding='utf-8').split('\n\n## Recherche v7 sur les grandes instances')[0]
    readme.write_text(before + note, encoding='utf-8')
    print(json.dumps(decision, indent=2))


if __name__ == '__main__':
    main()
