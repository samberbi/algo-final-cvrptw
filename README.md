# CVRPTW — Minimisation de la durée totale

**Version de remise — 13 novembre 2026.** L’objectif est la somme des durées des tournées : trajets + attentes + services, départs fixés à zéro et retour au dépôt compris. La capacité, les fenêtres et la flotte maximale restent strictes. Le temps de calcul du programme est une mesure séparée.

## Ouvrir le livrable

- **Remise actuelle : le notebook ci-dessous.** Les anciens Word/PDF/HTML ne sont pas synchronisés avec cette révision et ne constituent pas la remise actuelle.
- [Notebook exécuté](notebooks/Livrable_Final_CVRPTW.ipynb), [HTML](notebooks/Livrable_Final_CVRPTW.html), [Markdown illustré](LIVRABLE_FINAL.md).
- [Formulation mathématique](docs/MODELE_DUREE.md), [évolution de l’algorithme](docs/JOURNAL_EVOLUTION_ALGORITHME.md).
- [Tous les résultats en durée](livraison/RESULTATS_DUREE.html), [CSV des 646 essais](livraison/RESULTATS_DUREE.csv), [356 instances](livraison/INSTANCES_DUREE.csv), [statistiques descriptives](livraison/STATISTIQUES_DESCRIPTIVES_DUREE.csv).

## Résultats mesurés et références

Les sections **6.10 et 6.11** du livrable complètent l'analyse : [sensibilité contrôlée](docs/SENSIBILITE_CONTROLEE_DUREE.md), avec 90 profils sur six instances et trois graines, et [scénarios géographiques et contraintes](docs/ANALYSE_SCENARIOS_DUREE.md), sur les 356 instances de la campagne initiale. Les gains depuis la construction sont distingués des écarts aux plans témoins. Les départs mutualisés et les temps totaux recomposés de l'étude sont documentés ; ses résultats ne remplacent pas l'archive des meilleures solutions.


L'archive actuelle des meilleures solutions couvre **356 instances et 472 couples instance–graine**, tous réalisables et sous +6 % d'écart au plan témoin en durée ; le pire est à **+5,76 %**. Les budgets sont différents et identifiés : cette archive n'est pas une nouvelle campagne uniforme. Les index complets sont [COUVERTURE_472_ESSAIS.csv](results/time_objective/best_duration/COUVERTURE_472_ESSAIS.csv) et [COUVERTURE_356_INSTANCES.csv](results/time_objective/best_duration/COUVERTURE_356_INSTANCES.csv).

La campagne **initiale**, conservée pour la comparaison avant/après, couvre les **356 instances** Solomon et Gehring–Homberger de 100 à 1 000 clients. Elle contient **646 résolutions nouvelles et réalisables** : 472 pour la couverture et 180 pour la comparaison à vingt graines de trois méthodes sur trois cas, avec six essais communs aux deux périmètres. Chaque résolution dispose de dix secondes de recherche ; la construction et la préparation s’ajoutent au temps réel.

Sur le lot de couverture, le gain moyen par instance depuis la construction est **13,52 %**. L’écart moyen au plan témoin réévalué en durée est **−17,17 %**. Certains cas restent défavorables : le pire écart moyen d’instance au témoin atteint **+24,97 %** au budget étudié. Tous les cas restent publiés.

Les fichiers `.sol` fournis ont été sélectionnés pour la distance. Leurs tournées sont réévaluées en durée, mais leur optimalité temporelle n’est pas établie : **l’écart au témoin n’est pas un gap à une BKS temps**. Un écart négatif est possible. Le rapport distingue ce témoin d’une borne inférieure MST et des véritables optimums prouvés sur dix petits cas de contrôle. Aucun ancien pourcentage en distance n’est présenté comme une qualité en temps.

Les durées sont exprimées en unités de temps du benchmark (u.t.), les temps de calcul en secondes. Les services sont constants pour une instance ; leur décomposition avec les trajets et attentes accompagne les pourcentages.

