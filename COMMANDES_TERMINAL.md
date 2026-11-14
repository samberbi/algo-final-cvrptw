# Commandes terminal CVRPTW — PowerShell Windows

## Configuration actuelle des commandes : sélection par taille

Depuis cette révision, les nouvelles commandes de test utilisent `size_based`
par défaut : construction seule pour 25/50/100 clients, renforcé au-delà.
Le moteur choisi est affiché et enregistré. Pour reproduire un ancien test
implicitement renforcé, ajouter `--method refined`. Les résultats historiques
et leurs références restent conservés ; ils ne deviennent pas des résultats
du nouveau sélecteur. Le seuil ne dépend pas du gap. La validation de six cas
et les limites sont dans [SELECTION_PAR_TAILLE.md](docs/SELECTION_PAR_TAILLE.md).

Les commandes de cette fiche ont été vérifiées sur le projet. Les transcriptions,
codes retour et résultats sont dans `results/terminal_validation/`.
`scripts/test_instances.py` et `scripts/run_benchmark.py` utilisent la même
interface. Les fonctions historiques importées par les scripts CPU sont conservées.

## 1. Choisir le bon Python

Sur le PC actuel, copier ce bloc dans PowerShell :

```powershell
cd "C:\Users\user\Downloads\CVRPTW_REMISE_PROF_20261112T203928"
$py = "C:\Users\user\OneDrive - Association Cesi Viacesi mail\Bureau\PROJET ALGO\.venv\Scripts\python.exe"
```

Le chemin ci-dessus est celui des exécutions de validation. Sur le portable,
ouvrir le dossier extrait contenant `README.md`, puis installer une fois :

```powershell
py -3.12 -m venv .venv
$py = Join-Path (Get-Location) ".venv\Scripts\python.exe"
& $py -m pip install -r requirements-reference-final.txt
& $py -m pip check
```

La procédure d'installation portable n'a pas été rejouée sur un deuxième
ordinateur. L'environnement actuel a passé `pip check`. Après installation,
toutes les commandes suivantes utilisent `& $py`. Si le terminal utilise déjà
ce même environnement, `python scripts/test_instances.py ...` convient aussi.

## 2. Une instance et ses tournées

```powershell
& $py -X utf8 scripts/test_instances.py --instances C101 --size 25 --seconds 5 --show-routes
```

Un label est créé automatiquement. C101 sans `--size` sélectionne 100 clients ;
`--size 25` ou `--size 50` sélectionne le préfixe standard correspondant. La
forme `--instances C101:25` est également acceptée. Les services et fenêtres
de ces sous-instances restent ceux des clients d'origine ; les manifestes
conservent leurs empreintes et la dérivation depuis les fichiers à 100 clients.

## 3. Plusieurs instances et les six familles

```powershell
& $py -X utf8 scripts/test_instances.py --instances C101 C201 R101 R201 RC101 RC201 --seconds 5 --label commandes_terminal_runs_100
```

| Famille | Instance à 100 clients réellement testée |
|---|---|
| C1 | C101 |
| C2 | C201 |
| R1 | R101 |
| R2 | R201 |
| RC1 | RC101 |
| RC2 | RC201 |

Pour filtrer par famille et taille, une instance représentative est choisie :

```powershell
& $py -X utf8 scripts/test_instances.py --family R1 --size 200 --seconds 5 --label commandes_terminal_runs_R1_200
```

La sélection des six familles peut être inspectée sans calcul :

```powershell
& $py -X utf8 scripts/test_instances.py --families C1 C2 R1 R2 RC1 RC2 --size 100 --dry-run
```

`--size 200` seul choisit une instance de chaque famille à cette taille.
`--all` demande explicitement toutes les instances correspondant aux filtres.
Par défaut, aucune commande sans sélection ne lance les 356 instances : elle
choisit seulement C101 à 100 clients. Les familles et tailles absentes donnent
une erreur explicite, sans ignorer silencieusement une instance nommée.

## 4. Toutes les tailles progressivement, huit résolutions seulement

```powershell
& $py -X utf8 scripts/run_benchmark.py --progressive --seconds 5 --label commandes_terminal_runs_progressif
```

