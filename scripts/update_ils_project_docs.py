"""Refresh entry points and guidance for the ILS edition, preserving ALNS history."""
from pathlib import Path
import json
import nbformat
ROOT=Path(__file__).resolve().parents[1]

README='''# CVRPTW : ILS et recuit simulé

Solveur Python de tournées avec capacité et fenêtres horaires strictes. La méthode principale est la **recherche locale itérée (ILS)** ; le comparateur est un **recuit simulé sur mouvements directs**. La distance DIMACS est minimisée, sans priorité au nombre de véhicules. Le PLNE complet est implémenté avec SciPy/HiGHS pour les petits cas.

## Lire le livrable

- [Livrable Markdown](LIVRABLE_FINAL.md) : modèle, méthodes, résultats et explications sous chaque schéma.
- [Notebook exécuté](notebooks/Livrable_Final_CVRPTW.ipynb) : lectures reproductibles, figures et démonstration courte.
- [Rapport PDF](livraison/RAPPORT_CVRPTW.pdf) et [Word avec équations modifiables](livraison/RAPPORT_CVRPTW.docx).
- [Guide oral](docs/GUIDE_ORAL.md) et [interface web](docs/INTERFACE_WEB.md).

La nouvelle campagne contient **28 instances × 20 graines × 2 méthodes = 1 120 essais**, avec départs communs et budgets appariés. Les dix petits cas PLNE, 100 essais heuristiques associés, 144 essais de sensibilité et 252 observations sur contraintes modifiées sont séparés. Les chiffres ALNS antérieurs sont historiques ; ils ne décrivent pas le nouveau moteur.

## Installation et démonstration

Python 3.12, depuis ce dossier :

```powershell
py -3.12 -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements-web.txt
.\\.venv\\Scripts\\python.exe -m pytest
.\\.venv\\Scripts\\python.exe cli.py C101 --method ils --seconds 2 --seed 101
.\\.venv\\Scripts\\python.exe cli.py C101 --method sa --seconds 2 --seed 101
.\\.venv\\Scripts\\python.exe -m streamlit run web/app.py
```

L'interface est sur http://127.0.0.1:8501 lorsque le serveur local tourne. Elle anime les tournées avec lecture/pause et vitesse réglable ; les tableaux permettent de contrôler chaque client, la capacité et le retour au dépôt. La simulation rejoue une solution calculée, sans représenter un trafic réel.

## Organisation et reproduction

`algo/iterated.py` orchestre les deux recherches ; `algo/direct.py` propose les mouvements ; `algo/kernels.py` contient les routines compilées de construction et de recherche locale. `algo/verify.py` recalcule indépendamment toute solution. `controle/plne.py` résout réellement la formulation sur les petits cas.

Les protocoles, départs, résultats et sources figées sont dans `results/revision_ils/`. Le manifeste des références est `data/manifest.json`. La bibliothèque vrplib lit les données ; elle ne prescrit ni les instances à tester ni le nombre de runs.

```powershell
.\\.venv\\Scripts\\python.exe scripts\\run_ils_benchmark.py --workers 4
.\\.venv\\Scripts\\python.exe scripts\\run_ils_studies.py
.\\.venv\\Scripts\\python.exe scripts\\build_ils_report.py
.\\.venv\\Scripts\\python.exe scripts\\export_report.py
```

Les deux premières commandes reprennent les fichiers déjà présents sous protocole identique. Une reproduction indépendante nécessite un nouveau dossier de campagne et un protocole distinct. Le constructeur est mesuré séparément dans la comparaison appariée ; en CLI son temps est inclus. Le premier préchauffage Numba peut être long.

## Historique et limites

`livraison/historique_alns_avant_refonte/` préserve les documents antérieurs ; `algo/legacy_alns.py`, `metier/` et les anciens scripts de campagne restent des outils historiques. Les nouvelles expériences utilisent exclusivement ILS/recuit. La CLI actuelle optimise la distance ; les expériences de durée de l'ancienne édition ne sont pas réattribuées à ces méthodes.

Les BKS doivent correspondre aux mêmes contraintes et à la même troncature par arc. Elles ne sont pas toutes des optimums prouvés. Les budgets imposés et les ressources partagées ne permettent pas de déduire une loi de complexité ni une vitesse universelle. Le rapport publie moyenne, dispersion, pire cas et limites.
'''

