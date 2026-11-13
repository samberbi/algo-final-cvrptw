# Variante simplifiée — construction seule, ablation explicite

La variante testée est **construction seule**, déjà disponible dans le projet :
douze constructions regret-2, sélection du meilleur plan selon la durée totale,
sans ILS, sans recuit, sans recherche locale PyVRP, sans HGS et sans partitionnement.
Ce profil est une heuristique constructive, pas une nouvelle métaheuristique.
Le profil renforcé reste le profil de production ; il n'est pas remplacé.

Le lot a été fixé avant les résultats : six familles à 100 clients, C101/25
et R2_10_8/1000 ; graines 4101 et 4102. Aucun arrêt ou choix de solution n'est
piloté par le gap. Les références sont lues après la résolution. Les mêmes
contraintes et le même objectif trajets + attentes + services sont appliqués.

La construction s'arrête après douze tentatives. Le renforcé reçoit cinq
secondes de budget total souple. Ce sont des niveaux d'effort différents,
mesurés par CPU et temps réel ; ce n'est pas une preuve d'égalité de CPU.
Chaque tournée et chaque référence a été recalculée indépendamment à partir
des coordonnées originales. Les deux méthodes ont exactement les mêmes
références par instance. C101/25 utilise OR-Tools enregistré ; les autres cas
utilisent les plans publics distance réévalués en durée, sans preuve d'optimum.

Le gap moyen présenté est la moyenne des deux graines lorsque les deux écarts
sont positifs. Lorsqu'elles battent ou égalent la référence, un statut le dit.
Les valeurs signées réelles et toutes les graines restent dans les CSV.
Une référence dépassée ne devient pas un optimum et aucun résultat n'est forcé
entre les bornes souhaitées.

| Instance   |   Clients | Construction seule : gap moyen / statut     | Renforcé : gap moyen / statut               |
|:-----------|----------:|:--------------------------------------------|:--------------------------------------------|
| C101       |        25 | 9.1748 %                                    | Référence égalée — optimalité non démontrée |
| C101       |       100 | 4.5979 %                                    | Référence égalée — optimalité non démontrée |
| C201       |       100 | Référence égalée — optimalité non démontrée | Référence égalée — optimalité non démontrée |
| R101       |       100 | Référence dépassée sur les deux graines     | Référence dépassée sur les deux graines     |
| R201       |       100 | Référence dépassée sur les deux graines     | Référence dépassée sur les deux graines     |
| RC101      |       100 | 10.7601 %                                   | Référence dépassée sur les deux graines     |
| RC201      |       100 | Référence dépassée sur les deux graines     | Référence dépassée sur les deux graines     |
| R2_10_8    |      1000 | Référence dépassée sur les deux graines     | Référence dépassée sur les deux graines     |

## Détail de la qualité et du temps

| instance   |   clients | methode      |   essais |   faisables |   duree_moyenne |   reference |   cpu_moyen_s |   reel_moyen_s |   references_depassees |   references_egalees |   ecarts_positifs |   depassements_six |
|:-----------|----------:|:-------------|---------:|------------:|----------------:|------------:|--------------:|---------------:|-----------------------:|---------------------:|------------------:|-------------------:|
| C101       |        25 | construction |        2 |           2 |       2864.2000 |   2623.5000 |        0.0078 |         0.0066 |                      0 |                    0 |                 2 |                  2 |
| C101       |        25 | refined      |        2 |           2 |       2623.5000 |   2623.5000 |        0.4219 |         0.6053 |                      0 |                    2 |                 0 |                  0 |
| C101       |       100 | construction |        2 |           2 |      10279.1500 |   9827.3000 |        0.0234 |         0.0271 |                      0 |                    0 |                 2 |                  0 |
| C101       |       100 | refined      |        2 |           2 |       9827.3000 |   9827.3000 |        0.5312 |         0.5786 |                      0 |                    2 |                 0 |                  0 |
| C201       |       100 | construction |        2 |           2 |       9589.1000 |   9589.1000 |        0.0312 |         0.0287 |                      0 |                    2 |                 0 |                  0 |
| C201       |       100 | refined      |        2 |           2 |       9589.1000 |   9589.1000 |        0.5234 |         0.6153 |                      0 |                    2 |                 0 |                  0 |
| R101       |       100 | construction |        2 |           2 |       3507.4500 |   3715.8000 |        0.0312 |         0.0285 |                      2 |                    0 |                 0 |                  0 |
| R101       |       100 | refined      |        2 |           2 |       3543.3500 |   3715.8000 |        0.3828 |         0.5294 |                      2 |                    0 |                 0 |                  0 |
| R201       |       100 | construction |        2 |           2 |       4025.4000 |   6296.6000 |        0.0391 |         0.0538 |                      2 |                    0 |                 0 |                  0 |
| R201       |       100 | refined      |        2 |           2 |       3038.0500 |   6296.6000 |        0.5391 |         0.6061 |                      2 |                    0 |                 0 |                  0 |
| RC101      |       100 | construction |        2 |           2 |       3313.5000 |   2991.6000 |        0.0312 |         0.0292 |                      0 |                    0 |                 2 |                  2 |
| RC101      |       100 | refined      |        2 |           2 |       2939.8000 |   2991.6000 |        0.5781 |         0.5970 |                      2 |                    0 |                 0 |                  0 |
| RC201      |       100 | construction |        2 |           2 |       3957.6500 |   6505.3000 |        0.0312 |         0.0317 |                      2 |                    0 |                 0 |                  0 |
| RC201      |       100 | refined      |        2 |           2 |       3216.9500 |   6505.3000 |        0.5781 |         0.5926 |                      2 |                    0 |                 0 |                  0 |
| R2_10_8    |      1000 | construction |        2 |           2 |     107031.2000 | 114208.0000 |        4.9531 |         5.0018 |                      2 |                    0 |                 0 |                  0 |
| R2_10_8    |      1000 | refined      |        2 |           2 |      82894.5000 | 114208.0000 |        4.6719 |         4.8465 |                      2 |                    0 |                 0 |                  0 |

La simplification ne garantit pas un écart entre les bornes académiques :
elle peut augmenter les attentes, dépasser six pour cent, ou continuer à
améliorer un témoin heuristique. Le choix de référence reste déterminant.
Les observations de ce petit lot ne sont pas généralisées aux 356 instances.
Ces essais d'ablation ne remplacent ni les meilleures solutions archivées ni
les statistiques des campagnes précédentes.


## Effectifs et moyenne conditionnelle

| methode      |   essais |   positifs |   references_depassees |   references_egalees | moyenne_positive_pct            | mediane_positive_pct            |   superieurs_six |
|:-------------|---------:|-----------:|-----------------------:|---------------------:|:--------------------------------|:--------------------------------|-----------------:|
| construction |       16 |          6 |                      8 |                    2 | 8.1776 %                        | 9.1748 %                        |                4 |
| refined      |       16 |          0 |                     10 |                    6 | Références dépassées ou égalées | Références dépassées ou égalées |                0 |

La moyenne positive ne porte que sur la colonne positifs. Elle ne représente pas tous les essais et ne constitue pas un gap certifié. Les références hétérogènes et les statuts restent explicitement décrits.
