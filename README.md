# CVRPTW : ILS et recuit simulé

Solveur Python de tournées avec capacité et fenêtres horaires strictes. La méthode principale est la **recherche locale itérée (ILS)** ; le comparateur est un **recuit simulé sur mouvements directs**. La distance DIMACS est minimisée, sans priorité au nombre de véhicules. Le PLNE complet est implémenté avec SciPy/HiGHS pour les petits cas.

## Lire le livrable

- [Livrable Markdown](LIVRABLE_FINAL.md) : modèle, méthodes, résultats et explications sous chaque schéma.
- [Notebook exécuté](notebooks/Livrable_Final_CVRPTW.ipynb) : lectures reproductibles, figures et démonstration courte.
- [Rapport PDF](livraison/RAPPORT_CVRPTW.pdf) et [Word avec équations modifiables](livraison/RAPPORT_CVRPTW.docx).
- [Guide oral](docs/GUIDE_ORAL.md) et [interface web](docs/INTERFACE_WEB.md).

La nouvelle campagne contient **28 instances × 20 graines × 2 méthodes = 1 120 essais**, avec départs communs et budgets appariés. Les dix petits cas PLNE, 100 essais heuristiques associés, 144 essais de sensibilité et 252 observations sur contraintes modifiées sont séparés. Les chiffres ALNS antérieurs sont historiques ; ils ne décrivent pas le nouveau moteur.

Une étude complémentaire de 36 essais mesure le temps à **50 000 propositions fixées** : `scripts/run_ils_scaling.py`. Elle distingue les effets de taille des budgets imposés, sans assimiler les unités de travail des deux méthodes.

## Installation et démonstration

Python 3.12, depuis ce dossier :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe cli.py C101 --method ils --seconds 2 --seed 101
.\.venv\Scripts\python.exe cli.py C101 --method sa --seconds 2 --seed 101
.\.venv\Scripts\python.exe -m streamlit run web/app.py
```

L'interface est sur http://127.0.0.1:8501 lorsque le serveur local tourne. Elle anime les tournées avec lecture/pause et vitesse réglable ; les tableaux permettent de contrôler chaque client, la capacité et le retour au dépôt. La simulation rejoue une solution calculée, sans représenter un trafic réel.

## Organisation et reproduction

`algo/iterated.py` orchestre les deux recherches ; `algo/direct.py` propose les mouvements ; `algo/kernels.py` contient les routines compilées de construction et de recherche locale. `algo/verify.py` recalcule indépendamment toute solution. `controle/plne.py` résout réellement la formulation sur les petits cas.

Les protocoles, départs, résultats et sources figées sont dans `results/revision_ils/`. Le manifeste des références est `data/manifest.json`. La bibliothèque vrplib lit les données ; elle ne prescrit ni les instances à tester ni le nombre de runs.

```powershell
.\.venv\Scripts\python.exe scripts\run_ils_benchmark.py --workers 4
.\.venv\Scripts\python.exe scripts\run_ils_studies.py
.\.venv\Scripts\python.exe scripts\build_ils_report.py
.\.venv\Scripts\python.exe scripts\export_report.py
```

Les deux premières commandes reprennent les fichiers déjà présents sous protocole identique. Une reproduction indépendante nécessite un nouveau dossier de campagne et un protocole distinct. Le constructeur est mesuré séparément dans la comparaison appariée ; en CLI son temps est inclus. Le premier préchauffage Numba peut être long.

Pour régénérer l'ensemble des figures, exécuter aussi `scripts/run_ils_scaling.py` avant le constructeur de rapport. `scripts/validate_ils_artifacts.py` recalcule les contraintes et coûts de toutes les nouvelles solutions. Le PDF livré est exporté avec Microsoft Word ; sur Windows avec Word et pywin32 installés, `scripts/render_ils_word.py` le régénère et produit les PNG de contrôle.

## Historique et limites

`livraison/historique_alns_avant_refonte/` préserve les documents antérieurs ; `algo/legacy_alns.py`, `metier/` et les anciens scripts de campagne restent des outils historiques. Les nouvelles expériences utilisent exclusivement ILS/recuit. La CLI actuelle optimise la distance ; les expériences de durée de l'ancienne édition ne sont pas réattribuées à ces méthodes.

Les BKS doivent correspondre aux mêmes contraintes et à la même troncature par arc. Elles ne sont pas toutes des optimums prouvés. Les budgets imposés et les ressources partagées ne permettent pas de déduire une loi de complexité ni une vitesse universelle. Le rapport publie moyenne, dispersion, pire cas et limites.
