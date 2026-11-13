"""Valide mesures temporelles, références qualifiées, modèle et documents exécutés."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import nbformat
import numpy as np
import pymupdf
from algo.model import Instance,Objective
from algo.verify import verify
from controle.exact import exact
from scripts.analyze_duration import analyze,BASE


def main():
    df,cases,sizes,repeated,descriptive,info=analyze()
    assert info['complete'] and len(df)==646 and len(cases)==356 and len(repeated)==180
    assert df.valid.all() and len(df[df.core])==472
    exact_paths=sorted((ROOT/'results/time_objective/exact').glob('exact-duration-*.json'))
    assert len(exact_paths)==10
    for path in exact_paths:
        r=json.loads(path.read_text());data=r['data']
        ins=Instance(r['instance'],np.array(data['xy']),np.array(data['demand']),np.array(data['service']),
                     np.array(data['early']),np.array(data['late']),np.array(data['travel']),
                     r['capacity'],r['vehicles'],r['horizon'])
        check=verify(r['solver']['routes'],ins)
        oracle=exact(ins,Objective.DURATION,max_clients=6)
        assert check['valid'] and oracle['status']==r['solver']['status']=='optimal'
        assert abs(oracle['score']/10-r['optimum'])<1e-7
        assert abs(check['duration']/10-r['optimum'])<1e-7
    # Les adaptateurs d'entrée peuvent évoluer ; les modules de calcul de la
    # campagne restent identiques à leurs instantanés exécutés.
    protocol=json.loads((BASE/'protocol.json').read_text())
    frozen={name.replace('\\','/'):sha for name,sha in protocol['sources'].items()}
    for stem in ['duration','duration_moves','duration_kernels','hgs_tuning','iterated','kernels','direct','verify','model','data','optimized','profiles']:
        path=Path('algo')/(stem+'.py')
        expected=frozen[path.as_posix()]
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
    nb=nbformat.read(ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb',4)
    code=[c for c in nb.cells if c.cell_type=='code']
    assert code and all(c.execution_count is not None for c in code)
    assert not any(o.output_type=='error' for c in code for o in c.outputs)
    report=(ROOT/'livraison/RAPPORT_CVRPTW.md').read_text(encoding='utf-8')
    assert 'min T=' in report and 'unit_duration_cost=1' in report and 'start_late=0' in report
    assert '646' in report and '356' in report and '24.969' in report.replace(',','.')
    assert not any(c in report for c in ['\x08','\x0c'])
    tests=ET.parse(ROOT/'livraison/TESTS.xml').getroot()
    assert not list(tests.iter('failure')) and not list(tests.iter('error'))
    skipped=len(list(tests.iter('skipped')));passed=len(list(tests.iter('testcase')))-skipped
    assert passed>=165
    with pymupdf.open(ROOT/'livraison/RAPPORT_CVRPTW.pdf') as pdf:
        pages=len(pdf)
        assert all(p.get_text().strip() for p in pdf)
        assert not any(w[0]<-1 or w[2]>p.rect.width+1 for p in pdf for w in p.get_text('words'))
    manifest=ROOT/'MANIFESTE_SHA256.json'
    if manifest.exists() and '--no-manifest' not in sys.argv:
        for name,expected in json.loads(manifest.read_text()).items():
            path=(ROOT/name).resolve();assert path.is_relative_to(ROOT.resolve())
            assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,name
    receipt=dict(validated=True,objective='sum_route_duration',departures=0,
                 components=['travel','waiting','service'],instances=356,runs=646,feasible=int(df.valid.sum()),
                 core_runs=472,repetitions=180,shared_runs=6,exact_controls=10,
                 tests_passed=passed,tests_skipped=skipped,pdf_pages=pages,
                 mean_instance_gain_initial_pct=info['mean_instance_gain_initial_pct'],
                 mean_instance_delta_reference_pct=info['mean_instance_delta_reference_pct'],
                 worst_instance_delta_reference_pct=float(cases.mean_delta_reference_pct.max()),
                 reference_kind='Duration of distance-BKS plans, not a known time optimum',
                 attribution='Own duration ILS/SA and integration; external PyVRP 0.12.2 HGS',
                 report_sha256=hashlib.sha256((ROOT/'livraison/RAPPORT_CVRPTW.pdf').read_bytes()).hexdigest())
    (ROOT/'livraison/VALIDATION_DUREE.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
