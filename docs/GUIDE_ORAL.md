# Présenter notre livrable CVRPTW
<!-- WORST_V9_GUIDE_BEGIN -->
## Actualisation v9

La confirmation à 120 s donne 4.642 % de moyenne, 6.638 % au pire et 14/14 sous 7 % avec le partage 20/100. Séparément, les dix reprises de 180 s font passer le maximum de l’archive de 11,021 % à 6.889 %. Annoncer le budget supplémentaire avec ce dernier chiffre. Le nouveau reçu courant est `validation_worst_v9.json`. [Détails et limites](REDUCTION_PIRES_GAPS_V9.md). Les paragraphes précédents sur v8 restent le bilan de la campagne de référence.
<!-- WORST_V9_GUIDE_END -->


## 1. Quel problème résolvons-nous ?

Nous devons livrer tous les clients une fois, avec des véhicules de capacité limitée, respecter le début du service dans chaque fenêtre et revenir au dépôt à temps. Nous optimisons la distance sur des données statiques selon la convention DIMACS. Le nombre de véhicules est une borne, pas le premier objectif. La durée et le trafic du sujet initial restent distingués de cet objectif expérimental.

## 2. Qu’avons-nous développé ?

Notre constructeur par regret-2, notre ILS, les mouvements et leur contrôle, les expériences, l’interface et l’intégration avec PyVRP. Dire : « Nous avons développé une solution hybride qui combine notre ILS avec le HGS de PyVRP. » Le moteur HGS provient de la bibliothèque externe, attribuée à ses auteurs.

## 3. Pourquoi une ILS avant le moteur génétique ?

Une construction réalisable peut rester très coûteuse. L’essai construction puis HGS à 60 s a donné 6,624 % en moyenne et un cas à 41,238 %. Notre ILS améliore d’abord ce départ ; le HGS reçoit ensuite une meilleure solution et diversifie avec sa population. Dans la comparaison appariée à deux phases de 60 s : 9,036 % pour ILS puis ILS, 4,253 % pour ILS puis HGS, 23 gains sur 24 paires. Ce constat porte sur douze grandes instances et deux graines, pas sur tout le catalogue.

## 4. Que signifie le gap ?

Gap = 100 × (notre distance − référence) / référence. À 4 %, la distance dépasse la référence de 4 %. La référence est une meilleure solution connue compatible, pas forcément un optimum prouvé. Les demandes, capacités, fenêtres, flotte, objectif et troncature doivent correspondre.

La moyenne principale sur 356 cas donne le même poids à chaque instance : **2.078 %**. La moyenne de tous les essais vaut **2.045 %** et pondère davantage les cas ayant deux graines. Le lot de 116 cas à 100/1 000 clients vaut **1.946 %**. À 1 000 clients, la moyenne est **3.681 %**, avec un pire essai de **11.021 %**. Toujours annoncer le périmètre avec le chiffre.

## 5. Combien de calculs et combien de clients ?

356 instances différentes, six tailles ; 472 pipelines, dont 448 nouveaux et 24 réutilisés. Chaque pipeline a deux phases et une construction. À 100/1 000 clients, deux graines ; aux tailles intermédiaires, une graine. « 1 000 clients » n’est pas « 1 000 runs ». Une répétition réexécute la même instance avec une autre graine.

## 6. Pourquoi ne pas garder toutes les modifications ?

Le cache peut accélérer certains mouvements sans améliorer le gap. Des voisins plus riches, SWAP* ou RVND peuvent consommer du temps et réduire le nombre d’explorations. Les comparaisons v5/v6/v7 gardent ces régressions. Nous retenons une méthode sur ses résultats mesurés, pas sur sa complexité ou son nom.

## 7. Comment savons-nous que les solutions sont valides ?

Un contrôleur indépendant recalcule couverture, charges, horaires au plus tôt, attente, retours et distance sur les données originales. Le service doit commencer dans la fenêtre ; sa fin peut la dépasser si le reste et le retour sont valides. Le HGS peut explorer des états pénalisés, mais aucune solution finale irréalisable ne peut être publiée. Les références sont aussi revérifiées.

## 8. Comment lire les graphiques ?

Les boîtes montrent la dispersion entre instances, pas une précision garantie sur de futures graines. Les points extrêmes restent inclus. Le graphique par taille évite de cacher les grandes instances derrière les petites. La carte par familles montre la structure spatiale et temporelle. Les cartes/Gantt C101 et R2_10_4 expliquent deux résultats réels avec la graine 2101 ; le Gantt est limité aux quatre premières tournées pour être lisible.

## 9. Quelles limites reconnaissons-nous ?

Une ou deux graines seulement, des budgets différents selon la taille, aucune ablation interne du HGS, un moteur externe, des cas déjà étudiés pour certains réglages, des données statiques et aucun essai au-delà de 1 000 clients. La durée totale n’est pas l’objectif optimisé. Un bon gap ne prouve pas l’optimalité ni une note. Tous les cas défavorables restent accessibles.

## 10. Où montrer les preuves ?

Le rapport principal expose le modèle, la méthode et les synthèses. `RESULTATS_CATALOGUE_V8.html` montre les 356 cas et toutes les répétitions. Les JSON contiennent les tournées et les mesures. `protocol.json` et `source/` figent les données de l’expérience. `VALIDATION.json` pointe vers le reçu courant ; les anciennes validations sont historiques.
