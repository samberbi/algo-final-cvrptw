# Progression — finalisation CVRPTW CESI

## 14 novembre 2026 — lots comparatifs et correction de l'environnement Python

- Comparatif immédiat après chaque instance/taille/graine dès que toutes les
  méthodes demandées sont terminées, puis bilan global. L'affichage est aussi
  correct lorsque les processus terminent dans un ordre différent.
- Essai réel de deux instances (C101/25 et C201/25), deux moteurs, deux secondes :
  quatre solutions réalisables et deux comparatifs immédiats affichés. Preuves
  `results/terminal_comparison/comparaison_affichage_lot_v1/` et transcription.
- Sélection complète vérifiée sans résolution : 56 Solomon/100 + 60 Homberger/1000,
  116 instances, 232 résolutions pour les deux moteurs. Commandes par famille,
  par taille et pour les lots complets ajoutées au guide et au notebook.
- Erreur utilisateur reproduite : `.venv_dabia` ne fournit pas numba, scipy,
  PyVRP ni VRPLIB. Nouveau contrôle avant création de campagne : message explicite,
  Python actif et procédure d'installation ; sortie 2 sans traceback. Les paquets
  optionnels non utilisés ne bloquent pas une méthode autonome.
- Environnement statique local `.venv` en préparation avec les versions validées.
  Utilisation directe de son python.exe : aucune activation PowerShell requise.
- Tests CLI : vingt réussites après correction. Validation complète du nouvel
  environnement et synchronisation finale du notebook restent à terminer.
- Reprise : `.\.venv\Scripts\python.exe scripts/test_instances.py --instances C101 C201 R101 R201 RC101 RC201 --seconds 5 --label verification_env_six_familles`.

## 14 novembre 2026 — comparaison automatique initial / renforcé

- Les commandes sans méthode explicite lancent désormais `ils` et `size_based`
  sur chaque instance/graine. Une option `--method` explicite conserve le mode
  à un seul moteur. Deux méthodes impliquent deux résolutions, pas un seul run.
- Le tableau terminal montre pour chaque méthode durée, faisabilité, flotte,
  comparaison au témoin, réel, CPU et budget. Un second tableau calcule le gain
  signé entre méthodes, distinct du gap à la référence ; égalités, régressions
  et échecs ne sont pas masqués. CSV apparié sauvegardé et relecture disponible.
- Le budget ILS reste un budget de recherche avec construction en supplément ;
  celui du renforcé est un total souple. Les temps mesurés restent explicites,
  sans présenter ces configurations comme un temps total strictement égal.
- Démonstrations : RC101, C204, R109 (100 clients, 5 s) et C2_10_7 (1000,
  30 s), graine 4101, un processus : huit solutions réalisables, contrôlées
  indépendamment ainsi que leurs références et les empreintes de sources.
- C2_10_7 : ILS 124703,9 / 33,37 s, renforcé 112338,0 / 29,60 s, gain de
  durée 9,9162 %. Au plan témoin : +16,6111 % contre +5,0477 %.
- Petits cas : renforcé meilleur sur C204 ; ILS légèrement meilleur sur R109
  et RC101. Ces résultats sont conservés : pas de supériorité universelle annoncée.
- Tests : **229 réussis, 2 ignorés**. Syntaxe PowerShell vérifiée ; le script
  de démonstration utilise aussi les deux moteurs sauf `-Method` explicite.
- Preuves : `results/terminal_comparison/`, guide
  `docs/COMPARAISON_INITIAL_RENFORCE.md`. Notebook réexécuté : seize cellules,
  zéro erreur, 32,68 s. Validations statique et présentation réussies ; HTML
  et copie notebook à envoyer synchronisés. Sauvegarde par commit local,
  sans push, ZIP, Word ou PDF.
- Reprise : `python scripts/finalize_static.py --execute --validate`.

## 14 novembre 2026 — correction du profil de test et audit des dépassements

- Cause RC101 identifiée : le défaut v1 appelait la construction seule sur les
  petits cas. Passage à construction regret-2 + Local Search **PyVRP externe**
  + notre ILS, avec conservation et contrôle du meilleur coût à chaque étape.
- 72 nouveaux essais complets, graine 4101, cinq secondes, deux processus :
  72 réalisables, zéro dépassement de six pour cent parmi les comparaisons
  disponibles. Les 56 cas à 100 clients ont une référence ; 12 des 16 préfixes
  25/50 restent sans référence indépendante. Aucun chiffre inventé pour ces cas.
- RC101/100 : durée 3335,2 -> 2921,1, référence 2991,6. Solution améliorante
  vérifiée ; pas un optimum temporel battu. Les anciennes mesures sont conservées.
