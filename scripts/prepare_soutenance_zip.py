"""Archive portable complète : sources, données et résultats, sans environnements."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import hashlib
import json
import os
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED_DIRS={'.git','.tools','.vscode','.idea','.pytest_cache','__pycache__',
    '.ipynb_checkpoints','node_modules','venv','htmlcov','.cache'}
EXCLUDED_SUFFIXES={'.pyc','.pyo','.nbc','.nbi','.tmp','.pem','.key'}


def selected_files():
    paths=[]
    for directory,dirs,files in os.walk(ROOT,followlinks=False):
        dirs[:]=sorted(d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith('.venv')
                       and not (Path(directory)/d).is_symlink())
        for name in sorted(files):
            path=Path(directory)/name
            if path.is_symlink() or path.suffix.lower() in EXCLUDED_SUFFIXES:continue
            if name.startswith('.env') and name!='.env.example':continue
            if name in {'Thumbs.db','.DS_Store','.coverage'}:continue
            paths.append(path)
    return paths


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    destination=args.output or Path.home()/'Downloads'/('CVRPTW_SOUTENANCE_FINAL_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.zip')
    destination=destination.resolve()
    if destination.is_relative_to(ROOT):raise ValueError('Créer le ZIP en dehors du projet pour éviter de l’archiver lui-même')
    destination.parent.mkdir(parents=True,exist_ok=True)
    paths=selected_files()
    relative={path.relative_to(ROOT).as_posix() for path in paths}
    tracked={s for s in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf-8').split('\0') if s}
    missing=tracked-relative
    if missing:raise AssertionError('Fichiers versionnés exclus de manière inattendue : '+str(sorted(missing)))
    required={'notebooks/Livrable_Final_CVRPTW.ipynb','notebooks/Livrable_Final_CVRPTW.html',
        'test a executer dans la soutenance/README.md','test a executer dans la soutenance/INSTALLER.ps1',
        'test a executer dans la soutenance/LANCER_TESTS.ps1','scripts/test_instances.py','requirements-reference-final.txt'}
    assert required<=relative
    entries=[];prefix='CVRPTW_SOUTENANCE_FINAL/'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9,allowZip64=True) as archive:
        for path in paths:
            rel=path.relative_to(ROOT).as_posix()
            with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            entries.append(dict(path=rel,bytes=path.stat().st_size,sha256=digest))
            archive.write(path,prefix+rel)
        manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),branch=branch,commit=commit,
            working_tree_dirty=dirty,files=len(entries),uncompressed_bytes=sum(r['bytes'] for r in entries),
            includes='All tracked files and available local results; complete instances and tests',
            excludes='Python environments, Git internals, IDE/cache files, compiled files and private credentials',
            start_here='test a executer dans la soutenance/README.md',entries=entries)
        archive.writestr(prefix+'CONTENU_ARCHIVE.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    # Vérifier les octets archivés, pas seulement l'existence du ZIP.
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for entry in entries:
            with archive.open(prefix+entry['path']) as stream:
                assert hashlib.file_digest(stream,'sha256').hexdigest()==entry['sha256'],entry['path']
        assert len(archive.namelist())==len(entries)+1
    with destination.open('rb') as stream:zip_hash=hashlib.file_digest(stream,'sha256').hexdigest()
    receipt=dict(path=str(destination),commit=commit,branch=branch,files=len(entries),
        tracked_files_included=len(tracked),zip_bytes=destination.stat().st_size,
        uncompressed_bytes=manifest['uncompressed_bytes'],sha256=zip_hash,crc_and_all_file_hashes_verified=True)
    local=ROOT/'.tools/ARCHIVE_SOUTENANCE.json';local.parent.mkdir(exist_ok=True)
    local.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
