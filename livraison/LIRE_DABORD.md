# Livraison active — optimisation CVRPTW du 11 novembre 2026

- `RAPPORT_CVRPTW.pdf` et `.docx` : rapport de l'édition optimisée.
- `../notebooks/Livrable_Final_CVRPTW.ipynb` : notebook exécuté correspondant.
- `RESULTATS_OPTIMISES.html` et `.csv` : les 360 trajectoires de validation,
  sur 36 instances et trois tailles équilibrées.
- `VALIDATION.json` : pointe vers le justificatif actuel
  `validation_livraison_ils.json`, avec les empreintes et contrôles.

Le lot avant/après de 80 essais est dans
`../results/optimization_v2/regression/`. Le développement séparé comporte
324 essais, dans `development/` et `adaptive/`.

Les fichiers `MILLE_EXECUTIONS.html`, `ETUDE_80_EXECUTIONS.html` et l'ancienne
annexe de 356 instances décrivent les campagnes **ALNS historiques**. Leurs
chiffres ne sont pas ceux du moteur ILS optimisé. Les documents ILS v1 et
leurs 1 120 essais sont conservés dans `historique_ils_e104927/` et
`../results/revision_ils/`.

Les moyennes et pires cas sont tous conservés. La moyenne équilibrée sous 5 %
ne signifie pas que toutes les grandes instances atteignent ce seuil : leur
bilan spécifique et les limites sont publiés dans le rapport.
