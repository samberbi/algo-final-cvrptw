# Progression — finalisation CVRPTW CESI

Date de référence : 13 novembre 2026 (Europe/Paris).
Quota restant : non accessible. Les résultats et commandes sont sauvegardés ici.

## Consigne prioritaire et périmètre

La mission finale confirme : trajets **fixes et symétriques**, départs à zéro,
objectif **somme des durées complètes**, avec attentes, services et retours.
Les expériences Dabia2013/Lera2026 ont des trajets variables et des départs
optimisés : elles sont **exploratoires et hors modèle principal**, même si leurs
coûts ont été vérifiés. Elles ne constituent pas une preuve de conformité CESI.

## État actuel après validation finale

| Étape | État | Preuve |
|---|---|---|
| Audit | Terminé dans le périmètre statique confirmé | Cahier transmis, bilan de conformité, sauvegardes Git |
| Compatibilité | Vérifiée avec réserves explicites | Phonin non certifié directement ; cinq contrôles numériques, OR-Tools indépendant |
| Corrections | Effectuées | Modèle statique, provenance, comparateurs, variante ILS testée séparément |
| Tests | Réussis | 182 réussites, deux modules optionnels ignorés |
| Notebook | Corrigé et réexécuté | 16 cellules, zéro erreur, dernier passage 33,99 s |
| Benchmarks progressifs | Terminés pour les trois lots pilotes | 119 résolutions, 117 faisables, deux échecs conservés ; tailles 25 à 1000 |
| Statistiques et figures | Produites | CSV complets, statistiques par lot, PNG/SVG et explications |
| Validation finale | Réussie dans le périmètre documenté | VALIDATION_FINALE_STATIQUE.json, données et sources figées contrôlées |

**Ce qui n'est pas démontré :** un gap à un optimum temporel inférieur à 6 %
sur tous les cas, une nouvelle campagne uniforme sur les 356 instances ou une
supériorité générale de la variante ILS. Le comparateur indépendant est parfois
plus faible que notre méthode ; les écarts négatifs restent visibles. Aucun
résultat n'a été plafonné, renommé en preuve d'optimalité ou supprimé.

Le notebook canonique est `notebooks/Livrable_Final_CVRPTW.ipynb`. La copie de
lecture avec figures intégrées est
`C:/Users/user/Downloads/Livrable_Final_CVRPTW_A_ENVOYER.ipynb` (environ 2,93 Mo).
Son exécution exige le projet complet ; elle ne remplace pas le dépôt.

## État sauvegardé avant la révision finale

- Code statique : ILS, recuit, hybride PyVRP 0.12.2, constructions renforcées,
  réservoir et partitionnement HiGHS ; contrôleur indépendant.
- Campagne statique historique : 646 résolutions sur 356 instances ; 472 lignes
  de couverture dans l'archive. Références distance réévaluées en durée : ne pas
  qualifier leurs écarts d'optimalité temporelle.
- Tests statiques récents : **171 réussis**, module optionnel TD ignoré dans cet
  environnement. XML : `results/local/verification_apres_dabia/tests.xml`.
- Audit statique indépendant : 356 témoins, 964 enregistrements contrôlés,
  712 empreintes de fichiers, aucune anomalie détectée dans ce périmètre.
- Exploration TD : 24 résolutions à 25 clients ; 18 dans le lot à trois graines,
  toutes réalisables et au coût des BKS Duration ; 16 tests spécifiques réussis.
- Montée en taille TD (hors modèle principal) : 12 résolutions à 50/100 clients,
  puis 30 résolutions Lera à 200–1000 ; toutes sauvegardées dans
  `results/temporal_sizes/`. Le dernier lot comporte **28 succès et 2 échecs** ;
  plusieurs écarts dépassent 6 %. Aucun résultat n'est supprimé.
- Chargement IGP paresseux : 8 tests réussis, comparaison bit à bit avec le
  matérialiseur complet sur des arcs d'une instance à 200 clients.

## État de démarrage des étapes (historique)

