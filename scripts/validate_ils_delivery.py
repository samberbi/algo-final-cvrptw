"""Structural checks for the final, executed notebook and exported documents."""
from pathlib import Path
import hashlib,json,re,zipfile
import nbformat
import pymupdf
from docx import Document
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'livraison'
nb=nbformat.read(ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb',as_version=4)
code=[c for c in nb.cells if c.cell_type=='code']
assert all(c.execution_count is not None for c in code)
assert not any(o.output_type=='error' for c in code for o in c.outputs)
assert sum('image/png' in o.get('data',{}) for c in code for o in c.outputs)==20
for name in ['LIVRABLE_FINAL.md','livraison/RAPPORT_CVRPTW.md']:
    text=(ROOT/name).read_text(encoding='utf-8')
    assert not re.search(r'\{\{[A-Z_]+\}\}|<!-- EXEC:',text)
pdf=pymupdf.open(OUT/'RAPPORT_CVRPTW.pdf')
overflow=[]
for i,page in enumerate(pdf):
    assert len(page.get_text().strip())>80
    for b in page.get_text('dict')['blocks']:
        for line in b.get('lines',[]):
            for span in line['spans']:
                x0,y0,x1,y1=span['bbox']
                if x0<0 or y0<0 or x1>page.rect.width+.1 or y1>page.rect.height+.1:overflow.append((i+1,span['text']))
assert not overflow,overflow
doc=Document(OUT/'RAPPORT_CVRPTW.docx')
assert len(doc.inline_shapes)==20 and len(doc.tables)==13
with zipfile.ZipFile(OUT/'RAPPORT_CVRPTW.docx') as archive:xml=archive.read('word/document.xml').decode('utf-8')
assert xml.count('<m:oMath>')>=100
files=['LIVRABLE_FINAL.md','notebooks/Livrable_Final_CVRPTW.ipynb','livraison/RAPPORT_CVRPTW.docx',
       'livraison/RAPPORT_CVRPTW.pdf','livraison/RAPPORT_CVRPTW.html','docs/GUIDE_ORAL.md']
payload=dict(code_cells_executed=len(code),figures=20,tables=13,editable_equations=xml.count('<m:oMath>'),
             pdf_pages=len(pdf),text_outside_pages=overflow,unresolved_sections=False,
             sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files})
(OUT/'validation_livraison_ils.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
(OUT/'RAPPORT_CVRPTW_validation.json').write_text(json.dumps(dict(pages=len(pdf),
    sha256=payload['sha256']['livraison/RAPPORT_CVRPTW.pdf'],text_within_bounds=not overflow),indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in payload.items() if k!='sha256'},indent=2))