- Quatre contrôles 1000 clients révèlent l'arrêt du renforcé vers cinq secondes
  et les dépassements C2_10_2 (+6,0221 %) et C2_10_7 (+7,6865 %).
- Ajout d'une continuation HGS **externe PyVRP** dans le budget restant des
  grands cas, sans lecture de référence et sans modifier les moteurs historiques.
  Deux essais soixante secondes : +1,9592 % et +4,2518 %, réalisables, environ
  59,6/59,8 s écoulées et 58,8/58,5 s CPU. Gains non attribués à l'ILS autonome.
- Audit historique relancé : 1321 comparaisons, zéro anomalie. Audit terminal :
  166 enregistrements, 163 réalisables, trois échecs conservés, zéro anomalie.
  Ces registres se chevauchent : ne pas additionner leurs effectifs de runs.
- Tests : **224 réussis, 2 ignorés**, XML actualisé. Notebook réexécuté :
  seize cellules de code, zéro erreur, 34,05 secondes. Validations statique et
  présentation réussies ; HTML et copie notebook à envoyer synchronisés.
- Résultats et sources figées : `results/policy_v2_audit/`, rapport
  `CORRECTION_DEPASSEMENTS.md`, tableaux avant/après et statuts par instance.
- Reprise sans benchmark : `python scripts/finalize_static.py --execute --validate`.
  Aucun push, ZIP, Word ou PDF automatique. Quota restant non accessible.

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
| Tests | Réussis | 222 réussites, deux modules optionnels ignorés |
| Notebook | Corrigé et réexécuté | 16 cellules, zéro erreur, dernier passage 52,78 s |
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

### Commandes terminal : vérification terminée

- Fiche complète : `COMMANDES_TERMINAL.md`. Script PowerShell réellement testé :
  `scripts/demo_terminal.ps1`. Le notebook et sa copie à envoyer ont été actualisés.
- **18 commandes automatisées validées** : aides, pytest, validateur, petites
  instances, six familles, huit tailles, comparatif à six profils, référence
  indisponible, véritable échec PyVRP, garde-fou, deux processus et relectures.
- Suite complète : **194 réussites, 2 modules TD optionnels ignorés**.
  Validateur `validate_soutenance.py` réussi, avec transcriptions sauvegardées.
- Profils complémentaires construction/sans partitionnement/renforcé+ILS aussi
  exécutés. Les neuf profils de l'interface sont opérationnels dans ce périmètre.
- `validate_terminal_artifacts.py` vérifie **32 enregistrements**, 30 faisables
  et deux échecs attendus, dans douze campagnes. Vérification des tournées,
  horaires, coûts, décompositions, écarts signés, CSV/JSON et sources figées.
  Reçu : `livraison/VALIDATION_COMMANDES_TERMINAL.json`.
- Les sources des campagnes sont dédupliquées dans
  `results/terminal_validation/sources/`, avec `SOURCE_INDEX.json` : les preuves
  et le code exécuté ne restent pas uniquement dans `results/local/` ignoré.
- Progressif à budget demandé 5 s : huit solutions réalisables aux tailles
  25/50/100/200/400/600/800/1000, références et temps réels documentés dans la fiche.
- C1_10_6/1000, graine 4101, budget demandé 30 s : durée 140502,9, témoin
  réévalué 133754,7, écart **+5,0452 %**, réel résolution **3,452 s**,
  CPU **3,312 s**. Pas de certificat d'optimalité en durée.
- Les six méthodes comparées sur C101/25 trouvent 2623,5 ; les écarts nuls
  sont conservés sans prétendre prouver un optimum. La construction seule
  présente +8,4925 % sur ce cas : dépassement réel conservé.
- Échec réel : PyVRP sur R2_10_8, recherche 0,001 s, statut `not_found`.
  Garde-fou 0,05 s testé : statut `time_limit`, environ 0,0675 s observée.
  Les deux retours 1 sont attendus et ne représentent pas des données rendues
  artificiellement irréalisables. Aucun coût ni gap fictif n'est affiché.
- Le garde-fou 120 s surveille le processus entier (initialisation comprise),
  tandis que le CPU/réel de résolution exclut chargement et préchauffage.
  Un léger dépassement dû à la surveillance ou à l'arrêt reste possible.
- Dernière exécution intégrale du notebook : **16 cellules, zéro erreur,
  44,35 s**. Validation statique finale réussie avec la suite à 194 tests.
- Les algorithmes et les anciennes campagnes sont conservés ; ces essais
  de commandes ne sont pas fusionnés dans les moyennes historiques.

Reprise sans recherche :

```powershell
python scripts/validate_terminal_artifacts.py
python scripts/validate_final_static.py
python scripts/test_instances.py --show-results commandes_terminal_runs_comparaison --show-routes
```

