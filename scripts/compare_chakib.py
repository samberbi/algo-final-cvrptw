"""Read-only analysis of saved routes; never import the archive's programs."""
from pathlib import Path
from functools import lru_cache
import argparse
import hashlib
import json
import math
import statistics as st

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(None)
def instance(name):
    """Parse only the EUC_2D CVRPTW subset present in this pinned dataset."""
    headers, sections, section = {}, {}, None
    for line in (ROOT / "data/instances" / f"{name}.vrp").read_text().splitlines():
        line = line.strip()
        if line.endswith("_SECTION"):
            section = line
            sections[section] = []
        elif section and line and line not in ("EOF", "-1"):
            sections[section].append([float(v) for v in line.split()])
        elif not section and ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()
    assert headers["TYPE"] in ("CVRPTW", "VRPTW") and headers["EDGE_WEIGHT_TYPE"] == "EUC_2D"
    size = int(headers["DIMENSION"])
    coords = [v[1:] for v in sections["NODE_COORD_SECTION"]]
    demand = [v[1] for v in sections["DEMAND_SECTION"]]
    windows = [[round(10 * x) for x in v[1:]] for v in sections["TIME_WINDOW_SECTION"]]
    assert len(coords) == len(demand) == len(windows) == size
    service = [round(10 * float(headers["SERVICE_TIME"]))] * size
    if "SERVICE_TIME_SECTION" in sections:
        service = [round(10 * v[1]) for v in sections["SERVICE_TIME_SECTION"]]
    service[0] = 0
    return coords, demand, windows, service, float(headers["CAPACITY"]), int(headers["VEHICLES"])


def check(name, routes):
    coords, demand, windows, service, capacity, fleet = instance(name)
    used = [r for r in routes if r]
    assert len(used) <= fleet
    assert sorted(c for r in used for c in r) == list(range(1, len(coords)))
    cost = 0
    for route in used:
        assert sum(demand[c] for c in route) <= capacity
        clock, prev = 0, 0
        for c in [*route, 0]:
            arc = math.floor(10 * math.dist(coords[prev], coords[c]))
            cost += arc
            clock = max(clock + arc, windows[c][0])
            assert clock <= windows[c][1], (name, c, clock)
            clock += service[c]
            prev = c
    return cost / 10


def table(headers, rows):
    def fmt(v):
        return f"{v:.3f}" if isinstance(v, float) else str(v)
    return "\n".join(["| " + " | ".join(headers) + " |",
                       "| " + " | ".join(["---"] * len(headers)) + " |",
                       *["| " + " | ".join(map(fmt, r)) + " |" for r in rows]])


