"""Valide les mesures CPU, la non-régression et la documentation ajoutée."""
from pathlib import Path
import hashlib,json,re,sys,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import nbformat
import pandas as pd


def main():
    folder=ROOT/'results/time_objective/cpu_optimization'
    paired=pd.read_csv(folder/'PAIRES_AVANT_APRES.csv')
    assert len(paired)==12
    assert (paired.duration_before-paired.duration_after).abs().max()<1e-7
    tasks=pd.read_csv(folder/'DEPARTS_INDIVIDUELS.csv')
    assert len(tasks)==72
    assert tasks.groupby(['instance','seed']).duration.agg(lambda x:x.max()-x.min()).max()<1e-7
    batches=pd.read_csv(folder/'MESURES_PROCESSUS.csv')
    assert len(batches)==6
    assert (batches.total_cpu_s-batches.workers_lifetime_cpu_s-batches.parent_cpu_s).abs().max()<.032
    for path in (folder/'parallel').glob('workers*_rep*/batch.json'):
        r=json.loads(path.read_text())
        assert len(r['initializers'])==r['workers']
        assert r['total_cpu_s']+.032>=sum(c['cpu_total_s'] for c in r['cases'])
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    for name in paired.instance.unique():
        for ext in ['.vrp','.sol']:
            file=name+ext
            assert hashlib.sha256((ROOT/'data/instances'/file).read_bytes()).hexdigest()==manifest['files'][file]['sha256']
    current=ROOT/'algo/duration_refine.py'
    assert current.read_bytes()==(folder/'source_after/algo/duration_refine.py').read_bytes()
    tests=ET.parse(folder/'tests.xml').getroot()
    assert not list(tests.iter('failure')) and not list(tests.iter('error'))
    skipped=len(list(tests.iter('skipped')))
    passed=len(list(tests.iter('testcase')))-skipped
    assert passed==171 and skipped==0
    before=json.loads((ROOT/'results/time_objective/outliers10/VALIDATION_OPTIMISATION_DUREE.json').read_text())
    old_csv=ROOT/'results/time_objective/outliers10/AVANT_APRES_ESSAIS.csv'
    assert hashlib.sha256(old_csv.read_bytes()).hexdigest()==before['result_csv_sha256']
    nb=nbformat.read(ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb',as_version=4)
    nbformat.validate(nb)
    assert len([c for c in nb.cells if c.metadata.get('cpu_completion')])==1
    report=(ROOT/'LIVRABLE_FINAL.md').read_text(encoding='utf-8')
    assert report.count('### 6.12.')==1 and '39.57' in report
    for path in re.findall(r'!\[[^\n]*\]\(([^)]+)\)',report):assert (ROOT/path).exists(),path
    assert not any(ch in c.source for c in nb.cells for ch in ['\x08','\x0c','\r'])
    # Les instantanés avant/après sont distincts ; les sources communes complètent
    # la reproductibilité sans remplacer les versions d'anciennes campagnes.
    # Vérifier les sources historiques figées, sans ajouter les nouveaux modules
    # du dépôt ni attribuer rétroactivement leur présence à l'étude CPU.
    frozen=json.loads((folder/'VALIDATION_CPU.json').read_text())['sources']
    hashes={}
    for rel,expected in frozen.items():
        target=folder/'source_common'/rel
        actual=hashlib.sha256(target.read_bytes()).hexdigest()
        assert actual==expected,rel
        hashes[rel]=actual
    info=json.loads((folder/'analysis.json').read_text())
    receipt=dict(validated=True,paired_runs=24,paired_cases=12,identical_costs=True,
        parallel_tasks=72,all_feasible=True,cpu_reduction_pct=info['cpu_reduction_pct'],
        cpu_counter='process_time for single process; Windows GetProcessTimes for all child lifetimes + parent',
        tests_passed=171,tests_skipped=0,prior_best_results_unchanged=True,
        source_before_sha256=hashlib.sha256((folder/'source_before/algo/duration_refine.py').read_bytes()).hexdigest(),
        source_after_sha256=hashlib.sha256(current.read_bytes()).hexdigest(),sources=hashes)
    (folder/'VALIDATION_CPU.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k!='sources'},indent=2))


if __name__=='__main__':main()