Cette commande choisit un cas C1 à chacune des tailles 25, 50, 100, 200, 400,
600, 800 et 1000. Ce n'est pas le catalogue complet. Les options `--sizes` et
`--families` permettent de réduire ou modifier cette sélection.

Un cas précis à 1000 clients, avec budget de trente secondes, a aussi été exécuté :

```powershell
& $py -X utf8 scripts/test_instances.py --instances C1_10_6 --seconds 30 --max-seconds 120 --label commandes_terminal_1000_30s
```

## 5. Comparer les méthodes sur la même instance

```powershell
& $py -X utf8 scripts/run_benchmark.py --instance C101 --size 25 --methods ils sa pyvrp hybrid refined ortools --seconds 5 --reference independent --label commandes_terminal_runs_comparaison
```

Le terminal affiche chaque résultat immédiatement, puis un classement par
durée réalisable pour chaque couple instance–graine. Les ex æquo sont affichés ;
les échecs ne reçoivent pas de rang. Les budgets et temps totaux figurent dans
le tableau : un classement sur un cas n'est pas une supériorité générale.

| Code | Méthode et attribution |
|---|---|
| `size_based` | Nouveau défaut : construction seule jusqu'à 100 clients, renforcé au-delà |
| `ils` | Notre ILS et nos opérateurs, sans optimisation PyVRP |
| `sa` | Notre recuit simulé et nos opérateurs |
| `pyvrp` | PyVRP/HGS externe seul, population native |
| `hybrid` | Notre construction et ILS, puis HGS PyVRP externe |
| `refined` | Constructions propres, Local Search PyVRP et partitionnement HiGHS |
| `duration_refined` | Alias historique conservé de `refined` |
| `ortools` | OR-Tools externe, objectif somme des durées complètes |
| `construction` | Construction propre regret-2, douze tentatives |
| `refined_no_partition` | Profil renforcé sans partitionnement |
| `refined_ils` | Profil renforcé puis notre ILS dans le temps restant |

Les trois derniers profils ont également été vérifiés via cette commande :

```powershell
& $py -X utf8 scripts/run_benchmark.py --instance C101 --size 25 --methods construction refined_no_partition refined_ils --seconds 1 --label commandes_terminal_profils_complementaires
```

La construction seule a réellement donné +8,4925 % au comparateur indépendant
sur ce cas. Ce dépassement est affiché et conservé, pas ramené artificiellement
sous 6 %. L'optimum du partitionnement ne concerne que son réservoir de tournées.

## 6. Lire les références et les gaps

La durée est trajets + attentes + services, retour au dépôt inclus, départs
à zéro. Les trajets sont fixes et symétriques. Chaque solution est recalculée
par `algo.verify`, indépendamment des noyaux de recherche.

`--reference auto` utilise le plan public réévalué en durée pour les tailles
100–1000, et une solution OR-Tools enregistrée compatible si disponible pour
25/50. `--reference independent` choisit uniquement une référence OR-Tools
figée, jamais le résultat de notre propre méthode évaluée. Cette référence
n'est pas recalculée à chaque test : son chemin est affiché. Le profil `ortools`
permet en revanche d'exécuter une nouvelle résolution OR-Tools comme méthode.

L'écart vaut `100 * (durée_solution / durée_reference - 1)`. Il reste signé.
Zéro signifie égalité au coût de référence ; une valeur négative signifie que
la solution est meilleure que cette référence réalisable. Cela ne prouve pas
un optimum temporel. Sans preuve compatible, **Gap certifié : NON DISPONIBLE**.
Les valeurs Phonin non totalement certifiées compatibles ne sont pas utilisées
comme optima dans la CLI. Une référence manquante n'invalide pas une solution
réalisable : son coût reste affiché et son écart est indisponible.

Cette dernière situation est vérifiée explicitement :

```powershell
& $py -X utf8 scripts/test_instances.py --instance C101 --size 25 --seconds 5 --reference none --label commandes_terminal_runs_sans_reference
```

## 7. Réafficher sans relancer les algorithmes

