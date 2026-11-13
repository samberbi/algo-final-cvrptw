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
    dabia = None
    if (ROOT/'results/dabia2013/VALIDATION.json').exists():
        executables = [ROOT/'.venv_dabia/Scripts/python.exe', ROOT/'.venv_dabia/bin/python']
        executable = next((p for p in executables if p.is_file()), None)
        if executable is None:
            raise SystemExit('Extension Dabia : créer .venv_dabia et installer requirements-dabia.txt avant la validation complète')
        subprocess.run([str(executable), str(ROOT/'scripts/validate_dabia.py')], cwd=ROOT, check=True)
        dabia = json.loads((ROOT/'results/dabia2013/VALIDATION.json').read_text())
        assert len([c for c in notebook.cells if c.metadata.get('dabia_extension')]) == 1
    receipt = dict(validated=True, instances=len(manifest['reference_instances']),
        tests=len(list(suite.iter('testcase'))), skipped=len(list(suite.iter('skipped'))),
        notebook_code_cells=len(code),
        scope='Current notebook, recorded solutions, immutable instance hashes and local test suite',
        limitation='No new uniform 356-instance optimization campaign; best archive uses mixed budgets',
        canonical_notebook='notebooks/Livrable_Final_CVRPTW.ipynb',
        dabia_extension=dabia)
    (ROOT/'livraison/VALIDATION_SOUTENANCE.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
