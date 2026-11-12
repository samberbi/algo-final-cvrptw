# Livraison actuelle — réduction des pires gaps v9

Ouvrir `RAPPORT_CVRPTW.pdf` ou `../notebooks/Livrable_Final_CVRPTW.ipynb`. La section 9 explique le nouveau réglage et les reprises, avec tous les coûts. Le reçu courant est `validation_worst_v9.json`, indiqué par `VALIDATION.json`.

**Référence v8 :** campagne figée de 472 pipelines, maximum 11,021 %. Ses données et tableaux restent conservés.

**Archive après reprises v9 :** les mêmes 472 solutions, dont dix reprises pendant 180 s supplémentaires ; maximum 6.889 %, moyenne par instance 1.988 %. Ce sont des budgets variables. Voir `ARCHIVE_APRES_REPRISES_V9.html` et `.csv`.

**Nouveau réglage à 120 s :** 20 s d’ILS puis 100 s de HGS, contrôlé sur sept cas et deux nouvelles graines ; pire gap 6.638 %, 14/14 sous 7 %. Le profil est `ILS court + HGS (v9)` ou `--method ils_hgs_refined`. Ce lot n’est pas un nouveau catalogue complet.

Les essais de 360 s, départs multiples et recombinaison sont dans `../docs/REDUCTION_PIRES_GAPS_V9.md` et `../notebooks/Reduction_Pires_Gaps_V9.ipynb`. Le HGS externe reste attribué à PyVRP. Les anciens reçus correspondent à leurs études historiques.
