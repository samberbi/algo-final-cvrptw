# ALGO FINAL — Livrable CVRPTW

Le benchmark minimise **la distance totale**, avec les conventions DIMACS de
PyVRP/Instances. La flotte est un maximum autorisé ; elle n'est pas un objectif
prioritaire. Les capacités, fenêtres et retours au dépôt sont obligatoires.

L'étude principale comporte **80 nouvelles résolutions sur 28 instances**, toutes
réalisables : gap moyen **0,407 %**, pire gap **3,379 %**, soit 80/80 sous 5 %.
Elle présente 24 cas à 100 clients et quatre cas à 200 ou 1 000 clients.
Les instances étaient déjà connues ; il ne s'agit pas d'un test aveugle.

L'extension reste intégrale : **1 000 trajectoires, 356 instances et 100 % de
solutions réalisables**. Le gap moyen final par exécution est **3,169 %** ;
sur les **167 essais à 1 000 clients**, il est **5,927 %**. Le pire gap global
reste **15,262 %** ; 863 essais sur 1 000 sont strictement sous 7 %.
Les quinze tests passent. Ces résultats décrivent le protocole et les temps
cumulés publiés, sans garantie de ce seuil pour chaque exécution.

## Installation sur un autre ordinateur

Le guide [INSTALLATION_PORTABLE.md](docs/INSTALLATION_PORTABLE.md) explique
comment cloner le dépôt, créer un environnement Python 3.12, lancer les tests
et ouvrir le Notebook. Le dépôt est autonome : les commandes utilisent
`.\.venv\Scripts\python.exe` après création de cet environnement dans ce dossier.
Les commandes historiques `..\.venv` ci-dessous correspondent à l'ancien poste.

## Documents à ouvrir

- `notebooks/Livrable_Final_CVRPTW.ipynb` : Notebook principal, exécuté et commenté.
- `notebooks/Livrable_Final_CVRPTW.html` : lecture sans Jupyter.
- `livraison/RAPPORT_CVRPTW.pdf` : rapport à lire ou remettre.
- `livraison/RAPPORT_CVRPTW.docx` : version Word avec équations éditables.
- `livraison/ANNEXE_INSTANCES.pdf` : bilan des 356 instances.
- `livraison/MILLE_EXECUTIONS.html` : tableau filtrable des 1 000 runs.
- `results/report/mille_executions.csv` : chacune des 1 000 résolutions.
- `livraison/ETUDE_80_EXECUTIONS.html` : les 80 nouveaux essais du lot principal.
- `results/report/etude_principale_80.csv` : mêmes essais en valeurs numériques.
- `results/report/essais_hors_cible.csv` : échecs ou gaps supérieurs ou égaux à 7 %.

Ces documents sont construits après la fin et la vérification de la campagne.
Pendant les calculs, `results/campaign/progress.json` donne l'effectif terminé.
Un résultat non exécuté n'est pas présenté comme une mesure.

## Code et données

`algo/solver.py` orchestre notre ALNS ; `algo/kernels.py` contient les calculs
compilés ; `algo/verify.py` contrôle les tournées indépendamment. Le moteur ne
lit pas les fichiers de référence. `metier/` contient le moteur séparé pour la
durée, attente et service compris. `cli.py` permet une démonstration courte.

Les données publiques sont dans `data/instances/`. La révision, les URLs,
empreintes et vérifications des BKS figurent dans `data/manifest.json`.
La convention est `floor(10 * distance euclidienne)` par arc. Le solveur travaille
en dixièmes ; son champ `cost` est ramené aux unités affichées. Les métriques
internes du vérificateur restent en dixièmes.

## Exécuter et reproduire

Depuis ce dossier, avec l'environnement existant du projet :

```powershell
..\.venv\Scripts\python.exe cli.py R202 --seconds 5 --seed 11
..\.venv\Scripts\python.exe -m pytest tests
..\.venv\Scripts\python.exe scripts\run_focused_validation.py
..\.venv\Scripts\python.exe scripts\run_campaign.py
..\.venv\Scripts\python.exe scripts\study_polish.py
..\.venv\Scripts\python.exe scripts\run_polish_campaign.py
..\.venv\Scripts\python.exe scripts\run_largest_polish.py
..\.venv\Scripts\python.exe scripts\study_parameters.py
..\.venv\Scripts\python.exe scripts\study_duration.py
..\.venv\Scripts\python.exe scripts\build_report.py
..\.venv\Scripts\python.exe scripts\export_report.py
..\.venv\Scripts\python.exe scripts\export_pdf.py
..\.venv\Scripts\python.exe scripts\export_pdf.py --stem ANNEXE_INSTANCES
```

Pour une installation autonome, créer un environnement Python 3.12 et installer
`requirements-lock.txt`. Le constructeur de Notebook utilise l'interpréteur
Python qui le lance et prépare un noyau local. Pour ouvrir le Notebook dans
l'éditeur, sélectionner cet environnement Python. La conversion Word utilise Pandoc ; le script
le télécharge si aucune copie locale compatible n'est disponible. Le PDF utilise
Edge ou Chrome installé localement.

Les commandes de campagne reprennent les fichiers existants et les conservent.
Elles ne prétendent pas avoir exécuté de nouvelles recherches lorsqu'elles
relisent un essai déjà enregistré. Pour une reproduction intégrale à neuf,
utiliser une autre copie du projet sans ses sorties de campagne, en conservant
les archives originales et les protocoles de référence.

## Protocole et limites

1 000 résolutions sont prévues sur 356 problèmes, avec deux ou trois graines
par instance. Les budgets initiaux vont de cinq à quinze secondes selon la taille.
Une intensification exploratoire ajoute cinq secondes aux cas d'au moins
400 clients et une seconde passe ajoute cinq secondes à 1 000 clients ;
le budget cumulé atteint alors 13, 15, 17 ou 25 secondes.
Quatre processus mono-thread ont des affinités CPU distinctes. Chaque fichier
dans `results/campaign/runs/` conserve sa provenance ; une reprise ne le remplace pas.
Les états après intensification sont dans `results/final/runs/`, avec les
empreintes des départs et les temps cumulés. Ces continuations ne sont pas
comptées comme des résolutions indépendantes supplémentaires. Deux autres
cœurs les exécutent ; les ressources de cache et de refroidissement restent partagées.
Dans un JSON dérivé, les champs du `job`, le PID initial et
`wall_with_loading_s` décrivent le départ enregistré. Le temps de recherche
cumulé est `result.runtime_s`, détaillé par `base_runtime_s` et
`continuation_runtime_s` ; `total_budget_s` donne le budget cumulé nominal.
Les états définitifs à 1 000 clients sont dans `results/largest_v2/runs/` ;
le constructeur les utilise à la place du premier état continué, avec la
preuve de filiation par empreinte. Un lancement auxiliaire mal filtré a été
écarté ; son code, sa justification et ses sorties restent dans les dossiers
`results/rejected_largest_v1/` et `results/largest/`, sans entrer dans les statistiques.
Les essais pilotes, l'étude de sensibilité et l'étude durée restent séparés.

Le temps réel peut dépasser légèrement le budget pendant une opération atomique.
Le protocole parallèle permet un débit élevé, pas une comparaison directe de
vitesse avec un autre ordinateur ou une campagne séquentielle. Les petites
différences de temps peuvent modifier les dernières itérations.

Les statistiques distinguent moyenne par exécution et moyenne par instance.
Deux ou trois graines ne suffisent pas à garantir la robustesse sur toutes les
situations. Aucun calcul d'émissions réelles, de trafic variable ou de gap BKS
en durée n'est revendiqué.
