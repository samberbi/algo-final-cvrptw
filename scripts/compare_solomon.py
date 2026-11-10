"""Build a Solomon-only comparison from the frozen historical campaign.

No new solves and no pooling with the focused campaign. Standard library only.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import statistics as stats

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(headers, rows):
    def fmt(value):
        return f"{value:.3f}" if isinstance(value, float) else str(value)
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
        *["| " + " | ".join(map(fmt, row)) + " |" for row in rows],
    ])


def main():
    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    protocol = json.loads((ROOT / "results/campaign/protocol.json").read_text())
    refs = {r["instance"]: r for r in manifest["reference_instances"]
            if re.fullmatch(r"(?:C|R|RC)[12]\d{2}", r["instance"])}
    assert len(refs) == 56
    rows, all_gaps, family_rows = [], [], []
    source_hashes = {}
    for name, ref in sorted(refs.items()):
        jobs = sorted((j for j in protocol["jobs"] if j["instance"] == name),
                      key=lambda j: j["seed"])
        assert len(jobs) in (2, 3)
        records = []
        for job in jobs:
            path = ROOT / "results/campaign/runs" / f'{job["id"]:04d}_{name}_{job["seed"]}.json'
            record = json.loads(path.read_text())
            assert record["job"] == job and record["from_zero"]
            result = record["result"]
            if result["status"] == "feasible":
                assert result["metrics"]["valid"]
                assert math.isclose(result["metrics"]["distance"] / 10,
                                    result["cost"], abs_tol=1e-7)
                gap = 100 * (result["cost"] / ref["reference_distance"] - 1)
                assert math.isclose(gap, record["gap_pct"], abs_tol=1e-8)
                assert result["vehicles"] <= ref["fleet_limit"]
                all_gaps.append(gap)
            else:
                assert record["gap_pct"] is None
            source_hashes[str(path.relative_to(ROOT))] = digest(path)
            records.append(record)
        for suffix in ("vrp", "sol"):
            filename = f"{name}.{suffix}"
            path = ROOT / "data/instances" / filename
            assert digest(path) == manifest["files"][filename]["sha256"]
        valid = [r for r in records if r["result"]["status"] == "feasible"]
        gaps = [r["gap_pct"] for r in valid]
        costs = [r["result"]["cost"] for r in valid]
        vehicles = [r["result"]["vehicles"] for r in valid]
        row = dict(instance=name, family=name[:-2], runs=len(records),
                   seeds=[r["job"]["seed"] for r in records], valid=len(valid),
                   reference=ref["reference_distance"], reference_vehicles=ref["reference_vehicles"],
                   best=min(costs) if costs else None, mean=stats.mean(costs) if costs else None,
                   mean_gap=stats.mean(gaps) if gaps else None,
                   std_gap=stats.stdev(gaps) if len(gaps) > 1 else None,
                   worst_gap=max(gaps) if gaps else None,
                   mean_seconds=stats.mean(r["result"]["runtime_s"] for r in records),
                   vehicle_range=f"{min(vehicles)}–{max(vehicles)}" if vehicles else "—",
                   below7=sum(g < 7 for g in gaps), gaps=gaps)
        rows.append(row)
    assert sum(r["runs"] for r in rows) == 160
    for family in ("C1", "C2", "R1", "R2", "RC1", "RC2"):
        subset = [r for r in rows if r["family"] == family]
        gaps = [g for r in subset for g in r["gaps"]]
        family_rows.append([family, len(subset), sum(r["runs"] for r in subset),
                            sum(r["valid"] for r in subset), stats.mean(gaps),
                            max(gaps), sum(g < 7 for g in gaps)])
    text = "# Comparaison complète : 56 instances Solomon à 100 clients\n\n"
    text += ("Analyse des **160 runs historiques**, sans nouvelle résolution. Les 72 runs Solomon "
             "du lot principal de 80 essais ne sont pas ajoutés : il s'agit d'un autre protocole.\n\n"
             "**Consigne fournie par l'utilisateur :** au moins 20 instances différentes, dans des "
             "scénarios variés. Aucune liste nominative ni aucun nombre de runs par instance ne sont "
             "imposés. Les 2 ou 3 répétitions ci-dessous sont celles du protocole historique, "
             "pas une obligation du sujet. Voir aussi `COMPARAISON_CHAKIB.md`.\n\n"
             "**Convention :** minimisation de la distance totale DIMACS, troncature de chaque arc "
             "à une décimale, flotte du fichier comme maximum. Ces références ne doivent pas être "
             "mélangées avec des tableaux donnant priorité au nombre de véhicules ou utilisant une "
             "autre précision. BKS signifie meilleure solution publiée, sans preuve générale d'optimalité.\n\n")
    text += f"Source figée : {manifest['repository']}, révision `{manifest['revision']}`.\n\n"
    text += (f"Résultats : **{len(all_gaps)}/160 runs réalisables**, gap moyen par run "
             f"**{stats.mean(all_gaps):.3f} %**, pire gap **{max(all_gaps):.3f} %**, "
             f"**{sum(g < 7 for g in all_gaps)}/160 strictement sous 7 %**. "
             f"Moyenne à poids égal par instance : **{stats.mean(r['mean_gap'] for r in rows):.3f} %**.\n\n")
    text += "## Synthèse par famille\n\n" + table(
        ["Famille", "Instances", "Runs", "Valides", "Gap moyen (%)", "Pire gap (%)", "Sous 7 %"],
        family_rows) + "\n\n"
    text += "## Détail de toutes les instances\n\n"
    text += ("L'écart-type est calculé sur les gaps avec n−1 au dénominateur, en points de "
             "pourcentage. Les distances sont en unités de benchmark et les temps en secondes. "
             "La moyenne et le pire résultat conservent toutes les répétitions.\n\n")
    text += table(["Instance", "Runs valides/prévus", "Graines", "BKS distance", "Meilleure distance",
                   "Distance moyenne", "Gap moyen (%)", "Écart-type (points)", "Pire gap (%)", "Temps moyen (s)",
                   "Véh. BKS", "Véh. obtenus"],
                  [[r["instance"], f'{r["valid"]}/{r["runs"]}', ", ".join(map(str, r["seeds"])),
                    r["reference"], r["best"], r["mean"], r["mean_gap"], r["std_gap"],
                    r["worst_gap"], r["mean_seconds"], r["reference_vehicles"], r["vehicle_range"]] for r in rows])
    text += ("\n\n## Interprétation et vérification\n\n"
             "Un gap nul égale la référence en distance. Tous les runs sont inclus ; une graine "
             "est une répétition du même problème. Deux ou trois graines restent insuffisantes pour "
             "garantir un comportement futur. Le nombre de véhicules est descriptif et ne définit pas "
             "le classement. Les temps de recherche incluent la construction, hors chargement et "
             "préchauffage, selon le protocole enregistré.\n\n"
             "Ce script contrôle les jobs attendus, les coûts, les gaps, la limite de flotte, les "
             "empreintes des données et les validations enregistrées. Il ne relance ni les résolutions "
             "ni le vérificateur de tournées. Les empreintes des 160 fichiers sources figurent dans "
             "`results/report/comparaison_solomon.json`.\n")
    report = ROOT / "livraison/COMPARAISON_SOLOMON.md"
    report.write_text(text, encoding="utf-8")
    (ROOT / "results/report/comparaison_solomon.json").write_text(json.dumps(
        dict(instances=56, runs=160, requested_repetitions=None,
             requirement_note="Sujet : au moins 20 instances variées ; répétitions non spécifiées", rows=rows,
             protocol_sha256=digest(ROOT / "results/campaign/protocol.json"),
             sources_sha256=source_hashes), indent=2), encoding="utf-8")
    cells = [dict(cell_type="markdown", metadata={}, source=text.splitlines(keepends=True))]
    code = ("from pathlib import Path\nimport runpy\nfrom IPython.display import Markdown, display\n"
            "ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] "
            "if (p / 'scripts/compare_solomon.py').is_file())\n"
            "runpy.run_path(str(ROOT / 'scripts/compare_solomon.py'), run_name='__main__')\n"
            "display(Markdown((ROOT / 'livraison/COMPARAISON_SOLOMON.md').read_text(encoding='utf-8')))\n")
    cells.append(dict(cell_type="code", metadata={}, execution_count=None, outputs=[], source=code.splitlines(keepends=True)))
    notebook = dict(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}, nbformat=4, nbformat_minor=4)
    (ROOT / "notebooks/Comparaison_Solomon.ipynb").write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"56 instances ; 160 runs ; gap moyen {stats.mean(all_gaps):.3f} % ; pire {max(all_gaps):.3f} %")
    print(report)


if __name__ == "__main__":
    main()
