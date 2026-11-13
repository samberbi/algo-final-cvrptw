# Bilan de conformité — modèle statique confirmé

Ce bilan distingue les exigences de l'énoncé transmis et les hypothèses
professorales confirmées dans `CONSIGNES_FINALES_20261113.md`.
Le document transmis est conservé dans `CAHIER_DES_CHARGES_TRANSMIS.md`.

| Exigence | Preuve ou emplacement | État / limite |
|---|---|---|
| Contexte CesiCDP/ADEME, objectif métier | Introduction du notebook | Présent ; aucune réduction CO₂ chiffrée inventée |
| CVRPTW : capacité et fenêtres strictes | `algo/model.py`, `verify.py`, tests | Réalisabilité contrôlée, fenêtres sur début de service |
| Trajets fixes et symétriques | Matrices immuables et validation Instance | Modèle principal conforme à la confirmation du professeur |
| Trafic variable évoqué dans l'énoncé initial | Archive `EXPLORATION_TD_HORS_PERIMETRE.md` | Hors périmètre principal confirmé ; ne pas confondre les deux modèles |
| Départs nuls, retours compris | PLNE C6/C7, contrôleur, adaptateurs | Objectif somme des durées complètes ; ni flotte prioritaire ni makespan |
| Graphe orienté avec o/r | Section mathématique et figure `graphe_modele` | Un dépôt physique, deux sommets de décision |
| Preuve de complexité | Section 2 : réduction TSP, certificat polynomial | NP-difficile ; décision NP-complète pour données rationnelles |
| PLNE complet et exact opérationnel | `controle/plne.py`, dix petits cas comparés à énumération | Preuves limitées aux petits cas ; pas d'optimalité globale revendiquée |
| Métaheuristique propre | `duration.py`, `duration_moves.py` | ILS autonome et recuit ; opérateurs, acceptation, arrêt expliqués |
| Origine des moteurs | HGS, Local Search, HiGHS et OR-Tools explicitement attribués | Les coûts hybrides ne sont jamais étiquetés ILS autonome |
| Partitionnement | `route_pool.py`, ablation `refined_ablation.py` | Couverture exacte, flotte bornée, routes faisables ; optimum restreint |
| Au moins vingt instances | Historique 356 instances, 646 résolutions | Présent ; les copies auditées ne sont pas comptées comme nouveaux runs |
| Tailles réalistes | Historique 100–1000 ; nouveaux pilotes 25/50 et tailles intermédiaires | Milliers multiples non démontrés ; 1000 accepté selon retour utilisateur |
| Références via VRPLIB | `data.py`, `static_small.py`, manifestes SHA-256 | Conventions d'unités figées |
| Gap compatible à une référence | Audit Phonin, référence OR-Tools indépendante, témoins publics réévalués | Pas d'optimum temporel certifié sur tout le jeu ; aucune garantie <6 % |
| Qualité, temps, dispersion | CSV, statistiques historiques à vingt graines et pilotes séparés | Mélange de budgets explicitement interdit dans une moyenne de classement |
| Sensibilité et scénarios | Sections 6.10/6.11 : 90 profils et familles C/R/RC | Mutualisation des phases et limites causales signalées |
| Améliorations justifiées | Journal des modifications ; variante ILS testée séparément | Retenue seulement comme candidate si bénéfice non généralisable |
| Démonstration courte | `TESTER_SUR_PORTABLE.md`, annexe notebook | Petits cas ; chargement, faisabilité, décomposition et écart visibles |
| Exécution intégrale du notebook et tests | Reçu final et XML horodatés | Seuls les contrôles effectivement exécutés sont annoncés |

Le seuil académique est un objectif de qualité, pas un filtre des résultats.
Un écart signé au coût d'un solveur indépendant réalisable n'est pas un gap à
un optimum prouvé. Une égalité de coût ne prouve pas non plus l'optimalité.
L'accord final sur cette référence pour la notation reste à confirmer avec
le professeur ; ce point ne peut pas être certifié uniquement par le programme.
