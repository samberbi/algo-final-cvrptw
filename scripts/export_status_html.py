"""Synchronise le HTML de lecture avec le notebook exécuté, sans Word/PDF."""
from pathlib import Path
import hashlib
import json
import nbformat
from nbconvert import HTMLExporter
ROOT=Path(__file__).resolve().parents[1]


def main():
    source=ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb'
    nb=nbformat.read(source,4)
    assert nb.metadata.get('comparison_status_presentation')==1
    assert all(c.execution_count is not None for c in nb.cells if c.cell_type=='code')
    exporter=HTMLExporter()
    if exporter.has_trait('embed_images'):exporter.embed_images=True
    body,_=exporter.from_notebook_node(nb,resources={'metadata':{'path':str(source.parent)}})
    target=source.with_suffix('.html');target.write_text(body,encoding='utf-8')
    receipt=dict(html=str(target.relative_to(ROOT)),bytes=target.stat().st_size,
        notebook_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        html_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    (ROOT/'results/presentation_status/HTML.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
