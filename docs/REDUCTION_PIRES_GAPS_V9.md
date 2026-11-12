## 9. Réduire les pires écarts : réglage du temps et reprises ciblées

### 9.1. Diagnostic et protocole

La campagne de référence v8 reste figée : son pire essai vaut 11,021 %. Dix essais, sur sept instances, dépassent ou atteignent 7 %. Les familles R2 sont particulièrement représentées. Nous avons donc évalué le partage du temps, le nombre de voisins, les redémarrages et la recombinaison de tournées. Les BKS servent à l’évaluation et à cette sélection postérieure des cas difficiles ; elles ne sont jamais transmises aux moteurs.

Sur trois cas de développement et la graine 3101, quatre variantes disposent chacune de 120 s de recherche. La variante est sélectionnée d’après son pire gap, puis sa moyenne. Toutes enregistrent la convergence interne du HGS ; la référence est réexécutée avec la même instrumentation.

| variant | runs | valid | mean_gap | worst_gap | mean_total_s | under7 |
| --- | --- | --- | --- | --- | --- | --- |
| neighbors60 | 3 | 3 | 6,090 | 7,926 | 126,480 | 2 |
| neighbors80 | 3 | 3 | 6,812 | 8,735 | 126,030 | 2 |
| split20 | 3 | 3 | 5,379 | 6,717 | 126,018 | 3 |
| split60 | 3 | 3 | 6,748 | 7,153 | 126,049 | 1 |

Le partage 20/100 est retenu pour une confirmation sur les sept cas, avec deux nouvelles graines, 3102 et 3103. Il reste une variante contrôlée sur des cas difficiles : il ne remplace pas rétroactivement les résultats du catalogue complet.

### 9.2. Confirmation à budget inchangé

| variant | runs | valid | mean_gap | worst_gap | mean_total_s | under7 |
| --- | --- | --- | --- | --- | --- | --- |
| split20 | 14 | 14 | 4,642 | 6,638 | 125,238 | 14 |
| split60 | 14 | 14 | 6,326 | 8,805 | 124,888 | 8 |

La moyenne sur ces quatorze essais passe de 6.326 % à 4.642 % ; les pires valeurs sont 8.805 % et 6.638 %. Le réglage 20/100 est sous 7 % dans 14/14 essais. Deux graines par cas restent limitées et les sept instances avaient été sélectionnées d’après leurs difficultés antérieures. Il n’en résulte aucune garantie sur des graines ou instances futures.

Les deux cas à 800 clients disposent ici de 120 s, comme leur référence réexécutée ; ils n’avaient que 64 s dans le catalogue initial. La comparaison interne est à budget égal, mais elle ne doit pas être confondue avec une amélioration à coût inchangé face au catalogue pour ces deux cas.

### 9.3. Recherche longue, départs multiples et partitionnement

Une autre expérience porte sur trois cas difficiles : une recherche de 360 s, ou trois recherches de 120 s. Chaque pipeline consacre au plus 20 s à notre ILS puis le reste au HGS. Les trois départs utilisent les graines 3301, 3302 et 3303 ; la recherche longue utilise 3301. Les tournées réalisables de toutes les phases sont ensuite proposées au partitionnement restreint, avec au plus 5 s supplémentaires dans les deux stratégies.

| instance | strategy | before_pool | gap_pct | pool_gain_pp | total_s |
| --- | --- | --- | --- | --- | --- |
| R2_10_7 | long | 1,980 | 1,980 | 0,000 | 365,316 |
| R2_10_7 | multistart | 4,209 | 4,209 | 0,000 | 374,704 |
| R2_10_8 | long | 3,286 | 3,286 | 0,000 | 365,981 |
| R2_10_8 | multistart | 4,569 | 4,569 | 0,000 | 379,341 |
| RC2_10_4 | long | 2,843 | 2,843 | 0,000 | 367,367 |
| RC2_10_4 | multistart | 4,135 | 4,135 | 0,000 | 379,700 |

Sur ce lot, le critère du pire gap favorise la stratégie `long`. Le partitionnement n’apporte aucun gain sur ces six essais au budget testé.

