# Couverture du sujet par le livrable final

Cette grille distingue les preuves réalisées et les limites. Les résultats de benchmark ne suffisent pas à prouver tous les aspects métier du sujet initial.

| Exigence | Preuve dans notre projet | Statut et limite |
|---|---|---|
| Capacité et fenêtres temporelles | Formulation C1–C8, contrôleur indépendant, tournées de chaque essai | Réalisé sur les données statiques étudiées |
| Couvrir tous les clients une seule fois, revenir au dépôt, respecter la flotte | Vérification complète sur données originales | Obligatoire pour chaque solution publiée |
| Formalisation mathématique | Variables, domaines, objectif, contraintes, flot anti-sous-tournées et justification de M | Modèle statique détaillé |
| Complexité et intérêt de la métaheuristique | Décision, certificat polynomial, réduction du TSP et rôle de l’exact | Expliqué ; preuve générale distincte des performances empiriques |
| Implémentation en Python | Constructeur, ILS, mouvements, vérification et intégration Python/Numba | Partie propre expliquée ; moteur HGS externe explicitement attribué |
| Choix et justification des méthodes | Registre des améliorations, essais négatifs et comparaison appariée | Gain du pipeline mesuré ; pas d’ablation interne du HGS |
| Au moins vingt instances variées | Catalogue complet de 356 instances, six tailles et six familles | Couverture élargie réellement exécutée |
| Étude statistique et répétitions | 472 pipelines, tableaux, moyennes, dispersion, temps, pires cas | Une graine sur 200–800 clients et deux sur 100/1 000 ; robustesse limitée |
| Références et gap | Données figées, .sol revérifiés, convention DIMACS identique | BKS de la révision figée, pas preuve d’optimalité ni promesse de référence la plus récente |
| Grandes instances | Les 60 instances à 1 000 clients, deux graines chacune | Démontré jusqu’à 1 000 ; plusieurs milliers non démontrés |
| Durée et trafic du sujet initial | Décomposition trajet/attente/service calculée ; limites annoncées | Partiel : distance benchmark optimisée, trafic variable non implémenté |
| Illustration et explication | Données, schémas de mouvements, pipeline, cartes/Gantt, formules et extraits de code réels | Exemples préfixés et résultats non sélectionnés |
| Reproductibilité et livraison | Protocoles figés, sources, empreintes, CSV/JSON, notebook exécuté, PDF et Word | Temps dépendants du matériel ; arrêt au temps non déterministe en nombre d’itérations |

Les moyennes sur le catalogue complet, les essais appariés et les archives cumulées restent des preuves différentes. Aucun score de benchmark n’est présenté comme une garantie de note.
