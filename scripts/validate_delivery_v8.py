"""Authoritative final audit: full catalog, mathematical report and real tests."""
from pathlib import Path
import hashlib, json, sys, xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import nbformat
import pymupdf
from docx import Document
from scripts.analyze_catalog_v8 import analyze,BASE
from scripts.package_ils_v5 import semantic_text,EXCLUDED_WORD


def main():
    df,cases,sizes,a=analyze()
    assert a['complete'] and len(df)==472 and len(cases)==356
    assert a['new_pipelines']==448 and a['reused_pipelines']==24
    assert df.groupby('n').size().to_dict()=={100:112,200:60,400:60,600:60,800:60,1000:120}
    assert cases.groupby('n').size().to_dict()=={100:56,200:60,400:60,600:60,800:60,1000:60}
    assert df[df.n.isin([100,1000])].groupby('instance').seed.nunique().eq(2).all()
    assert df[~df.n.isin([100,1000])].groupby('instance').seed.nunique().eq(1).all()
    # An executed failure remains a failure; a real mean is never forced below 6.
    fields=['README.md','LIVRABLE_FINAL.md','docs/LIVRABLE_OPTIMISE_SOURCE.md',
        'docs/MODIFICATIONS_LIVRABLE_V8.md','docs/JOURNAL_EVOLUTION_ALGORITHME.md',
        'livraison/catalog_v8_figures/graph_model.png','livraison/catalog_v8_figures/graph_model.svg',
        'results/catalog_v8/graph_model_example.json','notebooks/Livrable_Final_CVRPTW.ipynb',
        'notebooks/Livrable_Final_CVRPTW.html','livraison/RAPPORT_CVRPTW.md',
        'livraison/RAPPORT_CVRPTW.html','livraison/RAPPORT_CVRPTW.pdf','livraison/RAPPORT_CVRPTW.docx',
        'livraison/RESULTATS_CATALOGUE_V8.csv','livraison/INSTANCES_CATALOGUE_V8.csv',
        'livraison/RESULTATS_CATALOGUE_V8.html','results/catalog_v8/analysis.json',
        'results/catalog_v8/tests.xml']
    nb=nbformat.read(ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb',as_version=4)
    code=[c for c in nb.cells if c.cell_type=='code']
    assert code and all(c.execution_count is not None for c in code)
    assert not any(o.output_type=='error' for c in code for o in c.outputs)
    suite=ET.parse(BASE/'tests.xml').getroot()
    assert not list(suite.iter('failure')) and not list(suite.iter('error'))
    tests=len(list(suite.iter('testcase')))-len(list(suite.iter('skipped')))
    assert tests>=142
    for f in fields:
        assert (ROOT/f).is_file(),f
        content=semantic_text(ROOT/f)
        assert EXCLUDED_WORD not in content.lower(),f
        assert not any(c in content for c in ['\x08','\x0c']),('Invalid formula control character',f)
    word=Document(ROOT/'livraison/RAPPORT_CVRPTW.docx')
    assert len(word.inline_shapes)>=12
    assert len(word.tables)>=8
    report=(ROOT/'livraison/RAPPORT_CVRPTW.md').read_text(encoding='utf-8')
    assert 'PyVRP' in report and '472' in report and '356' in report and '116' in report
    assert 'croisement' in report and 'réutilis' in report
    assert 'G_{phys}' in report and 'V_{phys}' in report and 'JOURNAL_EVOLUTION_ALGORITHME' in report
    with pymupdf.open(ROOT/'livraison/RAPPORT_CVRPTW.pdf') as pdf:
        pages=len(pdf)
        assert all(p.get_text().strip() for p in pdf)
        assert not any(w[0]<-1 or w[2]>p.rect.width+1 for p in pdf for w in p.get_text('words'))
        text='\n'.join(p.get_text() for p in pdf)
        assert '356' in text and '472' in text and 'PyVRP' in text
    payload=dict(edition='hybrid_catalog_v8',complete=True,instances=356,pipelines=472,
        new_pipelines=448,reused_pipelines=24,tests_passed=tests,pdf_pages=pages,
        model='Static CVRPTW, capacity, hard service-start windows, distance-only DIMACS',
        attribution='Our construction/ILS/integration/verification; external PyVRP 0.12.2 HGS',
        scopes=a['scopes'],failures=int((~df.valid).sum()),
        goal_mean_below_6=a['scopes']['catalog_356']['mean_instance_gap']<6,
        goal_1000_mean_below_6=float(sizes[sizes.n.eq(1000)].mean_instance_gap.iloc[0])<6,
        source_protocol_sha256=hashlib.sha256((BASE/'protocol.json').read_bytes()).hexdigest(),
        sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in fields})
    (ROOT/'livraison/validation_catalogue_v8.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    pointer=dict(edition='hybrid_catalog_v8',complete=True,authoritative_receipt='validation_catalogue_v8.json',
        instances=356,pipelines=472,new_pipelines=448,reused_pipelines=24,
        prior_receipts_history_only=['validation_ils_v6.json','validation_recherche_v7.json'])
    (ROOT/'livraison/VALIDATION.json').write_text(json.dumps(pointer,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in payload.items() if k!='sha256'},indent=2))


if __name__=='__main__':main()
