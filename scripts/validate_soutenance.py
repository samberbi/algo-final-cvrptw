"""Contrôle de la remise notebook actuelle, sans PDF ni nouvelle optimisation."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    # Ces validations recalculent coûts et contraintes depuis les tournées
    # enregistrées ; elles ne prétendent pas relancer toutes les recherches.
    for script in ['analyze_duration.py', 'validate_duration_optimization.py',
                   'validate_reporting_completion.py']:
        subprocess.run([sys.executable, str(ROOT/'scripts'/script)], cwd=ROOT, check=True)
    if (ROOT/'results/time_objective/quality_cpu_check/summary.json').exists():
        subprocess.run([sys.executable, str(ROOT/'scripts/report_quality_time.py')], cwd=ROOT, check=True)
    manifest = json.loads((ROOT/'data/manifest.json').read_text())
    for name, info in manifest['files'].items():
        path = ROOT/'data/instances'/name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == info['sha256'], name
    import nbformat
    notebook = nbformat.read(ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb', as_version=4)
    nbformat.validate(notebook)
    code = [c for c in notebook.cells if c.cell_type == 'code']
    assert all(c.execution_count is not None for c in code)
    assert not any(o.output_type == 'error' for c in code for o in c.outputs)
    assert sum(bool(c.metadata.get('soutenance_commands')) for c in notebook.cells) == 1
    report = (ROOT/'LIVRABLE_FINAL.md').read_text(encoding='utf-8')
    for path in re.findall(r'!\[[^\n]*\]\(([^)]+)\)', report):
        assert (ROOT/path).is_file(), path
    tests = ROOT/'livraison/TESTS_SOUTENANCE.xml'
    assert tests.exists(), 'Exécuter pytest avec --junitxml=livraison/TESTS_SOUTENANCE.xml'
    suite = ET.parse(tests).getroot()
    assert not list(suite.iter('failure')) and not list(suite.iter('error'))
    receipt = dict(validated=True, instances=len(manifest['reference_instances']),
        tests=len(list(suite.iter('testcase'))), skipped=len(list(suite.iter('skipped'))),
        notebook_code_cells=len(code),
        scope='Current notebook, recorded solutions, immutable instance hashes and local test suite',
        limitation='No new uniform 356-instance optimization campaign; best archive uses mixed budgets',
        canonical_notebook='notebooks/Livrable_Final_CVRPTW.ipynb')
    (ROOT/'livraison/VALIDATION_SOUTENANCE.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
