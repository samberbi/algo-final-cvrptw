# Démarrage sur le portable Windows 11

## 1. Prendre la version à jour

La branche de soutenance est **rendu-professeur**. Les graphiques automatiques
et les 116 commandes individuelles sont sur cette branche.

```powershell
git clone --branch rendu-professeur --single-branch https://github.com/samberbi/algo-final-cvrptw.git
cd algo-final-cvrptw
```

Choisir un dossier de destination neuf si `algo-final-cvrptw` existe déjà.
Avec un clone existant contenant du travail personnel, sauvegarder ou committer
ses changements avant une mise à jour ; ne pas utiliser de réinitialisation forcée.
Le ZIP de livraison antérieur ne contient pas les ajouts de graphiques plus récents.

## 2. Installer et vérifier Python

Installer Python **3.12 en 64 bits (x64)** avec le lanceur `py`, puis ouvrir
un nouveau terminal PowerShell dans la racine du projet.

```powershell
py -3.12 --version
powershell -NoProfile -ExecutionPolicy Bypass -File ".\test a executer dans la soutenance\INSTALLER.ps1"
```

L'installateur crée le `.venv` du portable, utilise les versions enregistrées
pour les dépendances disponibles, vérifie Python et lance `pip check`.
Internet est nécessaire pour la préparation ; les données de tests sont locales.
Cette option PowerShell est limitée au processus lancé.

**Ne pas transférer `.venv` ou `.venv_dabia` depuis l'ancien PC.** Le nouvel
environnement est construit à partir des fichiers du dépôt. Pour les commandes
directes, employer `.\.venv\Scripts\python.exe` ; aucune activation n'est requise.

Vérifier un environnement déjà installé, sans réinstallation :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\test a executer dans la soutenance\INSTALLER.ps1" -VerifierSeulement
```

## 3. Vérifier la sélection sans lancer les recherches

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\test a executer dans la soutenance\LANCER_TESTS.ps1" -Mode Selection
```

Résultat attendu : **116 instances, 232 résolutions**, méthodes `ils` et `size_based`.
Cette commande n'exécute aucune résolution et ne crée pas de nouveaux résultats.

## 4. Lancer la démonstration

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\test a executer dans la soutenance\LANCER_TESTS.ps1" -Mode SixFamilles
```

Six instances à 100 clients, deux moteurs, cinq secondes demandées chacun.
Chaque instance reçoit son comparatif terminal. Après le lot, le navigateur
ouvre une page regroupant les courbes de convergence et les cartes des tournées.

Pour une seule instance, copier une ligne de
[TOUTES_COMMANDES_INSTANCE_PAR_INSTANCE.md](TOUTES_COMMANDES_INSTANCE_PAR_INSTANCE.md).

Pour enregistrer les images sans ouvrir le navigateur :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\test a executer dans la soutenance\LANCER_TESTS.ps1" -Mode SixFamilles -SansOuvertureGraphiques
```

Le paramètre `-SansGraphiques` désactive complètement leur génération.
La sortie du terminal indique le dossier des résultats et `GRAPHIQUES.html`.
On peut ouvrir cette page manuellement si le navigateur ne s'affiche pas.

## 5. Ouvrir le livrable

Dans VS Code, ouvrir **tout le projet**, installer les extensions Python et
Jupyter, puis ouvrir `notebooks/Livrable_Final_CVRPTW.ipynb`.
Choisir le noyau du **`.venv` local au portable** pour l'exécuter.
Pour simplement lire, ouvrir le notebook avec ses sorties déjà enregistrées
ou `notebooks/Livrable_Final_CVRPTW.html`.

Les anciennes mesures et leurs chemins de provenance restent archivés.
Les nouveaux essais du portable vont dans `results/local/<label>` ; les labels
déjà utilisés reçoivent un suffixe. Les résultats peuvent varier avec le matériel
et le nombre d'itérations réalisées dans le budget.

## Vérifications réalisées avant le push

Les scripts ont été vérifiés en PowerShell sur le PC de développement
Windows 10 x64 : syntaxe, détection de Python 3.12 x64, cohérence des dépendances
et mode Selection. Les tests du solveur et les rendus ont été exécutés sur
ce PC. Le parcours ci-dessus prépare Windows 11 ; la validation matérielle
sur le portable sera effectuée en lançant les étapes 2 à 4.
