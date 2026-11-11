# Corrections demandées et réalisation

> Édition active du 11 novembre 2026 : `LIVRABLE_FINAL.md` et le Notebook final
> présentent la validation optimisée v2 : 36 instances, cinq graines par méthode,
> douze instances par taille, plus 80 essais avant/apres a vingt graines sur deux
> cas. La calibration séparée comporte 324 essais, avec six familles à 1 000 clients.
> Les 1 120 essais décrits dans le tableau historique ci-dessous restent une
> référence v1 ; ils ne sont pas réattribués au code optimisé. Le bilan complet
> et les limites de gap sont publiés dans `results/optimization_v2/`.


Ce document traduit la consigne du projet et les remarques de l'enseignante rapportées dans la conversation. Le ZIP du groupe G5 a servi d'exemple de présentation ; ses hypothèses, résultats ou erreurs ne sont pas adoptés comme cahier des charges.

| Demande | Réponse dans la nouvelle édition |
|---|---|
| Formaliser les données et écrire les appartenances | Ensembles C, V, A, ensemble des véhicules, paramètres, domaines et quantificateurs ; explication française de chaque équation |
| Corriger le PLNE complet | C1 affectation, C2 entrées/sorties, C3 flotte, C4 capacité, C5 fenêtres, C6 propagation, C7 retours, C8 connexion au dépôt |
| Justifier la complexité | Certificat polynomial et réduction depuis le TSP symétrique |
| Remplacer ALNS ; VNS et tabou déjà pris | ILS principale et recuit simulé direct ; code réellement remplacé et tests interdisant la réparation pendant la recherche |
| Justifier la méthode et expliquer le code | Rôle de la construction, perturbation, recherche locale, règle d'acceptation et archive ; pseudo-code et lien aux fonctions |
| Tester au moins vingt instances variées | 28 instances : 24 Solomon à 100 clients, deux à 200 et deux à 1 000 |
| Étude statistique rigoureuse | 20 graines par instance/méthode, départs communs, budgets identiques, moyennes, médianes, écarts-types, pire cas, seuils et comparaison appariée |
| Comparer modèle et algorithmes | Dix résolutions PLNE et cinq graines par méthode sur chaque petit cas ; bornes et limites de temps explicites |
| Étudier les paramètres | Huit variantes, six instances de développement et trois graines : 144 essais |
| Étudier les changements de variables/contraintes | Capacité ±20 %, flotte ±20 %, largeur des fenêtres ±30 %, un facteur à la fois ; 252 observations |
| Montrer la convergence | Courbes temporelles moyennes et bandes interquartiles, départ commun, gain des derniers 20 % du budget |
| Temps en fonction de la taille | En plus des budgets imposés, 36 essais à 50 000 propositions fixées, avec limites d'interprétation explicites |
| Expliquer schémas et graphiques | Texte de lecture et portée sous chaque figure, sans confondre illustration et preuve |
| Démonstration et soutenance | Notebook court, interface animée avec contrôle des contraintes et guide oral |

Le sujet ne prescrit pas un nombre de répétitions ou une liste de 56 Solomon : vingt graines est notre choix de protocole, pas une exigence attribuée à l'enseignante. Le seuil du barème ne permet pas de promettre une note ; moyenne et pire cas restent distincts.

Toutes les contraintes du projet sont conservées : dépôt unique ; capacité homogène ; demande indivisible ; chaque client exactement une fois ; flotte maximale ; départ à zéro ; attente autorisée ; fenêtre inclusive sur le début du service ; fin éventuellement après fermeture client ; retour avant ou à la fermeture du dépôt ; temps et distances fixes et symétriques. Une baisse de distance ne compense jamais une violation.

Les anciens résultats ALNS et comparaisons Chakib restent dans l'historique. Ils ne servent pas de résultats ILS/recuit. Le livrable principal est `LIVRABLE_FINAL.md`, généré depuis `docs/LIVRABLE_ILS_SOURCE.md` et les nouvelles mesures.
