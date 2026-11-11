"""Build the optimized deliverable only from complete, verified measurements."""

from pathlib import Path
import hashlib
import html
import inspect
import json
import re
import sys

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
from scripts.analyze_optimization_v2 import analyze, BASE, read
from scripts.export_report import markdown_table
from algo.data import load
from algo.iterated import construct, arrays, encode, decode, build_neighbors
from algo.optimized import solve
from algo.direct import walk
from algo.model import Instance
from algo.verify import verify

FIGURES = ROOT / "livraison/optimization_figures"
LABELS = {
    "optimized_ils": "ILS optimisée",
    "optimized_sa": "Recuit décomposé",
    "baseline_ils": "ILS v1 réexécutée",
}
COLORS = {
    "optimized_ils": "#0f766e",
    "optimized_sa": "#b45309",
    "baseline_ils": "#64748b",
}


def table(df, rename=None):
    return markdown_table(df.rename(columns=rename or {}))


def num(value):
    return f"{value:.3f}".replace(".", ",")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIGURES / (name + ".png"), dpi=160)
    plt.close(fig)


def demonstration():
    xy = np.array([[0, 0], [1, 0], [0, 10], [2, 0], [0, 11]], float)
    distance = np.floor(
        10 * np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(axis=2))
    )
    ins = Instance(
        "mouvement",
        xy,
        np.array([0, 1, 1, 1, 1]),
        np.zeros(5),
        np.zeros(5),
        np.full(5, 1000.0),
        distance,
        2.0,
        2,
        1000.0,
    )
    initial = [[1, 2], [3, 4]]
    encoded, lengths = encode(initial, ins)
    result = walk(
        encoded,
        lengths,
        len(lengths) - 1,
        *arrays(ins),
        build_neighbors(ins, 4),
        2000,
        519,
        0.0,
        1,
    )
    routes = decode(result[1], result[2])
    before, after = verify(initial, ins), verify(routes, ins)
    assert after["valid"] and after["distance"] < before["distance"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
    for ax, solution, title in zip(
        axes, [initial, routes], ["Avant", "Après mouvement direct"]
    ):
        for i, route in enumerate(solution):
            nodes = [0] + route + [0]
            ax.plot(xy[nodes, 0], xy[nodes, 1], "-o", color=["#0f766e", "#b45309"][i])
        for i, (x, y) in enumerate(xy):
            ax.annotate(str(i), (x, y), xytext=(5, 4), textcoords="offset points")
        cost = verify(solution, ins)["distance"] / 10
        ax.set_title(f"{title} · distance {cost:.1f}")
        ax.set(xlabel="X", ylabel="Y")
        ax.grid(alpha=0.2)
    save(fig, "v2_example")
    return ins, initial, routes, before["distance"] / 10, after["distance"] / 10


def make_figures(df, summary, instances, reg, development):
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
    )
    fig, ax = plt.subplots(figsize=(9, 2.5))
    texts = [
        "Archive globale\nréalisable",
        "Tournées voisines\nclients complets",
        "ILS / recuit local\ncontraintes originales",
        "Remappage + contrôle\ngain strict seulement",
    ]
    for x, text in zip([0.10, 0.37, 0.64, 0.90], texts):
        ax.text(
            x,
            0.55,
            text,
            ha="center",
            va="center",
            transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=.6", fc="#e6f2ef", ec="#0f766e"),
        )
    for a, b in zip([0.20, 0.47, 0.74], [0.27, 0.54, 0.81]):
        ax.annotate(
            "",
            xy=(b, 0.55),
            xytext=(a, 0.55),
            xycoords="axes fraction",
            arrowprops=dict(arrowstyle="->", color="#64748b"),
        )
    ax.axis("off")
    save(fig, "v2_groups")
    fig, ax = plt.subplots(figsize=(8, 3.7))
    groups = []
    labels = []
    for size in [100, 200, 1000]:
        for profile in LABELS:
            if profile == "baseline_ils":
                continue
            groups.append(
                df[(df.n == size) & df.profile.eq(profile)].gap_pct.dropna().values
            )
            labels.append(f"{size}\n" + LABELS[profile])
    ax.boxplot(groups, tick_labels=labels, showmeans=True)
    ax.axhline(6, color="#b45309", ls="--", lw=1, label="6 %")
    ax.set_ylabel("Gap à BKS (%)")
    ax.legend()
    save(fig, "v2_distribution")
    large = instances[instances.n.eq(1000)]
    names = sorted(large.instance.unique())
    fig, ax = plt.subplots(figsize=(10, 4))
    x = np.arange(len(names))
    for offset, profile in [(-0.18, "optimized_ils"), (0.18, "optimized_sa")]:
        rows = large[large.profile.eq(profile)].set_index("instance").loc[names]
        ax.bar(
            x + offset,
            rows.mean_gap,
            0.36,
            yerr=rows.std_gap,
            capsize=2,
            label=LABELS[profile],
            color=COLORS[profile],
        )
    ax.axhline(5, color="#0f766e", ls=":", lw=1)
    ax.axhline(6, color="#b45309", ls="--", lw=1)
    ax.set_xticks(x, names, rotation=45, ha="right")
    ax.set_ylabel("Gap moyen (%)")
    ax.legend()
    save(fig, "v2_large")
    fig, ax = plt.subplots(figsize=(10, 4))
    rows = development[development.n.eq(1000)]
    ax.bar(rows.profile, rows.mean_gap, color="#0f766e")
    ax.set_xticks(range(len(rows)), rows.profile, rotation=35, ha="right")
    ax.set_ylabel("Gap moyen de développement (%)")
    ax.set_title("Six familles à 1 000 clients · trois graines · 10 secondes")
    save(fig, "v2_development")
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.7))
    for ax, name in zip(axes, ["C204", "R1_10_1"]):
        paired = reg[reg.instance.eq(name)].pivot(
            index="seed", columns="profile", values="gap_pct"
        )
        for _, row in paired.iterrows():
            ax.plot(
                [0, 1],
                [row.baseline_ils, row.optimized_ils],
                "-o",
                alpha=0.45,
                lw=1,
                ms=3,
                color="#0f766e",
            )
        ax.set_xticks([0, 1], ["ILS v1", "ILS optimisée"])
        ax.axhline(6, ls="--", color="#b45309")
        ax.set(title=name, ylabel="Gap (%)")
    save(fig, "v2_regression")
    fig, ax = plt.subplots(figsize=(8, 3.7))
    grid = np.linspace(0, 40.1, 250)
    for profile in ["optimized_ils", "optimized_sa"]:
        traces = []
        for path in (BASE / "validation/runs").glob("*.json"):
            item = read(path)
            if (
                item["job"]["n"] != 1000
                or item["job"]["variant"] != profile
                or not item["valid"]
            ):
                continue
            result = item["result"]
            trace = [dict(elapsed_s=0.0, best=result["initial_cost"])] + result["trace"]
            times = np.array([p["elapsed_s"] for p in trace])
            values = np.array([p["best"] for p in trace])
            ids = np.clip(
                np.searchsorted(times, grid, side="right") - 1, 0, len(times) - 1
            )
            traces.append(100 * (values[ids] / item["reference_distance"] - 1))
        traces = np.asarray(traces)
        ax.plot(grid, traces.mean(axis=0), label=LABELS[profile], color=COLORS[profile])
        lo, hi = np.quantile(traces, [0.25, 0.75], axis=0)
        ax.fill_between(grid, lo, hi, alpha=0.13, color=COLORS[profile])
    ax.axvline(25, ls=":", color="#64748b", label="Continuation prévue")
    ax.set(xlabel="Temps de recherche (s)", ylabel="Gap moyen (%)")
    ax.legend()
    save(fig, "v2_convergence")
    names = [
        "partner_skip",
        "structure_skip",
        "capacity_reject",
        "time_reject",
        "metropolis_reject",
        "accepted_moves",
    ]
    labels = [
        "Partenaire",
        "Structure",
        "Capacité",
        "Horaires",
        "Metropolis",
        "Accepté",
    ]
    diag = (
        df.groupby("profile")[[f"diag_{n}" for n in names]]
        .sum()
        .reindex(["optimized_ils", "optimized_sa"])
    )
    rates = diag.div(diag.sum(axis=1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(8, 3.4))
    bottom = np.zeros(len(rates))
    for column, label in zip(rates.columns, labels):
        ax.bar(
            [LABELS[p] for p in rates.index], rates[column], bottom=bottom, label=label
        )
        bottom += rates[column].values
    ax.set_ylabel("Propositions directes (%)")
    ax.legend(ncol=3, fontsize=8)
    save(fig, "v2_diagnostics")
    return demonstration()


def main():
    df, summary, instances, payload = analyze("validation")
    reg, reg_summary, reg_instances, reg_payload = analyze("regression")
    _, dev, _, _ = analyze("development")
    _, extra, _, _ = analyze("adaptive")
    development = pd.concat([dev, extra], ignore_index=True)
    assert len(df) == 360 and df.groupby("n").size().to_dict() == {
        100: 120,
        200: 120,
        1000: 120,
    }
    toy, initial, after, before_cost, after_cost = make_figures(
        df, summary, instances, reg, development
    )
    aggregate = (
        df.groupby("profile")
        .agg(
            runs=("valid", "size"),
            feasible=("valid", "sum"),
            mean_gap=("gap_pct", "mean"),
            median_gap=("gap_pct", "median"),
            std_gap=("gap_pct", "std"),
            worst_gap=("gap_pct", "max"),
            under5=("gap_pct", lambda s: int(s.lt(5).sum())),
            under6=("gap_pct", lambda s: int(s.lt(6).sum())),
            under7=("gap_pct", lambda s: int(s.lt(7).sum())),
        )
        .reset_index()
    )
    mean_by_size = summary.pivot(index="n", columns="profile", values="mean_gap")
    paired = df.pivot(
        index=["instance", "seed"], columns="profile", values="gap_pct"
    ).dropna()
    difference = paired.optimized_ils - paired.optimized_sa
    blocks = difference.groupby("seed").mean().values
    rng = np.random.default_rng(1111)
    ci = np.quantile(
        blocks[rng.integers(0, len(blocks), size=(10000, len(blocks)))].mean(axis=1),
        [0.025, 0.975],
    )
    labels = {
        "profile": "Méthode",
        "n": "Clients",
        "runs": "Essais",
        "feasible": "Réalisables",
        "mean_gap": "Gap moyen (%)",
        "median_gap": "Médiane (%)",
        "std_gap": "Écart-type (pt)",
        "worst_gap": "Pire gap (%)",
        "under5": "Sous 5 %",
        "under6": "Sous 6 %",
        "under7": "Sous 7 %",
        "mean_search_s": "Recherche (s)",
        "mean_total_s": "Total (s)",
        "instance": "Instance",
        "best_gap": "Meilleur gap (%)",
    }

    def translated(frame):
        return frame.assign(profile=frame.profile.map(lambda p: LABELS.get(p, p)))

    exact = []
    for path in (ROOT / "results/revision_ils/studies/exact").glob("*.json"):
        row = read(path)
        e = row["exact"]
        exact.append(
            dict(
                clients=row["n"],
                graine=row["seed"],
                statut=e["status"],
                coût=e["cost"],
                borne=e["lower_bound"],
                temps=e["runtime_s"],
            )
        )
    exact = pd.DataFrame(exact).sort_values(["clients", "graine"])
    source_construct = inspect.getsource(construct)
    source_walk = inspect.getsource(walk.py_func).splitlines()
    start = next(i for i, line in enumerate(source_walk) if "delta = ca" in line)
    end = next(
        i for i in range(start, len(source_walk)) if "if not take:" in source_walk[i]
    )
    source_solve = inspect.getsource(solve).splitlines()
    left = next(i for i, line in enumerate(source_solve) if "proposal = [" in line)
    right = next(
        i
        for i in range(left, len(source_solve))
        if "improvements += 1" in source_solve[i]
    )
    code = lambda text: "```python\n" + text.rstrip() + "\n```"
    model = (
        (ROOT / "docs/MODELISATION_CVRPTW_CORRIGEE.md")
        .read_text(encoding="utf-8")
        .replace("### 1.4.", "### 2.2.")
    )
    model = (
        model.split("**Rôle de l’approche exacte.**")[0]
        if "**Rôle de l’approche exacte.**" in model
        else model.split("**Rôle de l'approche exacte.**")[0]
    )
    chosen = read(BASE / "selection.json")
    continuation = (
        df[df.n.eq(1000)]
        .groupby("profile")
        .agg(
            runs=("gap_pct", "size"),
            gap_25=("gap_at25_pct", "mean"),
            gap_40=("gap_pct", "mean"),
            worst_40=("gap_pct", "max"),
        )
        .reset_index()
    )
    counters = [
        "diag_capacity_reject",
        "diag_time_reject",
        "diag_accepted_moves",
        "diag_attempts",
    ]
    diag = df.groupby(["n", "profile"])[counters].sum().reset_index()
    for col in counters[:-1]:
        diag[col] = 100 * diag[col] / diag.diag_attempts
    ils = aggregate[aggregate.profile.eq("optimized_ils")].iloc[0]
    large_ils = instances[instances.n.eq(1000) & instances.profile.eq("optimized_ils")]
    remaining = large_ils[large_ils.mean_gap.ge(6)]
    conclusion = f"L'ILS optimisée fournit {int(ils.feasible)}/{int(ils.runs)} solutions réalisables ; son gap moyen équilibré est {num(ils.mean_gap)} %, son pire gap {num(ils.worst_gap)} %. À 1 000 clients, la moyenne porte sur douze instances et vaut {num(mean_by_size.loc[1000,'optimized_ils'])} %. {len(remaining)} de leurs moyennes atteignent ou dépassent 6 %. La moyenne ne remplace pas le détail par instance ni une garantie sur les futurs essais."
    interpretations = []
    for size, row in mean_by_size.iterrows():
        interpretations.append(
            f"À {size} clients : ILS {num(row.optimized_ils)} %, recuit {num(row.optimized_sa)} %."
        )
    if len(remaining):
        interpretations.append(
            "Les cas encore au-dessus de 6 % en moyenne sont : "
            + ", ".join(remaining.instance)
            + "."
        )
    substitutions = dict(
        MODEL=model,
        V2_INTRO="La validation v2 comporte **36 instances × 5 graines × 2 méthodes = 360 trajectoires**, avec douze instances par taille. Le diagnostic avant/après conserve vingt graines sur chacun de deux cas. La calibration séparée totalise 324 essais ; aucun de ces essais ne remplace ceux de validation.",
        CODE_CONSTRUCT=code(source_construct),
        CODE_WALK=code("\n".join(source_walk[start:end])),
        CODE_SOLVE=code("\n".join(source_solve[left : right + 1])),
        EXACT=table(exact),
        EXACT_TEXT=f"HiGHS certifie {int(exact.statut.eq('optimal').sum())}/10 optimums. La ligne à limite de temps conserve son incumbent et sa borne ; elle n'est pas appelée optimale.",
        DEVELOPMENT=table(
            development[["n", "profile", "runs", "mean_gap", "worst_gap"]], labels
        ),
        SELECTION_TEXT=f"Le profil ILS retenu est `{chosen['chosen_ils']}` ; le recuit utilise `{chosen['chosen_sa']}`. SWAP* et le voisinage temporel restent des options expérimentales : leur ajout n'a pas fourni la meilleure moyenne de développement à 1 000 clients. Refroidir davantage le recuit n'a pas gagné sur ce lot. Le choix utilise uniquement les données de développement, avant la validation.",
        PROTOCOL=table(
            pd.DataFrame(
                [
                    dict(
                        clients=n,
                        instances=12,
                        graines=5,
                        méthodes=2,
                        trajectoires=120,
                        recherche_s=5 if n == 100 else 6 if n == 200 else 40,
                    )
                    for n in [100, 200, 1000]
                ]
            )
        ),
        ENVIRONMENT="Les mesures ont été exécutées sous Windows avec Python 3.12.8, sur un processeur AMD à six cœurs physiques et douze processeurs logiques, avec environ 16 Gio de mémoire. Quatre processus servent la validation et deux la comparaison avant/après, avec des affinités logiques distinctes. Ils partagent mémoire, caches et refroidissement ; aucun facteur de vitesse universel n'est revendiqué. L'environnement complet est enregistré dans `results/optimization_v2/environment.json`.\n\n"
        + table(
            pd.DataFrame(
                [
                    (name, version)
                    for name, version in read(BASE / "environment.json")[
                        "versions"
                    ].items()
                    if name in ["numpy", "pandas", "numba", "scipy"]
                ],
                columns=["Bibliothèque", "Version mesurée"],
            )
        ),
        SUMMARY=table(translated(aggregate), labels),
        PAIRED=f"Sur {len(difference)} paires, la différence moyenne ILS moins recuit est {num(difference.mean())} point. L'intervalle bootstrap conditionnel à 95 % par blocs de graines est [{num(ci[0])} ; {num(ci[1])}] point. Avec cinq blocs, il reste exploratoire.",
        SIZE_RESULTS=table(
            translated(
                summary[
                    [
                        "n",
                        "profile",
                        "runs",
                        "mean_gap",
                        "worst_gap",
                        "under5",
                        "under6",
                        "under7",
                        "mean_search_s",
                        "mean_total_s",
                    ]
                ]
            ),
            labels,
        ),
        SIZE_INTERPRETATION=" ".join(interpretations)
        + " Sur ce lot équilibré, le recuit décomposé obtient une meilleure moyenne globale que l'ILS. L'amélioration de l'ILS sur R1_10_1 ne constitue donc pas une supériorité universelle. La cible inférieure à 6 % n'est pas atteinte sur l'ensemble des grands cas.",
        LARGE_RESULTS=table(
            translated(
                large_ils[
                    [
                        "instance",
                        "profile",
                        "runs",
                        "mean_gap",
                        "std_gap",
                        "best_gap",
                        "worst_gap",
                        "under6",
                    ]
                ]
            ),
            labels,
        ),
        CONTINUATION=table(
            translated(continuation),
            dict(
                labels,
                gap_25="Gap moyen à 25 s (%)",
                gap_40="Gap moyen à 40 s (%)",
                worst_40="Pire gap à 40 s (%)",
            ),
        ),
        REGRESSION=table(
            translated(
                reg_instances[
                    [
                        "instance",
                        "profile",
                        "runs",
                        "mean_gap",
                        "worst_gap",
                        "under5",
                        "under6",
                        "under7",
                    ]
                ]
            ),
            labels,
        ),
        DIAGNOSTICS=table(
            translated(diag),
            dict(
                labels,
                diag_capacity_reject="Rejet capacité (%)",
                diag_time_reject="Rejet horaire (%)",
                diag_accepted_moves="Mouvement accepté (%)",
                diag_attempts="Propositions",
            ),
        ),
        TESTS=read(BASE / "test_validation.json")["summary"],
        CONCLUSION=conclusion,
    )
    text = (ROOT / "docs/LIVRABLE_OPTIMISE_SOURCE.md").read_text(encoding="utf-8")
    for key, value in substitutions.items():
        text = text.replace("{{" + key + "}}", value)
    assert not re.search(r"\{\{[A-Z_]+\}\}", text)
    setup = """from pathlib import Path
import sys,json
ROOT=next(p for p in [Path.cwd(),*Path.cwd().parents] if (p/'algo/optimized.py').exists())
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from IPython.display import Image,display
from algo.data import load
from algo.solver import solve,production_settings,warmup
from algo.verify import verify
data=json.loads((ROOT/'results/optimization_v2/validation/analysis.json').read_text())
assert data['complete'] and data['runs']==360 and data['instances']==36
print('Validation complète :',data['runs'],'trajectoires,',data['instances'],'instances.')
warmup();
"""
    example = """import numpy as np
from algo.model import Instance
from algo.iterated import arrays,encode,decode,build_neighbors
from algo.direct import walk
xy=np.array([[0,0],[1,0],[0,10],[2,0],[0,11]],float)
d=np.floor(10*np.sqrt(((xy[:,None,:]-xy[None,:,:])**2).sum(axis=2)))
toy=Instance('mouvement',xy,np.array([0,1,1,1,1]),np.zeros(5),np.zeros(5),np.full(5,1000.),d,2.,2,1000.)
before=[[1,2],[3,4]]
a,lengths=encode(before,toy)
movement=walk(a,lengths,len(lengths)-1,*arrays(toy),build_neighbors(toy,4),2000,519,0.,1)
after=decode(movement[1],movement[2])
control=verify(after,toy)
assert control['valid'] and control['distance']<verify(before,toy)['distance']
print(before,'->',after)
print('Distance avant :',verify(before,toy)['distance']/10,'; après :',control['distance']/10)
"""
    demo = """ins=load(ROOT/'data/instances/C101.vrp')
result=solve(ins,production_settings('ils',seconds=.2,seed=1001))
assert verify(result['routes'],ins)['valid']
print('Démonstration ILS : distance',result['cost'],'; réalisable ; temps',round(result['runtime_s'],3),'s')
"""
    captions = {
        "representation": "Données et solution",
        "schedule": "Trajet, attente et service",
        "moves": "Mouvements directs",
        "v2_groups": "Recherche dans des groupes de tournées",
        "v2_example": "Un mouvement exécuté sur un petit cas",
        "v2_development": "Réglages sur le lot de développement",
        "v2_distribution": "Dispersion par taille sur la validation équilibrée",
        "v2_large": "Gaps sur les douze grandes instances",
        "v2_convergence": "Convergence moyenne sur les grands cas",
        "v2_regression": "Avant/après à budget égal",
        "v2_diagnostics": "Diagnostic des propositions directes",
    }
    cells = []
    md = []
    for i, chunk in enumerate(re.split(r"<!-- EXEC:([a-zA-Z0-9_]+) -->", text)):
        if i % 2 == 0:
            if chunk.strip():
                cells.append(nbformat.v4.new_markdown_cell(chunk.strip()))
                md.append(chunk.strip())
        elif chunk.startswith("fig_"):
            name = chunk[4:]
            folder = "optimization_figures" if name.startswith("v2_") else "ils_figures"
            cell = nbformat.v4.new_code_cell(
                f"display(Image(filename=str(ROOT/'livraison/{folder}/{name}.png')))"
            )
            cell.metadata["figure_captions"] = [captions[name]]
            cells.append(cell)
            md.append(f"![{captions[name]}](livraison/{folder}/{name}.png)")
        else:
            cells.append(
                nbformat.v4.new_code_cell(
                    {"setup": setup, "example": example, "demo": demo}[chunk]
                )
            )
    nb = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python CVRPTW optimisé",
                "language": "python",
                "name": "algo-v2",
            }
        },
    )
    directory = ROOT / ".tools/kernels/algo-v2"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "kernel.json").write_text(
        json.dumps(
            dict(
                argv=[
                    sys.executable,
                    "-m",
                    "ipykernel_launcher",
                    "-f",
                    "{connection_file}",
                ],
                display_name="Python CVRPTW optimisé",
                language="python",
            )
        )
    )
    manager = KernelManager(
        kernel_name="algo-v2",
        kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(directory.parent)]),
    )
    try:
        NotebookClient(
            nb, timeout=180, km=manager, resources={"metadata": {"path": str(ROOT)}}
        ).execute()
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
        manager.cleanup_resources()
    nbformat.write(nb, ROOT / "notebooks/Livrable_Final_CVRPTW.ipynb")
    (ROOT / "LIVRABLE_FINAL.md").write_text("\n\n".join(md) + "\n", encoding="utf-8")
    base_templates = Path(sys.base_prefix) / "share/jupyter/nbconvert/templates"
    options = (
        {
            "extra_template_basedirs": [str(base_templates)],
            "extra_template_paths": [str(base_templates)],
        }
        if base_templates.exists()
        else {}
    )
    output, _ = HTMLExporter(**options).from_notebook_node(nb)
    for target in [
        ROOT / "notebooks/Livrable_Final_CVRPTW.html",
        ROOT / "livraison/RAPPORT_CVRPTW.html",
    ]:
        target.write_text(output, encoding="utf-8")
    df.assign(profile=df.profile.map(LABELS)).to_csv(
        ROOT / "livraison/RESULTATS_OPTIMISES.csv", index=False
    )
    page = '<!doctype html><meta charset="utf-8"><title>Résultats CVRPTW optimisés</title><style>body{font-family:Arial;margin:30px}table{border-collapse:collapse}th,td{padding:8px;border-bottom:1px solid #ddd}th{position:sticky;top:0;background:#e6f2ef}</style><h1>Validation équilibrée · 360 trajectoires · 36 instances</h1><p>Tous les résultats, y compris les essais défavorables. Distance et BKS DIMACS ; budget à 1 000 clients : 25 + 15 secondes.</p><input id="q" placeholder="Filtrer une instance ou méthode" oninput="for(const r of document.querySelectorAll(\'tbody tr\'))r.hidden=!r.innerText.toLowerCase().includes(this.value.toLowerCase())">'
    page += (
        df.assign(profile=df.profile.map(LABELS))
        .round(4)
        .to_html(index=False, border=0)
    )
    (ROOT / "livraison/RESULTATS_OPTIMISES.html").write_text(page, encoding="utf-8")
    aggregate.to_csv(BASE / "validation/global_summary.csv", index=False)
    print(
        "Notebook optimisé exécuté ;",
        len(cells),
        "cellules ; figures et tableaux mesurés générés.",
    )


if __name__ == "__main__":
    main()
