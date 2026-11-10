# Continuer le projet sur un autre ordinateur

Le dépôt contient le projet final autonome : moteur, 356 instances, références,
résultats enregistrés, tests et livrables. Les environnements Python et les caches
compilés sont propres à chaque machine et se recréent après le clonage.

## Installation Windows

Installer Git, Python 3.12 et VS Code avec les extensions Python et Jupyter.
Dans PowerShell, depuis le dossier cloné :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\python.exe cli.py C101 --seconds 5 --seed 11 --output results/local/c101.json
```

Le premier lancement compile les noyaux Numba ; ce préchauffage est mesuré
séparément du temps de recherche. Il n'est pas nécessaire de réexécuter les
1 000 essais pour consulter les résultats déjà publiés.

Dans VS Code, ouvrir `notebooks/Livrable_Final_CVRPTW.ipynb` et sélectionner
comme noyau le Python du dossier `.venv`. Le HTML et les PDF se lisent directement.

## Documents et résultats

- Notebook : `notebooks/Livrable_Final_CVRPTW.ipynb`.
- Rapport : `livraison/RAPPORT_CVRPTW.pdf`.
- Tableau interactif des 1 000 essais : `livraison/MILLE_EXECUTIONS.html`.
- Tableau des 356 instances : `results/report/toutes_les_instances.csv`.
- Chaque essai : `results/report/mille_executions.csv`.
- Étude principale de 80 essais : `results/report/etude_principale_80.csv`.
- Code : `algo/`, `ameliorations/`, `metier/`, `controle/` et `cli.py`.

## Travailler entre deux ordinateurs

Avant de commencer : `git pull`. Après les modifications :

```powershell
git add .
git commit -m "Décrire les modifications"
git push
```

Les données brutes et les protocoles historiques doivent être conservés.
Enregistrer les nouveaux essais dans `results/local/` ou dans une nouvelle
campagne explicitement identifiée, sans remplacer les mesures publiées.

Les scripts historiques de campagne enregistrent un protocole figé qui inclut
les affinités CPU de l'ordinateur d'origine. Une autre machine peut donc refuser
leur reprise si sa topologie diffère. Le CLI ci-dessus permet de lancer de
nouveaux essais sans modifier ces protocoles. Les commandes `..\.venv` présentes
dans le livrable correspondent à l'ancienne arborescence : pour ce dépôt autonome,
utiliser `.\.venv`.

## Interface web

L'interface est disponible : installer `requirements-web.txt` puis lancer
`python -m streamlit run web/app.py` avec l'environnement du projet.
Elle utilise notre moteur pour choisir les instances, budgets et graines,
lancer les résolutions, vérifier leur faisabilité et afficher les tournées,
la convergence, les statistiques et les gaps DIMACS. Voir [INTERFACE_WEB.md](INTERFACE_WEB.md).
