"""Current delivery audit: keep fixed-budget results and recovery costs distinct."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import nbformat
import pymupdf
from scripts.analyze_worst_v9 import analyze,recovery,archive,restarts,BASE
from scripts.analyze_catalog_v8 import analyze as original_catalog
from scripts.package_ils_v5 import semantic_text,EXCLUDED_WORD


def main():
    original,_,_,original_info=original_catalog()
    dev,_,_=analyze('development');confirm,summary,comp=analyze('confirmation')
    recovered=recovery();d,_,info=archive();long=restarts()
    assert len(dev)==12 and len(confirm)==28 and len(recovered)==10 and len(long)==6
    assert len(d)==472 and d.valid.all() and len(original)==472
    unchanged=d[d.recovery_source.eq('')].set_index(['instance','seed'])
    before=original.set_index(['instance','seed'])
    assert len(unchanged)==462
    assert all(abs(row.gap_pct-before.loc[key,'gap_pct'])<1e-7 for key,row in unchanged.iterrows())
    tests=ET.parse(BASE/'tests.xml').getroot()
    assert not list(tests.iter('failure')) and not list(tests.iter('error'))
    count=len(list(tests.iter('testcase')))-len(list(tests.iter('skipped')))
    assert count>=151
    for stem in ['Livrable_Final_CVRPTW','Reduction_Pires_Gaps_V9']:
        nb=nbformat.read(ROOT/'notebooks'/(stem+'.ipynb'),4)
        code=[c for c in nb.cells if c.cell_type=='code']
        assert code and all(c.execution_count is not None for c in code)
        assert not any(o.output_type=='error' for c in code for o in c.outputs)
    report=(ROOT/'livraison/RAPPORT_CVRPTW.md').read_text(encoding='utf-8')
    assert 'budgets différents' in report and '180 s' in report and '14' in report
    assert 'PyVRP' in report and '40 voisins' in report
    fields=['README.md','LIVRABLE_FINAL.md','docs/LIVRABLE_OPTIMISE_SOURCE.md',
        'docs/REDUCTION_PIRES_GAPS_V9.md','docs/JOURNAL_EVOLUTION_ALGORITHME.md',
        'notebooks/Livrable_Final_CVRPTW.ipynb','notebooks/Livrable_Final_CVRPTW.html',
        'notebooks/Reduction_Pires_Gaps_V9.ipynb','notebooks/Reduction_Pires_Gaps_V9.html',
        'livraison/RAPPORT_CVRPTW.pdf','livraison/RAPPORT_CVRPTW.docx','livraison/RAPPORT_CVRPTW.html',
        'livraison/ARCHIVE_APRES_REPRISES_V9.csv','livraison/ARCHIVE_APRES_REPRISES_V9.html',
        'results/worst_v9/updated_archive/analysis.json','results/worst_v9/tests.xml',
        'docs/REVUE_FINALE_CONFORMITE.md','scripts/hgs_method_notes.py',
        'scripts/review_final_delivery.py']
    for name in fields:
        assert EXCLUDED_WORD not in semantic_text(ROOT/name).lower(),name
    with pymupdf.open(ROOT/'livraison/RAPPORT_CVRPTW.pdf') as pdf:
        pages=len(pdf)
        assert all(p.get_text().strip() for p in pdf)
        assert not any(w[0]<-1 or w[2]>p.rect.width+1 for p in pdf for w in p.get_text('words'))
    payload=dict(edition='worst_v9',complete=True,tests_passed=count,pdf_pages=pages,
        development_runs=12,confirmation_runs=28,confirmed_candidate_under7=int(summary.set_index('variant').loc['split20','under7']),
        confirmed_candidate_worst=float(summary.set_index('variant').loc['split20','worst_gap']),
        recovery_runs=10,comparison_strategies=6,comparison_subpipelines=12,
        archive=info,original_catalog_max=original_info['scopes']['catalog_356']['worst_run_gap'],
        paired_comparisons=comp,attribution='Own ILS/integration; external PyVRP 0.12.2 HGS',
        sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in fields})
    (ROOT/'livraison/validation_worst_v9.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    pointer=dict(edition='worst_v9',complete=True,authoritative_receipt='validation_worst_v9.json',
        reference_campaign='catalog_v8',reference_receipt_history_only='validation_catalogue_v8.json',
        archive_scope='472 historical pipelines with ten additional 180s continuations; mixed budgets',
        archive_worst=info['maximum'])
    (ROOT/'livraison/VALIDATION.json').write_text(json.dumps(pointer,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in payload.items() if k!='sha256'},indent=2))


if __name__=='__main__':main()
