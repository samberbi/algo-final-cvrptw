"""Package the current audited delivery and evidence, preserving prior ZIPs."""
from pathlib import Path
from datetime import datetime
import hashlib,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.package_ils_v5 import semantic_text,EXCLUDED_WORD


def main():
    receipt=json.loads((ROOT/'livraison/validation_catalogue_v8.json').read_text(encoding='utf-8'))
    assert receipt['complete']
    base=Path.home()/'Downloads/ALGO_FINAL_CVRPTW_ILS_V6_20261111.zip'
    target=Path.home()/'Downloads'/('ALGO_FINAL_CVRPTW_HYBRIDE_V8_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'.zip')
    with zipfile.ZipFile(base) as archive:
        names=[name.removeprefix('ALGO FINAL/') for name in archive.namelist()
               if name.startswith('ALGO FINAL/') and not name.endswith('MANIFESTE_SHA256.json')]
    files={ROOT/name for name in names}
    files.add(ROOT/'requirements-reference-v7.txt')
    files.add(ROOT/'requirements-documents-v8.txt')
    files.add(ROOT/'docs/LIVRABLE_OPTIMISE_SOURCE.md')
    files.add(ROOT/'docs/JOURNAL_EVOLUTION_ALGORITHME.md')
    files.add(ROOT/'scripts/editorial_math_review_v8.py')
    files.update((ROOT/'algo').glob('*.py'))
    for name in ['benchmark_v7','benchmark_continuation_v7','analyze_v7','build_v7_study',
        'run_external_reference','run_hybrid_reference','validate_v7_study','create_penalty_descent_v7',
        'benchmark_catalog_v8','analyze_catalog_v8','build_delivery_v8','build_results_table_v8','write_delivery_notes_v8',
        'validate_delivery_v8','package_delivery_v8','render_ils_word']:
        files.add(ROOT/'scripts'/(name+'.py'))
    for name in ['test_guidance_v7','test_catalog_statistics']:
        files.add(ROOT/'tests'/(name+'.py'))
    for name in ['UTILISER_ILS_HGS','RECHERCHE_GRANDES_INSTANCES_V7','MODIFICATIONS_LIVRABLE_V8']:
        files.add(ROOT/'docs'/(name+'.md'))
    for suffix in ['.ipynb','.html']:
        files.add(ROOT/'notebooks'/('Recherche_1000_clients_V7'+suffix))
    for name in ['RESULTATS_ILS_V7.csv','RESULTATS_ILS_V7.html','validation_recherche_v7.json',
        'RESULTATS_CATALOGUE_V8.csv','INSTANCES_CATALOGUE_V8.csv','RESULTATS_CATALOGUE_V8.html',
        'validation_catalogue_v8.json','validation_rapport.json']:
        files.add(ROOT/'livraison'/name)
    for folder in ['livraison/ils_v7_figures','livraison/catalog_v8_figures',
                   'results/optimization_v7','results/catalog_v8']:
        for path in (ROOT/folder).rglob('*'):
            if path.is_file() and not any(p in ['manual','foundation','__pycache__'] for p in path.relative_to(ROOT/folder).parts) and path.suffix in ['.py','.json','.csv','.txt','.xml','.png']:
                files.add(path)
    count=json.loads((ROOT/'livraison/validation_rapport.json').read_text())['images']
    for i in range(1,count+1):files.add(ROOT/'livraison/figures'/f'figure_{i:02d}.png')
    files.update(ROOT/name for name in receipt['sha256'])
    manifest={}
    for path in sorted(files):
        assert path.is_file(),path
        assert EXCLUDED_WORD not in path.relative_to(ROOT).as_posix().lower(),path
        assert EXCLUDED_WORD not in semantic_text(path).lower(),path
        manifest[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(files):archive.write(path,'ALGO FINAL/'+path.relative_to(ROOT).as_posix())
        archive.writestr('ALGO FINAL/MANIFESTE_SHA256.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(target) as archive:assert archive.testzip() is None
    payload=dict(path=str(target),files=len(files)+1,bytes=target.stat().st_size,
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),crc_valid=True,semantic_scan_passed=True)
    (ROOT/'livraison/ARCHIVE_CATALOGUE_V8.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print(json.dumps(payload,indent=2))


if __name__=='__main__':main()
