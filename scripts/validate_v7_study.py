"""Audit the v7 research appendix without replacing the assessed v6 receipt."""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nbformat
from scripts.analyze_v7 import analyze, BASE


def main():
    labels = ['development', 'development_descent', 'development_intensive', 'confirmation_external', 'continuation_120']
    results = {label: analyze(label) for label in labels}
    total = sum(len(data[0]) for data in results.values())
    failures = sum(data[3]['failures'] for data in results.values())
    assert total == 129 and failures == 3
    runs, summary, _, analysis = results['confirmation_external']
    assert len(runs) == 48 and runs.valid.all()
    assert runs.groupby('variant').size().to_dict() == dict(baseline=24, external_warm=24)
    final_runs, final_summary, _, final_analysis = results['continuation_120']
    assert len(final_runs) == 48 and final_runs.valid.all()
    assert final_runs.groupby('variant').size().to_dict() == dict(baseline=24, hybrid_hgs=24)
    protocol120 = json.loads((BASE/'continuation_120/protocol.json').read_text(encoding='utf-8'))
    assert len(protocol120['prefix_origins']) == 24
    for name, expected in protocol120['prefix_origins'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected
    nb = nbformat.read(ROOT/'notebooks/Recherche_1000_clients_V7.ipynb', as_version=4)
    code = [c for c in nb.cells if c.cell_type == 'code']
    assert code and all(c.execution_count is not None for c in code)
    assert not any(o.output_type == 'error' for c in code for o in c.outputs)
    suites = ET.parse(BASE/'tests.xml').getroot()
    leaves = list(suites.iter('testcase'))
    assert len(leaves) >= 134 and not list(suites.iter('failure')) and not list(suites.iter('error'))
    decision = json.loads((BASE/'decision.json').read_text(encoding='utf-8'))
    assert not decision['own_default_changed'] and not decision['external_is_our_implementation']
    protocol = json.loads((BASE/'confirmation_external/protocol.json').read_text(encoding='utf-8'))
    normalized_sources = {Path(k).as_posix():v for k,v in protocol['sources'].items()}
    for name in ['algo/optimized.py', 'algo/iterated.py', 'algo/profiles.py']:
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == normalized_sources[name]
    assessed = json.loads((ROOT/'livraison/VALIDATION.json').read_text(encoding='utf-8'))
    assert assessed['edition'] in ['ils_v6','hybrid_catalog_v8']
    external = final_summary.set_index('variant').loc['hybrid_hgs']
    assert decision['external_mean_below_6'] == bool(external.mean_gap < 6)
    files = ['docs/RECHERCHE_GRANDES_INSTANCES_V7.md', 'notebooks/Recherche_1000_clients_V7.ipynb',
             'notebooks/Recherche_1000_clients_V7.html', 'livraison/RESULTATS_ILS_V7.csv',
             'livraison/RESULTATS_ILS_V7.html', 'results/optimization_v7/tests.xml']
    receipt = dict(edition='research_v7_external_reference', complete=True, executed=total,
        technical_failures=failures, valid_60s_runs=48, valid_120s_pipelines=48,
        reused_distinct_prefixes=24, tests_passed=len(leaves)-len(list(suites.iter('skipped'))),
        own_default_changed=False, current_delivery_edition=assessed['edition'],
        research_receipt_not_authoritative=True,
        external_version='0.12.2', external_mean_gap=float(external.mean_gap),
        external_worst_gap=float(external.worst_gap), paired_analysis=final_analysis['comparisons'],
        files={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files},
        caveat='External reference, not our implementation; two seeds and twelve previously studied instances')
    (ROOT/'livraison/validation_recherche_v7.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