| Étape | État | Livrable / prochaine action |
|---|---|---|
| A — Audit et sauvegarde | En cours | Sauvegarde Git, lecture consignes, inventaire ciblé |
| B — Compatibilité des références | À vérifier | Lire Phonin 2025, vérifier retour/départ/services/précision |
| C — Corrections modèle/code | En attente B | Recentrer le notebook sur le modèle statique confirmé |
| D — Tests de validité | Socle existant validé | Ajouter les contrôles ciblés des références et du solveur indépendant |
| E — Notebook prioritaire | À corriger | Isoler les expériences TD hors périmètre, conserver les preuves |
| F — Pilotes statiques | À lancer après B | Petits cas 25/50, budgets documentés, référence indépendante |
| G — Statistiques / figures | Résultats historiques disponibles | Générer la synthèse du nouveau pilote sans mélange de conventions |
| H — Validation finale | À faire | Exécution du notebook complet et commandes reproductibles |

## Reprise

Dossier : `C:\Users\user\Downloads\CVRPTW_REMISE_PROF_20261112T203928`.

```powershell
& "C:\Users\user\OneDrive - Association Cesi Viacesi mail\Bureau\PROJET ALGO\.venv\Scripts\python.exe" -m pytest tests -q --junitxml=results/local/finalisation/tests.xml
```

Ne pas relancer les grandes campagnes TD : incompatibles avec les hypothèses
prioritaires. Prochaine action : compatibilité Phonin 2025, puis pilote statique.

## Journal des décisions

- Première sauvegarde : captures toutes les modifications et mesures existantes,
  sans push GitHub, PDF ou Word. Les décisions finales restent fondées sur les
  dernières consignes professorales fournies.
- Ne jamais transformer, plafonner ou prendre la valeur absolue d'un écart pour
  satisfaire le seuil. Les statuts optimum/BKS/témoin/borne restent distincts.

## Bilan A–B et corrections prioritaires

- Sauvegarde initiale : commit `51adb56` ; résultats antérieurs préservés.
- Compatibilité : `docs/COMPATIBILITE_REFERENCES_STATIQUES.md` ; six comparaisons
  numériques dans `results/final_static/reference_audit/PHONIN_VERIFICATION.csv`.
  Cinq nouvelles résolutions OR-Tools à 25 clients, trois secondes chacune ;
  C101/100 est seulement réévalué, sans nouveau run.
- Phonin : retour explicite dans l'équation (9), mais précision, intégralité
  temporelle et preuves détaillées non suffisamment établies pour annoncer
  un gap d'optimalité compatible. Concordance numérique ne vaut pas certification.
- Sous-instances 25/50 : 16 préfixes standards, manifeste parent/SHA ; archives
  originales bloquées HTTP 403, aucune prétention de téléchargement réussi.
- Comparateur OR-Tools indépendant : coût somme des spans Time, départs nuls,
  coûts d'arcs nuls ; attentes, services et retours vérifiés dans le coût natif.
- **5 tests ciblés réussis** : `results/final_static/tests_contract.xml`.
- Notebook et Markdown recentrés sur le modèle statique ; complexité placée
  avant les équations. Exploration TD conservée dans
  `docs/EXPLORATION_TD_HORS_PERIMETRE.md`, exclue des exigences du validateur.
- Correction de provenance : le validateur historique n'ajoute plus du code
  nouveau aux sources figées d'une campagne passée.
- Prochaine étape : pilote contrôlé, puis tests globaux et exécution complète
  du notebook. Aucun lancement de 356 instances ou push automatique.

## Pilote de validation et nouveau candidat

- Pilote `results/final_static/pilote25/` : **24/24 résolutions réalisables**,
  trois instances (C101, R101, RC201 à 25 clients), huit méthodes, graine 4101.
  Référence OR-Tools indépendante à 6 s, recherches à 2 s (budgets et temps
  totaux distincts). Les constructions C101 et RC201 dépassent 6 % ; aucune
  transformation du pourcentage. Les méthodes optimisées vont ici de 0 à 0,912 %.
- Ce premier pilote a partiellement chevauché les tests automatisés : ses temps
  ne servent pas à conclure sur une accélération. Le prochain lot sera séquentiel
  sans autre campagne CPU lancée par nous en parallèle.
- Ablation explicite du partitionnement : `algo/refined_ablation.py`, mêmes
  constructions/voisinages, gain du MILP mesuré sur le même réservoir. Sur les
  trois cas du pilote, aucun gain de coût attribuable au partitionnement.
