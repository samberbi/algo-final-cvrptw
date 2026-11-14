"""Vérifie le pilote du sélecteur et documente le nouveau profil de test."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import nbformat
import pandas as pd
import vrplib
from algo.size_policy import selected_method,SMALL_MAX_CLIENTS
from algo.comparison_status import present,describe_positive
from scripts.audit_gap_status import check
from scripts.revision_duree import write_markdown


def main():
    label='selection_par_taille_validation';source=ROOT/'results/local'/label
    out=ROOT/'results/size_policy'/label;out.mkdir(parents=True,exist_ok=True)
    if not source.is_dir():source=out  # Relecture sur un clone dépourvu de results/local.
    records=[];rows=[]
    for path in sorted(source.glob('*.json')):
        record=json.loads(path.read_text(encoding='utf-8'))
        if 'measurement' not in record:continue
        m=record['measurement'];result=record['result']
        assert m['method']=='size_based' and m['selected_method']==selected_method(m['n'])
        assert result['selection_policy']['small_max_clients']==SMALL_MAX_CLIENTS
        assert result['selection_policy']['no_reference_or_gap_used']
        checked=check(m['instance'],m['n'],result['routes'])
        assert checked['valid'] and abs(checked['duration']-m['duration'])<1e-7
        ref=record['reference'];pathref=ROOT/ref['source']
        routes=(vrplib.read_solution(pathref)['routes'] if pathref.suffix=='.sol'
                else json.loads(pathref.read_text())['result']['routes'])
        reference=check(m['instance'],m['n'],routes)
        assert reference['valid'] and abs(reference['duration']-m['reference_duration'])<1e-7
        assert abs(100*(checked['duration']/reference['duration']-1)-m['delta_reference_pct'])<1e-7
        rows.append(dict(Instance=m['instance'],Clients=m['n'],Moteur=m['selected_method'],
            Duree=m['duration'],Comparaison=present(m['duration'],m['reference_duration']),
            CPU_s=m['cpu_s'],Reel_s=m['wall_s']))
        records.append(record)
    assert len(records)==6
    if source.resolve()!=out.resolve():
        for path in source.iterdir():
            target=out/path.name
            if path.is_dir() and path.name=='source':shutil.copytree(path,target,dirs_exist_ok=True)
            elif path.is_file():
                if target.exists():assert target.read_bytes()==path.read_bytes()
                else:shutil.copy2(path,target)
    protocol=json.loads((out/'protocol.json').read_text())
    for rel,expected in protocol['sources'].items():
        assert hashlib.sha256((out/'source'/rel).read_bytes()).hexdigest()==expected
    frame=pd.DataFrame(rows).sort_values(['Clients','Instance'])
    frame.to_csv(out/'TABLEAU_SELECTION.csv',index=False,encoding='utf-8-sig')
    text='''### 6.14. Nouvelle configuration : sélection explicite selon la taille

Les nouvelles commandes de test utilisent le profil `size_based` par défaut :

| Taille | Moteur choisi |
|---|---|
| Au plus 100 clients | Construction regret-2 seule, douze tentatives |
| Plus de 100 clients | Profil renforcé existant : constructions propres, recherche locale PyVRP et partitionnement HiGHS |

Le seuil de 100 est une règle déclarée avant les mesures, alignée sur la
séparation des petites tailles Solomon et des grandes tailles testées. Ce
sélecteur n'est pas une nouvelle métaheuristique : il choisit un moteur existant.
Il ne consulte ni référence, ni coût cible, ni gap. Aucune solution n'est rejetée
ou détériorée pour forcer son écart dans un intervalle.

Pour les petits cas, cette configuration privilégie une construction rapide.
Elle peut être moins bonne que notre ILS ou le renforcé : cette perte de qualité
est mesurée, pas masquée. La variante ne garantit pas le seuil académique. Les
ILS et recuit autonomes restent disponibles, ainsi que les anciens hybrides.
Le code des deux moteurs sélectionnés reste inchangé ; ils minimisent toujours
la durée complète avec les mêmes contraintes. L'API et les campagnes historiques
conservent leurs configurations pour la reproductibilité. Les résultats déjà
enregistrés ne sont pas réétiquetés comme résultats de cette nouvelle sélection.

**Vérification réellement exécutée.** Six instances, une graine (4101), budget
demandé cinq secondes. Les choix, les tournées et les coûts ont été revérifiés
indépendamment. Sur les petits cas, la construction s'arrête après douze
tentatives ; sur les grands cas, le renforcé utilise un budget total souple.
Les limites de temps et dépassements éventuels sont ceux mesurés, pas des valeurs
artificiellement plafonnées. Le garde-fou par processus reste 120 secondes.

'''+frame.to_markdown(index=False,floatfmt='.4f')+'''

Les références sont OR-Tools enregistré pour C101/25 et C101/50, puis les plans
publics optimisés en distance et réévalués en durée. Ce ne sont pas des optima
temporels démontrés ; les statuts de comparaison gardent donc cette qualification.
Le dépassement de six pour cent observé sur C101/25 est conservé. Ce petit pilote
ne démontre pas la performance du sélecteur sur tous les scénarios.

```powershell
python scripts/test_instances.py --instances C101:25 C101:50 C101:100 C1_2_1:200 C1_10_6:1000 R2_10_8:1000 --seconds 5 --label selection_par_taille_validation
python scripts/test_instances.py --instances C101 --method refined --seconds 5
```

La première commande explicite la sélection (également active sans `--method`).
La seconde force le profil renforcé, y compris sur une petite instance. Les
sorties affichent `size_based` et **Moteur exécuté**, conservés aussi dans les
CSV/JSON. Les résultats et sources de ce pilote sont dans
`results/size_policy/selection_par_taille_validation/`.
'''
    suite=ET.parse(ROOT/'livraison/TESTS_SOUTENANCE.xml').getroot()
    assert not list(suite.iter('failure')) and not list(suite.iter('error'))
    passed=len(list(suite.iter('testcase')))-len(list(suite.iter('skipped')))
    text+=f'\n**Tests après ajout du sélecteur : {passed} réussites**, deux modules optionnels ignorés. Les bornes 100/101 et le transfert des paramètres aux moteurs sont contrôlés.\n'
    (ROOT/'docs/SELECTION_PAR_TAILLE.md').write_text(text,encoding='utf-8')
    nbpath=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb';nb=nbformat.read(nbpath,4)
    existing=next((c for c in nb.cells if c.metadata.get('size_policy_summary')),None)
    nb.cells=[c for c in nb.cells if not c.metadata.get('size_policy_summary')]
    cell=nbformat.v4.new_markdown_cell(text,metadata={'size_policy_summary':True})
    if existing is not None:cell.id=existing.id
    index=next(i for i,c in enumerate(nb.cells) if c.source.startswith('## 7.'))
    nb.cells.insert(index,cell)
    old='La méthode associe notre constructeur et notre ILS à un HGS externe fourni par **PyVRP 0.12.2**, explicitement attribué à ses auteurs.'
    new=('Les expériences historiques comparent notre constructeur et notre ILS aux hybrides intégrant '
         'le moteur externe **PyVRP 0.12.2**, explicitement attribué à ses auteurs. '
         'La nouvelle configuration des commandes choisit la construction seule jusqu’à 100 clients '
         'et notre profil renforcé au-delà ; son fonctionnement et son pilote sont documentés en section 6.14.')
    nb.cells[0].source=nb.cells[0].source.replace(old,new)
    meta=nb.cells[0].metadata.get('comparison_render')
    if meta:meta['original_source']=meta['original_source'].replace(old,new)
    nbformat.validate(nb);nbformat.write(nb,nbpath);write_markdown(nb)
    notice='''## Configuration actuelle des commandes : sélection par taille

Depuis cette révision, les nouvelles commandes de test utilisent `size_based`
par défaut : construction seule pour 25/50/100 clients, renforcé au-delà.
Le moteur choisi est affiché et enregistré. Pour reproduire un ancien test
implicitement renforcé, ajouter `--method refined`. Les résultats historiques
et leurs références restent conservés ; ils ne deviennent pas des résultats
du nouveau sélecteur. Le seuil ne dépend pas du gap. La validation de six cas
et les limites sont dans [SELECTION_PAR_TAILLE.md](docs/SELECTION_PAR_TAILLE.md).

'''
    for path in [ROOT/'COMMANDES_TERMINAL.md',ROOT/'README.md']:
        body=path.read_text(encoding='utf-8')
        if '## Configuration actuelle des commandes : sélection par taille' not in body:
            split=body.find('\n\n');body=body[:split+2]+notice+body[split+2:]
            path.write_text(body,encoding='utf-8')
    receipt=dict(validated=True,policy='size_based',small_max_clients=100,small_engine='construction',
        large_engine='refined',selection_uses_only_n=True,checked_trials=6,feasible=6,
        input_instances=[dict(instance=r['measurement']['instance'],n=r['measurement']['n']) for r in records],
        no_target_gap_guarantee=True,original_engine_implementations_changed=False)
    (out/'VALIDATION.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(frame.to_string(index=False));print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
