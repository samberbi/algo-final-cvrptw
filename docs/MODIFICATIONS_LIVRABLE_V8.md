# Modifications du livrable et de la solution hybride — édition v8
<!-- WORST_V9_GUIDE_BEGIN -->
## Actualisation v9

La confirmation à 120 s donne 4.642 % de moyenne, 6.638 % au pire et 14/14 sous 7 % avec le partage 20/100. Séparément, les dix reprises de 180 s font passer le maximum de l’archive de 11,021 % à 6.889 %. Annoncer le budget supplémentaire avec ce dernier chiffre. Le nouveau reçu courant est `validation_worst_v9.json`. [Détails et limites](REDUCTION_PIRES_GAPS_V9.md). Les paragraphes précédents sur v8 restent le bilan de la campagne de référence.
<!-- WORST_V9_GUIDE_END -->


Le livrable principal est désormais le notebook `notebooks/Livrable_Final_CVRPTW.ipynb`, ses exports HTML/PDF/Word et `LIVRABLE_FINAL.md`. Les études v5/v6/v7 restent des annexes historiques avec leurs budgets et résultats propres.

## Résultats ajoutés et périmètre exact

- Catalogue complet : 356 instances, de 100 à 1 000 clients, une graine commune et une seconde sur 100/1 000.
- Sous-ensemble demandé : 116 instances, deux graines chacune, sans sélectionner les cas favorables.
- Campagne : 472 pipelines, dont 448 nouveaux et 24 réutilisés avec leurs coûts mesurés.
- Moyenne par instance sur 356 cas : **2.078 %** ; moyenne brute des essais : **2.045 %**.
- Moyenne sur les 116 cas à 100/1 000 : **1.946 %**.
- À 1 000 clients : **3.681 %**, avec pire essai **11.021 %**.
- Échecs de la campagne finale : **0 sur 472**. Les erreurs techniques des premières expériences v7 restent archivées séparément.

| n | instances | attempts | valid | mean_instance_gap | worst_run_gap | mean_total_s |
| --- | --- | --- | --- | --- | --- | --- |
| 100 | 56 | 112 | 112 | 0,086 | 1,463 | 10,038 |
| 200 | 60 | 60 | 60 | 0,411 | 2,562 | 16,131 |
| 400 | 60 | 60 | 60 | 1,527 | 3,960 | 32,572 |
| 600 | 60 | 60 | 60 | 2,858 | 6,515 | 49,379 |
| 800 | 60 | 60 | 60 | 3,770 | 7,359 | 66,717 |
| 1000 | 60 | 120 | 120 | 3,681 | 11,021 | 124,530 |

## Ce qui change dans l’algorithme utilisé

La solution recommandée combine notre constructeur regret-2, notre ILS puis le HGS de PyVRP 0.12.2. Notre ILS organise un départ de qualité ; le moteur génétique externe ajoute population, croisement et recherche locale. Le code d’intégration partage le budget à parts égales et contrôle la solution finale indépendamment. Le HGS reste attribué à ses auteurs.

La combinaison est accessible sous `--method ils_hgs` et dans le profil web « ILS + HGS (PyVRP) ». Les options ILS et recuit restent disponibles comme références. Le changement ne modifie ni données ni contraintes ni objectif : la distance DIMACS est minimisée sous capacité, fenêtres strictes, couverture unique, flotte maximale et retour au dépôt.

La comparaison appariée sur douze grandes instances et deux graines passe de 9,036 % pour ILS 60 s puis ILS 60 s à 4,253 % pour ILS 60 s puis HGS 60 s. Ce sont 4,782 points de gap en moins, pour environ 124,4 s contre 124,6 s de temps réel. La combinaison gagne dans 23 paires sur 24. Cette comparaison démontre le gain du pipeline sur ce lot ; elle n’isole pas chaque composant interne du HGS.

## Ce qui a été testé sans être retenu comme amélioration confirmée

Les voisinages temporels, SWAP*, RVND, chaînes, relais avec recuit, nombres de voisins, budgets de sous-recherche, cache de préfixes, groupes temporels, partitionnement de tournées, coût guidé et variantes propres pénalisées restent documentés dans les annexes. Les effets dépendent du lot et du budget. Leur présence dans le code ne signifie pas qu’ils sont tous actifs dans le pipeline recommandé.

Les caches ont des contrôles différentiels ; leurs gains de vitesse ne suffisent pas à prouver un gain de qualité. La combinaison cache/groupes temporels n’a pas battu sa référence en confirmation. Les archives issues de nombreuses recherches conservent un effort cumulé propre et ne sont pas présentées comme une résolution courte.

## Corrections du document

1. Résumé et conclusion alignés sur la campagne finale, avec les bonnes tailles et le bon nombre de pipelines.
2. Formulation mathématique complète conservée, avec fenêtres sur le début du service, capacité, retour, couverture et absence de sous-tournées.
3. Distinction entre distance optimisée, durée, attente et service ; la durée n’est pas comparée à une BKS en distance.
4. Attribution explicite du moteur externe et extrait réel de notre intégration.
5. Registre unique des modifications, de leur objectif, de leur effet observé et de leur statut.
6. Deux moyennes générales expliquées : poids égal par instance et poids égal par essai ; aucune sélection des gaps faibles.
7. Tableaux par taille, familles, toutes les instances et toutes les graines ; pires cas conservés.
8. Graphiques de dispersion, répartition cumulée, temps/qualité, cartes et Gantt de deux exemples préfixés.
9. Variabilité entre instances distinguée de celle des graines ; pas d’écart-type inventé avec une seule répétition.
10. Navigations README, guide oral et reçu courant harmonisés ; les vieux reçus sont historiques.

## Preuves et limites

Le protocole, les sources exécutées, empreintes des données, fichiers de référence et solutions individuelles sont conservés dans `results/catalog_v8/`. Le rapport est généré après la fin et la vérification de la campagne. Les tests et le reçu de validation ne revendiquent que des opérations effectivement exécutées.

Les limites restent explicites : budgets différents selon la taille, une graine intermédiaire et deux sur les tailles extrêmes, moteur externe, absence d’ablation interne du HGS, instances déjà étudiées pour certains réglages, données statiques, durée non optimisée, pas de résultat au-delà de 1 000 clients et pas de preuve d’optimalité globale.

## Relecture rédactionnelle et mathématique

Une introduction en graphe orienté complet et un tableau des notations précèdent désormais les équations détaillées. Le graphe physique utilise un dépôt 0 ; le PLNE distingue ensuite départ o et retour r. La tournée est notée R calligraphique, distincte de l’heure de retour. Un exemple de quatre clients, vérifié indépendamment et exclu des benchmarks, illustre deux tournées réalisables. Les formulations conversationnelles ont été harmonisées en rédaction de projet ; les sources et attributions sont conservées. Le [journal d’évolution](JOURNAL_EVOLUTION_ALGORITHME.md) précise les étapes et les preuves à joindre à chaque future modification.
