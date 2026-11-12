# CVRPTW — Livrable final

Le projet résout un problème de tournées capacitaires avec fenêtres temporelles strictes. La méthode associe notre construction et notre recherche locale itérée (ILS) au HGS externe de **PyVRP 0.12.2**, cité dans le livrable. Le benchmark minimise la distance selon les conventions DIMACS ; la flotte reste une borne supérieure.

## Documents à lire

1. [Rapport final PDF](livraison/RAPPORT_CVRPTW.pdf) : modèle mathématique, méthode, explications du code, graphiques, statistiques et limites.
2. [Notebook Jupyter](notebooks/Livrable_Final_CVRPTW.ipynb) : version exécutée, avec exemples et calculs. [Version HTML](notebooks/Livrable_Final_CVRPTW.html) sans installation.
3. [Rapport Word](livraison/RAPPORT_CVRPTW.docx) pour annotation.
4. [Journal des améliorations](docs/JOURNAL_EVOLUTION_ALGORITHME.md) : changements, comparaisons et décisions.

Le PDF, le Word, le notebook et les deux fichiers Markdown sont des formats du même livrable, pas des études différentes.

## Résultats et comparaison à la BKS

| Campagne | Périmètre | Gap moyen par instance | Maximum | Interprétation |
|---|---|---:|---:|---|
| Référence | 356 instances, 472 pipelines | 2,078 % | 11,021 % | Budgets fixés par taille, tous les essais conservés |
| Archive après reprises | Les mêmes 472 solutions, dont dix reprises | 1,988 % | 6,889 % | 180 s supplémentaires par essai repris, budgets variables |
| Confirmation 20/100 | Sept cas, deux nouvelles graines | 4,642 % | 6,638 % | Lot distinct à 120 s de recherche, 14/14 sous 7 % |

Le gap est `100 × (distance obtenue / distance BKS − 1)`. La moyenne par instance donne le même poids à chaque instance après moyenne de ses répétitions. Une BKS n’est pas nécessairement un optimum prouvé. Les valeurs de référence sont lues après la résolution, jamais fournies au moteur.

- [Tous les résultats de référence](livraison/RESULTATS_CATALOGUE_V8.html), [CSV des essais](livraison/RESULTATS_CATALOGUE_V8.csv), [CSV par instance](livraison/INSTANCES_CATALOGUE_V8.csv).
- [Archive après reprises et temps cumulés](livraison/ARCHIVE_APRES_REPRISES_V9.html), [CSV](livraison/ARCHIVE_APRES_REPRISES_V9.csv).
- Les protocoles, graines, sources figées et solutions individuelles sont dans `results/`. Les données et leur provenance sont dans `data/manifest.json`.

Les expériences portent sur 100 à 1 000 clients, en distance statique. Le trafic dépendant de l’heure et le passage à plusieurs milliers de clients ne sont pas démontrés. Les graines restent peu nombreuses aux tailles intermédiaires.

## Installer et exécuter

Depuis ce dossier, avec Python 3.12 :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python cli.py C101 --method ils_hgs_refined --seconds 10 --seed 3102
python scripts/valider_rendu.py
python -m pytest tests -q --junitxml=livraison/TESTS.xml
```

À 120 secondes, le profil `ils_hgs_refined` utilise 20 s d’ILS puis 100 s de HGS. Construction et préparation s’ajoutent au temps réel ; la compilation est mesurée séparément. Le profil `ils_hgs` conserve le partage historique à parts égales. `ils` et `sa` permettent les comparaisons avec nos méthodes seules. Aucune qualité de résultat n’est garantie pour une nouvelle exécution.

Pour réexécuter le notebook dans VS Code, sélectionner l’interpréteur `.venv` puis exécuter toutes les cellules. Cela recalcule analyses et exemples à partir des résultats fournis ; cela ne relance pas les 472 pipelines. La CLI lance une résolution neuve. Les scripts `benchmark_*.py` sont réservés aux campagnes longues : utiliser un nouveau dossier et conserver les résultats fournis.

L’interface de démonstration est facultative : `python -m streamlit run web/app.py`. Elle permet de lancer des essais et de visualiser tournées, horaires et statistiques. Les variantes non retenues sont conservées dans le code pour reproduire les comparaisons, et ne sont pas toutes activées dans le profil recommandé.

## Vérification

`scripts/valider_rendu.py` recalcule contraintes et gaps à partir des données originales, contrôle les protocoles et les sources figées, distingue les budgets des campagnes, et vérifie les empreintes des fichiers remis. Les résultats du contrôle sont dans `livraison/VALIDATION_REMISE.json` ; le rapport de tests est `livraison/TESTS.xml`.

Node.js est utilisé par un test de lecture de la simulation web. Son absence entraîne un test ignoré, signalé dans le bilan. Les documents exportés se lisent sans Python. Les dépendances et références scientifiques restent attribuées à leurs auteurs.