- PyVRP seul démarre de sa population native : aucune solution ILS injectée.
  Module : `algo/pyvrp_standalone_duration.py`. HGS reste un moteur externe.
- Hypothèse testable : le renforcé termine parfois après quelques centièmes de
  seconde. `algo/refined_with_ils.py` réserve et utilise le budget restant pour
  notre ILS ; variante expérimentale, pas nouveau profil par défaut.
- Tests : **176 réussis, 2 optionnels ignorés** dans la suite complète avant
  les nouveaux contrôles. Puis **26 ciblés réussis** après ajout des contrats
  PyVRP/ablation. Un test nouveau attendait à tort zéro attente sur le jouet :
  corrigé à 1 u.t. (10 unités internes) ; XML du premier échec conservé.
- Sous-processus du test CLI : encodage UTF-8 explicite pour supprimer une
  erreur de décodage Windows qui n'était pas un échec du solveur.
- Reprise du pilote : même commande avec le même label, JSON existants conservés.
  Un changement de code/protocole impose un nouveau label ; snapshots sauvegardés.

## Couverture progressive — résultats et décision

- Lot `couverture_progressive` terminé : **63 résolutions**, sept instances de
  50, 100, 200, 400, 600, 800 et 1000 clients, neuf méthodes, une graine.
  **61 faisables / 2 sans solution trouvée** (PyVRP seul à 600 et 1000 en 3 s).
- Références OR-Tools indépendantes : sept solutions faisables à 10 s. Leur
  qualité reste limitée : certains écarts sont négatifs ; aucune preuve d'optimum.
- Durée CPU maximale observée 10,016 s ; temps écoulé maximal 10,076 s.
  Les préparations et constructions sont mesurées, sans les confondre avec
  les trois secondes de recherche. Pas de garantie universelle sous 120 s.
- Première variante ILS : améliore R202 de 2913,1 à 2831,0 mais dégrade le
  résultat à 600/800/1000, car la moitié réservée coupe des constructions et
  voisinages utiles. **Elle n'est pas retenue par défaut.** Sources et résultats
  de ce premier essai conservés dans le lot, sans réécriture.
- Correction candidate v2 : conserver le planning complet du profil renforcé,
  n'utiliser en ILS que le temps réellement restant. Nouvelle confirmation
  séparée, deux graines, quatre cas ; pas de modification des anciennes mesures.
- L'analyse du cahier des charges transmis est conservée dans
  `docs/CAHIER_DES_CHARGES_TRANSMIS.md` et `docs/BILAN_CONFORMITE_FINAL.md`.
- Commande de reprise / confirmation (même interpréteur que ci-dessus) :
  `python scripts/benchmark_final_static.py --cases R101:25 R202:100 RC2_6_1:600 R2_10_8:1000 --seeds 4101 4102 --methods ils refined refined_ils ortools --seconds 3 --reference-seconds 10 --label confirmation_ils_v2`

## Finalisation G–H — sauvegarde du livrable exécutable

- Campagnes terminées : 24 + 63 + 32 = **119 résolutions pilotes**, **117 faisables**
  et deux recherches sans solution (conservées). Cinq autres résolutions à 25
  clients vérifient les références Phonin ; une réévaluation C101/100 n'est pas
  un nouveau run. Les 646 anciennes résolutions restent distinctes.
- Confirmation v2 : huit paires renforcé / renforcé+ILS sur quatre instances,
  deux graines. Coûts améliorés sur R101/R202, inchangés à 600/1000 dans ces
  essais. R202/4101 : 2913,1 -> 2779,9 ; écart au comparateur OR-Tools du lot
  +6,633 % -> +1,757 %. Pas de généralisation à un optimum inconnu.
- Premier candidat v1 : régressions explicites à grande taille ; conservé comme
  résultat de développement. Le moteur de production n'a pas été remplacé.
- Suite complète actuelle : **182 réussis, 2 modules optionnels ignorés**,
  `livraison/TESTS_SOUTENANCE.xml`. Avertissements PyVRP sur les jouets TSP et
  dépréciations SWIG ; l'erreur de décodage Windows a disparu.
