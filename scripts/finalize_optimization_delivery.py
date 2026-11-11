"""Finish the active delivery after every declared measurement is complete."""

from pathlib import Path
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/optimization_v2"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def command(*arguments):
    print("Run:", *arguments, flush=True)
    subprocess.run([sys.executable, *arguments], cwd=ROOT, check=True)


def docs():
    import pandas as pd

    df = pd.read_csv(BASE / "validation/flat.csv")
    reg = pd.read_csv(BASE / "regression/flat.csv")
    ils = df[df.profile.eq("optimized_ils")]
    large = ils[ils.n.eq(1000)]
    target = reg[reg.instance.eq("R1_10_1")]
    before = target[target.profile.eq("baseline_ils")].gap_pct.mean()
    after = target[target.profile.eq("optimized_ils")].gap_pct.mean()
    readme = f"""# CVRPTW — ILS optimisée et recuit décomposé

Le moteur minimise la **distance DIMACS**, avec capacité, fenêtres strictes,
couverture unique et flotte maximale. Les contraintes et données restent inchangées.

## Résultats et périmètre

La validation équilibrée contient **36 instances, cinq graines et deux méthodes :
360 trajectoires**. Chaque taille (100, 200, 1 000 clients) contient douze instances.
La calibration séparée comporte 324 essais sur douze instances. La comparaison
avant/après comporte 80 essais sur C204 et R1_10_1, avec vingt graines et des
départs/budgets appariés, y compris la réexécution des sources v1 figées.

- ILS : gap moyen équilibré **{ils.gap_pct.mean():.3f} %**, pire gap **{ils.gap_pct.max():.3f} %**.
- ILS à 1 000 clients : moyenne **{large.gap_pct.mean():.3f} %** sur douze instances.
- R1_10_1, à 25 secondes : moyenne v1 **{before:.3f} %**, optimisée **{after:.3f} %**.

Les grands cas de la validation conservent un état à 25 secondes puis une
continuation fixée de 15 secondes. Le total est 40 secondes de recherche, plus
construction et préchauffage. Cette continuation n'est pas un nouveau run.
Les cas dépassant les seuils restent visibles. Les anciennes moyennes v1 portent
sur un lot dominé par 100 clients ; elles ne se soustraient pas à la moyenne équilibrée.

La cible sous 6 % n'est pas atteinte sur tout le lot des grandes instances.
En CLI, le budget inclut la construction lorsqu'aucun départ n'est fourni ;
dans la comparaison appariée, celle-ci est mesurée séparément.

## Ouvrir les livrables

- [Notebook exécuté](notebooks/Livrable_Final_CVRPTW.ipynb).
- [Lecture HTML](notebooks/Livrable_Final_CVRPTW.html).
- [Rapport PDF](livraison/RAPPORT_CVRPTW.pdf) et [Word](livraison/RAPPORT_CVRPTW.docx).
- [Tous les résultats v2](livraison/RESULTATS_OPTIMISES.html) et [CSV](livraison/RESULTATS_OPTIMISES.csv).
- [Tableau par instance](results/optimization_v2/validation/instances.csv).
- [Guide oral](docs/GUIDE_ORAL.md).

## Installation et exécution

Python 3.12, depuis ce dossier :

```powershell
py -3.12 -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements-web.txt
.\\.venv\\Scripts\\python.exe -m pytest tests
.\\.venv\\Scripts\\python.exe cli.py R1_10_1 --method ils --seconds 25 --seed 101
.\\.venv\\Scripts\\python.exe -m streamlit run web/app.py
```

Le raccourci `lancer_web.bat` ouvre aussi le serveur local. L'interface permet de
choisir instances, graines, budgets, méthodes et répétitions ; elle sauvegarde
chaque nouveau run, affiche les statistiques, tournées, horaires et convergence.
Les nouveaux calculs dans `results/local/` restent locaux et ne sont pas envoyés
automatiquement par Git. Voir [INTERFACE_WEB.md](docs/INTERFACE_WEB.md).

## Code et décisions

`algo/optimized.py` traite les groupes de tournées complètes ; `algo/iterated.py`
contient la recherche directe et le constructeur regret-2 ; `algo/direct.py`
propose les mouvements ; `algo/profiles.py` fige les configurations retenues.
Le vérificateur indépendant est `algo/verify.py`. Le PLNE de petits cas est
`controle/plne.py`. Les BKS sont réservées au calcul des résultats.

SWAP*, le voisinage temporel et les températures alternatives sont testés et
conservés comme options. Ils ne sont pas activés par défaut sans gain mesuré.
Les constructeurs et descentes exploratoires de `results/optimization_v3/`
restent des recherches complémentaires, pas des résultats de la version active.

## Reproduire et vérifier

```powershell
.\\.venv\\Scripts\\python.exe scripts\\analyze_optimization_v2.py --stage validation
.\\.venv\\Scripts\\python.exe scripts\\analyze_optimization_v2.py --stage regression
.\\.venv\\Scripts\\python.exe scripts\\build_optimization_report.py
.\\.venv\\Scripts\\python.exe scripts\\validate_optimization_delivery.py
```

Les protocoles et sources figées sont dans `results/optimization_v2/`.
Les reprises ne remplacent pas les fichiers terminés. Une reproduction neuve
nécessite un nouveau dossier et protocole, avec les affinités CPU du nouveau poste.
Les versions de l'environnement mesuré figurent dans `environment.json` de ce dossier.
Les anciens résultats ILS et ALNS restent dans leurs archives. `livraison/VALIDATION.json`
désigne exclusivement la validation de la livraison courante.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    guide = f"""# Préparer la présentation

