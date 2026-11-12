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

## Réduction des écarts les plus élevés

Le partage 20 s ILS / 100 s HGS est confirmé sur sept cas et deux nouvelles graines : moyenne 4,642 %, maximum 6,638 %, 14/14 sous 7 %. Les voisins 60/80 et les départs multiples n’apportent pas un avantage systématique. Le partitionnement n’améliore aucun des six essais de la dernière comparaison.

Séparément, dix essais historiques reçoivent chacun 180 s supplémentaires. Le maximum de l’archive passe de 11,021 % à 6,889 % ; sa moyenne par instance vaut 1,988 %. Les budgets deviennent variables. Cette archive ne remplace pas la campagne de référence et son coût additionnel est conservé.

## Documentation et contrôles

Les fonctions principales et les étapes sensibles sont commentées en français. Les extraits du livrable correspondent au code fourni. La documentation ne modifie ni les instructions de calcul ni les campagnes figées. Les méthodes externes et leurs auteurs restent cités.

Les preuves sont dans `results/` : `catalog_v8/` pour les 472 pipelines, `worst_v9/` pour les réglages et reprises, et les lots `optimization_v2/`, `optimization_v5/`, `optimization_v6/`, `optimization_v7/` et `revision_ils/` pour les comparaisons et contrôles décrits. Les sources figées permettent de distinguer le code exécuté de sa documentation actuelle.
