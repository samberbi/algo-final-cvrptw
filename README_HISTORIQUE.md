# CVRPTW — Solution hybride ILS–HGS et livrable final
<!-- WORST_V9_BEGIN -->
**Actualisation v9.** Dans le livrable, les sections 1 à 8 décrivent la campagne de référence. La section 9 présente les nouveaux essais : après dix reprises ciblées avec un budget supplémentaire, le pire gap de l’archive est 6.889 %. Les anciens résultats et leurs budgets restent identifiés. Le nouveau profil à 120 s est accessible avec `--method ils_hgs_refined` et dans le web « ILS court + HGS (v9) ».
<!-- WORST_V9_END -->

[Étude v9](docs/REDUCTION_PIRES_GAPS_V9.md), [archive après reprises](livraison/ARCHIVE_APRES_REPRISES_V9.html), [notebook v9](notebooks/Reduction_Pires_Gaps_V9.ipynb).

Notre constructeur, notre ILS et notre vérification sont intégrés au moteur HGS externe **PyVRP 0.12.2**, attribué à ses auteurs. Les contraintes restent strictes sur chaque solution finale ; l’objectif est la distance DIMACS.

## Résultats de la campagne de référence v8

**356 instances couvertes**, de 100 à 1 000 clients ; **472 pipelines évalués**, dont 448 nouveaux et 24 réutilisés avec leur temps intégral. Gap moyen donnant le même poids à chaque instance : **2.078 %**. Moyenne brute des essais réalisables : **2.045 %**. Le sous-ensemble de **116 instances à 100/1 000 clients**, deux graines chacune, obtient **1.946 %**.

À **1 000 clients**, moyenne **3.681 %**, pire essai **11.021 %**. Une moyenne sous 6 % n’implique pas que chaque essai soit sous ce seuil. La couverture et tous les cas défavorables restent publiés.

| n | instances | attempts | valid | mean_instance_gap | worst_run_gap | mean_total_s |
| --- | --- | --- | --- | --- | --- | --- |
| 100 | 56 | 112 | 112 | 0,086 | 1,463 | 10,038 |
| 200 | 60 | 60 | 60 | 0,411 | 2,562 | 16,131 |
| 400 | 60 | 60 | 60 | 1,527 | 3,960 | 32,572 |
| 600 | 60 | 60 | 60 | 2,858 | 6,515 | 49,379 |
| 800 | 60 | 60 | 60 | 3,770 | 7,359 | 66,717 |
| 1000 | 60 | 120 | 120 | 3,681 | 11,021 | 124,530 |

Les budgets sont fixés par taille : 10, 16, 32, 48, 64 et 120 s de recherche totale, partagés entre les deux moteurs. Construction et préparation externe s’ajoutent au temps réel. Une graine sur les tailles intermédiaires, deux sur 100/1 000. La comparaison appariée distincte sur douze grandes instances passe de 9,036 % à 4,253 % à effort nominal égal ; ce chiffre ne remplace pas la moyenne du catalogue complet.

## Ouvrir le livrable et les résultats

- [Notebook principal exécuté](notebooks/Livrable_Final_CVRPTW.ipynb), [HTML](notebooks/Livrable_Final_CVRPTW.html), [PDF](livraison/RAPPORT_CVRPTW.pdf), [Word](livraison/RAPPORT_CVRPTW.docx).
- [Toutes les instances et répétitions](livraison/RESULTATS_CATALOGUE_V8.html), [CSV des essais](livraison/RESULTATS_CATALOGUE_V8.csv), [CSV par instance](livraison/INSTANCES_CATALOGUE_V8.csv).
- [Modifications et bénéfices mesurés](docs/MODIFICATIONS_LIVRABLE_V8.md), [guide oral](docs/GUIDE_ORAL.md), [utiliser le profil hybride](docs/UTILISER_ILS_HGS.md).
- [Journal d’évolution de l’algorithme](docs/JOURNAL_EVOLUTION_ALGORITHME.md), avec objectifs, protocoles, résultats et décisions.
- [Guide de livraison](livraison/LIRE_DABORD.md), [reçu courant](livraison/VALIDATION.json).

## Installer et lancer

Depuis ce dossier, avec Python 3.12 et l’environnement activé :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-reference-v7.txt
python cli.py R2_10_3 --method ils_hgs --seconds 120 --seed 2101
python -m streamlit run web/app.py
python scripts/analyze_catalog_v8.py
python -m pytest tests -q --junitxml=results/worst_v9/tests.xml
python scripts/validate_worst_v9.py
```

Dans le web, choisir « ILS + HGS (PyVRP) ». `--method ils` et `--method sa` conservent les références propres. Le profil hybride partage `--seconds` entre deux phases ; construction et préparation externe sont comptées en plus. La compilation est préchauffée et affichée séparément.

Le modèle, les unités et les limites figurent dans le livrable. Les moteurs ne lisent aucune BKS ; les solutions de référence sont utilisées après la recherche pour les statistiques. Les données et leur révision sont figées dans `data/manifest.json`.

Exécuter toutes les cellules du notebook ne relance pas les 472 recherches : il lit les résultats conservés, vérifie les calculs et montre les illustrations. La CLI et le web lancent de nouvelles résolutions. La régénération Word/PDF par Word requiert Microsoft Word et pywin32 sous Windows ; les exports fournis s’ouvrent sans cette régénération.

## Études antérieures et reproduction

Les études [v5](docs/AMELIORATIONS_ILS.md), [v6](docs/AMELIORATIONS_ILS_V6.md) et [v7](docs/RECHERCHE_GRANDES_INSTANCES_V7.md) gardent leurs lots, budgets, échecs et conclusions propres. Leurs moyennes ne sont pas mélangées à la campagne finale. Les reçus historiques ne sont pas le justificatif courant.

`scripts/benchmark_catalog_v8.py` reprend le protocole complet si son code et son environnement correspondent ; il conserve les essais terminés et refuse un protocole différent. Pour un nouveau protocole, utiliser un nouveau dossier de campagne, sans écraser celui-ci. La campagne v8 reste la référence figée ; la livraison actuelle est contrôlée par `scripts/validate_worst_v9.py`. Les reprises et leurs budgets sont décrits dans la section 9.

La [revue finale de conformité](docs/REVUE_FINALE_CONFORMITE.md) précise les contrôles réalisés et les exigences restant hors du périmètre démontré.