```powershell
& $py -X utf8 scripts/test_instances.py --show-results commandes_terminal_runs_comparaison --show-routes
& $py -X utf8 scripts/test_instances.py --show-results --label commandes_terminal_runs_100 --gaps-only
```

Ces labels existent après la validation réalisée. Les noms exacts de tes futurs
lots sont affichés en fin d'exécution. Si tu relances un label déjà présent,
un suffixe `_2`, `_3`, etc. est ajouté : aucun ancien lot n'est écrasé.

## 8. Fichiers enregistrés

Chaque lot est dans `results/local/<label>/` :

- `RESULTATS.csv` : coûts, décomposition, référence, écarts, faisabilité,
  budget, CPU et temps réel ;
- `BILAN.json` : succès, échecs et temps du lot ;
- `SYNTHESE.txt` : classement lisible ;
- JSON par instance/taille/méthode/graine : tournées, arrivées, débuts et fins
  de service, retour, vérification et erreurs ;
- `protocol.json` et `source/` : configuration, données sélectionnées,
  empreintes et copie du code effectivement exécuté.

Les preuves de la validation des commandes sont copiées dans
`results/terminal_validation/` pour ne pas rester uniquement dans un dossier ignoré.

## 9. Budgets, garde-fou et parallélisme

ILS, recuit, hybride initial et PyVRP reçoivent un budget de recherche ; la
construction et préparation s'ajoutent. Le renforcé utilise un budget total
souple. Le constructeur seul s'arrête après ses tentatives, sans attendre
artificiellement la durée demandée. Un appel natif ne peut pas être préempté
proprement à chaque instruction ; son dépassement réel est affiché.

Les CPU et temps réel de résolution incluent la vérification finale mais
excluent chargement/préchauffage. Le **temps total processus**, affiché
séparément, comprend lancement, chargement, compilation éventuelle et sortie.
Le garde-fou `--max-seconds`, 120 par défaut, surveille CPU et temps réel du
processus entier. Il peut le terminer, auquel cas le résultat est `time_limit`
sans solution inventée. Le délai de surveillance/arrêt peut légèrement dépasser
la limite : ce n'est pas une garantie mathématique d'arrêt à l'instant exact.

Deux processus ont été testés avec :

```powershell
& $py -X utf8 scripts/test_instances.py --instances C101 C201 --size 25 --seconds 1 --workers 2 --label commandes_terminal_runs_parallele
```

Le parallélisme peut réduire le temps du lot, sans réduire la somme des CPU.
La limite de 120 s est appliquée par résolution, pas à la somme des processus.

## 10. Vérifier la gestion des échecs, volontairement

```powershell
& $py -X utf8 scripts/test_instances.py --instances R2_10_8 --method pyvrp --seconds .001 --label commandes_terminal_runs_echec
& $py -X utf8 scripts/test_instances.py --instances C101 --method ils --seconds .01 --max-seconds .05 --label commandes_terminal_runs_limite
```

Ces deux commandes ont effectivement retourné le code 1, attendu : respectivement
`not_found` avec PyVRP et `time_limit` avec le garde-fou. Les données n'ont pas
été rendues irréalisables. Les budgets volontairement minuscules servent à
tester la gestion des échecs, pas à juger la qualité des algorithmes.

Code 0 : toutes les solutions de la commande sont réalisables, même si leur
écart dépasse 6 %. Code 1 : au moins une résolution a échoué ou a été arrêtée.
Code 2 : arguments invalides. La faisabilité ne se confond pas avec le seuil de qualité.

## 11. Tests, validateur et notebook

```powershell
& $py -X utf8 -m pytest tests -q --junitxml=livraison/TESTS_SOUTENANCE.xml
& $py -X utf8 scripts/validate_soutenance.py
```

Résultats réellement obtenus pendant cette passe : **194 tests réussis,
2 modules optionnels ignorés**, puis validateur du projet réussi. Les aides de
`test_instances.py`, `run_benchmark.py`, `benchmark_final_static.py` et
`finalize_static.py` ont aussi été exécutées.

Pour refaire l'exécution du notebook et sa validation sans relancer les campagnes :

```powershell
& $py -X utf8 scripts/finalize_static.py --execute --validate
```

