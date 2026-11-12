"""Contrôle indépendant des résultats et des fichiers de la remise CVRPTW."""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nbformat
import pymupdf
from scripts.analyze_catalog_v8 import analyze as catalog
from scripts.analyze_worst_v9 import analyze, archive, recovery, restarts


def main():
    # Les données, protocoles et solutions sont revérifiés avant de lire le bilan.
    reference, cases, _, info = catalog()
    development, _, _ = analyze('development')
    confirmation, summary, _ = analyze('confirmation')
    updates = recovery()
    consolidated, _, current = archive()
    comparison = restarts()
    assert len(reference) == 472 and len(cases) == 356 and reference.valid.all()
    assert len(development) == 12 and len(confirmation) == 28
    assert len(updates) == 10 and len(comparison) == 6
    assert len(consolidated) == 472 and consolidated.valid.all()
    nb = nbformat.read(ROOT / 'notebooks/Livrable_Final_CVRPTW.ipynb', 4)
    code = [c for c in nb.cells if c.cell_type == 'code']
    assert code and all(c.execution_count is not None for c in code)
    assert not any(o.output_type == 'error' for c in code for o in c.outputs)
    suite = ET.parse(ROOT / 'livraison/TESTS.xml').getroot()
    assert not list(suite.iter('failure')) and not list(suite.iter('error'))
    skipped = len(list(suite.iter('skipped')))
    passed = len(list(suite.iter('testcase'))) - skipped
    assert passed > 0
    with pymupdf.open(ROOT / 'livraison/RAPPORT_CVRPTW.pdf') as pdf:
        pages = len(pdf)
        assert all(page.get_text().strip() for page in pdf)
        assert not any(w[0] < -1 or w[2] > page.rect.width + 1 for page in pdf for w in page.get_text('words'))
    manifest = ROOT / 'MANIFESTE_SHA256.json'
    if manifest.exists():
        for name, expected in json.loads(manifest.read_text()).items():
            path = ROOT / name
            assert path.resolve().is_relative_to(ROOT.resolve())
            assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
    candidate = summary.set_index('variant').loc['split20']
    result = dict(validated=True, tests_passed=passed, tests_skipped=skipped,
                  pdf_pages=pages, instances=356, reference_runs=472,
                  reference_mean_instance_gap=info['scopes']['catalog_356']['mean_instance_gap'],
                  reference_worst_gap=info['scopes']['catalog_356']['worst_run_gap'],
                  recovered_trials=10, archive_mean_instance_gap=current['summary']['mean_instance_gap'],
                  archive_worst_gap=current['maximum'],
                  archive_budget='Initial effort plus ten additional 180s continuations; mixed budgets',
                  confirmation_under7=int(candidate.under7), confirmation_worst=float(candidate.worst_gap),
                  attribution='Own construction/ILS/integration; external PyVRP 0.12.2 HGS')
    (ROOT / 'livraison/VALIDATION_REMISE.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
