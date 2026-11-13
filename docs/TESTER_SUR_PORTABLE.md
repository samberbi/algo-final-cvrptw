## Annexe — Tests rapides pour la soutenance

L'objectif reste la durée totale des tournées (trajets, attentes, services).
La limite de calcul communiquée pour la soutenance est de deux minutes. Les
commandes ci-dessous utilisent seulement cinq secondes par résolution, avec une
seule graine. La limite est souple : un appel natif commencé peut se terminer
après l'échéance. Le temps réel est enregistré. L'installation et le préchauffage
initial ne constituent pas un temps de résolution.

### Installation sur le portable, une seule fois

```powershell
git clone --branch rendu-professeur https://github.com/samberbi/algo-final-cvrptw.git CVRPTW
cd CVRPTW
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Dans VS Code, ouvrir ce dossier et sélectionner le noyau `.venv`. Le livrable
courant est `notebooks/Livrable_Final_CVRPTW.ipynb` ; les anciens Word/PDF/HTML ne
sont pas synchronisés avec cette révision.

### Vérifier le code et les résultats enregistrés

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q --junitxml=livraison/TESTS_SOUTENANCE.xml
.\.venv\Scripts\python.exe scripts/validate_soutenance.py
```

Le validateur recalcule les contraintes et coûts des solutions enregistrées,
sans relancer les recherches. Le reçu courant est
`livraison/VALIDATION_SOUTENANCE.json` ; `MANIFESTE_SHA256.json` concerne l'édition
précédente. Un test de simulation peut être ignoré si Node.js est absent ; il
reste signalé comme ignoré, jamais comme réussi.

### Choisir des tests courts par famille

C désigne des clients regroupés, R une répartition aléatoire et RC un mélange.
Les types 1 et 2 se distinguent notamment par l'horizon et la capacité ; ils ne
désignent pas le nombre de clients. Les six exemples suivants ont 100 clients.

```powershell
# C1 et C2 : deux résolutions, clients regroupés
.\.venv\Scripts\python.exe scripts/test_instances.py --instances C101 C201 --seconds 5 --label rapide_C

# R1 et R2 : deux résolutions, clients dispersés
.\.venv\Scripts\python.exe scripts/test_instances.py --instances R101 R201 --seconds 5 --label rapide_R

# RC1 et RC2 : deux résolutions, clients mixtes
.\.venv\Scripts\python.exe scripts/test_instances.py --instances RC101 RC201 --seconds 5 --label rapide_RC

# Alternative : les six familles en une seule commande, six résolutions seulement
.\.venv\Scripts\python.exe scripts/test_instances.py --instances C101 C201 R101 R201 RC101 RC201 --seconds 5 --label rapide_6_familles

# C1 et C2 à 1 000 clients : deux résolutions seulement
.\.venv\Scripts\python.exe scripts/test_instances.py --instances C1_10_6 C2_10_2 --seconds 5 --label rapide_1000
```

Choisir les commandes souhaitées ; il n'est pas nécessaire de toutes les lancer.
Pour refaire un test, changer `--label` : les dossiers existants sont refusés
pour préserver les résultats. Le profil par défaut `duration_refined` associe
nos constructions, notre orchestration et notre partitionnement à la recherche
locale **externe PyVRP**. Il ne lance pas les longues continuations HGS.

Pour tester notre ILS sans optimisation PyVRP sur un seul cas :

```powershell
.\.venv\Scripts\python.exe scripts/test_instances.py --instances C101 --method ils --seconds 5 --label rapide_ils
```

Pour l'ILS, la construction s'ajoute au budget de recherche. Un seul essai permet
de vérifier le fonctionnement ; il ne suffit pas pour classer les méthodes.

### Lire les résultats

Chaque commande affiche la progression et les temps réels. Le dossier
`results/local/<label>/` contient `RESULTATS.csv` (faisabilité, durée de la
solution, durée du témoin, écart signé, véhicules, temps réel), les JSON des
tournées et erreurs éventuelles, ainsi que `BILAN.json`, `protocol.json` et les
sources exécutées. Le temps du lot inclut démarrage et préchauffage.

L'écart compare la durée au plan témoin réévalué ; il ne prouve pas un écart à
l'optimum temporel. Ces tests courts ne garantissent pas un écart sous 6 % et ne
remplacent pas une étude statistique. Les meilleurs résultats historiques à
budgets différents restent dans
`results/time_objective/best_duration/COUVERTURE_472_ESSAIS.csv`.
