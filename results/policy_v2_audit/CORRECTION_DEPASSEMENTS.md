# Correction des dépassements — 14 novembre 2026

Le premier profil `size_based` utilisait la construction seule jusqu'à 100
clients. Sur RC101/100, graine 4101, cela donnait 3335,2 contre 2991,6 pour
le plan public réévalué en durée : +11,4855 %. Le rang 1 signifiait seulement
qu'une méthode avait été exécutée. Le terminal le précise désormais.

La version 2 conserve la meilleure construction regret-2, applique la recherche
locale **externe PyVRP** à 40/80/120 voisins puis notre ILS dans le temps restant.
Chaque étape doit être réalisable et ne peut augmenter la durée conservée.
La résolution ne lit aucune référence ni cible de gap. Les données, contraintes
et objectif trajets + attentes + services, départs à zéro et retours compris,
restent inchangés.

Sur les grandes instances, le profil renforcé fini s'arrêtait après environ
cinq secondes malgré un budget supérieur. La composition conserve ce profil
initial sur cinq secondes au plus, puis lance une continuation **HGS externe
PyVRP**, à 60 voisins, selon le temps restant. Une seconde est réservée à la
préparation, et tout dépassement réel est mesuré. Le coût final ne peut être
plus mauvais que celui transmis au HGS. PyVRP et HiGHS sont explicitement
attribués aux bibliothèques externes.

## Mesures nouvelles, séparées des archives

Graine 4101. Les écarts portent sur des plans réalisables compatibles, sans
preuve d'optimalité temporelle. Les temps incluent les phases successives.

| Instance | Clients | Durée initiale | Durée finale | Comparaison avant | Comparaison finale | Temps écoulé |
|---|---:|---:|---:|---|---|---:|
| RC101 | 100 | 3335,2 | 2921,1 | +11,4855 % | Référence améliorée, solution vérifiée | 5,001 s |
| C101 | 25 | 2846,3 | 2623,5 | +8,4925 % | Référence égalée, optimalité non démontrée | 5,001 s |
| C2_10_2 | 1000 | 115983,7 | 111539,1 | +6,0221 % | +1,9592 % | 59,604 s |
| C2_10_7 | 1000 | 115159,9 | 111486,9 | +7,6865 % | +4,2518 % | 59,790 s |

La campagne des petits cas comprend 72 résolutions : 56 Solomon à 100 clients
et 16 préfixes disponibles à 25/50 clients, cinq secondes demandées, deux
processus. Toutes les solutions sont réalisables. Sur les 56 cas à 100 clients :
41 références améliorées, 8 égalées et 7 écarts positifs, aucun supérieur à six
pour cent. La moyenne **conditionnelle des sept écarts positifs** est 0,4034 %,
et leur maximum 1,5665 %. Ce n'est pas une moyenne sur 56 essais. Sur les
16 préfixes, 4 références sont égalées et 12 cas n'ont pas de référence
indépendante enregistrée : aucun gap n'est inventé pour ces derniers.

Quatre contrôles supplémentaires à 1000 clients ont été exécutés avec l'ancien
profil renforcé et un budget demandé de trente secondes : C1_10_6, C2_10_2,
C2_10_7 et R2_10_8. Ils ont révélé les deux dépassements et l'arrêt précoce.
Les deux continuations de soixante secondes restent une campagne distincte.
Leur gain utilise davantage de calcul effectif ; il ne démontre pas un avantage
à temps égal ou une garantie pour toutes les graines et grandes instances.

## Audit indépendant

Le registre historique a été recalculé : **1321 comparaisons, aucune anomalie**.
Les vues multiples d'archives et références différentes ne sont pas de nouveaux
runs. Les 947 améliorations de références et les 129 égalités ne révèlent pas
d'erreur. Les plans publics ont été optimisés en distance, puis réévalués en
durée ; les solutions OR-Tools sont également heuristiques et non certifiées.

L'audit complémentaire du terminal vérifie **166 enregistrements, dont 163
solutions réalisables et 3 échecs conservés**, sans anomalie. Il comprend
77 améliorations de références, 40 égalités et 10 anciens dépassements de six
pour cent. Ces derniers restent dans les archives et ne sont pas réétiquetés
comme les nouvelles solutions. Les deux audits se chevauchent : leurs effectifs
ne doivent pas être additionnés pour compter les résolutions.

La simulation indépendante lit les coordonnées originales et contrôle la
couverture unique, la capacité, les fenêtres de début de service, la flotte,
le retour avant fermeture et la décomposition de la durée. Les arcs sont
recalculés par `floor(10*hypot(...))`, indépendamment des noyaux du solveur.
Les coûts initiaux, finaux et références, ainsi que les formules, sont vérifiés.
Les empreintes des sources figées des nouvelles campagnes sont contrôlées.

Une amélioration de référence n'est pas une meilleure solution mondiale
proclamée. Une égalité ne prouve pas l'optimalité. Le livrable emploie les
statuts appropriés et conserve les écarts signés dans les annexes techniques,
sans fabriquer de pourcentage positif. Les échecs ne sont pas supprimés.

## Fichiers et reprise

- `TABLEAU_PETITES.md`, `AVANT_APRES_PETITES.csv` : les 72 essais détaillés.
- `AVANT_APRES_GRANDES_HGS.csv` : les deux continuations mesurées.
- `AUDIT_RECENTS.csv`, `AUDIT.json`, `ANOMALIES.json` : contrôles et causes.
- Sous-dossiers des campagnes : tournées, chronologies, protocoles, sources.
- `../../AUDIT_GAPS_FINAL.md` : audit historique détaillé.

```powershell
python scripts/test_instances.py --instances RC101 --seconds 5 --label verification_RC101
python scripts/test_instances.py --instances C2_10_2 C2_10_7 --seconds 60 --label verification_grandes
python scripts/audit_policy_v2.py
python -m pytest tests -q --junitxml=livraison/TESTS_SOUTENANCE.xml
python scripts/finalize_static.py --execute --validate
```

Les résolutions créent de nouvelles mesures. Le budget est souple et le
garde-fou est de 120 secondes par processus. Les temps ne sont pas plafonnés.
Les résultats peuvent varier avec le matériel et les itérations effectuées.
