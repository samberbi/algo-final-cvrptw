"""Export an original, professional report from the executed CVRPTW notebook.

The notebook retains executable code; the report presents narrative, actual
tables and figures. A portable, pinned Pandoc converts equations to Word OMML.
"""
from pathlib import Path
import base64,hashlib,io,json,re,subprocess,urllib.request,zipfile
import nbformat
import pandas as pd
from docx import Document
from docx.shared import Cm,Pt,RGBColor,Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'livraison'


def markdown_table(frame):
    def cell(x):
        if isinstance(x,float):
            if pd.isna(x):return '—'
            return ('0,000' if abs(x)<.0005 else f'{x:.3f}'.replace('.',','))
        s=str(x).replace('\n',' ').replace('|',' / ')
        return '—' if s=='nan' else s
    rows=['| '+' | '.join(map(cell,frame.columns))+' |',
          '| '+' | '.join(['---']*len(frame.columns))+' |']
    rows+=['| '+' | '.join(map(cell,row))+' |' for row in frame.itertuples(index=False,name=None)]
    return '\n'.join(rows)


def pandoc():
    shared=ROOT.parent/'.tools/pandoc-3.6.4/pandoc.exe'
    if shared.exists():return shared
    directory=ROOT/'.tools/pandoc-3.6.4'
    exe=directory/'pandoc.exe'
    if exe.exists():return exe
    directory.mkdir(parents=True,exist_ok=True)
    url='https://github.com/jgm/pandoc/releases/download/3.6.4/pandoc-3.6.4-windows-x86_64.zip'
    package=directory/'distribution.zip'
    urllib.request.urlretrieve(url,package)
    with zipfile.ZipFile(package) as archive:
        name=next(n for n in archive.namelist() if n.endswith('/pandoc.exe'))
        exe.write_bytes(archive.read(name))
    (directory/'origin.json').write_text(json.dumps(dict(url=url,
        archive_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),
        exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest()),indent=2))
    return exe


def reference_document():
    # documents skill: compact_reference_guide + editorial_cover, shared Letter geometry.
    doc=Document();section=doc.sections[0]
    section.page_width=Inches(8.5);section.page_height=Inches(11)
    section.top_margin=Inches(1);section.bottom_margin=Inches(1)
    section.left_margin=Inches(1);section.right_margin=Inches(1)
    section.header_distance=Inches(.492);section.footer_distance=Inches(.492)
    style=doc.styles['Normal'];style.font.name='Calibri';style.font.size=Pt(11)
    style.paragraph_format.line_spacing=1.25;style.paragraph_format.space_after=Pt(6)
    style.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
    style.element.get_or_add_rPr().append(OxmlElement('w:lang'))
    style.element.rPr.find(qn('w:lang')).set(qn('w:val'),'fr-FR')
    for name,size in [('Title',26),('Heading 1',16),('Heading 2',13),('Heading 3',12)]:
        s=doc.styles[name];s.font.name='Calibri';s.font.size=Pt(size)
        s.font.color.rgb=RGBColor.from_string('1F4D78' if name=='Heading 3' else '2E74B5')
        s.paragraph_format.keep_with_next=True
    for name,before,after in [('Heading 1',18,10),('Heading 2',14,7),('Heading 3',10,5)]:
        doc.styles[name].paragraph_format.space_before=Pt(before)
        doc.styles[name].paragraph_format.space_after=Pt(after)
    for name in ['List Bullet','List Number']:
        doc.styles[name].paragraph_format.left_indent=Inches(.375)
        doc.styles[name].paragraph_format.first_line_indent=Inches(-.188)
        doc.styles[name].paragraph_format.space_after=Pt(4)
        doc.styles[name].paragraph_format.line_spacing=1.25
    header=section.header.paragraphs[0]
    header.text='CESI  |  CVRPTW  |  Livrable final'
    header.style=doc.styles['Caption']
    footer=section.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run('Page ')
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    prop=OxmlElement('w:updateFields');prop.set(qn('w:val'),'true');doc.settings.element.append(prop)
    path=OUT/'reference_style.docx';doc.save(path)
    return path


