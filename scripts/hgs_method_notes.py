"""Teaching notes checked against the installed, pinned PyVRP 0.12.2 source."""

HGS_DETAILS = r'''#### 4.5.1. Fonctionnement du composant génétique utilisé

Une solution est une liste ordonnée de tournées. Notre intégration transmet au HGS le meilleur résultat de l’ILS et complète son initialisation par des solutions aléatoires. Le moteur conserve des sous-populations réalisables et irréalisables : ces dernières servent à la recherche, mais seules des solutions complètes et réalisables peuvent être publiées.

À chaque itération, deux parents sont sélectionnés par tournois binaires, avec un contrôle de diversité entre eux. Leur sélection combine qualité et diversité de la population. Le croisement **SREX** (*Selective Route Exchange*) échange des tournées entre les parents. Le descendant peut être incomplet ; la recherche du moteur traite les clients manquants et améliore l’ordre et l’affectation des visites. Les opérateurs activés comprennent des déplacements et échanges de clients ou de chaînes courtes, des échanges de fins de tournées et `SwapStar`.

Pour une solution complète de travail, l’évaluation pénalisée combine la distance et les violations :

$$\widetilde D(S)=D(S)+\lambda_Q E_Q(S)+\lambda_T W(S).$$

$E_Q$ somme les excès de capacité des tournées. $W$ mesure le décalage temporel, ou *time warp*, utilisé dans l’exploration pénalisée : il ne s’agit pas d’une autorisation de retard dans la solution finale. Les poids sont ajustés selon la fréquence de respect de chaque dimension de contrainte. Une recherche supplémentaire avec pénalités renforcées peut rendre un descendant réalisable. L’archive indépendante garde la meilleure solution réalisable et notre contrôleur recalcule ses contraintes sur les données originales.

| Paramètre de PyVRP 0.12.2 | Valeur utilisée | Rôle |
|---|---|---|
| Taille minimale et seuil de réduction d’une sous-population | 25 et 65 | Maintenir un ensemble de solutions et sélectionner les survivants |
| Parents | Tournois de deux candidats | Favoriser qualité et diversité |
| Voisinage local | 40 voisins par défaut | Limiter le nombre de mouvements évalués ; 60 et 80 sont testés séparément |
| Cible de faisabilité par dimension | 0,43, tolérance 0,05 | Adapter les pénalités toutes les 50 observations |
| Recherche de remise en faisabilité | Probabilité 0,8, renforcement ×12 | Traiter un descendant irréalisable |
| Renouvellement de la population sans nouveau record | Seuil de 20 000 itérations | Diversifier si ce seuil est atteint ; l’archive reste conservée |

L’arrêt principal est le budget de temps attribué à la phase HGS. Le seuil d’itérations ne signifie pas qu’un renouvellement a effectivement eu lieu dans chaque essai court. La diversité provient des initialisations aléatoires, des croisements, du contrôle des parents et de la sélection des survivants.

Cette description correspond au [code source de PyVRP 0.12.2](https://github.com/PyVRP/PyVRP/tree/v0.12.2/pyvrp), notamment `GeneticAlgorithm`, `Population`, `PenaltyManager` et SREX. Ces mécanismes appartiennent au moteur externe. Notre code réalise leur intégration avec l’ILS, le partage du temps, les contrôles et les expériences.

L’extrait suivant présente le code d’intégration développé dans le projet.
'''
