# MISSION FINALE — AUDIT, CORRECTION, BENCHMARKS ET VALIDATION COMPLÈTE DU PROJET CVRPTW CESI

Je souhaite finaliser intégralement notre projet d'algorithmique et d'optimisation combinatoire **CVRPTW (Capacitated Vehicle Routing Problem with Time Windows)** pour notre soutenance CESI.

Je veux que tu prennes en charge **l'ensemble du projet actuellement ouvert dans VS Code**, depuis l'analyse du cahier des charges jusqu'à la production d'un livrable final corrigé, scientifiquement rigoureux, exécutable et vérifié.

**Ce n'est pas une demande de plan ou de conseils : je veux que tu inspectes réellement le projet, modifies les fichiers nécessaires, exécutes les tests, réalises les expériences possibles et corriges le livrable.**

Notre priorité est de démontrer que notre algorithme obtient de bonnes performances sur des instances CVRPTW allant de **25 à 1 000 clients**, avec un écart aussi faible que possible par rapport à des références de durée totale compatibles.

Notre objectif académique est de viser un **gap inférieur à 6 %**, sans jamais fausser les données, les mesures ou la définition du gap.

---

# PARTIE 1 — COMPRENDRE ET AUDITER LE PROJET ACTUEL

## 1.1. Inspecter intégralement le projet

Commence par explorer la structure du dépôt VS Code et retrouver :

- Le cahier des charges officiel du projet.
- Les documents du professeur.
- Le Notebook Jupyter final.
- Les fichiers Python.
- Les algorithmes développés par notre équipe.
- Les moteurs externes intégrés.
- Les instances de test.
- Les résultats des expériences précédentes.
- Les fichiers CSV/JSON.
- Les figures et graphiques.
- Les fichiers de configuration.
- Les documentations mathématiques.
- Les dépendances.
- Les éventuels scripts de démonstration.

Ne suppose pas qu'un fichier existe simplement parce qu'il est mentionné ici. Retrouve les chemins réels.

Lis prioritairement les consignes officielles afin de vérifier la conformité du modèle et du livrable.

Conserve une sauvegarde de l'état initial avant les modifications importantes.

## 1.2. Identifier les éventuelles erreurs

Je veux un audit portant sur :

1. La conformité au cahier des charges.
2. La justesse de la modélisation mathématique.
3. La cohérence entre mathématiques et code.
4. La justesse de la fonction objectif.
5. La correction de tous les algorithmes.
6. La gestion des contraintes.
7. La validité des résultats déjà produits.
8. La reproductibilité des expériences.
9. La cohérence du Notebook avec le programme réellement exécuté.
10. Les performances et les possibilités d'amélioration.

Distingue clairement ce qui est validé, ce qui nécessite une correction et ce qui reste incertain.

---

# PARTIE 2 — RESPECT STRICT DES CONSIGNES DU PROFESSEUR

Notre professeur a confirmé des hypothèses très importantes.

## 2.1. Temps de déplacement fixes et symétriques

Pour deux clients A et B :

- A → B = B → A.
- Le temps de déplacement ne varie jamais selon l'heure.
- Il n'y a pas de trafic variable.
- Il n'y a pas de tranches horaires.
- Les fenêtres temporelles concernent les services chez les clients, pas la variation des durées de trajet.

Mathématiquement :

\[
\boxed{c_{ij}=c_{ji}}
\]

et :

\[
\boxed{c_{ij}(t)=c_{ij}\quad\forall t}
\]

Exemple : si A → B prend 10 minutes, B → A prend également 10 minutes, que le déplacement ait lieu à 8 h, 14 h ou minuit.

Ces hypothèses doivent être respectées dans tous les algorithmes, instances adaptées et calculs de coût.

## 2.2. Modélisation en graphe

Notre formulation utilise un graphe orienté pondéré :

\[
G=(V,A)
\]

Avec :

\[
C=\{1,\ldots,n\}
\]

\[
V=C\cup\{o,r\}
\]

Où :

- \(C\) représente les clients.
- \(o\) est le dépôt virtuel de départ.
- \(r\) est le dépôt virtuel de retour.
- \(A\) représente les arcs possibles.
- \(c_{ij}\) est le temps de déplacement sur un arc.

Même si les temps sont symétriques, les décisions de déplacement restent orientées, car l'ordre des visites influence les attentes et les horaires.

