from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[1]


def main():
    analysis = json.loads((ROOT / "results/optimization_v5/validation/analysis.json").read_text())
    table = {r["profile"]:r for r in analysis["summary"]}
    readme = f"""# CVRPTW — ILS, recuit et étude des améliorations

Le projet minimise la distance DIMACS avec capacité limitée, fenêtres strictes sur le début du service, couverture unique, retour au dépôt et flotte maximale. Le moteur par défaut reste l’ILS décomposée : les candidats testés n’ont pas apporté de gain moyen confirmé.

## Résultats de la nouvelle étude

144 résolutions de développement sur six instances à 1 000 clients, puis 72 résolutions de validation sur douze autres instances, deux graines et trois méthodes. Toutes sont réalisables. La validation impose un plafond de 40 secondes de recherche, avec construction mesurée séparément.

| Méthode | Gap moyen à la BKS | Essais |
|---|---:|---:|
| ILS de référence | {table['baseline_ils']['mean_gap']:.3f} % | 24 |
| ILS et partitionnement | {table['ils_sp']['mean_gap']:.3f} % | 24 |
| ILS avec 64 voisins | {table['wide']['mean_gap']:.3f} % | 24 |

Les variantes RVND complète, perturbations variables, relais et réglages sont documentées avec leurs régressions. La cible de moins de 6 % n’est pas atteinte en moyenne sur cette validation. Les archives combinant plusieurs résolutions sont identifiées séparément, avec leur effort total ; elles ne sont pas des essais indépendants de 40 secondes.

Les 360 trajectoires v2 sur 36 instances de 100, 200 et 1 000 clients restent une campagne distincte. Leur moyenne équilibrée ne remplace pas celle des grandes instances.

## Ouvrir les documents

- [Livrable principal exécuté](notebooks/Livrable_Final_CVRPTW.ipynb), [HTML](notebooks/Livrable_Final_CVRPTW.html), [PDF](livraison/RAPPORT_CVRPTW.pdf) et [Word](livraison/RAPPORT_CVRPTW.docx).
- [Explications et décisions](docs/AMELIORATIONS_ILS.md), [notebook de l’étude](notebooks/Ameliorations_ILS_CVRPTW.ipynb).
- [Tous les résultats v5](livraison/RESULTATS_ILS_V5.html), [CSV](livraison/RESULTATS_ILS_V5.csv), [tableau par instance](results/optimization_v5/validation/instances.csv).
- [Guide de lecture](livraison/LIRE_DABORD.md), [interface](docs/INTERFACE_WEB.md), [guide oral](docs/GUIDE_ORAL.md).

## Installer et exécuter

Depuis ce dossier, avec Python 3.12 :

```powershell
py -3.12 -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements-optimization-v5.txt
.\\.venv\\Scripts\\python.exe -m pytest tests
.\\.venv\\Scripts\\python.exe cli.py R1_10_3 --method ils --seconds 40 --seed 1401
.\\.venv\\Scripts\\python.exe -m streamlit run web/app.py
```

`--method sa` lance le recuit. `--method ils_sp` et `--method ils_rvnd` sont des variantes expérimentales, sans supériorité démontrée. Le budget CLI inclut la construction ; le préchauffage est indiqué séparément. Dans les campagnes appariées, le budget de recherche est séparé de la construction.

## Recalculer les statistiques et les expériences

```powershell
python scripts/analyze_ils_v5.py
python scripts/benchmark_ils_v5.py --role validation --label nouvelle_validation --seconds 40 --seeds 1401 1402 --variants baseline_ils wide ils_sp
python scripts/validate_ils_v5.py
```

La dernière commande vérifie les documents et les résultats après l’exécution des tests. La reprise d’une campagne conserve les résultats terminés et refuse un protocole différent. Les versions mesurées sont décrites dans `results/optimization_v5/environment.json` ; les temps dépendent aussi du matériel.

## Code

`algo/optimized.py` découpe en groupes de tournées complètes ; `algo/iterated.py` contient ILS et recuit ; `algo/direct.py` contient les mouvements directs. `algo/rvnd.py` ajoute les échanges de blocs. `algo/ils_rvnd.py`, `algo/relay.py` et `algo/ils_sp.py` sont les candidats étudiés. `algo/verify.py` vérifie indépendamment les résultats. Le PLNE de petits cas se trouve dans `controle/plne.py`.

Les données et solutions de référence figurent dans `data/`, avec leurs empreintes. Les solveurs ne lisent jamais les solutions de référence. Le trafic variable et le passage au-delà de 1 000 clients ne sont pas démontrés.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    archive_path = ROOT / "results/optimization_v5/portfolio_intensified/analysis.json"
    if archive_path.exists():
        archive = json.loads(archive_path.read_text())
        readme += f"\n## Archive combinée à budget supérieur\n\nL’archive issue de seize trajectoires par instance, recombinée puis intensifiée, atteint **{archive['mean_gap']:.3f} %** de gap moyen sur douze instances, avec un pire cas de **{archive['worst_gap']:.3f} %**. L’effort cumulé moyen est **{archive['mean_effort_s']:.1f} secondes par instance**, et non 40 secondes. Ce bilan contient une archive par instance ; il ne remplace pas les statistiques des répétitions. Voir [tous les résultats](results/optimization_v5/portfolio_intensified/summary.csv).\n"
        (ROOT / "README.md").write_text(readme, encoding="utf-8")
    with (ROOT / "README.md").open("a", encoding="utf-8") as handle:
        handle.write("\nLe ZIP contient le code actuel et les sources figées de la validation finale. Les instantanés de code intermédiaires du développement restent dans les archives de travail ; leurs empreintes et les résultats bruts sont conservés. Le validateur indique explicitement les instantanés non fournis.\n")
    (ROOT / "livraison/LIRE_DABORD.md").write_text("""# Livraison active — étude ILS du CVRPTW

