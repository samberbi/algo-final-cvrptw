"""Build the current extension from measured data, including failed candidates."""
from pathlib import Path
import json
import sys
import re
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from scripts.analyze_ils_v5 import analyze, BASE
from scripts.export_report import markdown_table

LABELS = dict(baseline_ils="ILS de référence", baseline_sa="Recuit seul", rvnd="RVND complète",
              fixed="RVND fixe", no_blocks="RVND sans blocs", relay="Relais ILS–recuit",
              polished="ILS puis RVND", light="Perturbation réduite", wide="64 voisins",
              long_sub="Groupes : 0,6 s", short_sub="Groupes : 0,05 s", ils_sp="ILS–partitionnement")


def execute(nb, filename):
    directory = ROOT / ".tools/kernels/ils-v5"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "kernel.json").write_text(json.dumps(dict(argv=[sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"], display_name="CVRPTW ILS", language="python")))
    manager = KernelManager(kernel_name="ils-v5", kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(directory.parent)]))
    try:
        NotebookClient(nb, timeout=180, km=manager, resources={"metadata": {"path": str(ROOT)}}).execute()
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
        manager.cleanup_resources()
    nbformat.write(nb, filename)
    templates = Path(sys.base_prefix) / "share/jupyter/nbconvert/templates"
    options = dict(extra_template_basedirs=[str(templates)], extra_template_paths=[str(templates)]) if templates.exists() else {}
    output, _ = HTMLExporter(**options).from_notebook_node(nb)
    filename.with_suffix(".html").write_text(output, encoding="utf-8")


def main():
    development = pd.concat([analyze(label)[0] for label in ["development", "development_relay", "development_parameters", "development_partition"]], ignore_index=True)
    df, summary, instances = analyze("validation")
    assert development.valid.all() and df.valid.all()
    dev_summary = development.groupby("profile").agg(runs=("valid", "size"), mean_gap=("gap_pct", "mean"), worst_gap=("gap_pct", "max")).reset_index()
    dev_summary.to_csv(BASE / "development_all.csv", index=False)
    paired = df.pivot(index=["instance", "seed"], columns="profile", values="gap_pct")
    comparison = []
    for method in ["wide", "ils_sp"]:
        delta = paired["baseline_ils"] - paired[method]
        case_means = delta.groupby(level=0).mean().to_numpy()
        samples = np.random.default_rng(20261111).choice(case_means, (10000, len(case_means))).mean(axis=1)
        comparison.append(dict(method=method, mean_improvement_pp=float(delta.mean()),
                               wins=int((delta > 1e-8).sum()), losses=int((delta < -1e-8).sum()),
                               cluster_bootstrap95=list(map(float, np.quantile(samples, [.025, .975])))))
    (BASE / "validation/paired_analysis.json").write_text(json.dumps(comparison, indent=2))
    # Keep the original default unless a useful paired gain is supported.
    supported = [r for r in comparison if r["mean_improvement_pp"] > .2 and r["cluster_bootstrap95"][0] > 0]
    adopted = max(supported, key=lambda r: r["mean_improvement_pp"])["method"] if supported else "baseline_ils"
    decision = dict(recommended=adopted, default="baseline_ils", rule="Mean paired gain >0.2 percentage point and exploratory instance-bootstrap lower limit >0; otherwise retain baseline", comparisons=comparison,
                    caution="Two seeds per instance; exploratory evidence, not a universal superiority claim")
    (BASE / "decision.json").write_text(json.dumps(decision, indent=2))
    figures = ROOT / "livraison/ils_v5_figures"
    figures.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 4))
    ordered = dev_summary.sort_values("mean_gap")
    ax.barh([LABELS[x] for x in ordered.profile], ordered.mean_gap, color="#0f766e")
    ax.invert_yaxis(); ax.set_xlabel("Gap moyen à la BKS (%)"); ax.set_title("Développement : 6 instances × 2 graines, plafond 20 s")
    fig.tight_layout(); fig.savefig(figures / "development.png", dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4))
    methods = ["baseline_ils", "wide", "ils_sp"]
    ax.boxplot([df[df.profile.eq(m)].gap_pct for m in methods], tick_labels=[LABELS[m] for m in methods], showmeans=True)
    ax.axhline(6, color="#b45309", linestyle="--", label="Cible 6 %")
    ax.set_ylabel("Gap à la BKS (%)"); ax.set_title("Validation : tous les 24 essais de chaque méthode")
    ax.legend(); fig.tight_layout(); fig.savefig(figures / "validation.png", dpi=160); plt.close(fig)
    matrix = instances.pivot(index="instance", columns="profile", values="mean_gap")[methods]
    fig, ax = plt.subplots(figsize=(8, 5))
    picture = ax.imshow(matrix.to_numpy(), cmap="YlOrRd", aspect="auto")
    ax.set_yticks(range(len(matrix)), matrix.index); ax.set_xticks(range(3), [LABELS[m] for m in methods])
    for i in range(len(matrix)):
        for j in range(3): ax.text(j, i, f"{matrix.iloc[i,j]:.2f}", ha="center", va="center", fontsize=9)
    fig.colorbar(picture, ax=ax, label="Gap moyen (%)"); fig.tight_layout(); fig.savefig(figures / "instances.png", dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 2.4)); ax.axis("off")
    boxes = [(0.01, "Départ réalisable"), (.27, "ILS par groupes"), (.53, "Tournées vérifiées"), (.79, "Combinaison exacte\ndans l’archive")]
    for x, text in boxes:
        ax.text(x, .5, text, transform=ax.transAxes, ha="left", va="center", fontsize=9,
                bbox=dict(boxstyle="round,pad=.65", facecolor="#e6f2ef", edgecolor="#0f766e"))
    for x in [.21, .47, .73]: ax.annotate("", xy=(x+.045,.5), xytext=(x,.5), xycoords="axes fraction", arrowprops=dict(arrowstyle="->"))
    fig.tight_layout(); fig.savefig(figures / "scheme.png", dpi=160); plt.close(fig)
    by_case = matrix.rename(columns=LABELS).reset_index()
    show = summary[["profile", "runs", "mean_gap", "std_gap", "worst_gap", "under6", "under7", "mean_search_s", "mean_total_s"]].copy()
    show.profile = show.profile.map(LABELS)
    show.columns = ["Méthode", "Essais", "Gap moyen %", "Écart-type", "Pire gap %", "Sous 6 %", "Sous 7 %", "Recherche s", "Total s"]
    baseline = summary.set_index("profile").loc["baseline_ils", "mean_gap"]
    best_method = summary.loc[summary.mean_gap.idxmin(), "profile"]
    best_mean = summary.mean_gap.min()
    conclusion = (f"La variante {LABELS[adopted]} satisfait notre règle de gain apparié exploratoire et est recommandée pour poursuivre l’évaluation."
                  if adopted != "baseline_ils" else "Les essais ne justifient pas de remplacer le moteur ILS de référence par défaut. Les nouvelles variantes restent expérimentales et leurs régressions sont conservées.")
    archive_text = ""
    if (BASE / "portfolio_intensified/analysis.json").exists():
        archive = json.loads((BASE / "portfolio_intensified/analysis.json").read_text())
        archive_table = pd.read_csv(BASE / "portfolio_intensified/summary.csv").sort_values("instance")
        archive_table.columns = ["Instance", "Avant intensification %", "Archive finale %", "Effort cumulé s"]
        archive_text = f"""### Archive combinée à effort supérieur

Une étude distincte réunit seize trajectoires admissibles par instance : dix résolutions ILS/recuit de v2 et six résolutions de la nouvelle validation. Les tournées sont recombinées pendant au plus deux secondes, puis la solution reçoit 60 secondes supplémentaires : un tiers d’ILS et deux tiers de recuit sur mouvements directs, graine 1501. Les résolutions d’origine sont toutes comptées dans l’effort, avec la construction v2 partagée comptée une seule fois par paire et les constructions v5 effectivement répétées.

Cette archive atteint **{archive['mean_gap']:.3f} % de gap moyen**, avec un pire cas de **{archive['worst_gap']:.3f} %** et un effort cumulé moyen de **{archive['mean_effort_s']:.1f} secondes par instance**. Il s’agit d’une solution combinée par instance et de douze intensifications supplémentaires, pas d’une moyenne de répétitions indépendantes ni d’un solveur obtenant ce résultat en 40 ou 60 secondes. La baisse de 6,600 % à cette moyenne mesure l’amélioration de cette archive précise ; elle ne démontre pas la supériorité du relais sur un autre algorithme à effort total égal. L’objectif sous 6 % est atteint en moyenne dans ce périmètre coûteux, pas sur chaque instance ni dans le protocole court.

{markdown_table(archive_table)}

Les résultats complets sont dans `results/optimization_v5/portfolio_intensified/`. L’archive initiale reste disponible dans `portfolio/` ; aucune référence BKS n’est passée au moteur de recherche.
"""
    narrative = f"""# Améliorations de l’ILS pour le CVRPTW

Notre objectif reste la distance totale DIMACS, avec capacité homogène, fenêtres strictes sur le début du service, retour au dépôt, couverture unique et flotte maximale. Les données, les arrondis et les contraintes ne sont pas modifiés. Les références ne sont lues qu’après la résolution.

## Résultats exécutés et décision

Nous avons exécuté **{len(development)} résolutions de développement** sur six instances à 1 000 clients, deux graines et douze variantes, puis **{len(df)} résolutions de validation** sur douze autres instances, deux nouvelles graines et trois méthodes. Les phases d’un même solveur ne sont pas des répétitions indépendantes.

Le développement utilise les suffixes `_10_2`, les graines 1301 et 1302, et un plafond de 20 secondes. La validation utilise les suffixes `_10_3` et `_10_4`, les graines 1401 et 1402, et un plafond de 40 secondes. Ces géographies avaient déjà été étudiées dans le projet ; ce n’est pas un jeu entièrement inconnu. Aucun réglage n’est effectué à partir des résultats de cette nouvelle validation.

Les départs sont identiques par instance et graine. La construction est effectuée et chronométrée séparément pour chaque résolution ; le total comprend construction et recherche. Le préchauffage de compilation est hors budget. Chaque processus de calcul est fixé à un cœur logique distinct, avec un maximum de six processus. Le solveur de partitionnement peut terminer avant sa limite : les durées effectives sont publiées.

{markdown_table(show)}

L’ILS de référence obtient {baseline:.3f} % de gap moyen sur ces 24 essais. La plus petite moyenne observée est {best_mean:.3f} % pour {LABELS[best_method]}. Ce minimum observé ne suffit pas, à lui seul, à démontrer une supériorité générale. Toutes les solutions de ces campagnes ont été vérifiées réalisables.

{conclusion}

## Ce qui a été développé

**Échanges de blocs et RVND.** Le module `algo/rvnd.py` ajoute Swap(2,1), Swap(1,2) et Swap(2,2). Il calcule d’abord la variation des liaisons, filtre la capacité, puis vérifie entièrement les horaires des deux tournées modifiées. La RVND explore les voisinages dans un ordre aléatoire et réinitialise leur liste après une amélioration. Les déplacements de chaînes utilisent au plus trois clients. L’énumération exhaustive de petits exemples contrôle l’existence des améliorations, y compris avec fenêtres serrées.

**Perturbations variables.** `algo/ils_rvnd.py` augmente le nombre de mouvements complets et le nombre de voisins après stagnation. La solution courante et la meilleure archive sont séparées ; seule une solution complète et réalisable peut être acceptée. Une détérioration bornée par un seuil sert à explorer. Le meilleur résultat retourné ne peut pas être plus mauvais que le départ fourni. Cette intégration complète a régressé pendant le développement : son intérêt théorique ne constitue pas une amélioration démontrée dans notre code.

**Relais et finition.** `algo/relay.py` teste soit ILS puis recuit sur mouvements directs, soit ILS puis RVND. Le budget est partagé et non additionné. Ces variantes ne sont pas retenues comme remplacements sur la base de leurs moyennes de développement.

**Réglages ciblés.** La force de perturbation (1 contre 4), les voisins (64 contre 24) et le budget par groupe (0,05, 0,2 ou 0,6 seconde) sont testés séparément. Élargir le voisinage ouvre des mouvements mais augmente leur coût ; renforcer un composant n’améliore donc pas automatiquement le résultat à temps limité.

**ILS avec partitionnement.** `algo/ils_sp.py` consacre 95 % du budget disponible à quatre phases ILS successives, puis réserve au plus 5 secondes au choix des tournées. Les phases continuent la meilleure solution de la phase précédente avec une nouvelle graine. Toutes les tournées stockées proviennent de solutions réalisables produites par notre recherche ; aucune solution de référence n’est utilisée.

Pour les tournées archivées r, de distance c_r, nous minimisons $\\sum_r c_r y_r$, sous $\\sum_{{r:i\\in r}}y_r=1$ pour chaque client i, $\\sum_r y_r\\leq K$ et $y_r\\in\\{{0,1\\}}$. La capacité et les fenêtres sont déjà satisfaites par chaque tournée. La résolution utilise SciPy/HiGHS. Son écart relatif demandé est 0,1 % **dans l’archive seulement** : ce n’est pas le gap à la BKS ni une preuve d’optimalité du CVRPTW. En absence de solution du solveur dans le délai, l’archive réalisable précédente est conservée.

## Statistiques et lecture du gap

Le gap d’un essai est $100(D-D_{{BKS}})/D_{{BKS}}$, avec la même convention DIMACS pour les deux distances. La moyenne est la moyenne arithmétique des 24 gaps d’une méthode, sans sélectionner les meilleures graines. Chaque instance a le même poids puisqu’elle possède deux répétitions. Le nombre de véhicules reste une contrainte maximale ; il ne remplace pas l’objectif de distance.

L’écart-type du tableau décrit la dispersion des essais sur plusieurs instances : il mélange difficulté des cas et variabilité des graines. Le fichier `instances.csv` fournit aussi la dispersion par instance. Deux graines restent insuffisantes pour estimer finement cette variabilité.

Les différences appariées et un bootstrap exploratoire par instance sont fournis dans `paired_analysis.json`. Les douze instances sont rééchantillonnées en conservant ensemble leurs graines ; traiter tous les essais comme indépendants sous-estimerait l’incertitude. L’intervalle ne constitue pas une garantie de résultat sur toute la famille d’instances.

{markdown_table(by_case)}

## Protocole d’ablation

{markdown_table(dev_summary.assign(profile=dev_summary.profile.map(LABELS)).rename(columns=dict(profile="Variante", runs="Essais", mean_gap="Gap moyen %", worst_gap="Pire gap %")))}

Les comparaisons de RVND complète, fixe et sans blocs isolent partiellement l’intérêt de l’adaptation et des blocs dans cette architecture. Les différences entre cette architecture et l’ancien moteur ne sont pas attribuées au seul ajout d’un opérateur : l’ordonnancement de la recherche change aussi.

## Reproduction et limites

Les fichiers JSON bruts, protocoles, empreintes et sources figées sont dans `results/optimization_v5/`. Les moyennes et tableaux se recalculent avec `python scripts/analyze_ils_v5.py`. La commande `python scripts/benchmark_ils_v5.py --role validation --seconds 40 --seeds 1401 1402 --variants baseline_ils wide ils_sp` reprend les essais terminés ; une reproduction neuve doit utiliser `--label nouveau_lot`. Le même matériel et les mêmes versions restent nécessaires pour des temps comparables. Le manifeste des données permet de vérifier les fichiers d’instances.

Cette étude ne démontre pas un gap inférieur à 6 % sur toutes les grandes instances. Elle ne démontre pas non plus le passage à plusieurs milliers de clients, ni le trafic variable. Le calcul plus rapide par résumés de segments reste une piste future : il n’est pas présenté comme déjà implémenté.

## Sources méthodologiques

- [Ribas et ses coauteurs : ILS, RVND et partitionnement pour le VRPTW](https://luizsatoru.github.io/conteudo/artigos/PAPER%20IESM2011-SABIR.pdf). L’article traite capacité et fenêtres, mais ses expériences portent sur 100 clients ; sa colonne « gap » mesure la dispersion par rapport à son meilleur essai, pas notre gap moyen à la BKS.
- [Vidal et ses coauteurs : évaluation et recherche locale multi-attributs](https://www.cirrelt.ca/documentstravail/cirrelt-2012-23.pdf). Les résumés de portions de tournée motivent une future accélération sûre, après profilage.
- [Kool et ses coauteurs : voisinages et intensification pour le VRPTW](https://wouterkool.github.io/pdf/paper-kool-hgs-vrptw.pdf). Les performances du solveur complet ne sont pas attribuées à notre ILS.
"""
    narrative += "\n\n" + archive_text
    (ROOT / "docs/AMELIORATIONS_ILS.md").write_text(narrative, encoding="utf-8")
    appendix = nbformat.v4.new_notebook()
    appendix.cells = [nbformat.v4.new_markdown_cell(narrative), nbformat.v4.new_code_cell(
        "from pathlib import Path\nfrom IPython.display import display, Image\nROOT=next(p for p in [Path.cwd(),*Path.cwd().parents] if (p/'algo/ils_sp.py').exists())\n"
        + "\n".join(f"display(Image(filename=str(ROOT/'livraison/ils_v5_figures/{name}.png')))" for name in ["scheme", "development", "validation", "instances"]))]
    execute(appendix, ROOT / "notebooks/Ameliorations_ILS_CVRPTW.ipynb")
    nbpath = ROOT / "notebooks/Livrable_Final_CVRPTW.ipynb"
    nb = nbformat.read(nbpath, as_version=4)
    nb.cells = [c for c in nb.cells if not c.metadata.get("ils_v5_extension")]
    brief = f"""## 9. Étude complémentaire de l’ILS à 1 000 clients

Cette section complète les campagnes v2 précédentes ; leurs chiffres ne sont pas remplacés ou mélangés. L’objectif reste la distance sous capacité et fenêtres strictes.

Nous avons exécuté 144 essais de développement sur six instances et 72 essais de validation sur douze autres instances, avec deux graines par variante. Les départs sont appariés. Le plafond de recherche est 20 secondes en développement et 40 secondes en validation ; construction et préchauffage sont distingués.

{markdown_table(show)}

{conclusion} L’écart-type agrégé mélange la difficulté des instances et la variabilité des graines. Avec deux graines, cette dernière reste imparfaitement estimée. Les échecs et régressions des variantes sont conservés dans l’étude détaillée.

La variante ILS–partitionnement conserve des tournées réalisables produites par quatre phases ILS et choisit une couverture exacte sous la limite de flotte. Son solveur optimise seulement l’archive disponible ; il ne certifie pas l’optimalité du problème complet. Le plafond de 40 secondes inclut ces phases et le partitionnement.

Le détail des choix, les références, l’ablation et les résultats par instance sont fournis dans `docs/AMELIORATIONS_ILS.md` et le notebook exécuté `Ameliorations_ILS_CVRPTW.ipynb`.

{markdown_table(by_case)}
"""
    brief += "\n\n" + archive_text
    cell = nbformat.v4.new_markdown_cell(brief); cell.metadata["ils_v5_extension"] = True; nb.cells.append(cell)
    code = nbformat.v4.new_code_cell("display(Image(filename=str(ROOT/'livraison/ils_v5_figures/validation.png')))\ndisplay(Image(filename=str(ROOT/'livraison/ils_v5_figures/instances.png')))")
    code.metadata.update(ils_v5_extension=True, figure_captions=["Validation appariée : 24 essais par variante à 1 000 clients, plafond 40 secondes.", "Tous les gaps moyens par instance ; aucune sélection des cas favorables."])
    nb.cells.append(code)
    execute(nb, nbpath)
    (ROOT / "LIVRABLE_FINAL.md").write_text("\n\n".join(c.source for c in nb.cells if c.cell_type == "markdown"), encoding="utf-8")
    df.to_csv(ROOT / "livraison/RESULTATS_ILS_V5.csv", index=False)
    (ROOT / "livraison/RESULTATS_ILS_V5.html").write_text('<!doctype html><meta charset="utf-8"><title>CVRPTW : résultats appariés</title><h1>72 résolutions réelles à 1 000 clients</h1><p>Deux graines, douze instances, trois méthodes. Tous les essais.</p>' + show.to_html(index=False) + df.to_html(index=False), encoding="utf-8")
    print(json.dumps(dict(development=len(development), validation=len(df), decision=decision), ensure_ascii=False))


if __name__ == "__main__":
    main()