Vérifie que toutes les équations et les graphes du livrable respectent cette convention.

## 2.3. Fonction objectif obligatoire

Notre projet doit minimiser la somme des durées complètes des tournées :

\[
\boxed{\min T=\sum_{k=1}^{K}R_k}
\]

Dans notre modèle historique, les départs sont fixés à l'instant zéro.

L'objectif comprend :

\[
\boxed{T=T_{\text{trajets}}+T_{\text{attentes}}+T_{\text{services}}}
\]

Les durées doivent notamment inclure les retours au dépôt.

Nous ne minimisons pas uniquement :

- La distance.
- Le nombre de véhicules.
- Le temps de trajet sans les attentes.
- La durée maximale d'un seul camion.
- Une combinaison arbitraire de plusieurs objectifs.

Toute variante différente doit être explicitement séparée du modèle principal et justifiée par le cahier des charges.

---

# PARTIE 3 — NOUVEAU PROTOCOLE DE BENCHMARK

Je veux adopter un protocole couvrant les tailles suivantes :

| Taille | Instances | Références proposées |
|---|---|---|
| 25 clients | Solomon | Phonin et al. (2025), sous réserve de compatibilité |
| 50 clients | Solomon | Références indépendantes / solveur exact |
| 100 clients | Solomon | Phonin et al. (2025) + références indépendantes |
| 200 clients | Gehring & Homberger | Solutions publiques réévaluées + référence indépendante |
| 400 clients | Gehring & Homberger | Même procédure |
| 600 clients | Gehring & Homberger | Même procédure |
| 800 clients | Gehring & Homberger | Même procédure |
| 1 000 clients | Gehring & Homberger | Même procédure |

Sources :

**Instances Solomon :**
https://vrp.dorronsoro.es/Problem_Instances/CVRPTWInstances.html

**Catalogue SINTEF, références et solutions VRPTW :**
https://www.sintef.no/projectweb/top/vrptw/

**Article Phonin et al. (2025) :**
https://www.mdpi.com/2305-6290/9/3/85

Titre : *Managing Home Healthcare System Using Capacitated Vehicle Routing Problem with Time Windows: A Case Study in Chiang Mai, Thailand*.

**Important :** ces sources ne sont pas automatiquement comparables. Tu dois établir et démontrer leur compatibilité avec notre modèle avant de calculer des gaps officiels.

## 3.1. Vérification de Phonin 2025

L'article présente des résultats pour une variante avec minimisation du temps d'achèvement des tournées.

Je veux que tu vérifies directement dans la publication :

- La fonction objectif exacte.
- Si le retour au dépôt est inclus dans les valeurs rapportées.
- L'heure de départ des véhicules.
- La gestion des attentes.
- La comptabilisation des services.
- Les capacités et les limites de flotte.
- Les horizons temporels.
- Les distances euclidiennes.
- Les règles d'arrondi.
- Les sous-instances Solomon de 25 clients.
- La signification exacte des valeurs déclarées optimales.
- La disponibilité éventuelle des tournées détaillées et des preuves d'optimalité.

Une ambiguïté a été relevée concernant l'inclusion du retour au dépôt dans certains passages de l'article : examine particulièrement ce point.

Les valeurs à vérifier en priorité dans les tableaux originaux sont notamment :

- C101, 25 clients : 2624,01.
- C105, 25 clients : 2530,20.
- C106, 25 clients : 2630,01.
- C201, 25 clients : 3195,27.
- R101, 25 clients : 1295,01.
- C101, 100 clients : 9828,94.

Ces valeurs ne doivent pas être considérées comme officiellement compatibles tant que tu n'as pas validé toutes les conventions.

Si la comparaison directe est impossible, signale-le, explique la différence et ne produis pas de faux gap. Cherche alors une autre référence valide ou construis une référence indépendante.

## 3.2. Instances de 200 à 1 000 clients

Utilise les instances officielles Gehring & Homberger.

Télécharge leurs fichiers d'instances et, lorsqu'elles sont disponibles, les tournées des meilleures solutions publiées.

Ces solutions ont généralement été optimisées selon des critères de flotte et de distance. Nous ne devons donc pas reprendre directement leur coût publié comme durée de référence.

Pour chacune :

