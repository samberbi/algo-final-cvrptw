"""Check the finished dataset, attempts, stages and executed publication."""
from pathlib import Path
import sys,json,hashlib,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
import nbformat,pymupdf


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    validation=json.loads((ROOT/'results/report/validation.json').read_text())
    assert validation['attempts']==1000 and validation['instances']==356
    focused=validation['focused']
    assert focused['runs']==80 and focused['instances']==28
    focus_paths=list((ROOT/'results/focused/runs').glob('*.json'))
    assert len(focus_paths)==80
    assert {p.name:digest(p) for p in focus_paths}==focused['raw_files_sha256']
    for folder,key in [('campaign','raw_files_sha256'),('final','derived_files_sha256')]:
        paths=list((ROOT/'results'/folder/'runs').glob('*.json'))
        assert len(paths)==1000
        assert {p.name:digest(p) for p in paths}==validation[key]
    largest=list((ROOT/'results/largest_v2/runs').glob('*.json'))
    assert len(largest)==167
    assert {p.name:digest(p) for p in largest}==validation['largest_files_sha256']
    nb_path=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb'
    assert digest(nb_path)==validation['notebook_sha256']
    nb=nbformat.read(nb_path,as_version=4);nbformat.validate(nb)
    codes=[c for c in nb.cells if c.cell_type=='code']
    assert all(c.execution_count is not None for c in codes)
    assert not any(o.output_type=='error' for c in codes for o in c.outputs)
    test=ET.parse(ROOT/'results/tests.xml').getroot().find('testsuite')
    assert test.get('failures')=='0' and test.get('errors')=='0'
    text=''
    for name in ['RAPPORT_CVRPTW','ANNEXE_INSTANCES']:
        pdf=pymupdf.open(ROOT/'livraison'/(name+'.pdf'))
        assert len(pdf)>0
        assert not any(w[0]<-1 or w[2]>page.rect.width+1 for page in pdf for w in page.get_text('words'))
        current='\n'.join(p.get_text() for p in pdf)
        if name=='RAPPORT_CVRPTW':text=current
        else:
            refs=json.loads((ROOT/'data/manifest.json').read_text())['reference_instances']
            assert all(r['instance'] in current for r in refs)
    assert '1 000' in text or '1000' in text
    assert '{{' not in text and '<!-- EXEC:' not in text
    receipt=dict(complete=True,primary_runs=80,primary_instances=28,base_attempts=1000,final_trajectories=1000,instances=356,
        tests_passed=int(test.get('tests')),executed_cells=len(codes),all_pdf_text_in_bounds=True,
        report_sha256=digest(ROOT/'livraison/RAPPORT_CVRPTW.pdf'),notebook_sha256=digest(nb_path))
    (ROOT/'livraison/VALIDATION.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
