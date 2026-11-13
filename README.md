# CVRPTW — Minimisation de la durée totale

**Version de remise — 13 novembre 2026.** L’objectif est la somme des durées des tournées : trajets + attentes + services, départs fixés à zéro et retour au dépôt compris. La capacité, les fenêtres et la flotte maximale restent strictes. Le temps de calcul du programme est une mesure séparée.

## Ouvrir le livrable

- [Rapport PDF](livraison/RAPPORT_CVRPTW.pdf), [Word pour annotation](livraison/RAPPORT_CVRPTW.docx).
- [Notebook exécuté](notebooks/Livrable_Final_CVRPTW.ipynb), [HTML](notebooks/Livrable_Final_CVRPTW.html), [Markdown illustré](LIVRABLE_FINAL.md).
- [Formulation mathématique](docs/MODELE_DUREE.md), [évolution de l’algorithme](docs/JOURNAL_EVOLUTION_ALGORITHME.md).
- [Tous les résultats en durée](livraison/RESULTATS_DUREE.html), [CSV des 646 essais](livraison/RESULTATS_DUREE.csv), [356 instances](livraison/INSTANCES_DUREE.csv), [statistiques descriptives](livraison/STATISTIQUES_DESCRIPTIVES_DUREE.csv).

## Résultats mesurés et références

La campagne couvre les **356 instances** Solomon et Gehring–Homberger de 100 à 1 000 clients. Elle contient **646 résolutions nouvelles et réalisables** : 472 pour la couverture et 180 pour la comparaison à vingt graines de trois méthodes sur trois cas, avec six essais communs aux deux périmètres. Chaque résolution dispose de dix secondes de recherche ; la construction et la préparation s’ajoutent au temps réel.

Sur le lot de couverture, le gain moyen par instance depuis la construction est **13,52 %**. L’écart moyen au plan témoin réévalué en durée est **−17,17 %**. Certains cas restent défavorables : le pire écart moyen d’instance au témoin atteint **+24,97 %** au budget étudié. Tous les cas restent publiés.

Les fichiers `.sol` fournis ont été sélectionnés pour la distance. Leurs tournées sont réévaluées en durée, mais leur optimalité temporelle n’est pas établie : **l’écart au témoin n’est pas un gap à une BKS temps**. Un écart négatif est possible. Le rapport distingue ce témoin d’une borne inférieure MST et des véritables optimums prouvés sur dix petits cas de contrôle. Aucun ancien pourcentage en distance n’est présenté comme une qualité en temps.

Les durées sont exprimées en unités de temps du benchmark (u.t.), les temps de calcul en secondes. Les services sont constants pour une instance ; leur décomposition avec les trajets et attentes accompagne les pourcentages.

## Installer et lancer

Le pire essai individuel est C1_10_6, graine 4102 : **+26,77 % au témoin**. Ce chiffre se distingue du pire écart moyen par instance. Les cas défavorables sont visibles dans le rapport et les fichiers complets.

Depuis ce dossier, avec Python 3.12 :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python cli.py C101 --method ils_hgs --seconds 10 --seed 4101
python -m streamlit run web/app.py
python scripts/analyze_duration.py
python scripts/valider_duree.py
python -m pytest tests -q --junitxml=livraison/TESTS.xml
```

La CLI et l’API publique `algo.solver` minimisent la durée par défaut. `--method ils`, `sa` et `ils_hgs` permettent de comparer notre ILS, notre recuit et l’hybride. Notre code construit et améliore les tournées ; le **HGS externe appartient à PyVRP 0.12.2** et reste attribué à ses auteurs. Le profil hybride utilise cinq secondes d’ILS puis cinq secondes de HGS à ce budget. Les références sont consultées après résolution et ne sont pas transmises au moteur.

Le notebook recalcule les contrôles, exemples et statistiques à partir des fichiers fournis ; il ne relance pas les 646 résolutions. Pour l’exécuter dans VS Code, sélectionner l’interpréteur `.venv`. Une nouvelle campagne complète est possible avec `scripts/benchmark_duration.py --label nouveau_lot`, sans écraser les mesures existantes.

## Vérification et limites

Le reçu courant est [VALIDATION_DUREE.json](livraison/VALIDATION_DUREE.json), complété par `livraison/TESTS.xml` et `MANIFESTE_SHA256.json`. Les données `.vrp/.sol`, les solutions, graines, durées, erreurs éventuelles, protocoles et sources effectivement exécutées sont conservés dans `data/` et `results/time_objective/`.

Les tests comprennent aussi des contrôles explicites des routines historiques de distance ; cela ne les transforme pas en benchmarks temporels. Les solutions anciennes utilisées uniquement comme fixtures vérifient couverture, capacité et horaires. Les anciennes campagnes et leurs documents ne font pas partie de cette remise en durée.

Le trafic dépendant de l’heure et les tailles supérieures à 1 000 clients ne sont pas démontrés. La couverture globale possède une ou deux graines selon la taille ; vingt répétitions sont réservées aux trois cas de stabilité. Une corrélation n’établit pas une causalité, et les histogrammes ne prouvent pas automatiquement une loi normale. Node.js est utilisé par un test de lecture de la simulation ; son absence est signalée comme test ignoré.
