# Progression — finalisation CVRPTW CESI

Date de référence : 13 novembre 2026 (Europe/Paris).
Quota restant : non accessible. Les résultats et commandes sont sauvegardés ici.

## Consigne prioritaire et périmètre

La mission finale confirme : trajets **fixes et symétriques**, départs à zéro,
objectif **somme des durées complètes**, avec attentes, services et retours.
Les expériences Dabia2013/Lera2026 ont des trajets variables et des départs
optimisés : elles sont **exploratoires et hors modèle principal**, même si leurs
coûts ont été vérifiés. Elles ne constituent pas une preuve de conformité CESI.

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

## Étapes de la mission finale

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
