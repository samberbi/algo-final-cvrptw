# Audit indépendant des écarts en durée

356 témoins, 964 enregistrements de solutions et les
472 lignes de l'archive ont été contrôlés. Il s'agit de
726 couples instance–ensemble de tournées distincts : les copies ne
sont pas comptées comme de nouveaux essais. Anomalies détectées : **0**.

Le recalcul repart des coordonnées et fenêtres originales, sans importer
`algo.verify` ou `algo.data`. Chaque arc est recalculé en distance euclidienne
tronquée au dixième ; horaires et durées sont évalués en entiers ×10. Les contrôles
portent sur la couverture unique, la capacité, la flotte maximale, les fenêtres,
le retour au dépôt, les services, les coûts enregistrés, les écarts et les
empreintes des 712 fichiers originaux. Les 646
essais du catalogue initial sont inclus. Aucune recherche n'est relancée.

## Ce qui explique les valeurs négatives

L'objectif utilisé est la **somme des durées des tournées avec départs à zéro**.
Le témoin a été choisi pour la distance. Son attente peut être élevée et se
cumule entre véhicules. Les services sont identiques entre deux plans complets.
Un écart négatif indique une durée cumulée inférieure au témoin ; il ne prouve
pas une amélioration par rapport à un optimum temporel. La durée du dernier
camion est une autre mesure, le makespan, et peut évoluer dans l'autre sens.

Sur RC201, la solution locale observée a 4 véhicules, 2 010,4 de trajets,
205,8 d'attentes et 1 000 de services, soit 3 216,2 de durée cumulée. Le témoin
a 9 véhicules, 1 261,8 de trajets, 4 243,5 d'attentes et 1 000 de services,
soit 6 505,3. L'écart −50,56 % provient donc d'un gain d'attente qui dépasse
la hausse des trajets. Ce n'est pas une réduction de 50 % du temps CPU ni
de l'heure de fin de l'ensemble des livraisons.

## Limite méthodologique à conserver

Le calcul est cohérent avec notre modèle. En revanche, la référence n'est pas
une BKS en durée : le seuil « écart inférieur à +6 % au témoin » ne démontre
pas une distance à l'optimum sous 6 %. Il ne faut ni prendre la valeur absolue
des écarts ni les plafonner à zéro, ni changer les unités pour les rapprocher.

Si les départs pouvaient être retardés, une partie des attentes du témoin
pourrait disparaître. Ce serait une autre hypothèse de modélisation, à appliquer
aux deux solutions et à réévaluer complètement ; cet audit ne la change pas.

## Fichiers de lecture

- `COMPARAISON_356_INSTANCES.csv` : les 356 instances de l'archive, décomposition
  solution/témoin, flottes, écarts de durée, de trajet et de makespan. Les colonnes
  propres sont moyennées sur les graines archivées de chaque instance ; les
  budgets sont mixtes et ce tableau n'est pas une campagne uniforme nouvelle.
- `AUDIT_TOUS_RESULTATS.csv` : chaque enregistrement contrôlé, avec son fichier source.
- `AUDIT_TEMOINS_356.csv` : chaque témoin réévalué indépendamment.
- `ECARTS_NEGATIFS_IMPORTANTS.csv` : tous les enregistrements sous −20 %, copies incluses.
- `ANOMALIES.json` et `BILAN.json` : anomalies et périmètre exact du contrôle.

Reproduction : `python scripts/audit_duration_independent.py`.
