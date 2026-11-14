### 6.14. Correction du profil de test : préserver la meilleure durée

Le premier sélecteur utilisait la construction seule jusqu’à 100 clients.
Cette variante rapide était une ablation, mais son emploi par défaut faisait
perdre de la qualité : RC101/100, graine 4101, coûtait 3 335,2 unités de temps
contre 2 991,6 pour le plan public réévalué, soit +11,4855 %. Son rang 1
signifiait seulement qu’une seule méthode avait été lancée.

**La version 2 corrige cette cause algorithmique.** Jusqu’à 100 clients, elle
construit douze candidats regret-2, conserve le meilleur, applique la recherche
locale externe PyVRP avec 40, 80 puis 120 voisins tant que le budget le permet,
puis consacre le temps restant à notre ILS et ses opérateurs propres. Chaque
étape est vérifiée et conserve une durée au plus égale à celle de l’étape
précédente. Les tournées initiales et finales sont archivées pour le contrôler.
Le calcul ne lit aucune référence ni cible de gap. Ce profil est hybride :
la recherche locale PyVRP n’est pas présentée comme notre implémentation.

Au-delà de 100 clients, le profil renforcé fournit d’abord une solution :
constructions propres, recherche locale PyVRP et partitionnement sur un pool
de tournées par HiGHS. Son budget est limité à cinq secondes (ou au budget
demandé s’il est inférieur). Avec plus de deux secondes restantes, une
continuation **HGS externe PyVRP**, à 60 voisins, reçoit cette solution.
Une seconde est réservée à la préparation ; le temps réellement mesuré reste
affiché car cette réserve n’est pas une garantie stricte. Les contraintes et
la durée complète sont revérifiées, et aucune solution moins bonne n’est retenue.
Le seuil dépend uniquement du nombre de clients. Les moteurs historiques,
leurs résultats et la première ablation restent disponibles ; ils ne sont pas
réétiquetés comme des résultats de la version 2.

**Campagne réellement exécutée : 72 essais**, une graine (4101), budget souple
de cinq secondes, deux processus indépendants : les 56 Solomon à 100 clients
et les 16 préfixes disponibles à 25/50 clients. Chaque solution et chaque plan
de référence sont recalculés indépendamment depuis les coordonnées originales,
avec contrôle de couverture, capacité, fenêtres, retour au dépôt et flotte.
Le budget demandé et le temps total mesuré restent distincts.

|   Clients |   Essais |   Réalisables |   Référence_améliorée |   Référence_égalée |   Sans_référence |   Écarts_positifs |   Au_dessus_de_6 | Moyenne_positive_pct   |   Réel_moyen_s |
|----------:|---------:|--------------:|----------------------:|-------------------:|-----------------:|------------------:|-----------------:|:-----------------------|---------------:|
|        25 |        8 |             8 |                     0 |                  3 |                5 |                 0 |                0 | Sans écart positif     |         5.0006 |
|        50 |        8 |             8 |                     0 |                  1 |                7 |                 0 |                0 | Sans écart positif     |         5.0008 |
|       100 |       56 |            56 |                    41 |                  8 |                0 |                 7 |                0 | 0.40340650973485254    |         5.0014 |

Sur RC101/100, la nouvelle durée est **2921.1**, contre
3335.2 à la construction : réduction réelle de
414.1 unités, soit 12.42 %.
Elle améliore le comparateur heuristique réévalué. Ce résultat ne prouve pas
un optimum temporel et ne reçoit pas un faux écart positif.

La moyenne indiquée est conditionnelle aux seuls écarts strictement positifs :
les autres effectifs sont affichés séparément. Les références sont des plans
publics optimisés en distance puis réévalués en durée, ou des solutions OR-Tools
indépendantes pour les petits préfixes ; aucune n’est déclarée optimum temporel.
Une égalité de coût ne constitue donc pas une preuve d’optimalité.

L’absence de dépassement dans ces 72 essais ne garantit pas le résultat de
toute graine ou de toute grande instance. Les tableaux complets avant/après,
les tournées, les chronologies d’amélioration, les budgets et les sources sont
conservés dans `results/policy_v2_audit/`. Les anciens dépassements restent
consultables dans l’audit ; aucune mesure historique n’est effacée.

```powershell
python scripts/test_instances.py --instances RC101 --seconds 5 --label verification_RC101
python scripts/test_instances.py --all --sizes 25 50 100 --method size_based --seconds 5 --workers 2 --label correction_petites
python scripts/test_instances.py --instances C2_10_2 C2_10_7 --seconds 60 --label verification_grandes
```

Le moteur réellement exécuté et son attribution sont affichés dans le terminal.
Le garde-fou du processus est de 120 secondes ; les dépassements éventuels du
budget souple restent mesurés, sans plafonnement artificiel.


**Contrôle ciblé à 1 000 clients.** Le profil renforcé fini s’arrêtait après
environ cinq secondes malgré un budget de trente secondes. Sur C2_10_2 et
C2_10_7, nous testons maintenant le pipeline avec un budget de soixante
secondes, graine 4101. Les coûts « avant » sont les solutions initiales
réellement transmises au HGS pendant ces mêmes essais, et non des solutions
choisies après coup. Deux processus ont été utilisés. Le coût et le temps
incluent le profil initial et la continuation ; préparation et contrôle
du processus restent distingués dans les fichiers JSON.

| instance   |    n |   initial_duration |    duration |   reference |   initial_delta_pct |   signed_delta_pct |   wall_s |   cpu_s |
|:-----------|-----:|-------------------:|------------:|------------:|--------------------:|-------------------:|---------:|--------:|
| C2_10_2    | 1000 |        115983.7000 | 111539.1000 | 109395.8000 |              6.0221 |             1.9592 |  59.6041 | 58.8438 |
| C2_10_7    | 1000 |        115159.9000 | 111486.9000 | 106940.0000 |              7.6865 |             4.2518 |  59.7897 | 58.5156 |

Le gain provient d’une exploration HGS supplémentaire sur une population
initialisée avec notre solution réalisable. Il n’est pas attribué à l’ILS
autonome. Cette comparaison montre le bénéfice de cette continuation sur
ces deux cas, avec une augmentation du temps effectivement utilisé ; elle
n’isole pas un avantage à temps de calcul égal. Une seule graine ne démontre
pas la robustesse du résultat sur toutes les instances de grande taille.
