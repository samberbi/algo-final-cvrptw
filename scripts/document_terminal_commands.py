"""Documente les commandes réellement vérifiées et ajoute l'annexe au notebook."""
from pathlib import Path
import json
import hashlib
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import nbformat
import pandas as pd
from algo.comparison_status import present
from scripts.revision_duree import write_markdown


def main():
    base=ROOT/'results/terminal_validation'
    checks=json.loads((base/'commandes_terminal_checks/VALIDATION.json').read_text())
    runs=json.loads((base/'commandes_terminal_runs/VALIDATION.json').read_text())
    assert checks['all_validated'] and runs['all_validated']
    for label in ['commandes_terminal_1000_30s','commandes_terminal_profils_complementaires','soutenance_demo']:
        source=ROOT/'results/local'/label;dest=base/'complements'/label;dest.mkdir(parents=True,exist_ok=True)
        for path in source.iterdir():
            if not path.is_file():continue
            target=dest/path.name
            if target.exists() and target.read_bytes()!=path.read_bytes():raise ValueError('Preuve différente : '+str(target))
            if not target.exists():target.write_bytes(path.read_bytes())
    labels=[r['campaign'] for r in runs['checks'] if r.get('campaign')]+[
        'commandes_terminal_1000_30s','commandes_terminal_profils_complementaires','soutenance_demo']
    source_pool=base/'sources';source_pool.mkdir(exist_ok=True)
    index={}
    for label in labels:
        source=ROOT/'results/local'/label
        protocol=json.loads((source/'protocol.json').read_text())
        index[label]={}
        for rel,digest in protocol['sources'].items():
            payload=(source/'source'/rel).read_bytes()
            assert hashlib.sha256(payload).hexdigest()==digest
            target=source_pool/(digest+'.py')
            if target.exists():assert target.read_bytes()==payload
            else:target.write_bytes(payload)
            index[label][rel]=target.relative_to(ROOT).as_posix()
    (base/'SOURCE_INDEX.json').write_text(json.dumps(index,indent=2),encoding='utf-8')
    progressive=pd.read_csv(ROOT/'results/local/commandes_terminal_runs_progressif/RESULTATS.csv')
    comparative=pd.read_csv(ROOT/'results/local/commandes_terminal_runs_comparaison/RESULTATS.csv')
    large=pd.read_csv(ROOT/'results/local/commandes_terminal_1000_30s/RESULTATS.csv').iloc[0]
    progressive['comparaison']=progressive.apply(lambda r:present(r.duration,r.reference_duration,valid=r.valid),axis=1)
    comparative['comparaison']=comparative.apply(lambda r:present(r.duration,r.reference_duration,valid=r.valid),axis=1)
    actual=progressive[['instance','n','duration','comparaison','wall_s','cpu_s']].to_markdown(index=False,floatfmt='.4f')
    compare=comparative[['method','duration','valid','vehicles','wall_s','comparaison']].to_markdown(index=False,floatfmt='.4f')
    text=r'''# Commandes terminal CVRPTW — PowerShell Windows

Les commandes de cette fiche ont été vérifiées sur le projet. Les transcriptions,
codes retour et résultats sont dans `results/terminal_validation/`.
`scripts/test_instances.py` et `scripts/run_benchmark.py` utilisent la même
interface. Les fonctions historiques importées par les scripts CPU sont conservées.

## 1. Choisir le bon Python

Sur le PC actuel, copier ce bloc dans PowerShell :

```powershell
cd "C:\Users\user\Downloads\CVRPTW_REMISE_PROF_20261112T203928"
$py = "C:\Users\user\OneDrive - Association Cesi Viacesi mail\Bureau\PROJET ALGO\.venv\Scripts\python.exe"
```

Le chemin ci-dessus est celui des exécutions de validation. Sur le portable,
ouvrir le dossier extrait contenant `README.md`, puis installer une fois :

```powershell
py -3.12 -m venv .venv
$py = Join-Path (Get-Location) ".venv\Scripts\python.exe"
& $py -m pip install -r requirements-reference-final.txt
& $py -m pip check
```

La procédure d'installation portable n'a pas été rejouée sur un deuxième
ordinateur. L'environnement actuel a passé `pip check`. Après installation,
toutes les commandes suivantes utilisent `& $py`. Si le terminal utilise déjà
ce même environnement, `python scripts/test_instances.py ...` convient aussi.

## 2. Une instance et ses tournées

```powershell
& $py -X utf8 scripts/test_instances.py --instances C101 --size 25 --seconds 5 --show-routes
```

Un label est créé automatiquement. C101 sans `--size` sélectionne 100 clients ;
`--size 25` ou `--size 50` sélectionne le préfixe standard correspondant. La
forme `--instances C101:25` est également acceptée. Les services et fenêtres
de ces sous-instances restent ceux des clients d'origine ; les manifestes
conservent leurs empreintes et la dérivation depuis les fichiers à 100 clients.

## 3. Plusieurs instances et les six familles

```powershell
& $py -X utf8 scripts/test_instances.py --instances C101 C201 R101 R201 RC101 RC201 --seconds 5 --label commandes_terminal_runs_100
```

| Famille | Instance à 100 clients réellement testée |
|---|---|
| C1 | C101 |
| C2 | C201 |
| R1 | R101 |
| R2 | R201 |
| RC1 | RC101 |
| RC2 | RC201 |

Pour filtrer par famille et taille, une instance représentative est choisie :

```powershell
& $py -X utf8 scripts/test_instances.py --family R1 --size 200 --seconds 5 --label commandes_terminal_runs_R1_200
```

La sélection des six familles peut être inspectée sans calcul :

```powershell
& $py -X utf8 scripts/test_instances.py --families C1 C2 R1 R2 RC1 RC2 --size 100 --dry-run
```

`--size 200` seul choisit une instance de chaque famille à cette taille.
`--all` demande explicitement toutes les instances correspondant aux filtres.
Par défaut, aucune commande sans sélection ne lance les 356 instances : elle
choisit seulement C101 à 100 clients. Les familles et tailles absentes donnent
une erreur explicite, sans ignorer silencieusement une instance nommée.

## 4. Toutes les tailles progressivement, huit résolutions seulement

```powershell
& $py -X utf8 scripts/run_benchmark.py --progressive --seconds 5 --label commandes_terminal_runs_progressif
```

Cette commande choisit un cas C1 à chacune des tailles 25, 50, 100, 200, 400,
600, 800 et 1000. Ce n'est pas le catalogue complet. Les options `--sizes` et
`--families` permettent de réduire ou modifier cette sélection.

Un cas précis à 1000 clients, avec budget de trente secondes, a aussi été exécuté :

```powershell
& $py -X utf8 scripts/test_instances.py --instances C1_10_6 --seconds 30 --max-seconds 120 --label commandes_terminal_1000_30s
```

## 5. Comparer les méthodes sur la même instance

```powershell
& $py -X utf8 scripts/run_benchmark.py --instance C101 --size 25 --methods ils sa pyvrp hybrid refined ortools --seconds 5 --reference independent --label commandes_terminal_runs_comparaison
```

Le terminal affiche chaque résultat immédiatement, puis un classement par
durée réalisable pour chaque couple instance–graine. Les ex æquo sont affichés ;
les échecs ne reçoivent pas de rang. Les budgets et temps totaux figurent dans
le tableau : un classement sur un cas n'est pas une supériorité générale.

| Code | Méthode et attribution |
|---|---|
| `ils` | Notre ILS et nos opérateurs, sans optimisation PyVRP |
| `sa` | Notre recuit simulé et nos opérateurs |
| `pyvrp` | PyVRP/HGS externe seul, population native |
| `hybrid` | Notre construction et ILS, puis HGS PyVRP externe |
| `refined` | Constructions propres, Local Search PyVRP et partitionnement HiGHS |
| `duration_refined` | Alias historique conservé de `refined` |
| `ortools` | OR-Tools externe, objectif somme des durées complètes |
| `construction` | Construction propre regret-2, douze tentatives |
| `refined_no_partition` | Profil renforcé sans partitionnement |
| `refined_ils` | Profil renforcé puis notre ILS dans le temps restant |

Les trois derniers profils ont également été vérifiés via cette commande :

```powershell
& $py -X utf8 scripts/run_benchmark.py --instance C101 --size 25 --methods construction refined_no_partition refined_ils --seconds 1 --label commandes_terminal_profils_complementaires
```

La construction seule a réellement donné +8,4925 % au comparateur indépendant
sur ce cas. Ce dépassement est affiché et conservé, pas ramené artificiellement
sous 6 %. L'optimum du partitionnement ne concerne que son réservoir de tournées.

## 6. Lire les références et les gaps

La durée est trajets + attentes + services, retour au dépôt inclus, départs
à zéro. Les trajets sont fixes et symétriques. Chaque solution est recalculée
par `algo.verify`, indépendamment des noyaux de recherche.

`--reference auto` utilise le plan public réévalué en durée pour les tailles
100–1000, et une solution OR-Tools enregistrée compatible si disponible pour
25/50. `--reference independent` choisit uniquement une référence OR-Tools
figée, jamais le résultat de notre propre méthode évaluée. Cette référence
n'est pas recalculée à chaque test : son chemin est affiché. Le profil `ortools`
permet en revanche d'exécuter une nouvelle résolution OR-Tools comme méthode.

L'écart vaut `100 * (durée_solution / durée_reference - 1)`. Il reste signé.
Zéro signifie égalité au coût de référence ; une valeur négative signifie que
la solution est meilleure que cette référence réalisable. Cela ne prouve pas
un optimum temporel. Sans preuve compatible, **Gap certifié : NON DISPONIBLE**.
Les valeurs Phonin non totalement certifiées compatibles ne sont pas utilisées
comme optima dans la CLI. Une référence manquante n'invalide pas une solution
réalisable : son coût reste affiché et son écart est indisponible.

Cette dernière situation est vérifiée explicitement :

```powershell
& $py -X utf8 scripts/test_instances.py --instance C101 --size 25 --seconds 5 --reference none --label commandes_terminal_runs_sans_reference
```

## 7. Réafficher sans relancer les algorithmes

```powershell
& $py -X utf8 scripts/test_instances.py --show-results commandes_terminal_runs_comparaison --show-routes
& $py -X utf8 scripts/test_instances.py --show-results --label commandes_terminal_runs_100 --gaps-only
```

Ces labels existent après la validation réalisée. Les noms exacts de tes futurs
lots sont affichés en fin d'exécution. Si tu relances un label déjà présent,
un suffixe `_2`, `_3`, etc. est ajouté : aucun ancien lot n'est écrasé.

## 8. Fichiers enregistrés

Chaque lot est dans `results/local/<label>/` :

- `RESULTATS.csv` : coûts, décomposition, référence, écarts, faisabilité,
  budget, CPU et temps réel ;
- `BILAN.json` : succès, échecs et temps du lot ;
- `SYNTHESE.txt` : classement lisible ;
- JSON par instance/taille/méthode/graine : tournées, arrivées, débuts et fins
  de service, retour, vérification et erreurs ;
- `protocol.json` et `source/` : configuration, données sélectionnées,
  empreintes et copie du code effectivement exécuté.

Les preuves de la validation des commandes sont copiées dans
`results/terminal_validation/` pour ne pas rester uniquement dans un dossier ignoré.

## 9. Budgets, garde-fou et parallélisme

ILS, recuit, hybride initial et PyVRP reçoivent un budget de recherche ; la
construction et préparation s'ajoutent. Le renforcé utilise un budget total
souple. Le constructeur seul s'arrête après ses tentatives, sans attendre
artificiellement la durée demandée. Un appel natif ne peut pas être préempté
proprement à chaque instruction ; son dépassement réel est affiché.

Les CPU et temps réel de résolution incluent la vérification finale mais
excluent chargement/préchauffage. Le **temps total processus**, affiché
séparément, comprend lancement, chargement, compilation éventuelle et sortie.
Le garde-fou `--max-seconds`, 120 par défaut, surveille CPU et temps réel du
processus entier. Il peut le terminer, auquel cas le résultat est `time_limit`
sans solution inventée. Le délai de surveillance/arrêt peut légèrement dépasser
la limite : ce n'est pas une garantie mathématique d'arrêt à l'instant exact.

Deux processus ont été testés avec :

```powershell
& $py -X utf8 scripts/test_instances.py --instances C101 C201 --size 25 --seconds 1 --workers 2 --label commandes_terminal_runs_parallele
```

Le parallélisme peut réduire le temps du lot, sans réduire la somme des CPU.
La limite de 120 s est appliquée par résolution, pas à la somme des processus.

## 10. Vérifier la gestion des échecs, volontairement

```powershell
& $py -X utf8 scripts/test_instances.py --instances R2_10_8 --method pyvrp --seconds .001 --label commandes_terminal_runs_echec
& $py -X utf8 scripts/test_instances.py --instances C101 --method ils --seconds .01 --max-seconds .05 --label commandes_terminal_runs_limite
```

Ces deux commandes ont effectivement retourné le code 1, attendu : respectivement
`not_found` avec PyVRP et `time_limit` avec le garde-fou. Les données n'ont pas
été rendues irréalisables. Les budgets volontairement minuscules servent à
tester la gestion des échecs, pas à juger la qualité des algorithmes.

Code 0 : toutes les solutions de la commande sont réalisables, même si leur
écart dépasse 6 %. Code 1 : au moins une résolution a échoué ou a été arrêtée.
Code 2 : arguments invalides. La faisabilité ne se confond pas avec le seuil de qualité.

## 11. Tests, validateur et notebook

```powershell
& $py -X utf8 -m pytest tests -q --junitxml=livraison/TESTS_SOUTENANCE.xml
& $py -X utf8 scripts/validate_soutenance.py
```

Résultats réellement obtenus pendant cette passe : **194 tests réussis,
2 modules optionnels ignorés**, puis validateur du projet réussi. Les aides de
`test_instances.py`, `run_benchmark.py`, `benchmark_final_static.py` et
`finalize_static.py` ont aussi été exécutées.

Pour refaire l'exécution du notebook et sa validation sans relancer les campagnes :

```powershell
& $py -X utf8 scripts/finalize_static.py --execute --validate
```

Cette procédure est celle déjà utilisée pour finaliser le livrable ; elle peut
prendre davantage de temps que la démonstration d'une petite instance.

## 12. Démonstration PowerShell

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/demo_terminal.ps1 -Python $py -Instance C101 -Size 25 -Seconds 5
```

Ce script a été exécuté : trois véhicules, durée 2623,5, faisabilité validée,
tournées et horaires affichés. Il utilise le Python fourni ou celui de `.venv`
dans le projet, puis le `python` du terminal en dernier recours. La politique
d'exécution est modifiée seulement pour le processus de cette commande.

## Résultats réels — campagne progressive

Les temps ci-dessous sont ceux de résolution, sans préchauffage. Les références
sont nommées dans les CSV : OR-Tools à 25/50, plans publics réévalués ensuite.
Cette vérification d'interface ne remplace pas une étude comparative exhaustive.

'''+actual+'''

Sur C1_10_6 à 1000 clients, budget demandé 30 s : durée **'''+f'{large.duration:.1f}'+'''**,
écart au témoin réévalué **'''+f'{large.delta_reference_pct:+.4f}'+''' %**, temps réel
de résolution **'''+f'{large.wall_s:.3f}'+''' s**, CPU **'''+f'{large.cpu_s:.3f}'+''' s**.
Le programme a fini avant son budget maximal ; il n'attend pas trente secondes
artificiellement. Cet écart ne constitue pas un gap à un optimum temporel prouvé.

## Résultats réels — comparaison C101/25

'''+compare+'''

Les six profils obtiennent ici la même durée réalisable. Les coûts égaux à la
référence expliquent les écarts nuls ; aucun certificat d'optimalité n'en est
déduit. Les temps et la réussite à ce cas ne permettent pas de classer les
méthodes sur toutes les familles et grandes tailles.

Erreurs corrigées : label auparavant obligatoire, tailles 25/50 indisponibles,
absence de sélection par famille et de comparaison multi-méthodes, affichage
incomplet et absence de garde-fou. La faisabilité et la disponibilité de la
référence sont désormais traitées séparément. Les erreurs de recherche restent
des résultats sauvegardés. L'ancien nom `duration_refined` est accepté.
'''
    (ROOT/'COMMANDES_TERMINAL.md').write_text(text,encoding='utf-8')
    nbpath=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb';nb=nbformat.read(nbpath,4)
    existing=next((c for c in nb.cells if c.metadata.get('terminal_commands_v2')),None)
    before=[c.source for c in nb.cells if c.cell_type=='code']
    nb.cells=[c for c in nb.cells if not c.metadata.get('terminal_commands_v2')]
    appendix='''## Annexe — Commandes terminal vérifiées et nouvelle interface

La fiche `COMMANDES_TERMINAL.md`, à la racine du projet, contient les commandes
PowerShell réellement testées. Les scripts `test_instances.py` et
`run_benchmark.py` partagent une interface. Les fonctions utilisées par les
anciennes reprises restent conservées ; les algorithmes et les résultats
historiques ne sont pas remplacés.

```powershell
python scripts/test_instances.py --instances C101 --size 25 --seconds 5 --show-routes
python scripts/run_benchmark.py --progressive --seconds 5 --label commandes_terminal_runs_progressif
python scripts/run_benchmark.py --instance C101 --size 25 --methods ils sa pyvrp hybrid refined ortools --seconds 5 --reference independent --label commandes_terminal_runs_comparaison
python scripts/test_instances.py --show-results commandes_terminal_runs_comparaison --show-routes
```

Dans ces exemples, `python` doit être celui des dépendances du projet ; la
fiche donne le chemin Windows réellement utilisé et l'installation portable.
Le terminal affiche faisabilité, décomposition, référence et source, écart
signé, gap certifié seulement si disponible, CPU, réel, budget et statut.
`--show-routes` affiche les listes de clients et les horaires. La relecture
`--show-results` ne lance aucune nouvelle recherche.

Les six familles à 100 clients et les huit tailles 25–1000 ont été exécutées.
La comparaison à six méthodes sur C101/25 retourne des coûts identiques à
2623,5 : un écart nul au comparateur réalisable n'est pas une preuve d'optimum.
Sur C1_10_6/1000 à budget 30 s, la résolution mesurée donne 140502,9 et
+5,0452 % au plan public réévalué en durée, avec faisabilité contrôlée.

La suite complète de cette passe compte **194 réussites et deux modules
optionnels ignorés**. Le validateur du projet réussit. Les échecs `not_found`
et `time_limit` ont été réellement testés avec des budgets volontairement très
courts ; ils restent sauvegardés et ne reçoivent pas de coût ni de gap fictif.
Les logs et preuves sont dans `results/terminal_validation/`. Ces essais
valident les commandes et ne sont pas fusionnés avec les moyennes historiques.

Le garde-fou est de 120 secondes CPU/réelles par processus par défaut,
initialisation comprise. Les temps de résolution excluent le préchauffage,
dont le coût reste visible dans le temps total du processus. Les appels
natifs et la surveillance peuvent dépasser légèrement un budget ; le
dépassement est mesuré. L'arrêt surveillé ne promet pas une borne stricte
à l'instant exact. Les références manquantes sont affichées NON DISPONIBLE,
sans invalider une solution réalisable ; les pourcentages signés sont conservés.
'''
    cell=nbformat.v4.new_markdown_cell(appendix,metadata={'terminal_commands_v2':True})
    if existing is not None:cell.id=existing.id
    nb.cells.append(cell)
    assert before==[c.source for c in nb.cells if c.cell_type=='code']
    nbformat.validate(nb);nbformat.write(nb,nbpath);write_markdown(nb)
    readme=ROOT/'README.md';body=readme.read_text(encoding='utf-8')
    marker='## Commandes terminal vérifiées'
    if marker not in body:
        section='''## Commandes terminal vérifiées

La fiche [COMMANDES_TERMINAL.md](COMMANDES_TERMINAL.md) donne les commandes
PowerShell, le Python exact, les six familles, les tailles 25–1000, neuf profils,
les comparaisons, les tournées, les gaps et la relecture sans calcul. Les preuves
sont dans `results/terminal_validation/`. Le script `scripts/demo_terminal.ps1`
prépare une démonstration courte. Aucun lancement implicite des 356 instances.

'''
        body=body.replace('## Finalisation statique du 13 novembre',section+'## Finalisation statique du 13 novembre')
    readme.write_text(body,encoding='utf-8')
    summary=ROOT/'docs/SYNTHESE_SOUTENANCE_FINALE.md'
    summary.write_text(summary.read_text(encoding='utf-8').replace('182 tests réussis','194 tests réussis'),encoding='utf-8')
    print('Fiche PowerShell et annexe sauvegardées ; aucune cellule de calcul modifiée.')


if __name__=='__main__':main()