1. Lire les tournées publiées.
2. Reconstituer leur ordre de visite.
3. Calculer les horaires à partir du départ à zéro.
4. Calculer les attentes.
5. Ajouter les services.
6. Calculer les retours au dépôt.
7. Vérifier les capacités.
8. Vérifier les fenêtres temporelles.
9. Vérifier l'horizon.
10. Vérifier que chaque client est livré exactement une fois.
11. Recalculer la durée complète.

Si une tournée publiée n'est pas réalisable selon notre modèle, ne l'utilise pas comme référence valide.

Enregistre séparément les solutions publiques réévaluées et les solutions produites par notre propre algorithme.

## 3.3. Construire une référence indépendante

Pour les instances dépourvues d'optimum certifié, utilise également un solveur indépendant.

Tu peux évaluer notamment **Google OR-Tools**, à condition de le configurer correctement pour minimiser la somme des durées de tournées, y compris les attentes et services.

Vérifie soigneusement la modélisation des dimensions temporelles et des coûts de durée. N'utilise pas involontairement un objectif de distance ou de makespan.

Si OR-Tools n'est pas approprié ou ne respecte pas certaines contraintes, recherche une autre approche indépendante.

L'objectif est d'obtenir des références de bonne qualité, avec des budgets de recherche documentés.

Utilise si possible :

- Plusieurs configurations.
- Plusieurs graines.
- Des budgets plus longs que ceux de notre méthode principale.
- Un vérificateur commun indépendant.
- Des fichiers de solutions reproductibles.

**Ne définis pas la BKS de référence d'une instance à partir du résultat de notre propre méthode évaluée dans ce même essai, car cela créerait une comparaison circulaire.**

Si une meilleure solution connue est construite à partir d'un ensemble de méthodes incluant la nôtre, indique clairement ce fait et présente cet indicateur comme un meilleur coût du portefeuille de méthodes, et non comme un benchmark externe indépendant.

## 3.4. Références exactes sur les petites instances

Sur les petites instances, utilise si possible une méthode exacte :

- PLNE/MILP.
- Branch-and-Bound.
- Branch-and-Cut.
- Énumération indépendante sur des cas suffisamment petits.

Conserve :

- La meilleure solution réalisable.
- La meilleure borne inférieure.
- Le statut de résolution.
- Le gap du solveur.
- Le temps de calcul.
- Le nombre de nœuds explorés si disponible.

Ne prétends jamais avoir prouvé l'optimalité si le solveur n'a fourni qu'une solution réalisable.

---

# PARTIE 4 — AUDIT ET CORRECTION DES ALGORITHMES

Notre projet possède une architecture hybride qu'il faut préserver et améliorer.

## 4.1. Heuristiques constructives

Vérifie :

- Regret-2.
- Clarke–Wright Savings.
- Insertion séquentielle.

Pour chacune :

- Comprendre le fonctionnement réel du code.
- Vérifier sa conformité au modèle.
- Vérifier le calcul des coûts d'insertion.
- Contrôler les capacités et les fenêtres.
- Vérifier le traitement des clients difficiles.
- Éviter les solutions incomplètes ou invalides.
- Mesurer la qualité des solutions initiales.

## 4.2. Notre ILS

ILS signifie **Iterated Local Search**, ou recherche locale itérée.

Vérifie son fonctionnement :

1. Construction initiale.
2. Perturbation.
3. Descente locale.
4. Échantillonnage des mouvements.
5. Critère d'acceptation.
6. Conservation du meilleur résultat.
7. Redémarrages.
8. Arrêt selon le budget temporel.

Dans notre version historique, l'acceptation repose sur une tolérance de 0,5 % autour de la meilleure solution, et un redémarrage intervient après 100 cycles sans amélioration.

Vérifie que ces paramètres correspondent bien au code courant.

Teste les mouvements :

- Relocate.
- Swap.
- 2-opt.
- 2-opt*.

Chaque mouvement doit produire une solution correctement évaluée et respectant les contraintes lorsqu'il est accepté comme solution réalisable.

Vérifie également que la meilleure solution trouvée n'est jamais perdue à cause d'une perturbation ou d'une erreur de copie.

## 4.3. Recuit simulé

Vérifie :

- Le calcul de la variation de durée.
- La température.
- La probabilité d'acceptation.
- Le refroidissement.
- Les limites de temps.
- Les règles de faisabilité.
- La sauvegarde du meilleur résultat.