`before_pool` est le meilleur gap avant partitionnement ; `gap_pct` est celui obtenu après, et `pool_gain_pp` mesure son gain marginal en points. Toutes les constructions, préparations et recombinaisons sont facturées. Le budget nominal est comparable, mais les trois constructions peuvent augmenter le temps réel. Cette expérience de développement ne prouve pas une supériorité générale des redémarrages. Une borne ou une optimalité du partitionnement ne concerne que son pool de tournées, jamais le CVRPTW complet.

### 9.4. Reprise des dix anciens essais défavorables

Chacun des dix essais initialement à au moins 7 % est repris depuis sa propre solution, avec 180 s de HGS supplémentaires, 40 voisins et une nouvelle graine dérivée de la graine initiale. Nous ne remplaçons pas une mauvaise graine par une autre graine favorable : chaque ancien essai possède une reprise identifiée. Son calcul initial et sa reprise sont intégralement comptés.

| instance | seed | before | after | previous_total_s | additional_s | total_s |
| --- | --- | --- | --- | --- | --- | --- |
| R2_10_2 | 2101 | 7,012 | 1,727 | 125,678 | 180,267 | 305,945 |
| R2_10_4 | 2101 | 8,110 | 4,408 | 125,501 | 180,411 | 305,912 |
| R2_10_4 | 2102 | 7,790 | 2,349 | 125,814 | 180,245 | 306,059 |
| R2_10_7 | 2101 | 8,757 | 2,580 | 126,254 | 180,541 | 306,796 |
| R2_10_7 | 2102 | 7,502 | 3,461 | 125,136 | 180,399 | 305,536 |
| R2_10_8 | 2101 | 8,735 | 3,995 | 125,906 | 180,428 | 306,335 |
| R2_10_8 | 2102 | 11,021 | 2,425 | 125,690 | 180,245 | 305,935 |
| R2_8_7 | 2101 | 7,121 | 2,101 | 67,164 | 180,215 | 247,378 |
| R2_8_8 | 2101 | 7,359 | 2,235 | 67,592 | 180,319 | 247,911 |
| RC2_10_4 | 2102 | 7,362 | 2,040 | 125,524 | 180,399 | 305,922 |

Le cas R2_10_8, graine 2102, passe de **11,021 % à 2.425 %**. Le pire résultat parmi les dix reprises vaut **4.408 %**. La somme des durées supplémentaires mesurées est 1803.47 s, réparties sur six processus lors de l’expérience ; ce cumul n’est pas une durée murale séquentielle observée.

### 9.5. Archive consolidée et limites d’interprétation

Les 462 autres résultats restent inchangés. Après les dix reprises, les 472 solutions de l’archive couvrent toujours les 356 instances : le pire gap est **6.889 %**, et 472/472 essais sont sous 7 %. La moyenne donnant le même poids à chaque instance est **1.988 %** ; sur les 60 instances à 1 000 clients, elle est **3.320 %**.

Il s’agit d’une **archive après reprises ciblées, à budgets différents**, et non d’une nouvelle campagne uniforme de 120 s. Les références v8 à 2,078 % de moyenne et 11,021 % au pire restent accessibles. La baisse du pire gap est réelle et vérifiée, mais son coût supplémentaire doit accompagner le résultat. Les résultats de confirmation du réglage 20/100 constituent une preuve distincte de cette reprise d’archive.

Le profil optionnel `ils_hgs_refined` expose le partage court-ILS/long-HGS. Le script `refine_worst_v9.py` reproduit les reprises expérimentales. Les sources, protocoles, traces et toutes les régressions sont conservés dans `results/worst_v9/`. Le HGS reste celui de PyVRP, attribué à ses auteurs. Le journal d’évolution répertorie cette phase et les décisions prises.

Pour une nouvelle résolution : `python cli.py R2_10_8 --method ils_hgs_refined --seconds 120 --seed 3102`. Le profil web correspondant est **ILS court + HGS (v9)**. Pour reprendre une solution précise : `python scripts/resume_solution_v9.py results/catalog_v8/runs/R2_10_8_2102.json --seconds 180 --neighbors 40 --seed 22102`. Le second exemple ajoute du temps à une solution existante ; il ne représente pas une résolution neuve de 180 s.
