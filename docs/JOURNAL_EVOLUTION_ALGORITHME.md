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

L’implémentation propre de l’ILS, les adaptateurs et la vérification sont dans le projet ; le moteur génétique externe appartient à PyVRP. Les commentaires du code expliquent les fonctions et les points sensibles.