Conserve le recuit comme méthode comparative si son implantation est correcte et pertinente.

## 4.4. PyVRP et HGS

HGS signifie **Hybrid Genetic Search**.

Vérifie :

- Les versions exactes des bibliothèques installées.
- L'encodage du problème dans PyVRP.
- Les coûts de distance et de durée.
- Les fenêtres temporelles.
- Les temps de service.
- La gestion des attentes.
- Les contraintes de charge.
- Les pénalités.
- Les populations réalisables et irréalisables.
- Les croisements génétiques.
- La diversité.
- Les opérateurs de recherche locale.
- Les budgets d'arrêt.
- La conversion des solutions PyVRP dans notre format.

Assure-toi que la solution finale est réévaluée indépendamment avec notre véritable fonction objectif.

Documente ce que nous avons implémenté nous-mêmes et ce que nous avons intégré à partir de bibliothèques externes.

## 4.5. Réservoir de tournées et partitionnement

Vérifie le stockage et la déduplication des tournées.

Le modèle de partitionnement doit notamment respecter :

\[
\min\sum_{p\in\mathcal P}\tau_pz_p
\]

Avec :

\[
\sum_{p\in\mathcal P}a_{ip}z_p=1
\]

pour chaque client \(i\), ainsi que :

\[
\sum_{p\in\mathcal P}z_p\le K
\]

Vérifie :

- La qualité des tournées conservées.
- Leur faisabilité.
- La cohérence des coûts.
- L'absence de doublons inutiles.
- Les contraintes de couverture.
- Le nombre de véhicules.
- Les résultats de SciPy/HiGHS.
- Les statuts d'optimalité du sous-problème.
- Le respect des limites de temps.

Rappelle dans le livrable qu'un optimum du partitionnement restreint n'est pas nécessairement un optimum global du CVRPTW.

## 4.6. Vérificateur commun

Je veux un évaluateur indépendant utilisé pour contrôler les résultats de tous les algorithmes.

Il doit recalculer :

- La couverture des clients.
- La capacité des véhicules.
- Les arrivées.
- Les attentes.
- Les débuts de service.
- Les fins de service.
- Les déplacements.
- Les retours au dépôt.
- La durée de chaque tournée.
- La somme des durées.
- La conformité à l'horizon.

Toute solution utilisée dans les tableaux finaux doit avoir passé cette validation.

---

# PARTIE 5 — CAMPAGNE EXPÉRIMENTALE DE 25 À 1 000 CLIENTS

## 5.1. Campagne pilote

Commence par une campagne de validation sur quelques instances de 25 clients.

Vérifie :

- Le parsing des fichiers.
- La conformité des unités.
- Les durées.
- Les références publiées.
- Les contraintes.
- Les résultats du solveur indépendant.
- Les valeurs obtenues par notre ILS et notre hybride.

N'entreprends pas une grande campagne coûteuse tant que ces tests ne sont pas concluants.

## 5.2. Campagne principale

Une fois la compatibilité validée, teste plusieurs instances des familles :

- C : clients regroupés.
- R : clients répartis aléatoirement.
- RC : structure mixte.

Couvre progressivement les tailles :

25, 50, 100, 200, 400, 600, 800 et 1 000 clients.

Je souhaite une campagne assez large pour produire des statistiques significatives, mais adaptée aux ressources et au temps réellement disponibles.

Utilise plusieurs graines aléatoires, des budgets comparables entre méthodes et des fichiers de configuration reproductibles.

## 5.3. Méthodes à comparer

Compare au minimum les méthodes opérationnelles suivantes :

- Construction initiale.
- ILS autonome.
- Recuit simulé.
- HGS/PyVRP.
- Notre profil hybride initial.
- Notre profil renforcé.
- Profil renforcé avec et sans partitionnement, si pertinent.
- Solveur indépendant de référence.

Évite toute comparaison trompeuse entre une méthode disposant de quelques secondes et une autre disposant de plusieurs heures, sans identifier cette différence de budget.

## 5.4. Mesures à sauvegarder

Pour chaque instance, méthode et graine, enregistre :