REQUIREMENTS='''# Corrections demandées et réalisation

Ce document traduit la consigne du projet et les remarques de l'enseignante rapportées dans la conversation. Le ZIP du groupe G5 a servi d'exemple de présentation ; ses hypothèses, résultats ou erreurs ne sont pas adoptés comme cahier des charges.

| Demande | Réponse dans la nouvelle édition |
|---|---|
| Formaliser les données et écrire les appartenances | Ensembles C, V, A, ensemble des véhicules, paramètres, domaines et quantificateurs ; explication française de chaque équation |
| Corriger le PLNE complet | C1 affectation, C2 entrées/sorties, C3 flotte, C4 capacité, C5 fenêtres, C6 propagation, C7 retours, C8 connexion au dépôt |
| Justifier la complexité | Certificat polynomial et réduction depuis le TSP symétrique |
| Remplacer ALNS ; VNS et tabou déjà pris | ILS principale et recuit simulé direct ; code réellement remplacé et tests interdisant la réparation pendant la recherche |
| Justifier la méthode et expliquer le code | Rôle de la construction, perturbation, recherche locale, règle d'acceptation et archive ; pseudo-code et lien aux fonctions |
| Tester au moins vingt instances variées | 28 instances : 24 Solomon à 100 clients, deux à 200 et deux à 1 000 |
| Étude statistique rigoureuse | 20 graines par instance/méthode, départs communs, budgets identiques, moyennes, médianes, écarts-types, pire cas, seuils et comparaison appariée |
| Comparer modèle et algorithmes | Dix résolutions PLNE et cinq graines par méthode sur chaque petit cas ; bornes et limites de temps explicites |
| Étudier les paramètres | Huit variantes, six instances de développement et trois graines : 144 essais |
| Étudier les changements de variables/contraintes | Capacité ±20 %, flotte ±20 %, largeur des fenêtres ±30 %, un facteur à la fois ; 252 observations |
| Montrer la convergence | Courbes temporelles moyennes et bandes interquartiles, départ commun, gain des derniers 20 % du budget |
| Expliquer schémas et graphiques | Texte de lecture et portée sous chaque figure, sans confondre illustration et preuve |
| Démonstration et soutenance | Notebook court, interface animée avec contrôle des contraintes et guide oral |

Le sujet ne prescrit pas un nombre de répétitions ou une liste de 56 Solomon : vingt graines est notre choix de protocole, pas une exigence attribuée à l'enseignante. Le seuil du barème ne permet pas de promettre une note ; moyenne et pire cas restent distincts.

Toutes les contraintes du projet sont conservées : dépôt unique ; capacité homogène ; demande indivisible ; chaque client exactement une fois ; flotte maximale ; départ à zéro ; attente autorisée ; fenêtre inclusive sur le début du service ; fin éventuellement après fermeture client ; retour avant ou à la fermeture du dépôt ; temps et distances fixes et symétriques. Une baisse de distance ne compense jamais une violation.

Les anciens résultats ALNS et comparaisons Chakib restent dans l'historique. Ils ne servent pas de résultats ILS/recuit. Le livrable principal est `LIVRABLE_FINAL.md`, généré depuis `docs/LIVRABLE_ILS_SOURCE.md` et les nouvelles mesures.
'''

