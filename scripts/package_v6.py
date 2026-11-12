"""Update the verified assessed ZIP with the current v6 source and evidence."""
from pathlib import Path
import hashlib,json,zipfile,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.package_ils_v5 import semantic_text,EXCLUDED_WORD


def main():
    receipt=json.loads((ROOT/'livraison/validation_ils_v6.json').read_text())
    assert receipt['complete']
    base=Path.home()/'Downloads/ALGO_FINAL_CVRPTW_ILS_20261111.zip'
    target=Path.home()/'Downloads/ALGO_FINAL_CVRPTW_ILS_V6_20261111.zip'
    if target.exists():raise FileExistsError('Existing export preserved')
    with zipfile.ZipFile(base) as z:
        names=[n.removeprefix('ALGO FINAL/') for n in z.namelist() if n.startswith('ALGO FINAL/') and not n.endswith('MANIFESTE_SHA256.json')]
    files={ROOT/n for n in names}
    for name in ['cached_local','cached_iterated','experimental_v6','temporal_groups','portfolio_v6']:
        files.add(ROOT/'algo'/(name+'.py'))
    for name in ['benchmark_v6','analyze_v6','build_v6_delivery','profile_cached_v6','create_cached_variant_v6',
                 'benchmark_cache_followup','recombine_cold_v6','run_portfolio_v6','validate_v6','package_v6']:
        files.add(ROOT/'scripts'/(name+'.py'))
    files.add(ROOT/'tests/test_cached_v6.py')
    files.add(ROOT/'docs/AMELIORATIONS_ILS_V6.md')
    files.add(ROOT/'livraison/validation_ils_v6.json')
    files.add(ROOT/'livraison/RESULTATS_ILS_V6.csv');files.add(ROOT/'livraison/RESULTATS_ILS_V6.html')
    for suffix in ['.ipynb','.html']:files.add(ROOT/'notebooks'/('Ameliorations_ILS_V6'+suffix))
    for folder in [ROOT/'livraison/ils_v6_figures',ROOT/'results/optimization_v6']:
        files.update(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.nbc','.nbi'})
    count=json.loads((ROOT/'livraison/validation_rapport.json').read_text())['images']
    for i in range(1,count+1):files.add(ROOT/'livraison/figures'/f'figure_{i:02d}.png')
    manifest={}
    for p in sorted(files):
        assert p.is_file(),p
        assert EXCLUDED_WORD not in p.relative_to(ROOT).as_posix().lower(),p
        assert EXCLUDED_WORD not in semantic_text(p).lower(),p
        manifest[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(files):z.write(p,'ALGO FINAL/'+p.relative_to(ROOT).as_posix())
        z.writestr('ALGO FINAL/MANIFESTE_SHA256.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(target) as z:assert z.testzip() is None
    result=dict(path=str(target),files=len(files)+1,bytes=target.stat().st_size,
                sha256=hashlib.sha256(target.read_bytes()).hexdigest(),crc_valid=True,semantic_scan_passed=True)
    (ROOT/'livraison/ARCHIVE_ILS_V6.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