Ouvrir `RAPPORT_CVRPTW.pdf` ou `../notebooks/Livrable_Final_CVRPTW.ipynb`. La dernière section complète l’édition v2 avec les nouveaux essais ; les anciennes moyennes restent identifiées par campagne.

`RESULTATS_ILS_V5.html` et `.csv` contiennent les 72 essais de validation à 1 000 clients. `RESULTATS_OPTIMISES.html` et `.csv` contiennent les 360 trajectoires v2 sur trois tailles. Ces populations ne se confondent pas.

`../docs/AMELIORATIONS_ILS.md` explique les modifications, les abandons, les temps et les limites. Le notebook `Ameliorations_ILS_CVRPTW.ipynb` est exécuté et illustré. Le moteur ILS initial reste le défaut ; les nouvelles variantes ne sont pas présentées comme de meilleures méthodes.

`VALIDATION.json` pointe vers `validation_ils_v5.json`, qui contient les contrôles et les empreintes actuels. Le ZIP de livraison contient le code actuel, les données, les preuves admissibles et les documents ; les archives privées n’en font pas partie.
""", encoding="utf-8")
    (ROOT / "docs/INTERFACE_WEB.md").write_text("""# Interface web

Lancer `python -m streamlit run web/app.py`, puis ouvrir http://127.0.0.1:8501.

**Nouvelle expérience** permet de choisir librement les instances de 100 à 1 000 clients, les graines, répétitions et budgets. ILS et recuit constituent les références ; ILS-RVND et ILS-SP sont des variantes expérimentales. Le budget de chaque appel inclut sa construction ; chargement et compilation sont mesurés à part. La finition facultative ajoute un budget distinct.

**Mes campagnes** affiche progression, résultats, tableaux, courbes et exports. Les calculs sont séquentiels et continuent si le navigateur est fermé. L’arrêt conserve les essais déjà terminés. Les résultats locaux se trouvent dans `results/local/`.

**Résultats historiques** sépare les campagnes v2 et v5. Les moyennes changent avec les filtres : il faut toujours lire la taille, le nombre d’essais et le budget avec le gap.

**Simulation** rejoue les solutions des campagnes publiées et locales. Les véhicules se déplacent, attendent, servent et reviennent au dépôt. Les onglets vérifient la couverture, la capacité, les fenêtres et les retours. La fenêtre concerne le début du service ; une attente avant ouverture est autorisée.

L’animation représente un planning vérifié sur les coordonnées du benchmark ; elle ne représente pas les itérations de recherche ni du trafic réel.
""", encoding="utf-8")
    (ROOT / "docs/EXIGENCES_PROJET_ET_RETOUR_PROF.md").write_text("""# Correspondance avec le projet CVRPTW

| Exigence | Éléments et limites |
|---|---|
| Modèle mathématique | Variables, objectif de distance et contraintes dans le rapport ; PLNE dans `controle/plne.py` |
| Capacité et fenêtres strictes | Vérificateur indépendant, tests des mouvements et horaires de service |
| Méthode expliquée | ILS principale, recuit comparateur et étude documentée des variantes |
| Au moins vingt instances variées | Campagne v2 : 36 instances réparties sur 100, 200 et 1 000 clients |
| Statistiques | Moyennes, dispersion, pire cas, seuils, détails par instance et graines |
| Grandes instances | Nouvelle validation : douze instances à 1 000 clients, deux graines et trois méthodes |
| Comparaisons équitables | Départs identiques par instance/graine, budgets demandés et durées effectives publiés |
| Reproductibilité | JSON bruts, données avec empreintes, versions, tests et scripts |
| Présentation | Notebook exécuté, PDF, Word, schémas, tableaux et interface animée |

Le sujet initial mentionne durée et trafic variable. Le périmètre retenu optimise la distance sur trajets fixes ; cette différence est explicite. Les expériences ne démontrent pas le passage à plusieurs milliers de clients. Deux graines sur les nouveaux cas limitent l’estimation de la variabilité. Aucun seuil de gap ni note n’est garanti.
""", encoding="utf-8")


if __name__ == "__main__":
    main()
