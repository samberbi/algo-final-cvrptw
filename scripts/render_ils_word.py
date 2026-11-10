"""Export our generated DOCX through installed Word and render every PDF page."""
from pathlib import Path
import json,hashlib
import win32com.client
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'livraison'
app=win32com.client.DispatchEx('Word.Application')
app.Visible=False;app.DisplayAlerts=0
try:
    doc=app.Documents.Open(str(OUT/'RAPPORT_CVRPTW.docx'),ReadOnly=False)
    try:
        doc.Fields.Update()
        for toc in doc.TablesOfContents:toc.Update()
        doc.Save()
        doc.ExportAsFixedFormat(str(OUT/'RAPPORT_CVRPTW.pdf'),17)
    finally:doc.Close(False)
finally:app.Quit()
pdf=fitz.open(OUT/'RAPPORT_CVRPTW.pdf');pages=OUT/'visual_qa';pages.mkdir(exist_ok=True)
texts=[]
for i,page in enumerate(pdf):
    page.get_pixmap(matrix=fitz.Matrix(1.35,1.35)).save(pages/f'page-{i+1:02d}.png')
    texts.append({'page':i+1,'characters':len(page.get_text()),'images':len(page.get_images())})
(pages/'pages.json').write_text(json.dumps({'renderer':'Microsoft Word PDF export + PyMuPDF PNG, LibreOffice unavailable','pages':texts},indent=2))
print('PDF exported and rendered:',len(pdf),'pages')
validation=json.loads((OUT/'validation_rapport.json').read_text(encoding='utf-8'))
validation.update(docx_sha256=hashlib.sha256((OUT/'RAPPORT_CVRPTW.docx').read_bytes()).hexdigest(),
                  pdf_sha256=hashlib.sha256((OUT/'RAPPORT_CVRPTW.pdf').read_bytes()).hexdigest(),
                  pdf_pages=len(pdf),renderer='Microsoft Word, then PyMuPDF; canonical LibreOffice renderer unavailable')
(OUT/'validation_rapport.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
