"""Clear current navigation, change register and oral guide from completed data."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
from scripts.export_report import markdown_table


def main():
    base=ROOT/'results/catalog_v8'
    a=json.loads((base/'analysis.json').read_text(encoding='utf-8'))
    assert a['complete'] and a['executed']==472
    full=a['scopes']['catalog_356'];core=a['scopes']['core_116']
    sizes=pd.read_csv(base/'sizes.csv')
    large=sizes[sizes.n.eq(1000)].iloc[0]
    summary=markdown_table(sizes[['n','instances','attempts','valid','mean_instance_gap','worst_run_gap','mean_total_s']])
    register=f'''# Modifications du livrable et de la solution hybride — édition v8

Le livrable principal est désormais le notebook `notebooks/Livrable_Final_CVRPTW.ipynb`, ses exports HTML/PDF/Word et `LIVRABLE_FINAL.md`. Les études v5/v6/v7 restent des annexes historiques avec leurs budgets et résultats propres.

## Résultats ajoutés et périmètre exact

- Catalogue complet : 356 instances, de 100 à 1 000 clients, une graine commune et une seconde sur 100/1 000.
- Sous-ensemble demandé : 116 instances, deux graines chacune, sans sélectionner les cas favorables.
- Campagne : 472 pipelines, dont 448 nouveaux et 24 réutilisés avec leurs coûts mesurés.
- Moyenne par instance sur 356 cas : **{full['mean_instance_gap']:.3f} %** ; moyenne brute des essais : **{full['mean_run_gap']:.3f} %**.
- Moyenne sur les 116 cas à 100/1 000 : **{core['mean_instance_gap']:.3f} %**.
- À 1 000 clients : **{large.mean_instance_gap:.3f} %**, avec pire essai **{large.worst_run_gap:.3f} %**.
- Échecs de la campagne finale : **{full['failures']} sur 472**. Les erreurs techniques des premières expériences v7 restent archivées séparément.

{summary}

## Ce qui change dans l’algorithme utilisé

La solution recommandée combine notre constructeur regret-2, notre ILS puis le HGS de PyVRP 0.12.2. Notre ILS organise un départ de qualité ; le moteur génétique externe ajoute population, croisement et recherche locale. Le code d’intégration partage le budget à parts égales et contrôle la solution finale indépendamment. Le HGS reste attribué à ses auteurs.

La combinaison est accessible sous `--method ils_hgs` et dans le profil web « ILS + HGS (PyVRP) ». Les options ILS et recuit restent disponibles comme références. Le changement ne modifie ni données ni contraintes ni objectif : la distance DIMACS est minimisée sous capacité, fenêtres strictes, couverture unique, flotte maximale et retour au dépôt.

La comparaison appariée sur douze grandes instances et deux graines passe de 9,036 % pour ILS 60 s puis ILS 60 s à 4,253 % pour ILS 60 s puis HGS 60 s. Ce sont 4,782 points de gap en moins, pour environ 124,4 s contre 124,6 s de temps réel. La combinaison gagne dans 23 paires sur 24. Cette comparaison démontre le gain du pipeline sur ce lot ; elle n’isole pas chaque composant interne du HGS.

## Ce qui a été testé sans être retenu comme amélioration confirmée

Les voisinages temporels, SWAP*, RVND, chaînes, relais avec recuit, nombres de voisins, budgets de sous-recherche, cache de préfixes, groupes temporels, partitionnement de tournées, coût guidé et variantes propres pénalisées restent documentés dans les annexes. Les effets dépendent du lot et du budget. Leur présence dans le code ne signifie pas qu’ils sont tous actifs dans le pipeline recommandé.

Les caches ont des contrôles différentiels ; leurs gains de vitesse ne suffisent pas à prouver un gain de qualité. La combinaison cache/groupes temporels n’a pas battu sa référence en confirmation. Les archives issues de nombreuses recherches conservent un effort cumulé propre et ne sont pas présentées comme une résolution courte.

## Corrections du document

1. Résumé et conclusion alignés sur la campagne finale, avec les bonnes tailles et le bon nombre de pipelines.
2. Formulation mathématique complète conservée, avec fenêtres sur le début du service, capacité, retour, couverture et absence de sous-tournées.
3. Distinction entre distance optimisée, durée, attente et service ; la durée n’est pas comparée à une BKS en distance.
4. Attribution explicite du moteur externe et extrait réel de notre intégration.
5. Registre unique des modifications, de leur objectif, de leur effet observé et de leur statut.
6. Deux moyennes générales expliquées : poids égal par instance et poids égal par essai ; aucune sélection des gaps faibles.
7. Tableaux par taille, familles, toutes les instances et toutes les graines ; pires cas conservés.
8. Graphiques de dispersion, répartition cumulée, temps/qualité, cartes et Gantt de deux exemples préfixés.
9. Variabilité entre instances distinguée de celle des graines ; pas d’écart-type inventé avec une seule répétition.
10. Navigations README, guide oral et reçu courant harmonisés ; les vieux reçus sont historiques.

## Preuves et limites

Le protocole, les sources exécutées, empreintes des données, fichiers de référence et solutions individuelles sont conservés dans `results/catalog_v8/`. Le rapport est généré après la fin et la vérification de la campagne. Les tests et le reçu de validation ne revendiquent que des opérations effectivement exécutées.

Les limites restent explicites : budgets différents selon la taille, une graine intermédiaire et deux sur les tailles extrêmes, moteur externe, absence d’ablation interne du HGS, instances déjà étudiées pour certains réglages, données statiques, durée non optimisée, pas de résultat au-delà de 1 000 clients et pas de preuve d’optimalité globale.

## Relecture rédactionnelle et mathématique

Une introduction en graphe orienté complet et un tableau des notations précèdent désormais les équations détaillées. Le graphe physique utilise un dépôt 0 ; le PLNE distingue ensuite départ o et retour r. La tournée est notée R calligraphique, distincte de l’heure de retour. Un exemple de quatre clients, vérifié indépendamment et exclu des benchmarks, illustre deux tournées réalisables. Les formulations conversationnelles ont été harmonisées en rédaction de projet ; les sources et attributions sont conservées. Le [journal d’évolution](JOURNAL_EVOLUTION_ALGORITHME.md) précise les étapes et les preuves à joindre à chaque future modification.
'''
    (ROOT/'docs/MODIFICATIONS_LIVRABLE_V8.md').write_text(register,encoding='utf-8')
    readme=f'''# CVRPTW — Solution hybride ILS–HGS et livrable final

Notre constructeur, notre ILS et notre vérification sont intégrés au moteur HGS externe **PyVRP 0.12.2**, attribué à ses auteurs. Les contraintes restent strictes sur chaque solution finale ; l’objectif est la distance DIMACS.

## Résultats de l’édition courante

**356 instances couvertes**, de 100 à 1 000 clients ; **472 pipelines évalués**, dont 448 nouveaux et 24 réutilisés avec leur temps intégral. Gap moyen donnant le même poids à chaque instance : **{full['mean_instance_gap']:.3f} %**. Moyenne brute des essais réalisables : **{full['mean_run_gap']:.3f} %**. Le sous-ensemble de **116 instances à 100/1 000 clients**, deux graines chacune, obtient **{core['mean_instance_gap']:.3f} %**.

À **1 000 clients**, moyenne **{large.mean_instance_gap:.3f} %**, pire essai **{large.worst_run_gap:.3f} %**. Une moyenne sous 6 % n’implique pas que chaque essai soit sous ce seuil. La couverture et tous les cas défavorables restent publiés.

{summary}

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
python -m pip install -r requirements-reference-v7.txt
python cli.py R2_10_3 --method ils_hgs --seconds 120 --seed 2101
python -m streamlit run web/app.py
python scripts/analyze_catalog_v8.py
python -m pytest tests -q --junitxml=results/catalog_v8/tests.xml
python scripts/validate_delivery_v8.py
```

Dans le web, choisir « ILS + HGS (PyVRP) ». `--method ils` et `--method sa` conservent les références propres. Le profil hybride partage `--seconds` entre deux phases ; construction et préparation externe sont comptées en plus. La compilation est préchauffée et affichée séparément.

Le modèle, les unités et les limites figurent dans le livrable. Les moteurs ne lisent aucune BKS ; les solutions de référence sont utilisées après la recherche pour les statistiques. Les données et leur révision sont figées dans `data/manifest.json`.

Exécuter toutes les cellules du notebook ne relance pas les 472 recherches : il lit les résultats conservés, vérifie les calculs et montre les illustrations. La CLI et le web lancent de nouvelles résolutions. La régénération Word/PDF par Word requiert Microsoft Word et pywin32 sous Windows ; les exports fournis s’ouvrent sans cette régénération.

## Études antérieures et reproduction

Les études [v5](docs/AMELIORATIONS_ILS.md), [v6](docs/AMELIORATIONS_ILS_V6.md) et [v7](docs/RECHERCHE_GRANDES_INSTANCES_V7.md) gardent leurs lots, budgets, échecs et conclusions propres. Leurs moyennes ne sont pas mélangées à la campagne finale. Les reçus historiques ne sont pas le justificatif courant.

`scripts/benchmark_catalog_v8.py` reprend le protocole complet si son code et son environnement correspondent ; il conserve les essais terminés et refuse un protocole différent. Pour un nouveau protocole, utiliser un nouveau dossier de campagne, sans écraser celui-ci. Les scripts de construction et de validation v8 sont ceux de l’édition actuelle.
'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')
    oral=f'''# Présenter notre livrable CVRPTW

## 1. Quel problème résolvons-nous ?

Nous devons livrer tous les clients une fois, avec des véhicules de capacité limitée, respecter le début du service dans chaque fenêtre et revenir au dépôt à temps. Nous optimisons la distance sur des données statiques selon la convention DIMACS. Le nombre de véhicules est une borne, pas le premier objectif. La durée et le trafic du sujet initial restent distingués de cet objectif expérimental.

## 2. Qu’avons-nous développé ?

Notre constructeur par regret-2, notre ILS, les mouvements et leur contrôle, les expériences, l’interface et l’intégration avec PyVRP. Dire : « Nous avons développé une solution hybride qui combine notre ILS avec le HGS de PyVRP. » Le moteur HGS provient de la bibliothèque externe, attribuée à ses auteurs.

## 3. Pourquoi une ILS avant le moteur génétique ?

Une construction réalisable peut rester très coûteuse. L’essai construction puis HGS à 60 s a donné 6,624 % en moyenne et un cas à 41,238 %. Notre ILS améliore d’abord ce départ ; le HGS reçoit ensuite une meilleure solution et diversifie avec sa population. Dans la comparaison appariée à deux phases de 60 s : 9,036 % pour ILS puis ILS, 4,253 % pour ILS puis HGS, 23 gains sur 24 paires. Ce constat porte sur douze grandes instances et deux graines, pas sur tout le catalogue.

## 4. Que signifie le gap ?

Gap = 100 × (notre distance − référence) / référence. À 4 %, la distance dépasse la référence de 4 %. La référence est une meilleure solution connue compatible, pas forcément un optimum prouvé. Les demandes, capacités, fenêtres, flotte, objectif et troncature doivent correspondre.

La moyenne principale sur 356 cas donne le même poids à chaque instance : **{full['mean_instance_gap']:.3f} %**. La moyenne de tous les essais vaut **{full['mean_run_gap']:.3f} %** et pondère davantage les cas ayant deux graines. Le lot de 116 cas à 100/1 000 clients vaut **{core['mean_instance_gap']:.3f} %**. À 1 000 clients, la moyenne est **{large.mean_instance_gap:.3f} %**, avec un pire essai de **{large.worst_run_gap:.3f} %**. Toujours annoncer le périmètre avec le chiffre.

## 5. Combien de calculs et combien de clients ?

356 instances différentes, six tailles ; 472 pipelines, dont 448 nouveaux et 24 réutilisés. Chaque pipeline a deux phases et une construction. À 100/1 000 clients, deux graines ; aux tailles intermédiaires, une graine. « 1 000 clients » n’est pas « 1 000 runs ». Une répétition réexécute la même instance avec une autre graine.

## 6. Pourquoi ne pas garder toutes les modifications ?

Le cache peut accélérer certains mouvements sans améliorer le gap. Des voisins plus riches, SWAP* ou RVND peuvent consommer du temps et réduire le nombre d’explorations. Les comparaisons v5/v6/v7 gardent ces régressions. Nous retenons une méthode sur ses résultats mesurés, pas sur sa complexité ou son nom.

## 7. Comment savons-nous que les solutions sont valides ?

Un contrôleur indépendant recalcule couverture, charges, horaires au plus tôt, attente, retours et distance sur les données originales. Le service doit commencer dans la fenêtre ; sa fin peut la dépasser si le reste et le retour sont valides. Le HGS peut explorer des états pénalisés, mais aucune solution finale irréalisable ne peut être publiée. Les références sont aussi revérifiées.

## 8. Comment lire les graphiques ?

Les boîtes montrent la dispersion entre instances, pas une précision garantie sur de futures graines. Les points extrêmes restent inclus. Le graphique par taille évite de cacher les grandes instances derrière les petites. La carte par familles montre la structure spatiale et temporelle. Les cartes/Gantt C101 et R2_10_4 expliquent deux résultats réels avec la graine 2101 ; le Gantt est limité aux quatre premières tournées pour être lisible.

## 9. Quelles limites reconnaissons-nous ?

Une ou deux graines seulement, des budgets différents selon la taille, aucune ablation interne du HGS, un moteur externe, des cas déjà étudiés pour certains réglages, des données statiques et aucun essai au-delà de 1 000 clients. La durée totale n’est pas l’objectif optimisé. Un bon gap ne prouve pas l’optimalité ni une note. Tous les cas défavorables restent accessibles.

## 10. Où montrer les preuves ?

Le rapport principal expose le modèle, la méthode et les synthèses. `RESULTATS_CATALOGUE_V8.html` montre les 356 cas et toutes les répétitions. Les JSON contiennent les tournées et les mesures. `protocol.json` et `source/` figent les données de l’expérience. `VALIDATION.json` pointe vers le reçu courant ; les anciennes validations sont historiques.
'''
    (ROOT/'docs/GUIDE_ORAL.md').write_text(oral,encoding='utf-8')
    delivery='''# Livraison actuelle — solution hybride et catalogue complet v8

Ouvrir **RAPPORT_CVRPTW.pdf** ou **../notebooks/Livrable_Final_CVRPTW.ipynb**. Le Word et l’HTML sont les exports de ce même notebook exécuté. `../LIVRABLE_FINAL.md` contient sa rédaction.

Le reçu courant est indiqué par **VALIDATION.json**, qui pointe vers **validation_catalogue_v8.json**. Les reçus v5, v6 et de recherche v7 décrivent leurs études historiques.

**RESULTATS_CATALOGUE_V8.html** contient toutes les instances et toutes les répétitions. **RESULTATS_CATALOGUE_V8.csv** donne les essais individuels ; **INSTANCES_CATALOGUE_V8.csv** donne la synthèse par instance. Les JSON et le protocole sont dans `../results/catalog_v8/`.

Les améliorations et leurs effets sont répertoriés dans `../docs/MODIFICATIONS_LIVRABLE_V8.md`. Le guide oral est `../docs/GUIDE_ORAL.md`. Le HGS utilisé est celui de PyVRP 0.12.2 ; notre contribution est l’intégration, notre ILS et les contrôles, avec attribution explicite du moteur externe.

Les tableaux précisent les tailles, budgets et graines. La moyenne du catalogue ne remplace pas celle des grandes instances ; les échecs et pires résultats restent visibles. Les anciennes archives à budgets cumulés ne sont pas des résolutions courtes de la campagne finale.
'''
    (ROOT/'livraison/LIRE_DABORD.md').write_text(delivery,encoding='utf-8')
    requirements='''# Couverture du sujet par le livrable final

Cette grille distingue les preuves réalisées et les limites. Les résultats de benchmark ne suffisent pas à prouver tous les aspects métier du sujet initial.

| Exigence | Preuve dans notre projet | Statut et limite |
|---|---|---|
| Capacité et fenêtres temporelles | Formulation C1–C8, contrôleur indépendant, tournées de chaque essai | Réalisé sur les données statiques étudiées |
| Couvrir tous les clients une seule fois, revenir au dépôt, respecter la flotte | Vérification complète sur données originales | Obligatoire pour chaque solution publiée |
| Formalisation mathématique | Variables, domaines, objectif, contraintes, flot anti-sous-tournées et justification de M | Modèle statique détaillé |
| Complexité et intérêt de la métaheuristique | Décision, certificat polynomial, réduction du TSP et rôle de l’exact | Expliqué ; preuve générale distincte des performances empiriques |
| Implémentation en Python | Constructeur, ILS, mouvements, vérification et intégration Python/Numba | Partie propre expliquée ; moteur HGS externe explicitement attribué |
| Choix et justification des méthodes | Registre des améliorations, essais négatifs et comparaison appariée | Gain du pipeline mesuré ; pas d’ablation interne du HGS |
| Au moins vingt instances variées | Catalogue complet de 356 instances, six tailles et six familles | Couverture élargie réellement exécutée |
| Étude statistique et répétitions | 472 pipelines, tableaux, moyennes, dispersion, temps, pires cas | Une graine sur 200–800 clients et deux sur 100/1 000 ; robustesse limitée |
| Références et gap | Données figées, .sol revérifiés, convention DIMACS identique | BKS de la révision figée, pas preuve d’optimalité ni promesse de référence la plus récente |
| Grandes instances | Les 60 instances à 1 000 clients, deux graines chacune | Démontré jusqu’à 1 000 ; plusieurs milliers non démontrés |
| Durée et trafic du sujet initial | Décomposition trajet/attente/service calculée ; limites annoncées | Partiel : distance benchmark optimisée, trafic variable non implémenté |
| Illustration et explication | Données, schémas de mouvements, pipeline, cartes/Gantt, formules et extraits de code réels | Exemples préfixés et résultats non sélectionnés |
| Reproductibilité et livraison | Protocoles figés, sources, empreintes, CSV/JSON, notebook exécuté, PDF et Word | Temps dépendants du matériel ; arrêt au temps non déterministe en nombre d’itérations |

Les moyennes sur le catalogue complet, les essais appariés et les archives cumulées restent des preuves différentes. Aucun score de benchmark n’est présenté comme une garantie de note.
'''
    (ROOT/'docs/EXIGENCES_PROJET_ET_RETOUR_PROF.md').write_text(requirements,encoding='utf-8')
    print(json.dumps(dict(written=['README.md','docs/MODIFICATIONS_LIVRABLE_V8.md','docs/GUIDE_ORAL.md','livraison/LIRE_DABORD.md']),indent=2))


if __name__=='__main__':main()