WEB='''# Interface web et simulation

Lancer `.\\.venv\\Scripts\\python.exe -m streamlit run web/app.py`, puis ouvrir http://127.0.0.1:8501.

La page **Simulation** propose les solutions de la nouvelle étude ILS/recuit, les anciennes solutions ALNS clairement étiquetées et les campagnes locales. Choisir une instance et un run, puis **Lecture**. Les commandes permettent de mettre en pause, changer la vitesse, revenir au début et déplacer l'horloge. Les camions roulent, attendent l'ouverture, servent puis reviennent au dépôt.

L'onglet **Vérifier toutes les contraintes** contrôle la couverture unique des clients, chaque fenêtre, la charge de chaque camion, la flotte et les retours. Une arrivée avant ouverture est autorisée avec attente ; le début du service doit être dans la fenêtre, pas nécessairement sa fin. La charge de livraison décroît après le service. Les contrôles portent à la fois sur le plan complet et sur la progression animée.

**Graphiques du run** montre fenêtres et débuts de service, charge restante, retours, décomposition trajet/attente/service et convergence. Chaque graphique est expliqué. **Schémas et méthode** décrit ILS, recuit et voisins. La **Vue d'ensemble** donne les courbes agrégées de convergence et la sensibilité. **Résultats historiques** permet de sélectionner la nouvelle comparaison ou une ancienne campagne ALNS ; leurs statistiques restent séparées.

**Nouvelle expérience** propose ILS et recuit sur une ou plusieurs instances, avec répétitions, graines et budget. Le budget local commence à l'entrée du solveur et inclut la construction ; le préchauffage et le chargement sont hors budget. La décomposition facultative ajoute une phase ILS et un budget distinct : elle n'est pas utilisée dans le benchmark principal. Les campagnes locales sont séquentielles. Les résultats restent sur cet ordinateur et la fermeture du navigateur ne les arrête pas.

La comparaison publiée utilise un protocole plus contrôlé : départ commun calculé une seule fois par paire, puis même budget d'amélioration pour les deux méthodes. Elle est reproduite par `scripts/run_ils_benchmark.py`, et non en mélangeant les campagnes locales.

La simulation rejoue des horaires fixes et vérifiés sur les coordonnées du benchmark. Elle ne simule pas le trafic réel, les pannes ou des demandes dynamiques. L'animation n'est pas une visualisation des itérations du solveur.
'''


def main():
    (ROOT/'README.md').write_text(README,encoding='utf-8')
    (ROOT/'docs/EXIGENCES_PROJET_ET_RETOUR_PROF.md').write_text(REQUIREMENTS,encoding='utf-8')
    (ROOT/'docs/INTERFACE_WEB.md').write_text(WEB,encoding='utf-8')
    proposal='# Choix retenu : ILS contre recuit simulé\n\nLa proposition antérieure est remplacée par la méthode validée : **ILS principale et recuit simulé sur mouvements directs**. ALNS est retiré du moteur actif ; VNS et recherche taboue ne sont pas retenues.\n\nVoir [le livrable](../LIVRABLE_FINAL.md) et [la correspondance avec les demandes](EXIGENCES_PROJET_ET_RETOUR_PROF.md). Les anciens résultats ALNS sont historiques et séparés.\n'
    (ROOT/'docs/PROPOSITION_CORRECTION_SANS_ALNS.md').write_text(proposal,encoding='utf-8')
    nb=nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell(proposal.replace('../LIVRABLE_FINAL.md','../LIVRABLE_FINAL.md').replace('(EXIGENCES_PROJET_ET_RETOUR_PROF.md)','(../docs/EXIGENCES_PROJET_ET_RETOUR_PROF.md)'))])
    nbformat.write(nb,ROOT/'notebooks/Proposition_Correction_Sans_ALNS.ipynb')
    # Retain the former document builder and explicitly bind old experiments to the historical engine.
    old=ROOT/'scripts/legacy_build_report.py'
    if not old.exists():old.write_bytes((ROOT/'scripts/build_report.py').read_bytes())
    (ROOT/'scripts/build_report.py').write_text('"""Current edition: build the measured ILS/SA report."""\nfrom build_ils_report import main\nif __name__ == "__main__": main()\n',encoding='utf-8')
    for name in ['legacy_build_report.py','run_campaign.py','run_largest_polish.py','run_focused_validation.py','run_polish_campaign.py','study_polish.py','study_parameters.py','study_duration.py']:
        path=ROOT/'scripts'/name
        text=path.read_text(encoding='utf-8').replace('from algo.solver import','from algo.legacy_alns import')
        if not text.startswith('# HISTORICAL'):text='# HISTORICAL ALNS experiment: never pool with results/revision_ils.\n'+text
        path.write_text(text,encoding='utf-8')
    print('Project entry points and correction checklist updated.')


if __name__=='__main__':main()
