# CVRPTW — ILS optimisée et recuit décomposé

Le moteur minimise la **distance DIMACS**, avec capacité, fenêtres strictes,
couverture unique et flotte maximale. Les contraintes et données restent inchangées.

## Résultats et périmètre

La validation équilibrée contient **36 instances, cinq graines et deux méthodes :
360 trajectoires**. Chaque taille (100, 200, 1 000 clients) contient douze instances.
La calibration séparée comporte 324 essais sur douze instances. La comparaison
avant/après comporte 80 essais sur C204 et R1_10_1, avec vingt graines et des
départs/budgets appariés, y compris la réexécution des sources v1 figées.

- ILS : gap moyen équilibré **4.933 %**, pire gap **24.321 %**.
- ILS à 1 000 clients : moyenne **10.055 %** sur douze instances.
- R1_10_1, à 25 secondes : moyenne v1 **9.746 %**, optimisée **4.234 %**.

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
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\python.exe cli.py R1_10_1 --method ils --seconds 25 --seed 101
.\.venv\Scripts\python.exe -m streamlit run web/app.py
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
.\.venv\Scripts\python.exe scripts\analyze_optimization_v2.py --stage validation
.\.venv\Scripts\python.exe scripts\analyze_optimization_v2.py --stage regression
.\.venv\Scripts\python.exe scripts\build_optimization_report.py
.\.venv\Scripts\python.exe scripts\validate_optimization_delivery.py
```

Les protocoles et sources figées sont dans `results/optimization_v2/`.
Les reprises ne remplacent pas les fichiers terminés. Une reproduction neuve
nécessite un nouveau dossier et protocole, avec les affinités CPU du nouveau poste.
Les versions de l'environnement mesuré figurent dans `environment.json` de ce dossier.
Les anciens résultats ILS et ALNS restent dans leurs archives. `livraison/VALIDATION.json`
désigne exclusivement la validation de la livraison courante.
