# Revue finale de conformité du livrable

Cette revue confronte la livraison au sujet officiel « B02 — Algorithmique et optimisation », pages PDF 5 à 8 (pages imprimées 8 à 11). Elle distingue les éléments vérifiés des exigences que les expériences actuelles ne démontrent pas.

| Attente du sujet | Éléments présents et contrôle | Limite ou conclusion |
|---|---|---|
| Formaliser les données et le problème | Graphe orienté, dépôt scindé pour le modèle, demandes, capacité, horaires, variables et contraintes C1 à C8 ; flot de connexion et grands M explicités | Modèle de CVRPTW statique ; les fenêtres portent sur le début du service |
| Définir et justifier la méthode | ILS propre, perturbations, recherche locale, acceptation et arrêt ; intégration du HGS externe PyVRP 0.12.2 | Le composant externe est cité ; il ne doit pas être présenté comme un moteur développé dans ce projet |
| Expliquer l’implémentation | Extraits réels et exemples, représentation des tournées, initialisation, contrôles, chronométrage ; ajout des mécanismes population/tournois/SREX/pénalités du HGS | Les états de travail du HGS peuvent être pénalisés ; seules les solutions finales vérifiées sont publiées |
| Donner des résultats variés et reproductibles | 356 instances, six tailles, 472 pipelines de référence, données et sources figées ; toutes les répétitions et leurs budgets sont conservés | Une graine aux tailles intermédiaires, deux à 100 et 1 000 clients : variabilité encore peu estimée |
| Comparer la qualité à une référence | Distances tronquées DIMACS identiques, BKS consultées après la résolution, moyennes par instance et par essai distinguées | Une BKS est une meilleure solution connue, pas nécessairement un optimum prouvé |
| Étudier temps, robustesse et paramètres | Temps de recherche et temps total distingués ; ablations et variantes défavorables conservées ; confirmation sur de nouvelles graines | Réglage ciblé sur des cas difficiles, sans preuve de généralisation à tous les cas |
| Justifier les améliorations | Nouveau partage 20/100 confirmé sur 14 essais ; voisinages 60/80, recherche longue, départs multiples et partitionnement comparés | Le partitionnement n’améliore aucun des six essais de la dernière étude ; ce résultat négatif reste indiqué |
| Permettre la relecture et l’exécution | Notebook exécuté, HTML, PDF, Word, CLI, interface web, tests et reçu courant `livraison/VALIDATION.json` | Réexécuter le notebook recalcule les analyses et exemples ; cela ne relance pas les centaines de recherches |
| Minimiser la durée et tenir compte du trafic | La livraison explicite le choix expérimental d’une distance statique, demandé pour cette édition | L’objectif originel de durée avec trafic horaire n’est pas démontré par ces benchmarks |
| Passer à plusieurs milliers de villes | Expériences jusqu’à 1 000 clients | Le passage à plusieurs milliers n’est pas démontré ; 1 000 clients ne remplit pas à lui seul cette exigence |

## Lecture correcte du bilan

La campagne de référence contient **472 solutions réalisables sur 356 instances** : gap moyen par instance **2,078 %**, pire essai **11,021 %**. Ces résultats restent inchangés.

L’archive après **dix reprises de 180 secondes supplémentaires** conserve les mêmes 472 solutions, dont dix améliorées : moyenne par instance **1,988 %**, maximum **6,889 %**. Les temps initiaux et supplémentaires sont tous comptés. Il s’agit de budgets variables et d’une sélection ciblée après observation des difficultés, pas d’une nouvelle campagne complète à budget uniforme.

La confirmation indépendante du réglage 20 s ILS / 100 s HGS porte sur sept cas et deux nouvelles graines : **14/14 solutions sous 7 %**, moyenne **4,642 %**, maximum **6,638 %**. Ce lot ne garantit pas un plafond de 7 % sur une instance ou une graine future.

## Corrections de cette passe

Les mécanismes internes du moteur externe sont expliqués avec les valeurs de sa version installée, les extraits d’intégration sont actualisés, les entrées de graines sont contrôlées et les modules concernés sont remis en forme. Le reçu courant contient le nombre de tests réellement exécutés et les empreintes des fichiers livrés. Aucune mesure historique n’a été réécrite pour améliorer le bilan.