- `pip check` : aucune dépendance cassée dans l'interpréteur utilisé.
- Notebook exécuté intégralement : **16 cellules, zéro erreur, 45,22 s** lors
  du premier passage de finalisation ; reçu `results/final_static/NOTEBOOK_EXECUTION.json`.
- Validation statique réussie : 712 fichiers historiques + 16 sous-instances
  vérifiés, 119 nouveaux enregistrements, dix preuves exactes indépendantes,
  références et CSV recalculés, contrôles du notebook et de ses figures.
- MILP C101/25, budget 10 s : **time_limit**, 10,55 s mesurées, incumbent 8297,9,
  borne 1020,6, gap HiGHS 87,70 %. Ni optimum annoncé ni référence de qualité ;
  les fichiers et ce résultat défavorable sont conservés.
- Trois figures nouvelles PNG/SVG haute résolution dans
  `livraison/figures_final_static/`, avec explications sous les schémas.
- Réexécution finale prévue après deux corrections de présentation : mention
  explicite de l'échec dans les cellules manquantes et explication du MILP limité.

### Commande exacte pour reprendre la finalisation sans relancer les campagnes

Dans `C:\Users\user\Downloads\CVRPTW_REMISE_PROF_20261112T203928` :

```powershell
& "C:\Users\user\OneDrive - Association Cesi Viacesi mail\Bureau\PROJET ALGO\.venv\Scripts\python.exe" -X utf8 scripts/finalize_static.py --execute --validate
```

Cette commande recalcule les statistiques/figures des fichiers déjà sauvés,
met à jour le notebook, exécute ses cellules et valide. Aucun nouveau benchmark,
push, PDF, Word ou ZIP. Pour les tests, la commande pytest du début reste valable.


## Clôture de cette passe

- Dernière exécution intégrale : 33,99 s, seize cellules, zéro erreur.
- Validation historique également réussie : 646 solutions initiales, archive
  472 lignes sur 356 instances, sensibilité contrôlée et étude CPU conservées.
- Le validateur CPU avait le même défaut de provenance que celui de l'ancienne
  optimisation : ajout automatique des nouveaux modules aux anciennes sources.
  Il vérifie désormais uniquement les fichiers figés. Les sept copies ajoutées
  par cette validation ont été retirées, sans supprimer de résultat historique.
  Nouvelle vérification CPU réussie ; sources avant/après et coûts inchangés.
- Les cinq contrôles numériques Phonin ont aussi été réévalués depuis leurs
  tournées pendant la dernière validation, sans nouvelle recherche.
- Aucun nouvel export PDF/Word/ZIP ou push GitHub. Commits locaux conservés.
- Quota Codex : toujours inaccessible. Toute reprise doit partir des fichiers
  et de la commande `scripts/finalize_static.py --execute --validate` ci-dessus.
- Prochaine extension scientifique éventuelle : renforcer les références
  indépendantes sur un petit lot difficile et augmenter les répétitions, avant
  toute campagne exhaustive. Aucune mesure future n'est incluse dans les tableaux.

## Mission commandes terminal — nouvelle passe

- Interface commune `scripts/run_benchmark.py`, également appelée par
  `scripts/test_instances.py`. Les fonctions historiques utilisées par les
  reprises CPU sont conservées. Aucun algorithme de résolution modifié.
- Sélection 25/50/100/200/400/600/800/1000, familles, plusieurs méthodes, labels
  automatiques, relecture, tournées et horaires, classement selon durée faisable.
- Références lues après résolution : plan public réévalué ou OR-Tools figé
  indépendant ; gap certifié indisponible en l'absence de preuve compatible.
- Processus isolés avec surveillance du CPU et du temps réel ; limite par
  défaut 120 secondes, initialisation comprise. Arrêt surveillé, pas promesse
  d'une borne mathématique stricte sur l'instant de terminaison.
- Premier essai réellement exécuté C101/25 : durée 2623,5, trois véhicules,
  faisable, affichage de la décomposition et des horaires dans le terminal.
- Douze tests ciblés de l'interface réussis. Suite complète et validateur du
  projet en cours via `scripts/validate_terminal_commands.py --phase checks`.
- Les preuves des commandes seront dans `results/terminal_validation/` ; aucun
  lancement automatique des 356 instances et aucun écrasement d'un ancien lot.
