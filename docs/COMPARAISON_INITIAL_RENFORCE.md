## Comparaison automatique : ILS initial et profil renforcé

Sans `--method` ou `--methods`, chaque commande exécute maintenant **deux
résolutions par instance et par graine** : notre `ils` autonome, puis le profil
hybride `size_based`. Le renforcé utilise la recherche locale externe PyVRP
et, sur les grands cas selon le temps restant, son HGS. Ces contributions sont
attribuées à la bibliothèque. L'initial n'est pas une construction seule.

Le terminal affiche pour chaque moteur la durée complète, la faisabilité,
la flotte, la référence et l'écart compatible, le temps réel, le CPU et le
budget demandé. Un second tableau donne le gain entre méthodes :

`gain = 100 × (durée ILS initial − durée renforcée) / durée ILS initial`.

Ce gain n'est pas le gap au plan témoin. Une valeur positive signifie que le
renforcé améliore l'ILS ; une égalité ou une régression reste explicitement
affichée. Un échec interdit de chiffrer le gain. Nous ne sélectionnons pas une
mauvaise exécution de l'initial pour rendre le renforcé artificiellement meilleur.

**Budgets :** `--seconds` s'applique séparément à chaque moteur. Pour l'ILS,
la construction s'ajoute au budget de recherche ; le renforcé utilise un
budget total souple. Le même paramètre ne constitue donc pas un temps total
strictement égal. Les temps réellement mesurés sont affichés pour juger le
compromis qualité/coût. Le garde-fou de 120 secondes concerne chaque processus,
pas la somme des deux méthodes. Par défaut, les exécutions sont séquentielles.

```powershell
python scripts/test_instances.py --instances RC101 --methods ils size_based --seconds 5 --label comparaison_RC1
python scripts/test_instances.py --instances C101 C201 --methods ils size_based --seconds 5 --label comparaison_C
python scripts/test_instances.py --instances R101 R201 --methods ils size_based --seconds 5 --label comparaison_R
python scripts/test_instances.py --instances RC101 RC201 --methods ils size_based --seconds 5 --label comparaison_RC
python scripts/test_instances.py --instances C2_10_7 --methods ils size_based --seconds 60 --label comparaison_1000
```

Le couple `--methods ils size_based` est explicite ici, mais il est désormais
le défaut lorsqu'aucune méthode n'est donnée. Pour une seule résolution,
utiliser `--method size_based` ou `--method ils`. Les labels déjà utilisés
reçoivent automatiquement un suffixe, sans écraser les résultats antérieurs.

Les fichiers `RESULTATS.csv`, `SYNTHESE.txt` et
`COMPARAISON_INITIAL_RENFORCE.csv` sont sauvegardés dans le dossier annoncé.
`--show-results <label>` réaffiche aussi le comparatif, sans relancer les moteurs.

**Essai de vérification réellement exécuté :** RC101, C204 et R109 à 100
clients, graine 4101, cinq secondes demandées par moteur, un processus.
Les six solutions et leurs références ont été recalculées indépendamment.
Un contrôle complémentaire de C2_10_7 à 1000 clients utilise trente secondes
par moteur, avec la même graine et le même ordre d'exécution séquentiel.

| instance   |    n |   initial_requested_s |   initial_duration |   reinforced_duration |   duration_gain_pct |   initial_wall_s |   reinforced_wall_s |   initial_cpu_s |   reinforced_cpu_s | conclusion           |
|:-----------|-----:|----------------------:|-------------------:|----------------------:|--------------------:|-----------------:|--------------------:|----------------:|-------------------:|:---------------------|
| C204       |  100 |                5.0000 |          9793.6000 |             9738.3000 |              0.5647 |           5.0316 |              5.0013 |          5.0312 |             4.9688 | Renforcé meilleur    |
| C2_10_7    | 1000 |               30.0000 |        124703.9000 |           112338.0000 |              9.9162 |          33.3713 |             29.5966 |         33.3594 |            29.4531 | Renforcé meilleur    |
| R109       |  100 |                5.0000 |          2394.6000 |             2420.7000 |             -1.0900 |           5.0274 |              5.0014 |          5.0156 |             4.8906 | ILS initial meilleur |
| RC101      |  100 |                5.0000 |          2917.7000 |             2921.1000 |             -0.1165 |           5.0299 |              5.0015 |          5.0312 |             4.8750 | ILS initial meilleur |

Les résultats de ces cas restent un contrôle de fonctionnement des
commandes. Ils ne constituent pas une nouvelle preuve statistique de supériorité
universelle. Les tournées et sources sont dans
`results/terminal_comparison/`.