Sur ce PC, utiliser l'interpréteur exact de `COMMANDES_TERMINAL.md` (`$py`).
L'installation portable n'a pas été simulée sur un second ordinateur. Le ZIP
créé avant cette mission n'a pas été régénéré automatiquement. Commits locaux
et résultats de cette passe sauvegardés ; aucun push demandé.

## Présentation par statuts — audit et mise en œuvre

- Demande acceptée : conserver les moteurs et les résultats, remplacer les
  comparaisons non positives par des statuts explicites dans la présentation.
  Aucun ralentissement ni détérioration volontaire de l'algorithme.
- Recalcul indépendant depuis les coordonnées et tournées : **1321 comparaisons**,
  dont **947 références dépassées, 129 égalités, 245 écarts positifs**. Aucune
  anomalie détectée dans ce registre consolidé ; plusieurs lignes peuvent
  représenter un même essai ou une vue d'archive, pas de faux nouveaux runs.
- **61 groupes à moyenne ou médiane nulle** examinés séparément. Pas de preuve
  d'optimalité déduite d'une moyenne nulle ou d'une égalité heuristique.
- Audit technique par cas : `AUDIT_GAPS_FINAL.md`, coûts, anciennes valeurs,
  nouveau calcul, cause, référence et vérification. Les valeurs d'origine sont
  conservées dans `results/presentation_status/` et les CSV historiques.
- `algo/comparison_status.py` : statuts optimum/référence dépassée/égalée/
  comparaison indisponible ; contradiction face à un optimum certifié bloquante.
- Moyennes/médianes conditionnelles aux seuls écarts positifs, avec effectif
  et comptage de tous les autres statuts. Les valeurs supérieures à six restent.
  Les graphiques de benchmark concernés sont remplacés par des effectifs de
  statuts et une distribution conditionnelle clairement légendée.
- Les paramètres nuls et variations signées de l'étude de sensibilité sont
  préservés : ce ne sont pas des gaps à une référence de benchmark.
- Interface terminal cohérente avec cette présentation ; CSV/JSON gardent leurs
  écarts signés pour l'audit. Guide des commandes et notebook actualisés.
- Tests complets : **206 réussites, deux modules optionnels ignorés**.
- Reprise : `python scripts/audit_gap_status.py`, puis
  `python scripts/present_gap_status.py`, `python scripts/execute_final_notebook.py`
  et `python scripts/validate_gap_presentation.py`. Le finaliseur général appelle
  désormais la couche de présentation après génération des tableaux.

### Présentation : validation finale

- `livraison/VALIDATION_PRESENTATION_GAPS.json` : vérification réussie des
  statuts, statistiques positives et dénominateurs, absence de pourcentages
  de benchmark non positifs dans la présentation, et empreintes des moteurs
  inchangées. Les paramètres et variations de sensibilité restent distincts.
- Notebook complet exécuté : **16 cellules, zéro erreur, 36,04 secondes**.
  Validation statique du projet réussie avec **206 tests réussis et deux ignorés**.
- HTML de lecture synchronisé : `notebooks/Livrable_Final_CVRPTW.html`.
  Copie notebook à envoyer actualisée dans Téléchargements, figures intégrées.
- Essai terminal à une seconde : `not_found` pendant la préparation, conservé
  dans `verification_statuts_console`. Il n'est pas caché ni transformé en succès.
- Vérification recommandée à cinq secondes : C101/25 et RC201/100 tous deux
  réalisables, affichant respectivement « Référence égalée — optimalité non
  démontrée » et « Référence dépassée — solution améliorante validée ».
  Les coûts et écarts bruts restent sauvegardés dans les JSON/CSV d'origine.
- Aucune nouvelle référence plus forte n'a été produite. Cette passe ne démontre
  pas un gap certifié sous six pour cent sur tout le catalogue et ne transforme
  pas une moyenne conditionnelle en moyenne de toutes les instances.

## Ablation acceptée : variante simplifiée explicite

- Test de la construction seule déjà disponible : douze tentatives regret-2,
  aucun ILS/recuit, aucune Local Search PyVRP, aucun HGS ni partitionnement.
  Aucun changement de la version de production ou de ses meilleures solutions.
- Lot fixé avant les mesures : six familles Solomon à 100 clients, C101/25,
  R2_10_8/1000 ; graines 4101 et 4102 ; construction contre renforcé à budget
  demandé cinq secondes. La construction se termine après ses douze tentatives,
  sans consommer artificiellement tout le budget. Temps réels et CPU conservés.
- **32/32 solutions réalisables**, coûts et références réévalués indépendamment
  depuis les coordonnées et les tournées. Références consultées après recherche.
