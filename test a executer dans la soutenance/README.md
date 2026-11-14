# Tests à exécuter dans la soutenance

Ce dossier rassemble les commandes de démonstration et la préparation du PC
portable. Le livrable à présenter est `notebooks/Livrable_Final_CVRPTW.ipynb`.
Sa version HTML permet une lecture sans exécuter Jupyter.

**Liste exhaustive pour tester une instance à la fois :**
[116 commandes Markdown](TOUTES_COMMANDES_INSTANCE_PAR_INSTANCE.md) ou
[version texte à copier](TOUTES_COMMANDES_INSTANCE_PAR_INSTANCE.txt).
Chaque ligne compare les deux moteurs sur une instance : 56 cas à 100 clients
et 60 cas à 1000 clients. Lancer uniquement la ligne choisie.

## 1. Récupérer la bonne version sur le portable

Deux possibilités : extraire intégralement le ZIP, ou cloner cette branche :

```powershell
git clone --branch rendu-professeur --single-branch https://github.com/samberbi/algo-final-cvrptw.git
cd algo-final-cvrptw
```

La branche de remise est **rendu-professeur**. Un clone sans option peut ouvrir
la branche par défaut, qui contient une autre version. Pour un clone existant,
sauvegarder d'abord son travail local, puis sélectionner la branche de remise
et récupérer ses mises à jour sans écrasement forcé.

Avec le ZIP, extraire tout le dossier avant de lancer les commandes. Dans
VS Code, ouvrir le dossier contenant `README.md`, `scripts`, `algo` et `data`,
puis ouvrir un terminal PowerShell à cet emplacement.

## 2. Préparer le Python du portable, une seule fois

Installer Python **3.12 en 64 bits**, avec le lanceur Windows `py`. Vérifier :

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-reference-final.txt
.\.venv\Scripts\python.exe -m pip check
```

L'installation nécessite Internet. Préparer et tester l'environnement avant
la soutenance ; les benchmarks utilisent ensuite les données locales.

L'environnement `.venv` doit être créé sur chaque ordinateur. Les environnements
du PC d'origine ne sont pas distribués dans le ZIP. `.venv_dabia` concerne
l'extension optionnelle et ne fournit pas le solveur statique de cette remise.
Le chemin explicite `.\.venv\Scripts\python.exe` sélectionne le bon Python,
même si un autre environnement apparaît dans l'invite PowerShell.

Un assistant d'installation est également fourni :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\test a executer dans la soutenance\INSTALLER.ps1"
```

Cette option s'applique à ce processus PowerShell. Les commandes Python directes
ci-dessus ne nécessitent pas d'activation ni de modification de politique.

## 3. Démonstration rapide : six familles

**Six instances, douze résolutions**, graine 4101, cinq secondes demandées par
méthode. C'est la démonstration recommandée pendant la présentation.

```powershell
.\.venv\Scripts\python.exe scripts/test_instances.py --instances C101 C201 R101 R201 RC101 RC201 --seconds 5
```

## 4. Toutes les instances à 100 clients

**56 instances, 112 résolutions**. Cette campagne est plus longue ; la préparer
avant la soutenance si l'on veut consulter tous ses résultats.

```powershell
.\.venv\Scripts\python.exe scripts/test_instances.py --all --sizes 100 --seconds 5 --label comparaison_100
```

## 5. Toutes les instances à 1 000 clients

**60 instances, 120 résolutions**, trente secondes demandées par méthode.
Prévoir environ une heure de recherche avec un processus, plus les constructions,
préparations et démarrages. La durée dépend du matériel et des arrêts anticipés.

```powershell
.\.venv\Scripts\python.exe scripts/test_instances.py --all --sizes 1000 --seconds 30 --label comparaison_1000
```

## 6. Sélection et commandes complémentaires

Le lanceur fourni fonctionne aussi depuis un autre dossier, car il retrouve
automatiquement la racine du projet :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\test a executer dans la soutenance\LANCER_TESTS.ps1" -Mode SixFamilles
powershell -NoProfile -ExecutionPolicy Bypass -File ".\test a executer dans la soutenance\LANCER_TESTS.ps1" -Mode Toutes100
powershell -NoProfile -ExecutionPolicy Bypass -File ".\test a executer dans la soutenance\LANCER_TESTS.ps1" -Mode Toutes1000
powershell -NoProfile -ExecutionPolicy Bypass -File ".\test a executer dans la soutenance\LANCER_TESTS.ps1" -Mode Selection
```

Le chemin vers le lanceur doit désigner son emplacement réel. Les options
`-Seconds`, `-Seed` et `-Workers` permettent d'adapter explicitement les essais.

Vérifier les 116 instances et 232 résolutions sélectionnées sans lancer de calcul :

```powershell
.\.venv\Scripts\python.exe scripts/test_instances.py --all --sizes 100 1000 --dry-run
```

Tester une famille complète, ici C1 à 100 clients :

```powershell
.\.venv\Scripts\python.exe scripts/test_instances.py --all --sizes 100 --families C1 --seconds 5
```

Remplacer C1 par C2, R1, R2, RC1 ou RC2. Pour les autres tailles disponibles,
adapter `--sizes` parmi 25, 50, 100, 200, 400, 600, 800 et 1000. La sélection
affichée avant le calcul indique le nombre de résolutions.

Vérifier le code, puis réexécuter et valider le notebook si nécessaire :

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe scripts/finalize_static.py --execute --validate
```

