# Comprendre et présenter le projet

## Le message principal

Nous organisons des livraisons sous contraintes de capacité et d'horaires.
Notre moteur construit une solution réalisable, puis améliore sa distance.
Le nombre de camions ne doit pas dépasser la limite du fichier. Nous n'imposons
pas de priorité à la diminution de ce nombre dans le benchmark DIMACS.

Le rapport et ses tableaux donnent les valeurs mesurées. Les chiffres ne
doivent pas être remplacés par le meilleur résultat trouvé après plusieurs essais.

## Déroulé conseillé

1. Présenter les clients, les demandes et les fenêtres, puis la liste de tournées.
2. Utiliser l'exemple à deux clients pour distinguer trajet, attente et service.
3. Expliquer une itération : retrait, réparation, recherche locale, décision.
4. Montrer les statistiques globales et le tableau par taille.
5. Commenter un cas difficile, son historique et les limites observées.
6. Exécuter un petit cas dans le Notebook ou la CLI.

## Pourquoi une ALNS ?

Les fenêtres et les capacités lient les décisions. Un client ne peut pas être
placé partout. Retirer plusieurs clients permet de revoir des affectations que
ne change pas un échange isolé. La réparation reconstruit une solution complète.
L'adaptation favorise progressivement les retraits qui ont apporté des résultats.

L'ALNS est une méthode de recherche, pas une preuve d'optimalité. Un budget
fini signifie que nous conservons le meilleur résultat observé jusqu'à l'arrêt.

## Pourquoi regret-2 et regret-3 ?

Nous considérons les meilleures possibilités dans des tournées distinctes.
Un client coûtant 4 dans une tournée et 20 dans une autre perdrait beaucoup
si sa meilleure place disparaissait. Son regret est 16. Un client coûtant 5
ou 7 a davantage de souplesse : son regret est seulement 2.

Le regret donne une priorité d'insertion, pas la certitude d'une décision
globalement optimale. Les clients sans insertion possible font échouer la
réparation ; ils ne sont pas supprimés de la liste des livraisons à réaliser.

## Pourquoi accepter un résultat moins bon ?

La solution courante peut être coincée dans un minimum local. Le recuit accepte
certaines augmentations de distance pour explorer un autre secteur. La probabilité
est exp(-delta/T) : plus la dégradation est forte ou la température basse,
moins elle est probable. La meilleure solution reste conservée séparément.

La température n'a aucun rapport avec celle du camion. Elle règle la tolérance
de la recherche aux détours temporaires. Les retards de livraison restent interdits.

## Pourquoi ne pas minimiser les véhicules d'abord ?

Le critère de référence choisi ici est la distance totale, avec une limite
maximale de véhicules. Ce choix correspond aux BKS du dossier VRPTW de
PyVRP/Instances. Ajouter un coût fixe de camion changerait le problème.
Nous publions néanmoins le nombre utilisé, car il reste utile pour comprendre
les solutions et contrôler leur faisabilité.

## Pourquoi tronquer les distances ?

Le benchmark DIMACS définit chaque arc par une troncature à une décimale.
Nous appliquons cette convention avant la recherche, également aux trajets.
Changer de précision peut changer les horaires réalisables et les BKS.
Il faut donc comparer un résultat et une référence calculés selon les mêmes règles.

## Que signifie un gap de 3 % ?

Pour cette exécution et cette référence, la distance trouvée dépasse la BKS de
3 %. Si la référence vaut 1 000, une distance de 1 030 donne 3 %.
La moyenne porte sur des pourcentages par exécution, pas sur un rapport de
sommes de distances. Le pire gap et les effectifs complètent cette moyenne.

Une BKS est une meilleure solution publiée, pas nécessairement un optimum
démontré. Un gap nul signifie égalité de coût avec cette référence.

## Que prouvent les mille exécutions ?

Elles couvrent les 356 problèmes VRPTW de la révision retenue, avec deux ou
trois graines chacun. Une graine change les décisions aléatoires ; elle ne crée
pas un nouveau problème géographique. Les répétitions renseignent la dispersion,
mais restent peu nombreuses pour estimer un événement rare sur chaque instance.

Les budgets varient selon la taille. Le graphe des temps ne démontre donc pas
une loi pure du temps de calcul en fonction du nombre de clients. La mémoire
des matrices denses augmente quadratiquement.

Après un pilote apparié sur six cas difficiles connus, les trajectoires d'au
moins 400 clients reçoivent cinq secondes de recherche par groupes de tournées.
Les cas de 1 000 clients reçoivent une seconde passe de cinq secondes ; leur
budget cumulé est de 25 secondes.
Nous conservons les états avant et après et indiquons le temps cumulé. Ce ne
sont pas de nouveaux problèmes ni des répétitions indépendantes supplémentaires.
L'ajout décidé après observation est une amélioration exploratoire déclarée,
pas une validation entièrement aveugle.

## Quelles limites annoncer ?

Les données ne modélisent pas le trafic variable, une flotte hétérogène ou
plusieurs dépôts. Le faible gap moyen ne garantit pas un seuil sur chaque
recherche. Les grands cas peuvent nécessiter davantage de temps ou une meilleure
réparation. Les quatre processus partagent les ressources physiques de la machine.

La comparaison en durée reste une expérience séparée, sans BKS optimale en durée.
L'étude ne chiffre aucune économie réelle d'émissions.

## Courte introduction en anglais

Our project addresses vehicle routing with capacity constraints and strict time
windows. We developed an adaptive large neighbourhood search that removes and
reinserts customers while preserving feasibility. Simulated annealing allows
temporary increases in distance, and a separate archive keeps the best solution.
For benchmarking, we minimise total distance under the DIMACS convention and
the fleet limit provided by each instance. We validate routes independently
and report all runs, including difficult cases. The campaign covers 356 public
instances through one thousand runs with fixed seeds and declared time budgets.
The average gap, worst gap, feasibility rate and runtime must be read together.
We also study route duration separately because waiting time can change the
ranking of solutions.
