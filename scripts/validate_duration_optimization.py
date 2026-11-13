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
        assert abs(row.selected_source_runtime_s-r['runtime_s'])<1e-7
        spent=0.
        for attempt_path in json.loads(row.attempt_sources):
            attempt=json.loads((ROOT/attempt_path).read_text())
            if 'parent_source' in attempt:
                parent=json.loads((ROOT/attempt['parent_source']).read_text())
                spent+=attempt['runtime_s']-parent['runtime_s']
            else:spent+=attempt['runtime_s']
        assert abs(row.cumulative_runtime_s-spent)<1e-7
        if 'parent_source' in r:
            parent=json.loads((ROOT/r['parent_source']).read_text())
            assert abs(r['runtime_s']-parent['runtime_s']-r['additional_runtime_s'])<1e-7
    coverage=pd.read_csv(ROOT/'results/time_objective/best_duration/COUVERTURE_472_ESSAIS.csv')
    assert len(coverage)==472 and coverage.instance.nunique()==356
    assert not coverage.duplicated(['instance','seed']).any()
    cache={}
    for row in coverage.itertuples():
        if row.instance not in cache:
            ins=load(ROOT/'data/instances'/(row.instance+'.vrp'))
            refs,_=reference(ROOT/'data/instances'/(row.instance+'.sol'))
            checked_ref=verify(refs,ins);assert checked_ref['valid']
            cache[row.instance]=(ins,checked_ref['duration'])
        ins,ref_duration=cache[row.instance]
        record=json.loads((ROOT/row.source).read_text())
        checked=verify(record['result']['routes'],ins)
        assert checked['valid']
        delta=100*(checked['duration']/ref_duration-1)
        assert abs(delta-row.best_delta_pct)<1e-7 and delta<6
        assert abs(checked['duration']/10-row.duration)<1e-7
    tests=ET.parse(folder/'tests.xml').getroot()
    assert not list(tests.iter('failure')) and not list(tests.iter('error'))
    skipped=len(list(tests.iter('skipped')))
    passed=len(list(tests.iter('testcase')))-skipped
    receipt_path=folder/'VALIDATION_OPTIMISATION_DUREE.json'
    frozen_expected=json.loads(receipt_path.read_text()).get('sources',{}) if receipt_path.exists() else {}
    for name,expected_hash in frozen_expected.items():
        assert hashlib.sha256((folder/'source'/name).read_bytes()).hexdigest()==expected_hash,name
    # Conserver aussi les dépendances et scripts utilisés pour la reproductibilité.
    hashes={}
    # Une validation ne doit jamais attribuer du code actuel à une ancienne campagne.
    # Les seuls fichiers historiques recevables sont ceux déjà figés dans son reçu.
    paths=[ROOT/name for name in frozen_expected]
    for path in paths:
        rel=path.relative_to(ROOT)
        destination=folder/'source'/rel;destination.parent.mkdir(parents=True,exist_ok=True)
        if not destination.exists():raise AssertionError('Source historique absente : '+str(rel))
        hashes[rel.as_posix()]=hashlib.sha256(destination.read_bytes()).hexdigest()
    receipt=dict(validated=True,objective='sum_route_duration',departures=0,
        reference_kind='Duration of feasible distance-BKS plan, not a proven duration optimum',
        scope='Targeted development on 26 previously selected instances; not full-catalogue independent validation',
        paired_trials=43,instances=26,all_feasible=True,above_6=0,
        worst_pct=float(rows.final_pct.max()),tests_passed=passed,tests_skipped=skipped,
        archive_coverage_trials=472,archive_coverage_instances=356,
        archive_all_feasible=True,archive_above_6=0,
        archive_worst_pct=float(coverage.best_delta_pct.max()),
        final_trials_using_continuation=int(rows.source.str.contains('outliers_hgs').sum()),
        max_cumulative_runtime_s=float(rows.cumulative_runtime_s.max()),sources=hashes,
        python=platform.python_version(),pyvrp=importlib.metadata.version('pyvrp'),
        result_csv_sha256=hashlib.sha256((folder/'AVANT_APRES_ESSAIS.csv').read_bytes()).hexdigest())
    (folder/'VALIDATION_OPTIMISATION_DUREE.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print({k:v for k,v in receipt.items() if k not in ['sources']})


if __name__=='__main__':main()
