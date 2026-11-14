"""Documente les deux moteurs réellement exécutés dans les nouvelles commandes."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import nbformat
import pandas as pd
import vrplib
from scripts.audit_gap_status import check
from scripts.terminal_support import paired_comparisons
from scripts.revision_duree import write_markdown


def main():
    label='comparaison_initial_renforce_v1'
    out=ROOT/'results/terminal_comparison'/label
    source=ROOT/'results/local'/label
    if source.exists():
        shutil.copytree(source,out,dirs_exist_ok=True)
    folders=[out]
    large_label='comparaison_grande_initial_renforce_v1'
    large_source=ROOT/'results/local'/large_label
    large_out=out.parent/large_label
    if large_source.exists():
        balance=json.loads((large_source/'BILAN.json').read_text(encoding='utf-8'))
        assert balance['completed']==2,'Attendre la fin des deux méthodes avant la documentation'
        shutil.copytree(large_source,large_out,dirs_exist_ok=True)
    if large_out.exists():folders.append(large_out)
    records=[]
    for path in sorted(p for folder in folders for p in folder.glob('*.json')):
        record=json.loads(path.read_text(encoding='utf-8'))
        if 'measurement' not in record:continue
        m=record['measurement']
        if m['valid']:
            own=check(m['instance'],m['n'],record['result']['routes'])
            assert own['valid'] and abs(own['duration']-m['duration'])<1e-7
        else:
            assert m['duration'] is None and record['result'].get('routes') is None
        refpath=ROOT/record['reference']['source']
        ref=check(m['instance'],m['n'],vrplib.read_solution(refpath)['routes'])
        assert ref['valid'] and abs(ref['duration']-m['reference_duration'])<1e-7
        if m['valid']:assert abs(100*(own['duration']/ref['duration']-1)-m['delta_reference_pct'])<1e-7
        records.append(record)
    assert len(records)==6+2*(len(folders)-1)
    for folder in folders:
        protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
        for rel,expected in protocol['sources'].items():
            assert hashlib.sha256((folder/'source'/rel).read_bytes()).hexdigest()==expected
    pairs=paired_comparisons([r['measurement'] for r in records])
    assert len(pairs)==3+len(folders)-1
    frame=pd.DataFrame(pairs)
    frame.to_csv(out.parent/'COMPARAISON_COMPLETE.csv',index=False,encoding='utf-8-sig')
    text=r'''## Comparaison automatique : ILS initial et profil renforcé

**Python à utiliser.** Depuis la racine du projet, appeler directement
`.\.venv\Scripts\python.exe` pour le solveur statique. L'activation de
`.venv_dabia` ne fournit pas ses dépendances : cet environnement appartient
à l'extension optionnelle. Le script vérifie maintenant les bibliothèques
nécessaires avant toute résolution et donne une erreur explicite si le
Python choisi est incomplet, sans créer une campagne vide.

Préparation unique sur un nouvel ordinateur :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-reference-final.txt
.\.venv\Scripts\python.exe -m pip check
```

Les commandes ci-dessous utilisent ce Python directement : elles fonctionnent
même si le terminal affiche encore `(.venv_dabia)` et ne nécessitent pas de
changer la politique d'exécution PowerShell.

Sans `--method` ou `--methods`, chaque commande exécute maintenant **deux
résolutions par instance et par graine** : notre `ils` autonome, puis le profil
hybride `size_based`. Le renforcé utilise la recherche locale externe PyVRP
et, sur les grands cas selon le temps restant, son HGS. Ces contributions sont
attribuées à la bibliothèque. L'initial n'est pas une construction seule.

Le terminal affiche pour chaque moteur la durée complète, la faisabilité,
la flotte, la référence et l'écart compatible, le temps réel, le CPU et le
budget demandé. Un second tableau donne le gain entre méthodes :

`gain = 100 × (durée ILS initial − durée renforcée) / durée ILS initial`.

Dans un lot, le comparatif est affiché **après chaque instance et chaque graine**,
dès que toutes les méthodes demandées sont terminées pour ce cas. Le bilan
global reprend ensuite tous les cas. Cette règle fonctionne aussi avec plusieurs
processus, sans mélanger les instances, tailles ou graines.

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

**Lots de test :** chaque ligne suivante compare les deux méthodes pour toutes
les instances sélectionnées. Une graine est utilisée par défaut (4101).

```powershell
# Un cas de chacune des six familles : six instances, douze résolutions.
python scripts/test_instances.py --instances C101 C201 R101 R201 RC101 RC201 --seconds 5 --label comparaison_six_familles

# Toutes les 56 Solomon à 100 clients : 112 résolutions.
python scripts/test_instances.py --all --sizes 100 --seconds 5 --label comparaison_solomon_complete

# Toutes les 60 instances à 1000 clients : 120 résolutions, campagne longue.
python scripts/test_instances.py --all --sizes 1000 --seconds 30 --label comparaison_1000_complete

# Vérifier la sélection et le nombre de résolutions sans lancer de calcul.
python scripts/test_instances.py --all --sizes 100 1000 --seconds 5 --dry-run
```

Pour avancer famille par famille, ajouter `--families C1`, `C2`, `R1`, `R2`,
`RC1` ou `RC2` à une commande avec `--all --sizes 100` ou `1000`.
Les campagnes complètes ci-dessus sont des commandes proposées, pas des
comparaisons exhaustives déjà exécutées. Deux moteurs doublent le nombre
de résolutions. Avec un processus, les 60 grands cas peuvent demander
environ une heure à trente secondes par moteur, plus construction et préparation.

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

'''+frame[['instance','n','initial_requested_s','initial_duration','reinforced_duration','duration_gain_pct',
        'initial_wall_s','reinforced_wall_s','initial_cpu_s','reinforced_cpu_s','conclusion']].to_markdown(index=False,floatfmt='.4f')+'''

Les résultats de ces cas restent un contrôle de fonctionnement des
commandes. Ils ne constituent pas une nouvelle preuve statistique de supériorité
universelle. Les tournées et sources sont dans
`results/terminal_comparison/`.
'''
    env_receipt=ROOT/'results/terminal_comparison/VALIDATION_ENV_STATIQUE.json'
    if env_receipt.exists():
        env=json.loads(env_receipt.read_text(encoding='utf-8'))
        assert env['validated'] and env['trials']==12 and env['paired_comparisons']==6
        text+='''

**Correction de l'environnement vérifiée.** L'environnement local `.venv`
a été installé et `pip check` ne signale aucune dépendance incohérente.
Le lot C101, C201, R101, R201, RC101 et RC201 a été réellement exécuté avec
ce Python, graine 4101, cinq secondes demandées par moteur : douze solutions
réalisables et six comparatifs immédiats affichés. Les tournées, références,
formules et empreintes de sources ont été contrôlées indépendamment.
Cette vérification des six familles ne représente pas une campagne exhaustive
sur les 116 instances. Les preuves sont dans
`results/terminal_comparison/verification_env_six_familles/` et
`results/terminal_comparison/VALIDATION_ENV_STATIQUE.json`.
'''
    text=text.replace('python scripts/test_instances.py',r'.\.venv\Scripts\python.exe scripts/test_instances.py')
    (ROOT/'docs/COMPARAISON_INITIAL_RENFORCE.md').write_text(text,encoding='utf-8')
    for doc in [ROOT/'COMMANDES_TERMINAL.md',ROOT/'README.md']:
        body=doc.read_text(encoding='utf-8')
        title='## Comparaison automatique : ILS initial et profil renforcé'
        short=text if doc.name=='COMMANDES_TERMINAL.md' else r'''## Comparaison automatique : ILS initial et profil renforcé

Les commandes sans méthode explicite exécutent désormais `ils` **et**
`size_based` : deux résolutions par instance/graine, avec tableau de durées,
écarts au témoin et temps, puis gain signé entre méthodes. Les égalités,
régressions et échecs sont conservés. Pour un seul moteur : `--method size_based`.
Utiliser directement `.\.venv\Scripts\python.exe`, même si `.venv_dabia` est actif.
Voir [COMPARAISON_INITIAL_RENFORCE.md](docs/COMPARAISON_INITIAL_RENFORCE.md).
'''
        if title in body:
            body=re.sub(re.escape(title)+r'\n.*?(?=\n## |\Z)',lambda m:short.rstrip(),body,flags=re.S)
        else:
            split=body.find('\n\n');body=body[:split+2]+short+'\n'+body[split+2:]
        doc.write_text(body,encoding='utf-8')
    path=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb';nb=nbformat.read(path,4)
    existing=next((c for c in nb.cells if c.metadata.get('initial_reinforced_commands')),None)
    nb.cells=[c for c in nb.cells if not c.metadata.get('initial_reinforced_commands')]
    cell=nbformat.v4.new_markdown_cell(text,metadata={'initial_reinforced_commands':True})
    if existing:cell.id=existing.id
    nb.cells.append(cell);nbformat.validate(nb);nbformat.write(nb,path);write_markdown(nb)
    (out/'VALIDATION.json').write_text(json.dumps(dict(validated=True,checked_trials=len(records),
        feasible=sum(r['measurement']['valid'] for r in records),
        checked_pairs=len(pairs),independent_evaluation=True,source_hashes_checked=True,
        campaign_labels=[folder.name for folder in folders],
        objective='Complete duration, fixed symmetric travel, departures zero',
        limitation='Equal requested parameters, not strictly equal measured total runtimes'),indent=2),encoding='utf-8')
    print(frame[['instance','initial_duration','reinforced_duration','duration_gain_pct','conclusion']].to_string(index=False))


if __name__=='__main__':main()
