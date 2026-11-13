# Évolution vers l’objectif durée

### 4.4. Modifications et vérifications

| Modification | Motif | Vérification |
|---|---|---|
| Objectif PLNE sur les retours $R_k$ | Minimiser la durée cumulée | Concordance de dix optimums avec une énumération indépendante |
| Évaluateur temporel des mouvements | Inclure attente, service et retour | Deux ordres de même trajet mais de durées 34/28 sont distingués |
| Sélection initiale et archive en durée | Éviter une acceptation restée en distance | Coûts confrontés à `verify`, archive non dégradée |
| HGS : coût durée et départ fixé | Aligner le moteur externe sur le modèle | Test d’une attente obligatoire que le départ ne peut masquer |
| Nouvelles références temporelles | Éviter de renommer les gaps distance | Tournées de référence réévaluées, qualification explicite |
| Nouvelle campagne et statistique descriptive | Mesurer l’effet réel de la méthode | Données individuelles, graines, sources figées et effectifs conservés |
| Simplification de C7 pour l'objectif durée | Retirer uniquement une borne supérieure redondante | Dix optimums exacts conservés ; fermeture du dépôt maintenue |
| Audit exhaustif des écarts temporels | Contrôler le seuil par essai et par instance | 646 solutions et 356 témoins revalidés ; dépassements listés en section 6.7 |
| Constructions alternatives et intensification locale | Réduire les mauvaises durées de départ | Essais exploratoires séparés, solutions revalidées et régressions conservées |
| Carte, horaires et temps d'exécution | Relier représentation, objectif et coût de calcul | Figures issues des mêmes résultats enregistrés et commentées individuellement |
| Cache local des voisinages | Supprimer les tris répétés sur une instance immuable | Listes identiques à PyVRP et coûts identiques sur douze paires ; CPU mesuré en section 6.12 |
| Étude multiprocessus | Distinguer délai de réponse et CPU consommé | Un, deux et quatre processus ; parent et workers comptés, démarrage publié |

L’implémentation propre de l’ILS, les adaptateurs et la vérification sont dans le projet ; le moteur génétique externe appartient à PyVRP. Les commentaires du code expliquent les fonctions et les points sensibles.

## Complément : optimisation ciblée en durée

Le profil `duration_refined` ajoute plusieurs constructions, une recherche locale externe PyVRP à voisinages progressifs et un réservoir de tournées évalué en durée. Les essais encore défavorables reçoivent une continuation HGS identifiée, avec le temps précédent inclus. Les résultats individuels, les budgets et les limites sont détaillés dans [OPTIMISATION_DUREE_CIBLEE.md](OPTIMISATION_DUREE_CIBLEE.md). La campagne initiale reste inchangée.


## Compléments expérimentaux et rédactionnels

Les sections 6.10 et 6.11 ajoutent une [sensibilité contrôlée](SENSIBILITE_CONTROLEE_DUREE.md) du profil ILS–HGS et une [analyse des scénarios](ANALYSE_SCENARIOS_DUREE.md) sur le catalogue initial. Le contexte métier, la réduction TSP, les fenêtres par objet/client, le départ à zéro et les budgets sont explicités. Cette passe ne modifie pas les opérateurs, le profil par défaut ou les meilleures tournées conservées.


## Réduction du temps CPU

Le profil renforcé réutilise désormais les voisins calculés sur une même instance immuable et évite les transferts identiques vers le moteur. Le tri stable et les préfixes sont vérifiés contre PyVRP. La [section CPU et parallélisme](TEMPS_CPU_ET_PARALLELISME.md) rapporte les mesures avant/après à travail et coûts identiques, puis les résultats sur un, deux et quatre processus. Le calcul du CPU inclut tous les workers. Aucun ancien temps écoulé n’est renommé en temps CPU ; les meilleurs résultats historiques restent conservés.


## Extension temporelle Dabia2013

Le module `algo/dabia.py` ajoute une insertion et un ILS propres avec relocate, swap, 2-opt et 2-opt*. Les évaluations utilisent les fonctions temporelles et départs optimaux du contrôleur externe MAMUT 0.12.0 (`td-fold/2`), sans HGS statique. Le manifeste fige six instances à 25 clients. Après six essais préliminaires, 18 résolutions à trois graines sont réalisables et au coût des BKS Duration, avec CPU maximal 5,031 s sur ce pilote. Les 16 tests de l’extension passent. Les limites, les notes de recertification et les paramètres sont détaillés dans [EXTENSION_DABIA2013.md](EXTENSION_DABIA2013.md). Les anciennes campagnes statiques ne sont ni supprimées ni renommées.
