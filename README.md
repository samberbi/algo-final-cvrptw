# CVRPTW — Minimisation de la durée totale

## Comparaison automatique : ILS initial et profil renforcé

Les commandes sans méthode explicite exécutent désormais `ils` **et**
`size_based` : deux résolutions par instance/graine, avec tableau de durées,
écarts au témoin et temps, puis gain signé entre méthodes. Les égalités,
régressions et échecs sont conservés. Pour un seul moteur : `--method size_based`.
Utiliser directement `.\.venv\Scripts\python.exe`, même si `.venv_dabia` est actif.
Voir [COMPARAISON_INITIAL_RENFORCE.md](docs/COMPARAISON_INITIAL_RENFORCE.md).
## Configuration actuelle des commandes : sélection par taille

Le profil renforcé `size_based` est en version 2 : construction regret-2,
recherche locale **PyVRP externe** puis notre ILS jusqu’à 100 clients ; profil
renforcé puis HGS externe selon le temps restant au-delà. La meilleure durée
est conservée à chaque étape.
Le moteur et les temps mesurés sont affichés et enregistrés. Le choix ne lit
aucun gap. La campagne de 72 essais et ses limites sont documentées dans
[SELECTION_PAR_TAILLE.md](docs/SELECTION_PAR_TAILLE.md).
Pour lancer la construction seule comme ablation : `--method construction`.
Pour forcer le renforcé : `--method refined`. Les anciens résultats restent
conservés et ne représentent pas la nouvelle configuration.
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

Le modèle principal suit les trajets fixes et symétriques confirmés par le professeur ; les tailles supérieures à 1 000 clients ne sont pas démontrées. La couverture globale possède une ou deux graines selon la taille ; vingt répétitions sont réservées aux trois cas de stabilité. Une corrélation n’établit pas une causalité, et les histogrammes ne prouvent pas automatiquement une loi normale. Node.js est utilisé par un test de lecture de la simulation ; son absence est signalée comme test ignoré.

## Version de soutenance : tests sur le portable

Les commandes courtes sont dans [TESTER_SUR_PORTABLE.md](docs/TESTER_SUR_PORTABLE.md) et à la fin du notebook : deux cas C1/C2, deux R1/R2, deux RC1/RC2 ou deux cas à 1 000 clients. Une graine et cinq secondes par résolution. Le reçu courant est `livraison/VALIDATION_SOUTENANCE.json`. La section CPU reste informative : la qualité des solutions prime, avec un objectif sous +6 % au témoin en durée et sous 120 secondes CPU par instance difficile. Ces deux critères sont à mesurer séparément. Les tests de cinq secondes ne sont pas le profil de meilleure qualité.

## Exploration hors périmètre

Les expériences TD sont archivées dans [EXPLORATION_TD_HORS_PERIMETRE.md](docs/EXPLORATION_TD_HORS_PERIMETRE.md). Elles ne valident pas le modèle principal à trajets fixes, symétriques et départs nuls.

## Présentation des comparaisons

Le notebook et son HTML de lecture utilisent des statuts pour les références
dépassées ou égalées, et des moyennes/médianes strictement positives conditionnelles
avec leurs effectifs. Les petites preuves exactes sont marquées « Optimum atteint ».
Les données signées sont conservées dans [AUDIT_GAPS_FINAL.md](AUDIT_GAPS_FINAL.md)
et `results/presentation_status/`. La vue publiée est
`results/presentation_status/TABLEAU_PRESENTATION.csv` ; aucun coût ni algorithme
n'a été dégradé pour changer un pourcentage. La validation dédiée se lance avec
`python scripts/validate_gap_presentation.py`.

## Commandes terminal vérifiées

La fiche [COMMANDES_TERMINAL.md](COMMANDES_TERMINAL.md) donne les commandes
PowerShell, le Python exact, les six familles, les tailles 25–1000, neuf profils,
les comparaisons, les tournées, les gaps et la relecture sans calcul. Les preuves
sont dans `results/terminal_validation/`. Le script `scripts/demo_terminal.ps1`
prépare une démonstration courte. Aucun lancement implicite des 356 instances.

## Finalisation statique du 13 novembre

Le livrable actuel est `notebooks/Livrable_Final_CVRPTW.ipynb`. Les nouvelles
comparaisons et leurs limites sont dans [RAPPORT_PILOTES_STATIQUES.md](docs/RAPPORT_PILOTES_STATIQUES.md).
Le bilan de conformité est [BILAN_CONFORMITE_FINAL.md](docs/BILAN_CONFORMITE_FINAL.md),
la progression et les commandes de reprise dans [PROGRESSION.md](PROGRESSION.md).
Pour le comparateur indépendant : `python -m pip install -r requirements-reference-final.txt`.

```powershell
python scripts/benchmark_final_static.py --cases C101:25 R101:25 RC201:25 --methods ils refined ortools --seconds 3 --reference-seconds 6 --label demonstration_statique
python scripts/report_final_static.py --label demonstration_statique
python -m pytest tests -q --junitxml=livraison/TESTS_SOUTENANCE.xml
python scripts/validate_final_static.py
python scripts/finalize_static.py --execute --validate
```

L'installation et le préchauffage initial précèdent les temps affichés. Une
commande interrompue reprend les JSON existants avec le même protocole et les
mêmes sources ; si le code change, choisir un nouveau label. Aucun lancement
automatique des 356 instances. Les anciens exports PDF/Word ne constituent
pas la remise de cette révision. Le reçu dédié est `livraison/VALIDATION_FINALE_STATIQUE.json`.