- Instance.
- Famille.
- Nombre de clients.
- Méthode.
- Graine aléatoire.
- Budget autorisé.
- Temps réellement consommé.
- Temps CPU lorsque mesurable.
- Nombre de véhicules.
- Durée des déplacements.
- Durée des attentes.
- Durée des services.
- Durée totale.
- Faisabilité.
- Source de la référence.
- Statut de la référence.
- Écart à la référence.
- Éventuelle borne inférieure.
- Statut de la résolution.
- Chemin du fichier contenant la solution.

Conserve aussi les échecs, dépassements de budget et résultats non réalisables afin de mesurer correctement le taux de réussite.

---

# PARTIE 6 — CALCUL SCIENTIFIQUE DES GAPS

Notre objectif académique est de viser un résultat inférieur à 6 %.

Mais il faut distinguer trois situations.

## 6.1. Gap à un optimum démontré

Lorsque nous possédons un optimum \(T^*\) strictement compatible :

\[
\boxed{
Gap=\frac{T_{\text{algo}}-T^*}{T^*}\times100
}
\]

## 6.2. Écart à une meilleure solution connue

Lorsque nous possédons seulement une solution de référence réalisable :

\[
\boxed{
Écart=\frac{T_{\text{algo}}-T_{\text{réf}}}{T_{\text{réf}}}\times100
}
\]

Il ne s'agit pas nécessairement d'un véritable gap à l'optimum.

## 6.3. Certification grâce à une borne inférieure

Si une borne inférieure valide \(L\) existe, calcule :

\[
\boxed{
Gap_{\text{certifié}}\le
\frac{T_{\text{algo}}-L}{L}\times100
}
\]

La formule donne une majoration valide du gap relatif lorsque le coût et la borne sont strictement positifs et compatibles.

Je veux que tu distingues ces métriques dans les CSV, les tableaux et les graphiques.

Ne compare jamais une durée totale à une BKS calculée uniquement en distance.

Ne présente jamais un gain par rapport à la solution initiale comme un gap à l'optimum.

## 6.4. Analyse du seuil de 6 %

Pour chaque famille et taille d'instances, calcule :

- Gap ou écart moyen.
- Médiane.
- Maximum.
- Minimum.
- Écart-type.
- Nombre d'instances sous 6 %.
- Pourcentage d'instances sous 6 %.
- Instances dépassant ce seuil.
- Temps d'exécution correspondant.

Identifie clairement si le seuil de 6 % concerne une moyenne, chaque instance ou un autre indicateur : ne suppose pas que cette règle est précisée si le cahier des charges ne l'indique pas.

Si certaines instances dépassent le seuil, analyse pourquoi et tente de réelles améliorations algorithmiques.

---

# PARTIE 7 — OPTIMISER LES PERFORMANCES DU PROGRAMME

Je veux que tu examines les performances du code pour les grandes instances.

Analyse notamment :

- Les fonctions les plus coûteuses.
- Les calculs répétés d'horaires.
- Les réévaluations inutiles.
- Les voisinages.
- Les caches.
- Les constructions initiales.
- Les mécanismes de perturbation.
- Les redémarrages.
- Les paramètres d'ILS.
- Les paramètres de PyVRP.
- La diversité des solutions.
- Le réservoir de tournées.
- Le partitionnement.
- La consommation mémoire.
- Les temps CPU et muraux.

Utilise un profileur lorsque nécessaire.

Teste les optimisations de code en comparant les résultats avant et après modification.

Je veux que les améliorations soient mesurables et qu'elles ne modifient pas silencieusement le problème résolu.

Si nécessaire, réalise des expériences d'ablation pour mesurer ce que chaque composant apporte.

Par exemple :

- Hybride sans ILS.
- Hybride sans HGS.
- Profil renforcé sans partitionnement.
- Profil complet.
- Recherche locale avec différentes tailles de voisinage.

Conserve une configuration stable pour la validation finale.

---

# PARTIE 8 — TESTS AUTOMATIQUES ET VÉRIFICATION

Je veux que tu développes ou complètes une véritable suite de tests.

## 8.1. Tests mathématiques

Vérifie :

- \(c_{ij}=c_{ji}\).
- Les trajets indépendants du temps.
- Les fenêtres temporelles.
- Les capacités.
- Le départ du dépôt.
- Le retour au dépôt.
- L'horizon.
- Le nombre de véhicules.
- La couverture exacte.
- Les contraintes de précédence temporelle.
- Les équations du PLNE.
- Les valeurs de la fonction objectif.