Le notebook actif est `notebooks/Livrable_Final_CVRPTW.ipynb`.
Le rapport présente le CVRPTW statique, à distance DIMACS et contraintes strictes.

## Déroulé court

1. Expliquer client, dépôt, capacité, fenêtre et attente.
2. Dire pourquoi début et fin de service diffèrent, puis présenter C1–C8.
3. Décrire construction regret-2, perturbation ILS, recherche locale et archive.
4. Montrer un groupe de tournées : mêmes données, remappage et contrôle global.
5. Comparer les résultats, annoncer leurs budgets et montrer aussi les cas difficiles.

## Chiffres à citer avec leur périmètre

- Validation : 36 instances, cinq graines, deux méthodes ; trois tailles équilibrées.
- ILS : moyenne globale équilibrée {ils.gap_pct.mean():.3f} % ; grands cas {large.gap_pct.mean():.3f} %.
- Avant/après R1_10_1 : {before:.3f} % contre {after:.3f} %, à 25 secondes identiques.
- Une moyenne favorable ne garantit ni chaque instance ni chaque futur essai.

## Exemple d'introduction en anglais

We study delivery routes with vehicle capacity and strict time windows. Our
objective is the total DIMACS distance. We implemented iterated local search
and a simulated annealing comparator, with an independent solution checker.
The optimized search works on groups of complete routes without changing the
original demands, time windows or fleet limit. We compare measured results on
a balanced set and report both average quality and difficult cases.

## Questions cruciales

- Pourquoi la distance ? Pour comparer à la même référence DIMACS. La durée avec
  attente et service est différente ; notre périmètre statique doit être annoncé.
- Pourquoi des groupes ? Pour consacrer davantage de recherche aux tournées
  qui peuvent interagir, puis revérifier la solution globale.
- Pourquoi pas tous les opérateurs ? SWAP* a été testé ; son ajout n'a pas été
  retenu par défaut lorsque le coût de calcul dégradait le résultat sous budget.
- Pourquoi cinq graines dans le nouveau lot ? Elles complètent la diversité des
  douze grandes instances ; l'étude diagnostique conserve vingt graines.
- Pourquoi le temps total dépasse le budget ? Construction séparée et fin des
  opérations atomiques. Ne pas inclure silencieusement le préchauffage Numba.
"""
    (ROOT / "docs/GUIDE_ORAL.md").write_text(guide, encoding="utf-8")


if __name__ == "__main__":
    while True:
        states = {}
        for stage in ["validation", "regression"]:
            path = BASE / stage / "progress.json"
            states[stage] = read(path) if path.exists() else dict(complete=False)
        if all(state["complete"] for state in states.values()):
            break
        print("Waiting:", json.dumps(states), flush=True)
        time.sleep(30)
    for stage in ["validation", "regression"]:
        command("scripts/analyze_optimization_v2.py", "--stage", stage)
    tests = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests",
            "-q",
            "--disable-warnings",
            "--junitxml=results/optimization_v2/tests.xml",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    (BASE / "tests.log").write_text(tests.stdout + tests.stderr, encoding="utf-8")
    print(tests.stdout, flush=True)
    tests.check_returncode()
    summary = next(
        (line for line in tests.stdout.splitlines()[::-1] if "passed" in line),
        tests.stdout[-400:],
    )
    (BASE / "test_validation.json").write_text(
        json.dumps(
            dict(
                summary=summary,
                command="python -m pytest tests -q --disable-warnings",
                tests_xml="results/optimization_v2/tests.xml",
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    docs()
    command("scripts/build_optimization_report.py")
    command("scripts/export_report.py")
    command("scripts/export_pdf.py")
    command("scripts/validate_optimization_delivery.py")
    print("Optimized delivery completed and verified.", flush=True)
