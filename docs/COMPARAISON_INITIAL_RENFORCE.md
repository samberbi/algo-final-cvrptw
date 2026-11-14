## Comparaison automatique : ILS initial et profil renforcé

**Python à utiliser.** Depuis la racine du projet, appeler directement
`.\.venv\Scripts\python.exe` pour le solveur statique. L'activation de
`.venv_dabia` ne fournit pas ses dépendances : cet environnement appartient
à l'extension optionnelle. Le script vérifie maintenant les bibliothèques
nécessaires avant toute résolution et donne une erreur explicite si le
Python choisi est incomplet, sans créer une campagne vide.

Préparation unique sur un nouvel ordinateur :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-reference-final.txt
.\.venv\Scripts\python.exe -m pip check
```

Les commandes ci-dessous utilisent ce Python directement : elles fonctionnent
même si le terminal affiche encore `(.venv_dabia)` et ne nécessitent pas de
changer la politique d'exécution PowerShell.

Sans `--method` ou `--methods`, chaque commande exécute maintenant **deux
résolutions par instance et par graine** : notre `ils` autonome, puis le profil
hybride `size_based`. Le renforcé utilise la recherche locale externe PyVRP
et, sur les grands cas selon le temps restant, son HGS. Ces contributions sont
attribuées à la bibliothèque. L'initial n'est pas une construction seule.

Le terminal affiche pour chaque moteur la durée complète, la faisabilité,
la flotte, la référence et l'écart compatible, le temps réel, le CPU et le
budget demandé. Un second tableau donne le gain entre méthodes :

`gain = 100 × (durée ILS initial − durée renforcée) / durée ILS initial`.

Dans un lot, le comparatif est affiché **après chaque instance et chaque graine**,
dès que toutes les méthodes demandées sont terminées pour ce cas. Le bilan
global reprend ensuite tous les cas. Cette règle fonctionne aussi avec plusieurs
processus, sans mélanger les instances, tailles ou graines.

Ce gain n'est pas le gap au plan témoin. Une valeur positive signifie que le
renforcé améliore l'ILS ; une égalité ou une régression reste explicitement
affichée. Un échec interdit de chiffrer le gain. Nous ne sélectionnons pas une
mauvaise exécution de l'initial pour rendre le renforcé artificiellement meilleur.

**Budgets :** `--seconds` s'applique séparément à chaque moteur. Pour l'ILS,
la construction s'ajoute au budget de recherche ; le renforcé utilise un
budget total souple. Le même paramètre ne constitue donc pas un temps total
strictement égal. Les temps réellement mesurés sont affichés pour juger le
compromis qualité/coût. Le garde-fou de 120 secondes concerne chaque processus,
pas la somme des deux méthodes. Par défaut, les exécutions sont séquentielles.

```powershell
.\.venv\Scripts\python.exe scripts/test_instances.py --instances RC101 --methods ils size_based --seconds 5 --label comparaison_RC1
.\.venv\Scripts\python.exe scripts/test_instances.py --instances C101 C201 --methods ils size_based --seconds 5 --label comparaison_C
.\.venv\Scripts\python.exe scripts/test_instances.py --instances R101 R201 --methods ils size_based --seconds 5 --label comparaison_R
.\.venv\Scripts\python.exe scripts/test_instances.py --instances RC101 RC201 --methods ils size_based --seconds 5 --label comparaison_RC
.\.venv\Scripts\python.exe scripts/test_instances.py --instances C2_10_7 --methods ils size_based --seconds 60 --label comparaison_1000
```

**Lots de test :** chaque ligne suivante compare les deux méthodes pour toutes
les instances sélectionnées. Une graine est utilisée par défaut (4101).

```powershell
# Un cas de chacune des six familles : six instances, douze résolutions.
.\.venv\Scripts\python.exe scripts/test_instances.py --instances C101 C201 R101 R201 RC101 RC201 --seconds 5 --label comparaison_six_familles

# Toutes les 56 Solomon à 100 clients : 112 résolutions.
.\.venv\Scripts\python.exe scripts/test_instances.py --all --sizes 100 --seconds 5 --label comparaison_solomon_complete

# Toutes les 60 instances à 1000 clients : 120 résolutions, campagne longue.
.\.venv\Scripts\python.exe scripts/test_instances.py --all --sizes 1000 --seconds 30 --label comparaison_1000_complete

