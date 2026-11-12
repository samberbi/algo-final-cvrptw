# Utiliser la combinaison ILS–HGS

Nous avons développé l’intégration de notre ILS avec le moteur HGS de **PyVRP 0.12.2**, ainsi que l’initialisation, le contrôle indépendant et les expériences. Le moteur génétique est attribué à PyVRP et à ses auteurs.

## Résultat vérifié

Douze instances à 1 000 clients, deux graines, 24 résultats par méthode :

| Pipeline | Gap moyen à la référence DIMACS | Pire essai | Temps réel moyen |
|---|---:|---:|---:|
| ILS 60 s puis ILS 60 s | 9,036 % | 17,103 % | 124,39 s |
| ILS 60 s puis HGS externe 60 s | **4,253 %** | 8,110 % | 124,63 s |

Les 48 résultats sont réalisables. La combinaison gagne dans 23 comparaisons sur 24 ; 19 de ses 24 essais sont sous 6 %. La moyenne porte sur **tous** ses essais, sans sélection des meilleurs. Elle ne décrit pas les 60 instances à 1 000 clients du catalogue.

Les premières phases ILS ont été réellement exécutées dans la campagne précédente, puis réutilisées pour les deux continuations. Leur temps est intégralement compté dans chaque pipeline. Le budget total de recherche est 120 s, auquel s’ajoutent construction et préparation. Les deux continuations partagent leur première phase ; il ne s’agit pas de 48 nouveaux départs indépendants.

## Ligne de commande

Depuis `ALGO FINAL`, avec l’environnement Python du poste :

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements-reference-v7.txt
..\.venv\Scripts\python.exe cli.py R2_10_3 --method ils_hgs --seconds 120 --seed 2101 --output results/ma_solution_hybride.json
```

`--seconds 120` partage le budget de recherche en 60 s d’ILS et 60 s de HGS. La construction et la préparation externe sont facturées en plus dans `runtime_s`. La compilation est affichée séparément. Le résultat contient l’attribution, les deux phases, les tournées et leur vérification.

Le script `scripts/run_hybrid_reference.py` permet aussi de recalculer le gap après résolution ; la BKS n’est jamais transmise aux moteurs.

## Interface web

```powershell
..\.venv\Scripts\python.exe -m streamlit run web/app.py
```

Choisir les instances, les graines et le profil **ILS + HGS (PyVRP)**. Saisir 120 secondes pour reproduire le partage du protocole, et conserver le budget supplémentaire de décomposition à zéro pour comparer avec les résultats publiés. Les résultats locaux restent séparés des campagnes publiées.

Le profil **ILS** reste disponible pour comparer notre moteur seul. La convergence interne du HGS n’est pas enregistrée dans cette version : ses points de début et de fin sont identifiés, sans inventer d’historique intermédiaire.

## Tous les détails

- [Étude complète, hypothèses et essais défavorables](RECHERCHE_GRANDES_INSTANCES_V7.md).
- [Notebook exécuté](../notebooks/Recherche_1000_clients_V7.ipynb).
- [Tous les essais](../livraison/RESULTATS_ILS_V7.html).
- [Comparaison par instance des deux pipelines](../results/optimization_v7/continuation_120/comparison_by_instance.csv).
- [Article décrivant le HGS pour le VRPTW avec capacité](https://wouterkool.github.io/pdf/paper-kool-hgs-vrptw.pdf).