Cette procédure est celle déjà utilisée pour finaliser le livrable ; elle peut
prendre davantage de temps que la démonstration d'une petite instance.

## 12. Démonstration PowerShell

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/demo_terminal.ps1 -Python $py -Instance C101 -Size 25 -Seconds 5
```

La validation initiale de ce script utilisait le renforcé : trois véhicules,
durée 2623,5, faisabilité validée et horaires affichés. Le nouveau défaut est
`size_based` ; `-Method refined` permet de forcer l'ancien moteur.
Il utilise le Python fourni ou celui de `.venv`
dans le projet, puis le `python` du terminal en dernier recours. La politique
d'exécution est modifiée seulement pour le processus de cette commande.

## Résultats réels — campagne progressive

Les temps ci-dessous sont ceux de résolution, sans préchauffage. Les références
sont nommées dans les CSV : OR-Tools à 25/50, plans publics réévalués ensuite.
Cette vérification d'interface ne remplace pas une étude comparative exhaustive.

| instance   |    n |    duration | comparaison                                       |   wall_s |   cpu_s |
|:-----------|-----:|------------:|:--------------------------------------------------|---------:|--------:|
| C101       |   25 |   2623.5000 | Référence égalée — optimalité non démontrée       |   0.4448 |  0.3438 |
| C101       |   50 |   5036.5000 | 1.6428 %                                          |   0.4571 |  0.3594 |
| C101       |  100 |   9827.3000 | Référence égalée — optimalité non démontrée       |   0.5160 |  0.4531 |
| C1_2_1     |  200 |  20760.7000 | Référence dépassée — solution améliorante validée |   0.7871 |  0.7031 |
| C1_4_1     |  400 |  43162.9000 | Référence dépassée — solution améliorante validée |   1.1611 |  1.0469 |
| C1_6_1     |  600 |  68099.6000 | Référence dépassée — solution améliorante validée |   1.5808 |  1.5000 |
| C1_8_1     |  800 |  97862.2000 | 0.1618 %                                          |   2.3296 |  2.3438 |
| C1_10_1    | 1000 | 133890.9000 | 0.0656 %                                          |   3.2543 |  3.0469 |

Sur C1_10_6 à 1000 clients, budget demandé 30 s : durée **140502.9**,
écart au témoin réévalué **+5.0452 %**, temps réel
de résolution **3.452 s**, CPU **3.312 s**.
Le programme a fini avant son budget maximal ; il n'attend pas trente secondes
artificiellement. Cet écart ne constitue pas un gap à un optimum temporel prouvé.

## Résultats réels — comparaison C101/25

| method   |   duration | valid   |   vehicles |   wall_s | comparaison                                 |
|:---------|-----------:|:--------|-----------:|---------:|:--------------------------------------------|
| hybrid   |  2623.5000 | True    |          3 |   5.1052 | Référence égalée — optimalité non démontrée |
| ils      |  2623.5000 | True    |          3 |   5.0092 | Référence égalée — optimalité non démontrée |
| ortools  |  2623.5000 | True    |          3 |   5.7465 | Référence égalée — optimalité non démontrée |
| pyvrp    |  2623.5000 | True    |          3 |   5.4987 | Référence égalée — optimalité non démontrée |
| refined  |  2623.5000 | True    |          3 |   0.4192 | Référence égalée — optimalité non démontrée |
| sa       |  2623.5000 | True    |          3 |   5.0064 | Référence égalée — optimalité non démontrée |

Les six profils obtiennent ici la même durée réalisable. Les coûts égaux à la
référence expliquent les écarts nuls ; aucun certificat d'optimalité n'en est
déduit. Les temps et la réussite à ce cas ne permettent pas de classer les
méthodes sur toutes les familles et grandes tailles.

Erreurs corrigées : label auparavant obligatoire, tailles 25/50 indisponibles,
absence de sélection par famille et de comparaison multi-méthodes, affichage
incomplet et absence de garde-fou. La faisabilité et la disponibilité de la
référence sont désormais traitées séparément. Les erreurs de recherche restent
des résultats sauvegardés. L'ancien nom `duration_refined` est accepté.
