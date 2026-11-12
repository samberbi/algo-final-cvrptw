# Journal d’évolution de la solution CVRPTW

Ce journal relie les changements de méthode aux preuves expérimentales. Les lots et les budgets sont conservés avec les résultats : une moyenne issue d’un autre lot n’est pas considérée comme un gain à conditions égales.

| Étape | Difficulté étudiée | Modification et protocole | Observation | Décision |
|---|---|---|---|---|
| Construction et recherche locale | Obtenir un départ complet et améliorer ordre et affectation | Regret-2 ; mouvements relocate, swap, 2-opt, 2-opt* ; contrôles des tournées | Base du moteur ILS réalisable | Conservé dans la première phase |
| Décomposition en groupes | Coût des recherches sur de grandes instances | Groupes de tournées complètes, données originales, taille adaptative et compilation Numba | Constitue le moteur optimisé de référence | Conservé |
| Voisinages et intensification de l’ILS | Minima locaux et affectations difficiles | Voisinage temporel, SWAP* propre, RVND, chaînes, relais et paramètres ; études de développement séparées | Effets variables ; aucune amélioration uniforme démontrée | Options expérimentales de l’ILS ; le HGS conserve son propre SwapStar |
| Partitionnement de tournées | Exploiter plusieurs solutions réalisables | Validation v5, douze cas et deux graines, recherche de 40 s | ILS 10,127 % ; ILS–partitionnement 10,355 % | Non retenu comme amélioration à ce budget |
| Cache et groupes temporels | Évaluer plus vite et choisir des groupes compatibles | Confirmation v6, douze autres cas, deux graines, 40 s | Référence 6,065 % ; combinaison 6,164 % | Gain moyen non confirmé |
| Coût guidé et variantes pénalisées propres | Traverser des zones de recherche difficiles | Essais v7 sur trois cas, avec archivage des solutions finales réalisables | Résultats irréguliers ; régressions conservées | Non retenus dans le moteur recommandé |
| Initialisation directe du HGS | Apporter une population génétique à partir du constructeur | Douze grandes instances, deux graines, 60 s | Gap moyen 6,624 % ; un essai à 41,238 % | Initialisation insuffisante pour la cible |
| ILS puis HGS de PyVRP | Fournir un départ amélioré au moteur génétique | Même départ ILS de 60 s, puis 60 s d’ILS ou de HGS ; douze cas, deux graines | 9,036 % contre 4,253 % ; gain dans 23 paires sur 24 | Combinaison retenue, composant externe attribué |
| Évaluation du catalogue complet | Établir la couverture au-delà des cas déjà étudiés | 356 instances ; 472 pipelines, dont 448 nouveaux et 24 réutilisés | 2,078 % par instance ; 3,681 % sur les 60 cas à 1 000 clients ; 472/472 réalisables | Bilan final publié, sans sélectionner les bons gaps |
| Relecture rédactionnelle et mathématique | Clarifier le réseau, les notations et la progression du travail | Ajout du graphe pédagogique, tableau des symboles et harmonisation de la rédaction | Aucun changement de l’algorithme ou des mesures de benchmark | Mise à jour documentaire |

La première ligne de chaque comparaison doit toujours préciser l’instance ou le lot, les graines et le budget. Les 4,253 % de la comparaison appariée et les 2,078 % du catalogue portent sur des périmètres différents : leur écart ne mesure pas un nouveau progrès du moteur.

## Preuves associées

- [Étude des variantes v5](AMELIORATIONS_ILS.md) : développement, résultats négatifs et archives à effort supérieur.
- [Étude du cache et des groupes v6](AMELIORATIONS_ILS_V6.md) : accélérations, confirmation et limites.
- [Étude préparatoire de l’hybridation v7](RECHERCHE_GRANDES_INSTANCES_V7.md).
- [Tableau final complet](../livraison/RESULTATS_CATALOGUE_V8.html).
- Protocoles et sources figées : `results/optimization_v5/`, `results/optimization_v6/`, `results/optimization_v7/` et `results/catalog_v8/`.

## Fiche à compléter pour une nouvelle modification

1. **Problème observé :** instances, graines et comportement constaté.
2. **Hypothèse :** pourquoi la modification pourrait améliorer la recherche.
3. **Changement réel :** fichiers, opérateurs ou paramètres concernés, avec leur version.
4. **Protocole :** lot de réglage, lot de contrôle, graines, budget, préparation et matériel.
5. **Résultats exécutés :** distances, gaps compatibles, faisabilité, temps et dispersion ; conserver les échecs.
6. **Comparaison :** référence pertinente au même effort, gains et régressions.
7. **Décision :** retenu, abandonné ou exploratoire ; limites et coût supplémentaire.
8. **Livrable :** actualiser le registre, les tableaux et les exports après validation, sans modifier les campagnes figées.

Les pistes proposées après la campagne finale, comme un autre partage du budget ILS/HGS, restent des hypothèses tant qu’elles n’ont pas été exécutées sous un nouveau protocole.

<!-- WORST_V9_JOURNAL_BEGIN -->
## Phase v9 — réduction des pires écarts

Le réglage 20/100 est évalué sur sept cas et deux nouvelles graines : moyenne 4.642 %, pire 6.638 %, 14/14 sous 7 %. Les dix anciens essais à au moins 7 % reçoivent chacun 180 s supplémentaires. Leur archive consolidée a un pire gap de 6.889 %, à budgets variables. Les essais de 360 s, départs multiples et partitionnement sont également exécutés et documentés dans [l’étude v9](REDUCTION_PIRES_GAPS_V9.md). La campagne v8 reste figée.
<!-- WORST_V9_JOURNAL_END -->

## Revue finale de livraison

La dernière passe explicite la population, les tournois, SREX, la recherche locale et les pénalités du HGS externe, avec les paramètres réellement utilisés. Les extraits sont synchronisés avec le code livré. Les modules d’intégration sont remis en forme et les graines invalides sont rejetées. Ces corrections de présentation et de validation des entrées ne constituent pas un gain numérique mesuré : les campagnes figées et leurs résultats restent inchangés. Voir la [revue de conformité](REVUE_FINALE_CONFORMITE.md).

## Documentation du code

Une passe ajoute ou traduit les descriptions de 45 fonctions dans 17 fichiers et commente les étapes sensibles : conversion des unités DIMACS, représentation en tableaux, insertion regret-2, caches temporels, mouvements, acceptation, archive et réintégration des groupes. La CLI et le worker web explicitent leur rôle. Les extraits du notebook sont synchronisés avec ces sources. La comparaison des arbres syntaxiques, après retrait des docstrings, confirme que les instructions exécutables restent identiques. Les sources figées des campagnes ne sont pas modifiées ; cette passe ne revendique aucun nouveau gain de gap.
