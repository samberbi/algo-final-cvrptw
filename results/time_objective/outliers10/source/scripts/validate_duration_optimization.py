"""Vérifie les 43 résultats finaux ciblés et écrit leur reçu, sans export de rapport."""
from pathlib import Path
import hashlib,json,platform,sys,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
import importlib.metadata
from algo.data import load,reference
from algo.verify import verify


def main():
    folder=ROOT/'results/time_objective/outliers10'
    protocol=json.loads((folder/'protocol.json').read_text())
    rows=pd.read_csv(folder/'AVANT_APRES_ESSAIS.csv')
    expected={(name,seed) for name,seed in protocol['jobs']}
    assert set(zip(rows.instance,rows.seed))==expected and len(rows)==43
    assert len(rows.instance.unique())==26
    for row in rows.itertuples():
        r=json.loads((ROOT/row.source).read_text())
        ins=load(ROOT/'data/instances'/(row.instance+'.vrp'))
        check=verify(r['result']['routes'],ins)
        refs,_=reference(ROOT/'data/instances'/(row.instance+'.sol'))
        ref=verify(refs,ins)
        assert check['valid'] and ref['valid']
        assert r['result']['objective']=='duration'
        assert abs(check['duration']/10-r['result']['cost'])<1e-7
        delta=100*(check['duration']/ref['duration']-1)
        assert abs(delta-row.final_pct)<1e-7 and delta<6
        assert abs(row.cumulative_runtime_s-r['runtime_s'])<1e-7
        if 'parent_source' in r:
            parent=json.loads((ROOT/r['parent_source']).read_text())
            assert abs(r['runtime_s']-parent['runtime_s']-r['additional_runtime_s'])<1e-7
    tests=ET.parse(folder/'tests.xml').getroot()
    assert not list(tests.iter('failure')) and not list(tests.iter('error'))
    skipped=len(list(tests.iter('skipped')))
    passed=len(list(tests.iter('testcase')))-skipped
    # Conserver aussi les dépendances et scripts utilisés pour la reproductibilité.
    hashes={}
    paths=list((ROOT/'algo').glob('*.py'))+[ROOT/'scripts'/name for name in
        ['optimize_duration_outliers.py','continue_duration_outliers.py','summarize_duration_optimization.py','validate_duration_optimization.py']]
    for path in paths:
        rel=path.relative_to(ROOT)
        destination=folder/'source'/rel;destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists():assert destination.read_bytes()==path.read_bytes(),rel
        else:destination.write_bytes(path.read_bytes())
        hashes[rel.as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    receipt=dict(validated=True,objective='sum_route_duration',departures=0,
        reference_kind='Duration of feasible distance-BKS plan, not a proven duration optimum',
        scope='Targeted development on 26 previously selected instances; not full-catalogue independent validation',
        paired_trials=43,instances=26,all_feasible=True,above_6=0,
        worst_pct=float(rows.final_pct.max()),tests_passed=passed,tests_skipped=skipped,
        continuation_trials=int(rows.source.str.contains('outliers_hgs30').sum()),
        max_cumulative_runtime_s=float(rows.cumulative_runtime_s.max()),sources=hashes,
        python=platform.python_version(),pyvrp=importlib.metadata.version('pyvrp'),
        result_csv_sha256=hashlib.sha256((folder/'AVANT_APRES_ESSAIS.csv').read_bytes()).hexdigest())
    (folder/'VALIDATION_OPTIMISATION_DUREE.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print({k:v for k,v in receipt.items() if k not in ['sources']})


if __name__=='__main__':main()