Le notebook peut aussi être lu avec ses sorties déjà enregistrées. Dans VS Code,
installer les extensions Python et Jupyter et choisir le noyau du `.venv` local.

## 7. Lire et conserver les résultats

Les commandes produisent aussi des graphiques **pour chaque instance et graine**.
Après le lot, une page `GRAPHIQUES.html` s'ouvre dans le navigateur : courbes de
convergence enregistrées, cartes des tournées finales de l'ILS et du renforcé,
durées, véhicules et tableaux de comparaison. Les PNG sont dans `figures`.
Les couleurs distinguent les tournées ; le carré noir représente le dépôt.
Une phase sans trace intermédiaire n'est pas reconstituée artificiellement.
La génération des images est chronométrée séparément des résolutions.

Ajouter `--no-open-plots` pour sauvegarder sans ouverture automatique, ou
`--no-plots` pour désactiver le rendu. Pour dessiner un lot ancien :

```powershell
.\.venv\Scripts\python.exe scripts/plot_terminal_results.py --label comparaison_100 --open
```

Chaque commande sans méthode explicite lance l'ILS initial et le profil renforcé
`size_based`. Le comparatif apparaît pour chaque instance et graine dès que les
deux méthodes sont terminées, puis dans le bilan global. Il affiche :

- durée complète, faisabilité et nombre de véhicules ;
- écart au plan témoin compatible ou statut de référence ;
- temps réel, CPU et budget demandé de chaque méthode ;
- gain de durée entre méthodes, avec égalités et régressions conservées.

Le gain entre méthodes est distinct du gap au témoin. Les plans témoins
réévalués en durée ne sont pas des optima temporels certifiés. Les contributions
externes PyVRP et HiGHS sont attribuées dans le livrable.

Les cinq ou trente secondes s'appliquent **à chaque moteur**. La construction
s'ajoute au budget de recherche de l'ILS ; le renforcé utilise un total souple.
Comparer les temps mesurés pour apprécier le coût réel. Le garde-fou de 120
secondes concerne chaque processus, et non le lot complet.

Les sorties se trouvent dans `results/local/<label>` : `RESULTATS.csv`,
`COMPARAISON_INITIAL_RENFORCE.csv`, `SYNTHESE.txt`, tournées JSON et protocole.
Un label existant reçoit un suffixe, sans écrasement. Relire un lot sans calcul :

```powershell
.\.venv\Scripts\python.exe scripts/test_instances.py --show-results comparaison_100
```

Utiliser le label effectivement affiché si un suffixe a été ajouté. Les résultats
du portable peuvent varier avec le temps disponible et le nombre d'itérations ;
conserver ces nouvelles mesures séparément des campagnes publiées.

## 8. Points à adapter sur le portable

- **Dossier courant :** être à la racine extraite ou clonée. Aucun chemin
  `C:\Users\user\...` du PC d'origine n'est nécessaire pour ces commandes.
- **Python :** utiliser Python 3.12 et recréer `.venv` localement.
- **Noyau VS Code :** sélectionner le Python du `.venv` de ce projet.
- **Branche Git :** récupérer `rendu-professeur` pour cette remise.
- **Données et résultats :** garder tous les dossiers du projet ensemble ; le
  notebook utilise aussi des CSV et des figures, pas seulement son fichier ipynb.
- **Mesures :** commencer par un processus (`--workers 1`, défaut). Une exécution
  parallèle modifie les ressources disponibles et doit être indiquée dans le protocole.
- **Budgets :** réserver la campagne complète à 1000 clients à la préparation,
  puis utiliser un cas ou les six familles pour une démonstration rapide.
- **Fichiers historiques :** les chemins du PC d'origine dans les protocoles
  décrivent la provenance des anciennes mesures ; ils ne sont pas à remplacer
  pour faire tourner les nouvelles commandes.

Le ZIP conserve le code, les données, les tests et les résultats disponibles.
Les caches, environnements Python et métadonnées internes Git sont exclus.
