"""Audit new measurements, compatible BKS, archives, reports and test results."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import nbformat
import pymupdf
from docx import Document
from algo.data import load,reference
from algo.verify import verify
from scripts.analyze_v6 import analyze,BASE
from scripts.package_ils_v5 import semantic_text,EXCLUDED_WORD


def main():
    studies={}
    for label in ['development','validation','targeted_120','cache_followup']:
        _,_,_,studies[label]=analyze(label)
    assert sum(p['new_runs'] for p in studies.values())==126
    assert studies['cache_followup']['reused_reference_runs']==24
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    refs={r['instance']:r['reference_distance'] for r in manifest['reference_instances']}
    names=set()
    for label in studies:
        names.update(json.loads((BASE/label/'protocol.json').read_text())['instances'])
    instances={name:load(ROOT/'data/instances'/(name+'.vrp')) for name in names}
    for name,ins in instances.items():
        routes,cost=reference(ROOT/'data/instances'/(name+'.sol'))
        checked=verify(routes,ins)
        assert checked['valid'],name
        assert abs(checked['distance']/10-refs[name])<1e-7 and abs(cost-refs[name])<1e-7,name
    def checked_result(record,name):
        ins=instances.get(name)
        if ins is None:
            ins=load(ROOT/'data/instances'/(name+'.vrp'));instances[name]=ins
        result=record['result'];metrics=verify(result['routes'],ins)
        assert metrics['valid'] and abs(metrics['distance']/10-result['cost'])<1e-7
        assert abs(100*(result['cost']/refs[name]-1)-record['gap_pct'])<1e-7
    archive=[]
    for path in (BASE/'updated_archive').glob('*_*.json'):
        r=json.loads(path.read_text());name=r['instance']
        assert hashlib.sha256((ROOT/r['origin']).read_bytes()).hexdigest()==r['origin_sha256']
        before=json.loads((ROOT/r['origin']).read_text())
        charged=before['total_effort_s']
        for item in r['additional_runs']:
            source=ROOT/item['path'];assert hashlib.sha256(source.read_bytes()).hexdigest()==item['sha256']
            charged+=json.loads(source.read_text())['total_s']
        assert abs(charged-r['total_effort_s'])<1e-6
        assert r['gap_pct']<=before['gap_pct']+1e-8
        checked_result(r,name);archive.append(r)
    assert len(archive)==12 and sum(bool(r['additional_runs']) for r in archive)==3
    portfolios=[]
    for path in (BASE/'cold_portfolio').glob('*_*.json'):
        r=json.loads(path.read_text());checked_result(r,r['instance'])
        charged=0.
        assert len(r['sources_sha256'])==3
        inputs=[]
        for relative,expected in r['sources_sha256'].items():
            source=ROOT/relative;assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
            original=json.loads(source.read_text());charged+=original['total_s']
            assert original['instance']==r['instance'] and original['seed']==r['seed']
            inputs.append(original['result']['cost'])
        assert abs(charged+r['result']['runtime_s']-r['total_effort_s'])<1e-6
        assert r['result']['cost']<=min(inputs)+1e-7
        portfolios.append(r)
    assert len(portfolios)==24
    suite=ET.parse(BASE/'tests.xml').getroot().find('testsuite')
    assert int(suite.attrib['failures'])==int(suite.attrib['errors'])==int(suite.attrib.get('skipped',0))==0
    files=['README.md','LIVRABLE_FINAL.md','docs/AMELIORATIONS_ILS_V6.md',
           'notebooks/Livrable_Final_CVRPTW.ipynb','notebooks/Livrable_Final_CVRPTW.html',
           'notebooks/Ameliorations_ILS_V6.ipynb','notebooks/Ameliorations_ILS_V6.html',
           'livraison/RAPPORT_CVRPTW.pdf','livraison/RAPPORT_CVRPTW.docx',
           'livraison/RESULTATS_ILS_V6.csv','livraison/RESULTATS_ILS_V6.html']
    for name in ['Livrable_Final_CVRPTW','Ameliorations_ILS_V6']:
        nb=nbformat.read(ROOT/'notebooks'/(name+'.ipynb'),as_version=4)
        code=[c for c in nb.cells if c.cell_type=='code']
        assert code and all(c.execution_count is not None for c in code)
        assert not any(o.output_type=='error' for c in code for o in c.outputs)
    for relative in files:
        assert EXCLUDED_WORD not in semantic_text(ROOT/relative).lower(),relative
    with pymupdf.open(ROOT/'livraison/RAPPORT_CVRPTW.pdf') as pdf:
        pages=len(pdf)
        assert all(page.get_text().strip() for page in pdf)
        assert not any(w[0]<-1 or w[2]>p.rect.width+1 for p in pdf for w in p.get_text('words'))
    assert len(Document(ROOT/'livraison/RAPPORT_CVRPTW.docx').inline_shapes)>=14
    payload=dict(complete=True,edition='ils_v6',new_resolutions=126,development_runs=48,
        confirmation_runs=48,cache_followup_new_runs=24,reused_baseline_runs=24,targeted_120_runs=6,
        cold_portfolios=24,archive_instances=12,bks_compatibility_checked=sorted(names),
        tests=dict(suite.attrib),pdf_pages=pages,
        archive_mean_gap=sum(r['gap_pct'] for r in archive)/12,
        archive_mean_effort_s=sum(r['total_effort_s'] for r in archive)/12,
        cold_portfolio_mean_gap=sum(r['gap_pct'] for r in portfolios)/24,
        cold_portfolio_mean_effort_s=sum(r['total_effort_s'] for r in portfolios)/24,
        sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files})
    (ROOT/'livraison/validation_ils_v6.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    (ROOT/'livraison/VALIDATION.json').write_text(json.dumps(dict(edition='ils_v6',complete=True,
        authoritative_receipt='validation_ils_v6.json',new_resolutions=126,
        prior_edition_receipt_history_only='validation_ils_v5.json'),indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in payload.items() if k!='sha256'},indent=2))


if __name__=='__main__':main()
