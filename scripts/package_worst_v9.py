"""Export the validated v9 delivery, preserving the complete v8 reference ZIP."""
from pathlib import Path
from datetime import datetime
import hashlib,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.package_ils_v5 import semantic_text,EXCLUDED_WORD


if __name__=='__main__':
    receipt=json.loads((ROOT/'livraison/validation_worst_v9.json').read_text())
    assert receipt['complete']
    previous=json.loads((ROOT/'livraison/ARCHIVE_CATALOGUE_V8.json').read_text())
    with zipfile.ZipFile(previous['path']) as z:
        names=[x.removeprefix('ALGO FINAL/') for x in z.namelist() if x.startswith('ALGO FINAL/') and not x.endswith('MANIFESTE_SHA256.json')]
    files={ROOT/n for n in names};files.update(ROOT/n for n in receipt['sha256'])
    for folder in ['algo','web','tests']:
        files.update((ROOT/folder).glob('*.py'))
    for name in ['benchmark_worst_v9','refine_worst_v9','benchmark_restarts_v9','analyze_worst_v9',
                 'build_worst_v9_delivery','validate_worst_v9','package_worst_v9','resume_solution_v9']:
        files.add(ROOT/'scripts'/(name+'.py'))
    files.add(ROOT/'livraison/validation_worst_v9.json')
    for folder in ['results/worst_v9','livraison/worst_v9_figures']:
        files.update(p for p in (ROOT/folder).rglob('*') if p.is_file() and
            not any(c in ['__pycache__','manual'] for c in p.parts) and p.suffix in ['.py','.json','.csv','.xml','.png','.txt'])
    count=json.loads((ROOT/'livraison/validation_rapport.json').read_text())['images']
    files.update(ROOT/'livraison/figures'/f'figure_{i:02d}.png' for i in range(1,count+1))
    manifest={}
    for p in sorted(files):
        assert p.is_file(),p
        assert EXCLUDED_WORD not in p.relative_to(ROOT).as_posix().lower(),p
        assert EXCLUDED_WORD not in semantic_text(p).lower(),p
        manifest[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    target=Path.home()/'Downloads'/('ALGO_FINAL_CVRPTW_PIRES_GAPS_V9_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'.zip')
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(files):z.write(p,'ALGO FINAL/'+p.relative_to(ROOT).as_posix())
        z.writestr('ALGO FINAL/MANIFESTE_SHA256.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(target) as z:assert z.testzip() is None
    output=dict(path=str(target),files=len(files)+1,bytes=target.stat().st_size,
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),crc_valid=True,semantic_scan_passed=True)
    (ROOT/'livraison/ARCHIVE_WORST_V9.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps(output,indent=2))