def main():
    OUT.mkdir(exist_ok=True);figdir=OUT/'figures';figdir.mkdir(exist_ok=True)
    nb=nbformat.read(ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb',as_version=4)
    assert all(c.execution_count is not None for c in nb.cells if c.cell_type=='code')
    assert not any(o.output_type=='error' for c in nb.cells if c.cell_type=='code' for o in c.outputs)
    parts=[];images=0
    for c in nb.cells:
        if c.cell_type=='markdown':parts.append(c.source);continue
        if 'inspect.getsource' in c.source and not c.metadata.get('include_code_in_report',False):
            parts.append('Le code détaillé de cette fonction est fourni dans le Notebook exécutable.');continue
        cell_image_index=0
        for o in c.outputs:
            data=o.get('data',{})
            if 'image/png' in data:
                images+=1;name=f'figure_{images:02d}.png'
                (figdir/name).write_bytes(base64.b64decode(data['image/png']))
                cell_captions=c.metadata.get('figure_captions',[])
                caption=cell_captions[cell_image_index] if cell_image_index<len(cell_captions) else 'Résultat expérimental documenté.'
                cell_image_index+=1
                parts.append(f'![Figure {images} — {caption}](figures/{name})')
            elif 'text/html' in data and '<table' in data['text/html']:
                for frame in pd.read_html(io.StringIO(data['text/html'])):
                    if isinstance(frame.columns,pd.MultiIndex):
                        frame.columns=[' / '.join(map(str,x)) for x in frame.columns]
                    frame=frame.loc[:,[not str(col).startswith('Unnamed:') for col in frame.columns]]
                    parts.append(markdown_table(frame))
            elif 'text/markdown' in data:parts.append(data['text/markdown'])
            elif 'text/plain' in data:
                plain=data['text/plain']
                plain=re.sub(r'\n(?:Name:.*?, )?dtype: [^\n]+$', '',plain)
                if not plain.startswith('<IPython.'):
                    parts.append('```text\n'+plain+'\n```')
            elif o.output_type=='stream' and o.get('name')=='stdout' and o.get('text','').strip():
                parts.append('```text\n'+o.text.strip()+'\n```')
    text='\n\n'.join(parts)
    text=re.sub(r'## Sommaire\n.*?(?=## Introduction)', '',text,flags=re.S)
    # A report has its own automatic contents; the title is provided as metadata.
    text=re.sub(r'^# Livrable final[^\n]*\n','',text)
    text='---\ntitle: "Optimisation de tournées de livraison CVRPTW"\nsubtitle: "ILS et recuit simulé — Modèle et étude expérimentale"\ntoc-title: "Sommaire"\nlang: fr-FR\n---\n\n'+text
    assert '<!-- EXEC:' not in text,'Unresolved executable section'
    md=OUT/'RAPPORT_CVRPTW.md';md.write_text(text,encoding='utf-8')
    exe=pandoc();ref=reference_document();target=OUT/'RAPPORT_CVRPTW.docx'
    command=[str(exe),str(md),'--from=markdown+tex_math_dollars+pipe_tables','--standalone',
        '--toc','--toc-depth=2','--reference-doc='+str(ref),'--resource-path='+str(OUT),'-o',str(target)]
    completed=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
    (OUT/'conversion_pandoc.log').write_text(completed.stdout+completed.stderr,encoding='utf-8')
    completed.check_returncode()
    doc=Document(target)
    for paragraph in doc.paragraphs:
        if paragraph.text.startswith('1. Contexte, objectif'):
            paragraph.paragraph_format.page_break_before=True
        if paragraph._p.xpath('.//w:drawing') or paragraph.text.startswith('Figure '):
            paragraph.paragraph_format.keep_with_next=True
        if paragraph.text.startswith(('Lecture ','Interprétation à')):
            paragraph.paragraph_format.keep_together=True
        if paragraph.text.startswith('Le run illustré'):paragraph.paragraph_format.keep_with_next=True
        if re.match(r'^C[1-8] —',paragraph.text):paragraph.paragraph_format.keep_with_next=True
    if 'Source Code' in doc.styles:
        doc.styles['Source Code'].font.size=Pt(8)
        doc.styles['Source Code'].paragraph_format.line_spacing=1.05
    for table in doc.tables:
        table.autofit=False
        cols=len(table.columns);widths=[9360//cols]*cols;widths[-1]+=9360-sum(widths)
        prop=table._tbl.tblPr
        for tag,attrs in [('tblW',{'w':'9360','type':'dxa'}),('tblInd',{'w':'120','type':'dxa'})]:
            element=prop.find(qn('w:'+tag))
            if element is None:element=OxmlElement('w:'+tag);prop.append(element)
            for key,value in attrs.items():element.set(qn('w:'+key),value)
        margins=prop.find(qn('w:tblCellMar'))
        if margins is None:margins=OxmlElement('w:tblCellMar');prop.append(margins)
        for edge,width in [('top',80),('bottom',80),('start',120),('end',120)]:
            element=OxmlElement('w:'+edge);element.set(qn('w:w'),str(width));element.set(qn('w:type'),'dxa');margins.append(element)
        for column,width in zip(table._tbl.tblGrid.gridCol_lst,widths):column.set(qn('w:w'),str(width))
        for row_index,row in enumerate(table.rows):
            row_property=row._tr.get_or_add_trPr()
            no_split=OxmlElement('w:cantSplit');row_property.append(no_split)
            for i,cell in enumerate(row.cells):
                cell.width=Inches(widths[min(i,cols-1)]/1440)
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.space_after=Pt(3)
                    paragraph.paragraph_format.line_spacing=1.05
                    for run in paragraph.runs:run.font.size=Pt(8.5)
                    if len(table.rows)<=15 and row_index<len(table.rows)-1:
                        paragraph.paragraph_format.keep_with_next=True
        if table.rows:
            prop=table.rows[0]._tr.get_or_add_trPr();repeat=OxmlElement('w:tblHeader');prop.append(repeat)
            for cell in table.rows[0].cells:
                shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E8EEF5');cell._tc.get_or_add_tcPr().append(shade)
                for p in cell.paragraphs:
                    for run in p.runs:run.bold=True
    # Fit native diagrams to the writable page area.
    for index,shape in enumerate(doc.inline_shapes):
        ratio=shape.height/shape.width
        if shape.width>Inches(6.5):shape.width=Inches(6.5);shape.height=int(shape.width*ratio)
        if images==20 and index==18:
            shape.width=Inches(5.4);shape.height=int(shape.width*ratio)
    doc.save(target)
    with zipfile.ZipFile(target) as archive:
        document=archive.read('word/document.xml').decode()
    assert '<m:oMath' in document,'equations must remain editable Word equations'
    payload=dict(images=images,paragraphs=len(doc.paragraphs),tables=len(doc.tables),
        word_equations=document.count('<m:oMath>'),all_sections_resolved=True,
        notebook_sha256=hashlib.sha256((ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb').read_bytes()).hexdigest(),
        docx_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        design_preset='compact_reference_guide',header_pattern='editorial_cover',page_geometry='Letter, 1-inch margins',
        named_overrides={'tables':'8.5 pt, 1.05 line spacing, 3 pt paragraph after for experimental data',
                         'route_illustration':'5.4-inch width to retain illustration and explanation on the same page'})
    (OUT/'validation_rapport.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print(json.dumps(payload,indent=2))


if __name__=='__main__':main()
