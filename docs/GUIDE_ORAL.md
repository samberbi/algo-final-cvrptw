# Préparer la présentation

Le notebook actif est `notebooks/Livrable_Final_CVRPTW.ipynb`.
Le rapport présente le CVRPTW statique, à distance DIMACS et contraintes strictes.

## Déroulé court

1. Expliquer client, dépôt, capacité, fenêtre et attente.
2. Dire pourquoi début et fin de service diffèrent, puis présenter C1–C8.
3. Décrire construction regret-2, perturbation ILS, recherche locale et archive.
4. Montrer un groupe de tournées : mêmes données, remappage et contrôle global.
5. Comparer les résultats, annoncer leurs budgets et montrer aussi les cas difficiles.

## Chiffres à citer avec leur périmètre

- Validation : 36 instances, cinq graines, deux méthodes ; trois tailles équilibrées.
- ILS : moyenne globale équilibrée 4.933 % ; grands cas 10.055 %.
- Avant/après R1_10_1 : 9.746 % contre 4.234 %, à 25 secondes identiques.
- Une moyenne favorable ne garantit ni chaque instance ni chaque futur essai.

## Exemple d'introduction en anglais

We study delivery routes with vehicle capacity and strict time windows. Our
objective is the total DIMACS distance. We implemented iterated local search
and a simulated annealing comparator, with an independent solution checker.
The optimized search works on groups of complete routes without changing the
original demands, time windows or fleet limit. We compare measured results on
a balanced set and report both average quality and difficult cases.

## Questions cruciales

- Pourquoi la distance ? Pour comparer à la même référence DIMACS. La durée avec
  attente et service est différente ; notre périmètre statique doit être annoncé.
- Pourquoi des groupes ? Pour consacrer davantage de recherche aux tournées
  qui peuvent interagir, puis revérifier la solution globale.
- Pourquoi pas tous les opérateurs ? SWAP* a été testé ; son ajout n'a pas été
  retenu par défaut lorsque le coût de calcul dégradait le résultat sous budget.
- Pourquoi cinq graines dans le nouveau lot ? Elles complètent la diversité des
  douze grandes instances ; l'étude diagnostique conserve vingt graines.
- Pourquoi le temps total dépasse le budget ? Construction séparée et fin des
  opérations atomiques. Ne pas inclure silencieusement le préchauffage Numba.