## 8.2. Tests des algorithmes

Vérifie :

- Regret-2.
- Clarke–Wright.
- Insertion séquentielle.
- ILS.
- Recuit simulé.
- Relocate.
- Swap.
- 2-opt.
- 2-opt*.
- HGS.
- Recherche locale PyVRP.
- Réservoir.
- HiGHS.
- Vérificateur indépendant.

Crée des petits cas où le résultat attendu peut être calculé manuellement.

Teste également les cas limites :

- Client impossible à livrer.
- Capacité exactement atteinte.
- Arrivée exactement à l'ouverture.
- Arrivée exactement à la fermeture.
- Attente importante.
- Retour exactement à l'horizon.
- Plusieurs véhicules inutilisés.
- Clients proches du dépôt.
- Solution sans attente.
- Tournées avec des horaires très serrés.

## 8.3. Tests de non-régression

Pour chaque correction importante :

- Exécute les tests avant et après.
- Vérifie les anciennes instances.
- Vérifie les coûts.
- Vérifie les solutions enregistrées.
- Vérifie les résultats des expériences historiques.

Les anciennes valeurs peuvent changer si elles provenaient d'un bug ; dans ce cas, documente précisément la correction et ne les présente plus comme des résultats directement comparables.

## 8.4. Validation de la reproductibilité

Vérifie qu'un autre étudiant peut reproduire les expériences à partir :

- Du code.
- Des dépendances.
- Des données.
- Des configurations.
- Des graines aléatoires.
- Des commandes documentées.

Les tests réellement exécutés doivent apparaître dans un rapport avec leurs résultats.

---

# PARTIE 9 — CORRECTION COMPLÈTE DU LIVRABLE JUPYTER

Je veux que tu corriges et enrichisses intégralement notre livrable final.

Utilise le cahier des charges et les remarques précédentes du professeur comme références prioritaires.

## 9.1. Structure scientifique souhaitée

Le Notebook doit comprendre :

1. Introduction et contexte du projet.
2. Problématique.
3. Objectifs.
4. Présentation du CVRPTW.
5. Hypothèses.
6. Modélisation en graphe.
7. Étude de complexité.
8. Définition des ensembles et paramètres.
9. Variables de décision.
10. Fonction objectif.
11. Contraintes mathématiques.
12. Description des heuristiques.
13. Description d'ILS.
14. Recherche locale et mouvements.
15. Description du recuit simulé.
16. HGS et PyVRP.
17. Réservoir et partitionnement.
18. Présentation du protocole expérimental.
19. Choix et justification des benchmarks.
20. Vérification des références.
21. Résultats expérimentaux.
22. Analyse statistique.
23. Comparaison des méthodes.
24. Discussion des limites.
25. Conclusion et perspectives.
26. Bibliographie.

Adapte l'ordre exact si le sujet officiel impose un autre format.

La complexité doit notamment être placée avant la modélisation mathématique détaillée, conformément à la remarque antérieure du professeur.

## 9.2. Modélisation mathématique complète

Je veux une formulation rigoureuse.

Vérifie les variables :

- \(x_{ij}^{k}\).
- \(y_i^{k}\).
- \(u_k\).
- \(t_i\), ou une version indexée par véhicule si le modèle l'exige.
- \(R_k\).

Ajoute les variables auxiliaires réellement nécessaires, mais n'en invente pas inutilement.

Explique et vérifie :

- Les contraintes de visite unique.
- Les contraintes de capacité.
- La conservation de flux.
- Les contraintes de départ et retour.
- Les contraintes temporelles.
- Les contraintes de fenêtre.
- Les contraintes d'horizon.
- L'élimination des sous-tournées.
- La formulation Big-M et la validité des bornes.
- La fonction objectif.

Chaque symbole doit être défini.

Chaque équation doit être expliquée dans un langage compréhensible pour le jury.

## 9.3. Complexité

Explique :

- La différence entre NP, NP-difficile et NP-complet.
- Pourquoi l'optimisation CVRPTW est NP-difficile.
- Le lien avec le TSP.
- La version décisionnelle du problème.
- La notion de certificat.
- La vérification polynomiale d'une solution.
- Pourquoi les heuristiques et métaheuristiques sont pertinentes.

N'affirme pas que le problème d'optimisation lui-même est NP-complet sans qualifier correctement la version décisionnelle.

