"""Package only this original project and its executed evidence."""
from pathlib import Path
import zipfile,hashlib,json
ROOT=Path(__file__).resolve().parents[1]


def main():
    validation=json.loads((ROOT/'livraison/VALIDATION.json').read_text());assert validation['complete']
    target=Path.home()/'Downloads/ALGO_FINAL_CVRPTW.zip';i=2
    while target.exists():target=target.with_name(f'ALGO_FINAL_CVRPTW_{i}.zip');i+=1
    files=[p for p in ROOT.rglob('*') if p.is_file() and not any(s in p.parts for s in ['__pycache__','.pytest_cache','.tools'])
        and p.suffix not in ['.pyc','.nbc','.nbi','.tmp'] and p.name!='ARCHIVE.json']
    assert not any('references' in p.relative_to(ROOT).parts for p in files)
    manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,'ALGO FINAL/'+p.relative_to(ROOT).as_posix())
        z.writestr('ALGO FINAL/MANIFESTE_SHA256.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(target) as z:assert z.testzip() is None
    receipt=dict(path=str(target),bytes=target.stat().st_size,files=len(files)+1,
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),crc_valid=True)
    (ROOT/'livraison/ARCHIVE.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