## Installer et lancer

### Amélioration ciblée en durée

Le profil expérimental `duration_refined` ajoute plusieurs constructions, une intensification externe PyVRP et un partitionnement de tournées évalué en durée. Sur les **26 instances ciblées / 43 couples instance–graine**, tous les écarts finaux au plan témoin sont sous +6 %, avec un maximum de **+5,19 %**. Trois essais ont reçu une continuation HGS de trente secondes ; une phase supplémentaire de vingt secondes a concerné treize essais au-dessus de +4 %, dont dix ont progressé. Toutes les tentatives sont comptées, même sans gain : le calcul cumulé maximal des nouvelles recherches atteint environ 58 s, hors essai historique initial. La moyenne donnant le même poids à ces 26 instances vaut **+1,98 %** ; ce n'est pas une nouvelle moyenne indépendante sur les 356 instances.

Le détail avant/après, les contraintes vérifiées et les budgets sont dans [l'étude ciblée](docs/OPTIMISATION_DUREE_CIBLEE.md) et [le tableau des essais](results/time_objective/outliers10/AVANT_APRES_ESSAIS.csv). La campagne initiale et ses écarts restent conservés. Le profil court seul dépasse encore +6 % sur trois essais ; les continuations sont identifiées séparément.

```powershell
python cli.py C1_10_6 --method duration_refined --objective duration --seconds 10 --seed 4101
python scripts/optimize_duration_outliers.py --seconds 10 --tag nouveau_lot_cible
python scripts/continue_duration_outliers.py --source nouveau_lot_cible --tag nouvelles_continuations --seconds 30 --neighbors 80
```

La recherche ne reçoit jamais le plan témoin. Les scripts de campagne lisent celui-ci après la résolution pour calculer l'écart. Le profil reste expérimental : son évaluation indépendante sur tout le catalogue n'est pas encore faite. Les documents Word/PDF et le manifeste de la livraison précédente ne sont pas régénérés pendant cette révision ; les fichiers de travail actuels sont le Markdown et le notebook.

Le pire essai individuel est C1_10_6, graine 4102 : **+26,77 % au témoin**. Ce chiffre se distingue du pire écart moyen par instance. Les cas défavorables sont visibles dans le rapport et les fichiers complets.

Depuis ce dossier, avec Python 3.12 :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python cli.py C101 --method ils_hgs --seconds 10 --seed 4101
python -m streamlit run web/app.py
python scripts/analyze_duration.py
python scripts/validate_soutenance.py
python -m pytest tests -q --junitxml=livraison/TESTS_SOUTENANCE.xml
```

La CLI et l’API publique `algo.solver` minimisent la durée par défaut. `--method ils`, `sa` et `ils_hgs` permettent de comparer notre ILS, notre recuit et l’hybride. Notre code construit et améliore les tournées ; le **HGS externe appartient à PyVRP 0.12.2** et reste attribué à ses auteurs. Le profil hybride utilise cinq secondes d’ILS puis cinq secondes de HGS à ce budget. Les références sont consultées après résolution et ne sont pas transmises au moteur.

Le notebook recalcule les contrôles, exemples et statistiques à partir des fichiers fournis ; il ne relance pas les 646 résolutions. Pour l’exécuter dans VS Code, sélectionner l’interpréteur `.venv`. Une nouvelle campagne complète est possible avec `scripts/benchmark_duration.py --label nouveau_lot`, sans écraser les mesures existantes.

## Vérification et limites

Le reçu courant est [VALIDATION_SOUTENANCE.json](livraison/VALIDATION_SOUTENANCE.json), complété par `livraison/TESTS_SOUTENANCE.xml`. `VALIDATION_DUREE.json` et `MANIFESTE_SHA256.json` appartiennent à l’édition antérieure. Les données `.vrp/.sol`, les solutions, graines, durées, erreurs éventuelles, protocoles et sources effectivement exécutées sont conservés dans `data/` et `results/time_objective/`.

Les tests comprennent aussi des contrôles explicites des routines historiques de distance ; cela ne les transforme pas en benchmarks temporels. Les solutions anciennes utilisées uniquement comme fixtures vérifient couverture, capacité et horaires. Les anciennes campagnes et leurs documents ne font pas partie de cette remise en durée.

Le trafic dépendant de l’heure et les tailles supérieures à 1 000 clients ne sont pas démontrés. La couverture globale possède une ou deux graines selon la taille ; vingt répétitions sont réservées aux trois cas de stabilité. Une corrélation n’établit pas une causalité, et les histogrammes ne prouvent pas automatiquement une loi normale. Node.js est utilisé par un test de lecture de la simulation ; son absence est signalée comme test ignoré.

## Version de soutenance : tests sur le portable

Les commandes courtes sont dans [TESTER_SUR_PORTABLE.md](docs/TESTER_SUR_PORTABLE.md) et à la fin du notebook : deux cas C1/C2, deux R1/R2, deux RC1/RC2 ou deux cas à 1 000 clients. Une graine et cinq secondes par résolution. Le reçu courant est `livraison/VALIDATION_SOUTENANCE.json`. La section CPU reste informative : la qualité des solutions prime, avec un objectif sous +6 % au témoin en durée et sous 120 secondes CPU par instance difficile. Ces deux critères sont à mesurer séparément. Les tests de cinq secondes ne sont pas le profil de meilleure qualité.

## Extension temporelle Dabia2013


Le [pilote Dabia2013](docs/EXTENSION_DABIA2013.md), section **6.13 du notebook**,
compare le même objectif `Duration` des deux côtés : trajets, attentes, services,
avec départs optimisés et trajets dépendant de l'heure. C'est un nouveau profil,
distinct du modèle statique à départs nuls décrit plus haut. Les coûts natifs des
deux benchmarks ne sont pas mélangés.

Six instances à **25 clients**, trois graines, cinq secondes par résolution :
**18/18 solutions réalisables et au coût des BKS**, gap moyen/maximal 0 %, CPU
maximal mesuré 5,031 s. Six essais préliminaires sont également conservés. Les
références C101, R201 et RC201 signalent une recertification en attente après
changement d'arithmétique ; le rapport ne revendique pas de nouvelle preuve
d'optimalité. Aucune mesure Dabia à 50/100 clients ou à 1 000 clients n'est annoncée.

**Contribution :** notre insertion séquentielle, ILS, relocate/swap/2-opt/2-opt*,
cache et orchestration ; évaluation des départs optimaux et contrôle fournis
par le moteur externe **MAMUT-routing-lib 0.12.0**. Le HGS statique PyVRP n'est
pas utilisé pour ce pilote.

```powershell
py -3.12 -m venv .venv_dabia
.\.venv_dabia\Scripts\python.exe -m pip install -r requirements-dabia.txt
.\.venv_dabia\Scripts\python.exe -m pytest tests/test_dabia.py -q
.\.venv_dabia\Scripts\python.exe scripts/validate_dabia.py
.\.venv_dabia\Scripts\python.exe scripts/benchmark_dabia.py --instances R201 --seconds 5 --label essai_dabia_R201
```

Le dernier appel résout une seule instance et affiche le gap BKS Duration dans
le terminal. Les relances créent automatiquement un nouveau dossier numéroté.
Pour les six familles : omettre `--instances R201`. Les fichiers sont écrits dans
`results/dabia2013/<label>/`. La validation des résultats fournis est
`results/dabia2013/VALIDATION.json` ; le XML des **16 tests TD réussis** est
`results/dabia2013/tests.xml`. Dans l'environnement historique sans MAMUT,
la suite statique conserve **171 tests réussis** ; le module TD y est explicitement
ignoré et doit être vérifié dans son environnement séparé.