## 9.4. Explication des algorithmes

Pour chaque algorithme, présente :

- Son nom complet.
- Sa catégorie.
- Son principe théorique.
- Son fonctionnement réel dans notre projet.
- Son rôle dans l'architecture.
- Ses avantages.
- Ses limites.
- Ses paramètres principaux.
- Sa contribution aux résultats.

Précise les sigles :

- CVRPTW : Capacitated Vehicle Routing Problem with Time Windows.
- ILS : Iterated Local Search.
- HGS : Hybrid Genetic Search.
- TSP : Traveling Salesperson Problem.
- PLNE : Programmation linéaire en nombres entiers.
- BKS : Best Known Solution.
- CPU : Central Processing Unit.
- PyVRP : bibliothèque Python de résolution des problèmes de tournées.
- HiGHS : solveur d'optimisation mathématique.

Il faut pouvoir comprendre le livrable sans connaître déjà tous les sigles.

## 9.5. Figures et schémas

Ajoute ou améliore :

- Le graphe CVRPTW.
- Un exemple de tournées avec fenêtres.
- Une timeline des horaires.
- Le schéma de l'architecture.
- Les étapes d'ILS.
- Les mouvements locaux.
- Le fonctionnement de HGS.
- Le réservoir de tournées.
- Le partitionnement.
- Les graphiques de résultats.
- Les courbes de convergence.
- Les comparaisons de gaps.
- Les temps CPU.
- Les courbes de montée en charge.

Toutes les figures doivent être produites à partir de données réelles ou clairement identifiées comme des exemples pédagogiques.

---

# PARTIE 10 — STATISTIQUES ET GRAPHIQUES POUR LA SOUTENANCE

Je veux un dossier contenant des résultats propres, présentables et directement exploitables dans notre présentation Canva.

Prépare :

1. Un tableau général des résultats.
2. Un tableau des références par instance.
3. Un tableau des gaps.
4. Un graphique des gaps par taille.
5. Un graphique des performances ILS contre HGS.
6. Une comparaison des profils hybrides.
7. Un graphique de l'apport du partitionnement.
8. Des boîtes à moustaches pour la dispersion.
9. Une courbe du temps de calcul selon le nombre de clients.
10. Une courbe de convergence sur plusieurs instances.
11. Un tableau des taux de faisabilité.
12. Une synthèse des cas difficiles.

Distingue visuellement :

- Optimum démontré.
- Meilleure référence connue indépendante.
- Solution publique réévaluée.
- Résultat de notre algorithme.
- Résultat historique.
- Résultat obtenu avec le nouveau protocole.

Je veux éviter toute ambiguïté scientifique pendant la soutenance.

---

# PARTIE 11 — PRÉPARER LA DÉMONSTRATION FINALE

Prépare un scénario reproductible pour la soutenance.

Il doit permettre de :

1. Charger une instance.
2. Afficher ses caractéristiques.
3. Construire une solution.
4. Exécuter une optimisation.
5. Vérifier la faisabilité.
6. Afficher les tournées.
7. Afficher la durée totale.
8. Décomposer trajets, attentes et services.
9. Comparer la durée à une référence compatible.
10. Afficher le gap ou l'écart approprié.

Choisis une petite instance sur laquelle l'exécution est fiable et suffisamment rapide pour une démonstration orale.

Prépare également des sorties de secours : figures, fichiers de résultats et captures provenant d'une exécution réellement validée.

---

# PARTIE 12 — VALIDATION FINALE DU LIVRABLE

Une fois toutes les corrections terminées :

1. Exécute le Notebook du début à la fin.
2. Vérifie toutes les cellules.
3. Vérifie les imports.
4. Vérifie les dépendances.
5. Vérifie toutes les équations.
6. Vérifie les graphiques.
7. Vérifie les références bibliographiques.
8. Vérifie les tableaux.
9. Vérifie les calculs de gap.
10. Vérifie les preuves d'optimalité revendiquées.
11. Vérifie les scripts de démonstration.
12. Vérifie les correspondances entre code, Notebook et données.
13. Vérifie la conformité intégrale au sujet CESI.
14. Vérifie que les hypothèses du professeur sont respectées partout.
15. Vérifie que les résultats historiques ne sont pas confondus avec les nouveaux benchmarks.

