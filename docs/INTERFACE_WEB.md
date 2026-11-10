# Interface web et simulation

Lancer `.\.venv\Scripts\python.exe -m streamlit run web/app.py`, puis ouvrir http://127.0.0.1:8501.

La page **Simulation** propose les solutions de la nouvelle étude ILS/recuit, les anciennes solutions ALNS clairement étiquetées et les campagnes locales. Choisir une instance et un run, puis **Lecture**. Les commandes permettent de mettre en pause, changer la vitesse, revenir au début et déplacer l'horloge. Les camions roulent, attendent l'ouverture, servent puis reviennent au dépôt.

L'onglet **Vérifier toutes les contraintes** contrôle la couverture unique des clients, chaque fenêtre, la charge de chaque camion, la flotte et les retours. Une arrivée avant ouverture est autorisée avec attente ; le début du service doit être dans la fenêtre, pas nécessairement sa fin. La charge de livraison décroît après le service. Les contrôles portent à la fois sur le plan complet et sur la progression animée.

**Graphiques du run** montre fenêtres et débuts de service, charge restante, retours, décomposition trajet/attente/service et convergence. Chaque graphique est expliqué. **Schémas et méthode** décrit ILS, recuit et voisins. La **Vue d'ensemble** donne les courbes agrégées de convergence et la sensibilité. **Résultats historiques** permet de sélectionner la nouvelle comparaison ou une ancienne campagne ALNS ; leurs statistiques restent séparées.

**Nouvelle expérience** propose ILS et recuit sur une ou plusieurs instances, avec répétitions, graines et budget. Le budget local commence à l'entrée du solveur et inclut la construction ; le préchauffage et le chargement sont hors budget. La décomposition facultative ajoute une phase ILS et un budget distinct : elle n'est pas utilisée dans le benchmark principal. Les campagnes locales sont séquentielles. Les résultats restent sur cet ordinateur et la fermeture du navigateur ne les arrête pas.

La comparaison publiée utilise un protocole plus contrôlé : départ commun calculé une seule fois par paire, puis même budget d'amélioration pour les deux méthodes. Elle est reproduite par `scripts/run_ils_benchmark.py`, et non en mélangeant les campagnes locales.

La simulation rejoue des horaires fixes et vérifiés sur les coordonnées du benchmark. Elle ne simule pas le trafic réel, les pannes ou des demandes dynamiques. L'animation n'est pas une visualisation des itérations du solveur.
