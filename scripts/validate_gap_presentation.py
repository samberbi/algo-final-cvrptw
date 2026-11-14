"""Contrôle la présentation sans confondre gaps, paramètres et variations appariées."""
from pathlib import Path
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import nbformat
import pandas as pd
from algo.comparison_status import describe_positive
from scripts.present_gap_status import summaries


def main():
    out=ROOT/'results/presentation_status'
    audit=json.loads((out/'AUDIT.json').read_text());assert audit['validated'] and audit['errors']==0
    assert not json.loads((out/'ANOMALIES.json').read_text())
    policy=json.loads((out/'PRESENTATION.json').read_text())
    assert hashlib.sha256((ROOT/'results/gap_tables/DETAIL_TOUS_LES_ECARTS.csv').read_bytes()).hexdigest()==audit['raw_source_sha256']
    for name,expected in policy['unchanged_engine_hashes'].items():
        assert hashlib.sha256((ROOT/'algo'/name).read_bytes()).hexdigest()==expected
    for source,name,metric in [('results/time_objective/catalogue/core.csv','COUVERTURE','delta_reference_pct'),
        ('results/time_objective/best_duration/COUVERTURE_472_ESSAIS.csv','ARCHIVE','best_delta_pct')]:
        actual=pd.read_csv(out/(name+'_STATUTS.csv'));frame=pd.read_csv(ROOT/source)
        expected=summaries(frame,['n'],metric)
        pd.testing.assert_frame_equal(actual,expected,check_dtype=False,check_exact=False,atol=1e-10,rtol=1e-10)
        assert (actual.Essais==actual.Positifs+actual.References_depassees+actual.References_egalees+actual.Non_comparables).all()
        assert actual.Moyenne_positive_pct.dropna().gt(0).all()
        assert actual.Mediane_positive_pct.dropna().gt(0).all()
    nb=nbformat.read(ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb',4);nbformat.validate(nb)
    assert nb.metadata['comparison_status_presentation']==1
    codes=[c for c in nb.cells if c.cell_type=='code']
    assert all(c.execution_count is not None for c in codes)
    assert not any(o.output_type=='error' for c in codes for o in c.outputs)
    for cell in nb.cells:
        if cell.cell_type!='markdown':continue
        if cell.source.startswith('### 6.10.'):
            assert cell.source==cell.metadata['comparison_render']['original_source'], 'Sensibilité altérée'
            continue
        assert not re.search(r'(?<![\w.,])[-−]\d+(?:[.,]\d+)?\s*%',cell.source)
        assert not re.search(r'(?<![\d.,])\+?0(?:[.,]0+)?\s*%',cell.source)
        for block in re.finditer(r'(?m)(?:^\|[^\n]*\n?){2,}',cell.source):
            lines=block.group().strip().splitlines();head=[s.strip().lower() for s in lines[0].strip('|').split('|')]
            indexes=[i for i,s in enumerate(head) if any(k in s for k in ['gap','écart','ecart','delta','moyenne_positive','mediane_positive'])]
            for line in lines[2:]:
                row=[s.strip() for s in line.strip('|').split('|')]
                for i in indexes:
                    if i>=len(row):continue
                    value=re.match(r'^([+−-]?\d+(?:[.,]\d+)?)(?:\s*%|$)',row[i])
                    if value:assert float(value[1].replace(',','.').replace('−','-'))>0,(head[i],row[i])
    tests=ET.parse(ROOT/'livraison/TESTS_SOUTENANCE.xml').getroot()
    assert not list(tests.iter('failure')) and not list(tests.iter('error'))
    receipt=dict(validated=True,audited_comparisons=audit['records_checked'],
        reference_improvements=audit['improved_reference'],reference_equalities=audit['equal_reference'],
        zero_mean_or_median_groups_checked=audit['zero_mean_or_median_groups'],
        scientific_values_unchanged=True,original_solver_implementations_unchanged=True,conditional_means_verified=True,
        notebook_code_cells=len(codes),notebook_errors=0,
        tests_passed=len(list(tests.iter('testcase')))-len(list(tests.iter('skipped'))),
        tests_skipped=len(list(tests.iter('skipped'))),
        exception='Sensitivity parameter zeros and signed variations between own configurations are preserved; they are not benchmark gaps',
        limitation='No stronger benchmark or certified duration optimum created by this presentation')
    (ROOT/'livraison/VALIDATION_PRESENTATION_GAPS.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