# Vérifier la sélection et le nombre de résolutions sans lancer de calcul.
.\.venv\Scripts\python.exe scripts/test_instances.py --all --sizes 100 1000 --seconds 5 --dry-run
```

Pour avancer famille par famille, ajouter `--families C1`, `C2`, `R1`, `R2`,
`RC1` ou `RC2` à une commande avec `--all --sizes 100` ou `1000`.
Les campagnes complètes ci-dessus sont des commandes proposées, pas des
comparaisons exhaustives déjà exécutées. Deux moteurs doublent le nombre
de résolutions. Avec un processus, les 60 grands cas peuvent demander
environ une heure à trente secondes par moteur, plus construction et préparation.

Le couple `--methods ils size_based` est explicite ici, mais il est désormais
le défaut lorsqu'aucune méthode n'est donnée. Pour une seule résolution,
utiliser `--method size_based` ou `--method ils`. Les labels déjà utilisés
reçoivent automatiquement un suffixe, sans écraser les résultats antérieurs.

Les fichiers `RESULTATS.csv`, `SYNTHESE.txt` et
`COMPARAISON_INITIAL_RENFORCE.csv` sont sauvegardés dans le dossier annoncé.
`--show-results <label>` réaffiche aussi le comparatif, sans relancer les moteurs.

**Graphiques automatiques.** Après les résolutions, chaque instance et graine
reçoit une figure de convergence et des cartes des tournées finales. Pour le
couple standard, les cartes représentent l'ILS initial et le renforcé hybride,
avec durée complète, flotte et dépôt. Les courbes montrent les meilleurs coûts
et les coûts courants effectivement archivés ; aucune température ni progression
manquante n'est inventée. Une page `GRAPHIQUES.html` s'ouvre dans le navigateur
et regroupe les figures PNG du sous-dossier `figures`, avec les tableaux de coûts.
Ces cartes n'affichent pas de trafic réel : ce sont les arcs entre coordonnées
des benchmarks, et la validité horaire reste vérifiée par le contrôleur.

La génération intervient après le lot pour garder son coût séparé des budgets
des solveurs. Son temps est conservé dans `GRAPHIQUES.json`. Ajouter
`--no-open-plots` pour enregistrer sans ouvrir le navigateur, ou `--no-plots`
pour une campagne sans rendu. Les résultats d'échec restent visibles.

Pour dessiner un ancien lot à partir de ses JSON, sans nouvelle résolution :

```powershell
.\.venv\Scripts\python.exe scripts/plot_terminal_results.py --label comparaison_100 --open
```

**Essai de vérification réellement exécuté :** RC101, C204 et R109 à 100
clients, graine 4101, cinq secondes demandées par moteur, un processus.
Les six solutions et leurs références ont été recalculées indépendamment.
Un contrôle complémentaire de C2_10_7 à 1000 clients utilise trente secondes
par moteur, avec la même graine et le même ordre d'exécution séquentiel.

| instance   |    n |   initial_requested_s |   initial_duration |   reinforced_duration |   duration_gain_pct |   initial_wall_s |   reinforced_wall_s |   initial_cpu_s |   reinforced_cpu_s | conclusion           |
|:-----------|-----:|----------------------:|-------------------:|----------------------:|--------------------:|-----------------:|--------------------:|----------------:|-------------------:|:---------------------|
| C204       |  100 |                5.0000 |          9793.6000 |             9738.3000 |              0.5647 |           5.0316 |              5.0013 |          5.0312 |             4.9688 | Renforcé meilleur    |
| C2_10_7    | 1000 |               30.0000 |        124703.9000 |           112338.0000 |              9.9162 |          33.3713 |             29.5966 |         33.3594 |            29.4531 | Renforcé meilleur    |
| R109       |  100 |                5.0000 |          2394.6000 |             2420.7000 |             -1.0900 |           5.0274 |              5.0014 |          5.0156 |             4.8906 | ILS initial meilleur |
| RC101      |  100 |                5.0000 |          2917.7000 |             2921.1000 |             -0.1165 |           5.0299 |              5.0015 |          5.0312 |             4.8750 | ILS initial meilleur |

Les résultats de ces cas restent un contrôle de fonctionnement des
commandes. Ils ne constituent pas une nouvelle preuve statistique de supériorité
universelle. Les tournées et sources sont dans
`results/terminal_comparison/`.


**Correction de l'environnement vérifiée.** L'environnement local `.venv`
a été installé et `pip check` ne signale aucune dépendance incohérente.
Le lot C101, C201, R101, R201, RC101 et RC201 a été réellement exécuté avec
ce Python, graine 4101, cinq secondes demandées par moteur : douze solutions
réalisables et six comparatifs immédiats affichés. Les tournées, références,
formules et empreintes de sources ont été contrôlées indépendamment.
Cette vérification des six familles ne représente pas une campagne exhaustive
sur les 116 instances. Les preuves sont dans
`results/terminal_comparison/verification_env_six_familles/` et
`results/terminal_comparison/VALIDATION_ENV_STATIQUE.json`.
