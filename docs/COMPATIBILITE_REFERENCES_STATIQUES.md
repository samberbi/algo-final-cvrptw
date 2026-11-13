# Compatibilité des références en durée

## Contrat du projet

Trajets fixes et symétriques, départs nuls, fenêtres sur le début de service,
retour avant fermeture, flotte bornée, objectif somme des retours : trajets,
attentes et services. Les coûts sont stockés en dixièmes entiers ; chaque arc
euclidien est tronqué au dixième avant le calcul des horaires.

## Phonin et al. (2025)

Source primaire : https://www.mdpi.com/2305-6290/9/3/85 (DOI 10.3390/logistics9030085).
La fonction objectif minimise la somme des fins de tournées. L'équation (9)
ajoute explicitement le retour au dépôt, malgré un passage textuel ambigu
sur la fin du dernier service. La définition de la première arrivée utilise
le trajet depuis le dépôt. Les attentes et services interviennent dans les horaires.

La comparaison demeure **conditionnelle** : la formulation écrite impose des
temps de début entiers ; les règles d'arrondi des trajets ne sont pas établies
avec certitude. Elle fait partir les véhicules de l'ensemble choisi, tandis
que notre flotte est une borne supérieure. Le lien dépôt–premier client n'est
pas explicité dans toutes les contraintes imprimées. Cela ne démontre pas une
erreur de leur implémentation, dont nous n'avons pas les journaux détaillés.
Les valeurs étoilées du tableau 2 sont les optima annoncés par les auteurs ;
les autres valeurs et le tableau 3 ne constituent pas toutes des preuves.
Les tournées et certificats complets nécessaires à une recertification n'ont
pas été retrouvés dans les éléments consultés.

Contrôle réellement exécuté : cinq résolutions indépendantes OR-Tools de trois
secondes à 25 clients, puis réévaluation des mêmes tournées en précision
euclidienne complète. C101 à 100 utilise le plan public existant, sans nouveau
run. Résultats détaillés :
`results/final_static/reference_audit/PHONIN_VERIFICATION.csv` et JSON associés.
C101/25 : 2623,50 avec troncature ; 2624,014190590107 en précision complète ;
publication 2624,01. Cette concordance explique une différence de convention,
sans certifier automatiquement toutes les comparaisons. **Aucun gap officiel
à Phonin n'est annoncé dans notre nouveau pilote.**

## Sous-instances 25 et 50

Le site source https://vrp.dorronsoro.es/Problem_Instances/CVRPTWInstances.html
a été identifié ; ses archives ont répondu HTTP 403 lors du téléchargement.
Les fichiers locaux utilisent donc explicitement les préfixes standards des
25/50 premiers clients de nos fichiers Solomon à 100 clients déjà figés.
Coordonnées, identifiants, demandes, services, fenêtres et paramètres du dépôt
sont conservés. Le manifeste conserve les empreintes du parent et du résultat.
Nous ne prétendons pas avoir téléchargé les octets des archives originales.

## Référence indépendante retenue pour le pilote

Google OR-Tools 9.15.6755, paramétré dans `algo/ortools_duration.py`.
La dimension Time additionne trajet et service, avec du slack pour les attentes ;
tous les départs sont fixés à zéro. Les coûts d'arcs sont nuls, et le coût de
chaque span temporel a un coefficient de 1. L'objectif est ainsi la somme des
retours, et non le makespan ni la distance. Le coût natif est vérifié contre
notre contrôleur complet. Aucune solution de notre ILS ou BKS n'est injectée.
Source : https://developers.google.com/optimization/routing/vrptw ; l'exemple
standard doit être adapté, car ses seuls coûts d'arcs ne suffisent pas ici.

Une solution OR-Tools est une **référence réalisable indépendante**, sans preuve
d'optimalité. Un écart négatif est possible et sera conservé. Les plans publics
optimisés en distance sont également vérifiés et réévalués en durée, mais leur
écart est un indicateur séparé. Nos résultats ne définissent pas leur propre
référence. Un optimum du partitionnement sur un réservoir fini n'est pas un
optimum global du CVRPTW.
