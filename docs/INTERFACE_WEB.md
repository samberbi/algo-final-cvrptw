# Interface web

Lancer `python -m streamlit run web/app.py`, puis ouvrir http://127.0.0.1:8501.

**Nouvelle expérience** permet de choisir librement les instances de 100 à 1 000 clients, les graines, répétitions et budgets. ILS et recuit constituent les références ; ILS-RVND et ILS-SP sont des variantes expérimentales. Le budget de chaque appel inclut sa construction ; chargement et compilation sont mesurés à part. La finition facultative ajoute un budget distinct.

**Mes campagnes** affiche progression, résultats, tableaux, courbes et exports. Les calculs sont séquentiels et continuent si le navigateur est fermé. L’arrêt conserve les essais déjà terminés. Les résultats locaux se trouvent dans `results/local/`.

**Résultats historiques** sépare les campagnes v2 et v5. Les moyennes changent avec les filtres : il faut toujours lire la taille, le nombre d’essais et le budget avec le gap.

**Simulation** rejoue les solutions des campagnes publiées et locales. Les véhicules se déplacent, attendent, servent et reviennent au dépôt. Les onglets vérifient la couverture, la capacité, les fenêtres et les retours. La fenêtre concerne le début du service ; une attente avant ouverture est autorisée.

L’animation représente un planning vérifié sur les coordonnées du benchmark ; elle ne représente pas les itérations de recherche ni du trafic réel.