def plot_comparison(paired, names):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), gridspec_kw={"height_ratios": [2, 1]})
    for ax, selected, title in [
        (axes[0], [n for n in names if "_" not in n], "24 instances Solomon à 100 clients — trois graines par instance"),
        (axes[1], [n for n in names if "_" in n], "Instances à 200 et 1 000 clients — une ou trois graines")]:
        for offset, key, label, color in [(-.2, "own", "Ton projet", "#267b91"), (.2, "chakib", "Chakib", "#df983d")]:
            means = [st.mean(r[f"{key}_gap"] for r in paired if r["instance"] == n) for n in selected]
            ax.bar([i+offset for i in range(len(selected))], means, width=.38, label=label, color=color)
        ax.set_xticks(range(len(selected)), selected, rotation=55, ha="right")
        ax.set(ylabel="Gap moyen (%)", title=title)
        ax.grid(axis="y", alpha=.15)
        ax.legend()
    fig.suptitle("Profils finaux enregistrés — mêmes instances et graines, budgets différents")
    fig.tight_layout()
    target = ROOT / "livraison/figures/comparaison_chakib.png"
    fig.savefig(target, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", type=Path, default=ROOT / "results/local/chakib_archive/livrable_final")
    parser.add_argument("--archive", type=Path, default=Path(r"C:\Users\samyb\Downloads\livrable_final.rar"))
    args = parser.parse_args()
    external = args.archive_dir
    # Same final-lot selection as threshold_report.py, read as data only.
    paths = []
    for path in sorted((external / "results/threshold7_local_v2").glob("*.json")):
        if path.name != "metadata.json" and json.loads(path.read_text()).get("n", 1000) < 1000:
            paths.append(path)
    paths += [p for p in sorted((external / "results/seuil7_20261109_103614").glob("*.json")) if p.name != "metadata.json"]
    assert len(paths) == 80
    other = {}
    for p in paths:
        r = json.loads(p.read_text())
        key = (r["name"], r["seed"])
        assert key not in other and r["status"] == "feasible" and r["objective"] == "distance"
        other[key] = r, p
    own = {}
    for p in sorted((ROOT / "results/focused/runs").glob("*.json")):
        r = json.loads(p.read_text())
        key = (r["job"]["instance"], r["job"]["seed"])
        assert key not in own
        own[key] = r, p
    assert len(own) == 80 and own.keys() == other.keys()
    paired, hashes = [], {}
    names = sorted({k[0] for k in own})
    assert len(names) == 28
    for name in names:
        for suffix in ("vrp", "sol"):
            a, b = ROOT / "data/instances" / f"{name}.{suffix}", external / "instances" / f"{name}.{suffix}"
            assert sha(a) == sha(b), (name, "different input/reference")
            hashes[str(a.relative_to(ROOT))] = sha(a)
        routes, reference = [], None
        for line in (ROOT / "data/instances" / f"{name}.sol").read_text().splitlines():
            if line.startswith("Route"):
                routes.append([int(x) for x in line.split(":", 1)[1].split()])
            elif line.lower().startswith("cost"):
                reference = float(line.replace(":", " ").split()[1])
        assert math.isclose(check(name, routes), reference, abs_tol=1e-7)
        for key in sorted(k for k in own if k[0] == name):
            a, ap = own[key]
            b, bp = other[key]
            ra = a["result"]
            assert ra["status"] == "feasible" and ra["objective"] == "distance"
            ca, cb = check(name, ra["routes"]), check(name, b["routes"])
            assert math.isclose(ca, ra["cost"], abs_tol=1e-7)
            assert math.isclose(cb, b["cost"], abs_tol=1e-7)
            ga, gb = 100 * (ca / reference - 1), 100 * (cb / reference - 1)
            assert math.isclose(ga, a["gap_pct"], abs_tol=1e-8)
            assert math.isclose(gb, b["gap_percent"], abs_tol=1e-8)
            assert reference == a["job"]["reference_distance"] == b["reference_distance"]
            paired.append(dict(instance=name, seed=key[1], n=b["n"], reference=reference,
                               own_cost=ca, chakib_cost=cb, own_gap=ga, chakib_gap=gb,
                               own_seconds=ra["runtime_s"], chakib_seconds=b["seconds"]))
            hashes[str(ap.relative_to(ROOT))] = sha(ap)
            hashes[str(bp.relative_to(external))] = sha(bp)
    summary = []
    for label, key in [("Ton projet", "own"), ("Archive Chakib", "chakib")]:
        gaps = [r[f"{key}_gap"] for r in paired]
        summary.append([label, len(paired), st.mean(gaps), st.median(gaps), st.stdev(gaps),
                        max(gaps), sum(g < 7 for g in gaps), st.mean(r[f"{key}_seconds"] for r in paired)])
    wins = sum(r["own_cost"] < r["chakib_cost"] - 1e-7 for r in paired)
    losses = sum(r["own_cost"] > r["chakib_cost"] + 1e-7 for r in paired)
    text = "# Consigne, benchmark et comparaison avec livrable_final.rar\n\n"
    text += ("## Ce que le sujet impose réellement\n\n"
             "Selon la consigne copiée par l'utilisateur : **au moins 20 instances différentes**, "
             "avec des scénarios variés, comparaison aux meilleures solutions connues, gaps, temps, "
             "robustesse, sensibilité et interprétation argumentée. **Aucune liste nominative et aucun "
             "nombre de répétitions par instance ne sont imposés.** Tester toutes les instances Solomon "
             "ou faire 30 runs par instance ne sont pas des obligations de ce texte.\n\n"
             "La formulation du barème « gap supérieur à 7–10 % » ne précise pas l'agrégation utilisée. "
             "On publie donc moyenne, pire gap et nombres sous les seuils, sans déduire une note garantie.\n\n"
             "VRPLIB est une bibliothèque de lecture/écriture ; elle ne fixe pas un protocole "
             "d'expérimentation. [Documentation officielle](https://github.com/PyVRP/VRPLIB). "
             "Les références locales proviennent de PyVRP/Instances, révision "
             "`7474b068a8effa7f39448b241314b615c9271525`. "
             "[Convention officielle](https://github.com/PyVRP/Instances/blob/7474b068a8effa7f39448b241314b615c9271525/VRPTW/README.md) : "
             "distance totale, trajets et durées tronqués à une décimale. Une BKS n'est pas nécessairement "
             "un optimum démontré.\n\n"
             "## Périmètres et répétitions\n\n"
             "Les deux profils finaux contiennent les **mêmes 28 instances et les mêmes 80 couples "
             "instance/graine** : 24 Solomon à 100 clients × 3 graines (11, 22, 33), deux instances "
             "à 200 clients × 1 graine (11), deux à 1 000 clients × 3 graines. Ce plan dépasse le minimum "
             "de 20 instances et fait varier familles et tailles. Les répétitions à 200 clients restent "
             "insuffisantes pour mesurer leur dispersion.\n\n"
             "Ton extension couvre en plus 356 instances et 1 000 trajectoires ; son sous-ensemble "
             "Solomon complet couvre 56 instances et 160 runs. Ces lots restent séparés. "
             "Voir [les 56 Solomon](COMPARAISON_SOLOMON.md). Les fichiers C105, C205, R105, R205, RC105, "
             "RC205 de l'archive servent au développement et au métier, sans être ajoutés au profil final.\n\n"
             "## Comparabilité et méthode\n\n"
             "Les 28 fichiers d'instances et les 28 références sont identiques octet pour octet. "
             "Les 160 solutions (80 par projet) et les 28 BKS ont été recalculées par un contrôleur "
             "Python de cet audit : couverture, capacité, flotte, fenêtres de début de service, retour "
             "au dépôt et distance. Aucun code provenant de l'archive n'a été importé ou exécuté.\n\n")
    text += table(["Composant", "Ton projet", "Archive Chakib"], [
        ["Construction", "Regret-2, jusqu'à 12 tentatives", "Regret-2, 12 tentatives"],
        ["Exploration", "ALNS, 6 retraits avec poids adaptatifs", "Retrait/réinsertion, 4 retraits tirés uniformément"],
        ["Réparation", "Regret-2 ou regret-3", "Regret-2"],
        ["Température initiale", "2 % du coût de construction", "3 % du coût de construction"],
        ["Refroidissement", "Selon le temps consommé", "Cycles de 2 500 itérations, réchauffement"],
        ["Recherche locale", "Pendant la recherche et décomposition des grands cas", "Descente finale avec --polish"],
        ["Arrêt principal", "Budget de temps", "Budget d'itérations"],
        ["Exécution enregistrée", "4 processus avec affinités CPU", "Campagnes séquentielles"],
    ]) + "\n\n"
    text += ("La méthode de l'archive partage une structure destruction/réparation de grand voisinage, "
             "avec recuit. Le tirage uniforme des retraits ne constitue pas l'adaptation des poids "
             "présente dans ton moteur. Les conventions permettent de comparer les coûts, mais les "
             "budgets, la construction des profils et les conditions de mesure diffèrent : aucune "
             "conclusion de supériorité à budget égal ou de vitesse intrinsèque n'est démontrée.\n\n"
             "## Résultats des deux profils finaux\n\n")
    text += table(["Projet", "Runs valides", "Gap moyen (%)", "Médiane (%)", "Écart-type (points)",
                   "Pire gap (%)", "Sous 7 %", "Temps moyen enregistré (s)"], summary) + "\n\n"
    text += (f"Sur les 80 couples instance/graine, ton coût est inférieur dans **{wins}** cas, "
             f"égal dans **{80-wins-losses}** cas, supérieur dans **{losses}** cas. Ce bilan descriptif "
             "n'est pas un test statistique sur des observations indépendantes : les répétitions "
             "d'une instance et certaines structures géographiques sont liées.\n\n"
             "## Tableau complet par instance\n\n"
             "Le nombre de runs est identique pour les deux projets. Δ désigne ton gap moyen moins "
             "celui de Chakib, en points : une valeur négative favorise ton profil.\n\n")
    by_name = []
    for name in names:
        rs = [r for r in paired if r["instance"] == name]
        ga, gb = st.mean(r["own_gap"] for r in rs), st.mean(r["chakib_gap"] for r in rs)
        by_name.append([name, rs[0]["n"], len(rs), ", ".join(str(r["seed"]) for r in rs), rs[0]["reference"],
                        ga, gb, ga-gb, max(r["own_gap"] for r in rs), max(r["chakib_gap"] for r in rs),
                        st.mean(r["own_seconds"] for r in rs), st.mean(r["chakib_seconds"] for r in rs)])
    text += "![Comparaison des gaps moyens par instance](../livraison/figures/comparaison_chakib.png)\n\n"
    text += table(["Instance", "Clients", "Runs/projet", "Graines", "BKS", "Ton gap moyen (%)", "Chakib (%)",
                   "Δ (points)", "Ton pire (%)", "Pire Chakib (%)", "Ton temps (s)", "Chakib (s)"], by_name)
    text += ("\n\n## Conclusions et travail nécessaire\n\n"
             "Le lot principal satisfait le minimum numérique d'instances. Aucune nouvelle campagne "
             "n'est nécessaire pour atteindre un nombre de runs prétendument obligatoire : le sujet "
             "n'en fixe pas. Les deux profils finaux restent sous 7 % sur leurs 80 essais. Ton extension "
             "plus large comporte néanmoins des dépassements (pire gap 15,262 %) : ces résultats "
             "doivent rester visibles et ne sont pas annulés par le bon bilan du petit lot.\n\n"
             "Pour renforcer l'étude, choisir à l'avance davantage de graines sur un sous-ensemble "
             "varié, notamment à 200 clients, et comparer les méthodes sur une même machine avec "
             "des budgets identiques. Une étude de temps à budget imposé mesure surtout le budget : "
             "une analyse de montée en charge doit aussi examiner les itérations, le coût par opération "
             "ou le temps nécessaire pour atteindre une qualité fixée. Ce sont des améliorations "
             "méthodologiques proposées, pas des obligations chiffrées supplémentaires.\n\n"
             "Les anciens lots et continuations de l'archive ne sont pas cumulés comme nouveaux essais "
             "indépendants. Le profil Chakib sélectionné suit explicitement `threshold_report.py` : "
             "74 états à 100/200 clients repris puis polis, et 6 recherches à 1 000 clients. Le tien "
             "contient 80 nouvelles résolutions avec leurs continuations. Aucun solveur n'a été relancé.\n")
    plot_comparison(paired, names)
    report = ROOT / "livraison/COMPARAISON_CHAKIB.md"
    report.write_text(text, encoding="utf-8")
    provenance = dict(archive_sha256=sha(args.archive) if args.archive.exists() else None,
                      archive_name="livrable_final.rar", required_instances_min=20, required_runs_per_instance=None,
                      validated_routes=160, validated_references=28, paired=paired, summary=summary,
                      own_wins=wins, ties=80-wins-losses, chakib_wins=losses, sources_sha256=hashes)
    (ROOT / "results/report/comparaison_chakib.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    notebook = dict(nbformat=4, nbformat_minor=4, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
                    cells=[dict(cell_type="markdown", metadata={}, source=text.splitlines(keepends=True))])
    (ROOT / "notebooks/Comparaison_Chakib.ipynb").write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(dict(summary=summary, wins=wins, ties=80-wins-losses, losses=losses), ensure_ascii=False))
    print(report)


if __name__ == "__main__":
    main()