Ne déclare aucun test réussi si celui-ci n'a pas réellement été exécuté.

Ne fabrique aucun résultat manquant.

Ne masque aucun échec de résolution.

Ne modifie pas les données ou les références pour satisfaire artificiellement le seuil de 6 %.

---

# PARTIE 13 — LIVRABLES À PRODUIRE

Je veux, dans le projet VS Code, une version finale contenant :

**1. Notebook Jupyter corrigé**

Complet, structuré, illustré, réexécutable et scientifiquement rigoureux.

**2. Code source corrigé**

Avec les algorithmes opérationnels, les tests et les optimisations validées.

**3. Benchmarks**

Données Solomon et Gehring & Homberger, avec leurs sources et conventions documentées.

**4. Références**

Tableaux des optima certifiés, solutions publiques réévaluées et meilleures références indépendantes.

**5. Résultats expérimentaux**

CSV/JSON complets avec les solutions et les métriques.

**6. Graphiques**

Figures haute résolution, lisibles et utilisables dans Canva.

**7. Rapport de tests**

Détail des tests exécutés, succès, échecs, corrections et tests de non-régression.

**8. Rapport scientifique de performance**

Comparaisons, gaps, statistiques, analyse des résultats, limites et interprétations.

**9. Synthèse pour la soutenance**

Les résultats essentiels, les choix algorithmiques, les contributions personnelles et les arguments à présenter au jury.

**10. Bilan de conformité**

Un tableau indiquant chaque exigence du cahier des charges et la preuve que le livrable y répond, ou la limitation restante.

---

# PARTIE 14 — MÉTHODE DE TRAVAIL ET PRIORITÉS

Je veux que tu réalises le travail dans cet ordre :

**Phase A — Audit**

Inspecter le projet et le cahier des charges, identifier les incohérences et sauvegarder l'état initial.

**Phase B — Compatibilité des références**

Vérifier Solomon et Phonin 2025 sur les petites instances avant de calculer des gaps.

**Phase C — Correction mathématique et algorithmique**

Corriger le modèle, l'évaluateur et les algorithmes.

**Phase D — Tests**

Créer et exécuter les tests unitaires, d'intégration et de non-régression.

**Phase E — Expériences pilotes**

Tester un nombre limité d'instances pour valider les conventions et les performances.

**Phase F — Campagne complète**

Étendre les tests aux tailles 25 à 1 000 clients selon les ressources disponibles et enregistrer les résultats.

**Phase G — Analyse et amélioration**

Calculer les écarts, identifier les cas difficiles et apporter des optimisations justifiées.

**Phase H — Livrable final**

Mettre à jour le Notebook, les figures, la documentation et la bibliographie.

**Phase I — Vérification complète**

Réexécuter le livrable, contrôler les résultats et produire le rapport de validation.

Ne lance pas aveuglément des expériences coûteuses avant d'avoir vérifié la compatibilité des benchmarks.

Si une phase ne peut pas être achevée, précise exactement ce qui a été réalisé et ce qui manque, sans prétendre que tout a été validé.

---

# OBJECTIF FINAL

Je veux que notre projet soit défendable scientifiquement et techniquement devant un jury d'ingénieurs.

À la fin, nous devons être capables de démontrer :

- Que notre CVRPTW respecte les consignes du professeur.
- Que notre modélisation mathématique est correcte.
- Que les heuristiques et métaheuristiques fonctionnent réellement.
- Que les solutions finales sont réalisables.
- Que les références de comparaison sont compatibles.
- Que nos gaps sont calculés honnêtement.
- Que nous comprenons les différences entre optimum, borne inférieure et BKS.
- Que notre architecture hybride apporte une amélioration mesurable.
- Que le programme traite plusieurs tailles d'instances, idéalement jusqu'à 1 000 clients.
- Que notre Notebook est propre, complet et exécutable.
- Que tous les résultats présentés peuvent être justifiés.

**Notre priorité académique est de viser moins de 6 % d'écart sur des références valides, mais notre priorité scientifique est de ne jamais présenter un faux gap ni une comparaison incompatible.**

Commence maintenant par inspecter les fichiers et les consignes du projet, puis réalise toutes les étapes possibles directement dans l'environnement.

À la fin, rends-moi un rapport précis de ce qui a été corrigé, testé, exécuté et validé, avec les résultats obtenus et les limites éventuelles.