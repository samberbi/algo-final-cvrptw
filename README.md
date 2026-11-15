# CVRPTW — Remise finale du groupe G5

**Dernière version à télécharger pour la correction et la soutenance :**

## [Télécharger le projet complet — ZIP final, 65,6 Mo](https://github.com/samberbi/algo-final-cvrptw/raw/refs/heads/main/remise_finale/CVRPTW_G5_VERSION_FINALE_FATIMA.zip)

Cette archive réunit les trois parties transmises par email. Elle contient la remise finale vérifiée : notebook exécuté et HTML, modélisation, code commenté, tests, données, résultats, graphiques et commandes de démonstration.

| Groupe | Membres |
| --- | --- |
| **G5** | Anes AMARI - Youcef HADJ AISSA - Axel CHEBAHI - Ramy HAMOUR - Samy BARBICHE |

## Lire et tester la dernière version

1. Télécharger le ZIP final ci-dessus et l'extraire entièrement.
2. Ouvrir le dossier `CVRPTW_SOUTENANCE_FINAL`, puis **`A_LIRE_PROFESSEUR.md`**.
3. Pour lire le livrable, ouvrir **`notebooks/Livrable_Final_CVRPTW.html`** dans un navigateur. Le notebook est fourni dans le même dossier au format `.ipynb`.
4. Pour installer et tester, utiliser les instructions incluses et Python 3.12 en 64 bits.

Depuis la racine du dossier extrait, dans PowerShell :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-pc-soutenance.txt
.\.venv\Scripts\python.exe -m pytest tests -q
```

Petite démonstration avec tableaux, convergence et cartes :

```powershell
.\.venv\Scripts\python.exe scripts/test_instances.py --instances C101 --size 25 --methods ils size_based --seconds 5 --label demonstration_professeur
```

Les commandes de démonstration et l'ouverture des résultats dans Chrome sont documentées dans l'archive. L'installation nécessite Internet ; le préchauffage peut rallonger le premier lancement.

## Vérifications incluses

- **242 tests réussis, 2 ignorés** pour l'extension temporelle optionnelle.
- **16 cellules de code du notebook exécutées sans erreur.**
- Vérification des 646 solutions historiques, des 356 instances de référence, des 24 figures et des 10 contrôles exacts.
- Section **3.1.1** : équivalence entre durée totale et trajets + attentes, à la constante des services près, lorsque **β = 1** et que les coûts d'arcs sont des temps de trajet.
- Les témoins issus de solutions en distance ne sont pas présentés comme des optimums temporels certifiés. Les campagnes historiques et leurs budgets restent identifiés.

L'archive contient **4 617 fichiers**, avec leurs comptes rendus de contrôle. Son empreinte SHA-256 et les informations de vérification sont dans [remise_finale/INTEGRITE.json](remise_finale/INTEGRITE.json).

## Versions historiques du dépôt

**La version finale à corriger et à tester est celle du ZIP ci-dessus.** Les sources et documents antérieurs présents ailleurs dans l'arborescence de `main` sont conservés pour l'historique et peuvent différer de cette remise. Utiliser le dossier extrait du ZIP pour exécuter la dernière version.

L'ancien accueil du dépôt est conservé dans [README_HISTORIQUE.md](README_HISTORIQUE.md).