- Construction seule : C101/25 **9,1748 %**, C101/100 **4,5979 %**,
  RC101/100 **10,7601 %**, moyennes sur les deux graines. C201/100 égale la
  référence ; les quatre autres cas la dépassent sur les deux graines.
- Sur les 16 essais de construction : six écarts positifs (moyenne conditionnelle
  **8,1776 %**, quatre dépassant six), deux égalités, huit références améliorées.
  Cette simplification ne garantit donc pas un intervalle de qualité choisi.
- Sources, protocole, résultats signés, horaires et rapport sont conservés dans
  `results/simplified_variant/variante_simplifiee_comparaison/`.
- Commande exécutée : `python scripts/run_benchmark.py --instances C101:25 C101:100 C201:100 R101:100 R201:100 RC101:100 RC201:100 R2_10_8:1000 --methods construction refined --seconds 5 --seeds 4101 4102 --label variante_simplifiee_comparaison`.
- Relecture/validation des résultats : `python scripts/report_simplified_variant.py`.
  Ce rapport est une étude séparée, non une réécriture du benchmark principal.

## Nouvelle configuration de test : sélection par taille

- Profil `size_based` ajouté ; nouveau défaut des commandes `test_instances.py`
  et `run_benchmark.py`. Seuil déclaré avant le pilote : **au plus 100 clients,
  construction seule (12 tentatives)** ; **plus de 100, renforcé existant**.
  Les moteurs exécutés sont affichés et enregistrés dans `selected_method`.
- La décision dépend uniquement du nombre de clients, jamais d'une référence
  ou d'un gap. Les contraintes et le coût durée complète sont conservés.
- Les moteurs historiques et leurs API restent disponibles ; aucun résultat
  historique n'est renommé comme résultat de la nouvelle sélection.
- Pilote réel : six instances 25/50/100/200/1000, graine 4101, budget demandé
  cinq secondes : **6/6 réalisables**, coûts et références revérifiés depuis
  les coordonnées par le calculateur indépendant.
- C101/25 : construction, +8,4925 % ; C101/50 : construction, +1,1826 % ;
  C101/100 : construction, +5,0848 % ; C1_10_6/1000 : renforcé, +5,0452 %.
  C1_2_1/200 et R2_10_8/1000 améliorent leurs témoins réalisables.
  Aucun intervalle de gap garanti ni référence supposée optimale.
- Tests complets : **222 réussites, deux modules optionnels ignorés** ;
  seuil 100/101, sélection, graines/budgets et métadonnées contrôlés.
- Rapport et tableau : `docs/SELECTION_PAR_TAILLE.md` ; preuves et sources :
  `results/size_policy/selection_par_taille_validation/`.
- Notebook : nouvelle section 6.14, introduction et guide terminal mis à jour.
  Pour forcer le profil historique sur petit cas : `--method refined`.
  Pour expliciter le nouveau choix : `--method size_based`.

### Sélection par taille : livraison vérifiée

- Notebook exécuté intégralement après ajout de la section 6.14 : seize
  cellules de code, zéro erreur, 52,78 secondes. Validations statique et
  présentation réussies, avec 222 tests réussis et deux modules ignorés.
- HTML et copie notebook à envoyer synchronisés avec cette configuration.
- Démonstration PowerShell réellement exécutée avec `-Method size_based` :
  C101/25 construit une solution réalisable, et le moteur est affiché.
  Log : `results/size_policy/selection_par_taille_validation/DEMO_POWERSHELL.txt`.
- Les moteurs initiaux restent inchangés ; la politique de sélection est une
  nouvelle configuration de test, pas une amélioration de tous les coûts.
  Le dépassement de qualité sur C101/25 reste publié, sans ajustement artificiel.

## Tableau complet des écarts conservés

- Export sans nouvelle résolution : `scripts/export_all_gaps.py`.
- `results/gap_tables/TABLEAU_GAPS_TOUTES_INSTANCES.md` et CSV : 363 couples
  instance/taille, dont 361 avec nos profils et deux contrôles de référence
  seulement (C105/25 et C106/25). Les variantes TD restent hors modèle statique.
- Colonnes distinctes : moyenne initiale au témoin, moyenne/pire valeur de
  l'archive à budgets mixtes et exemple renforcé avec sa référence/campagne.
- `DETAIL_TOUS_LES_ECARTS.csv` conserve aussi les autres méthodes, les échecs
  et les références distinctes. Plusieurs lignes peuvent représenter un même
  essai réévalué ou une vue de l'archive : pas de nouveau nombre de runs déduit.
- Les formules des écarts disponibles et l'unicité des 363 lignes ont été
  vérifiées. Les valeurs négatives et supérieures à 6 % restent présentes.
