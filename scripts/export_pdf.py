"""Local PDF export with embedded figures; no cloud document upload."""
from pathlib import Path
import argparse,subprocess,json,hashlib
ROOT=Path(__file__).resolve().parents[1]


def main(stem):
    out=ROOT/'livraison'
    pandoc=ROOT.parent/'.tools/pandoc-3.6.4/pandoc.exe'
    if not pandoc.exists():pandoc=ROOT/'.tools/pandoc-3.6.4/pandoc.exe'
    html=out/(stem+'.html');pdf=out/(stem+'.pdf')
    subprocess.run([str(pandoc),str(out/(stem+'.md')),'--standalone','--toc','--toc-depth=2',
        '--mathml','--embed-resources','--resource-path='+str(out),
        '--css='+str(ROOT/'scripts/submission_print.css'),'-o',str(html)],check=True,cwd=ROOT)
    browser=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    if not browser.exists():browser=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
    profile=ROOT/'.tools/pdf-profile'
    subprocess.run([str(browser),'--headless','--disable-gpu','--no-first-run','--disable-extensions',
        '--no-default-browser-check','--no-pdf-header-footer','--user-data-dir='+str(profile),
        '--print-to-pdf='+str(pdf),html.as_uri()],check=True,timeout=100,capture_output=True)
    import pymupdf
    doc=pymupdf.open(pdf)
    assert not any(w[0]<-1 or w[2]>p.rect.width+1 for p in doc for w in p.get_text('words'))
    receipt=dict(pages=len(doc),sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),text_within_bounds=True)
    (out/(stem+'_validation.json')).write_text(json.dumps(receipt,indent=2))
    print(receipt)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stem',default='RAPPORT_CVRPTW');main(p.parse_args().stem)
