"""Exécute les commandes réelles et garde stdout, erreurs, codes retour et preuves."""
from pathlib import Path
from datetime import datetime
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.terminal_support import dump


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase',choices=['checks','runs','all'],default='all')
    p.add_argument('--label',default='controle_terminal_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    args=p.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]+',args.label):p.error('Label simple requis')
    folder=ROOT/'results/terminal_validation'/args.label;folder.mkdir(parents=True,exist_ok=True)
    prefix=args.label
    checks=[('aide_test',['scripts/test_instances.py','--help'],0),
        ('aide_comparaison',['scripts/run_benchmark.py','--help'],0),
        ('aide_benchmark_historique',['scripts/benchmark_final_static.py','--help'],0),
        ('aide_finalisation',['scripts/finalize_static.py','--help'],0),
        ('tests_unitaires',['-m','pytest','tests','-q','--junitxml=livraison/TESTS_SOUTENANCE.xml'],0),
        ('validateur_projet',['scripts/validate_soutenance.py'],0)]
    runs=[('instance_25',['scripts/test_instances.py','--instances','C101','--size','25','--seconds','5','--show-routes'],0),
        ('six_familles_100',['scripts/test_instances.py','--instances','C101','C201','R101','R201','RC101','RC201',
            '--seconds','5','--label',prefix+'_100'],0),
        ('progressif_25_1000',['scripts/run_benchmark.py','--progressive','--seconds','5','--label',prefix+'_progressif'],0),
        ('comparaison',['scripts/run_benchmark.py','--instance','C101','--size','25','--methods','ils','sa','pyvrp','hybrid','refined','ortools',
            '--seconds','5','--reference','independent','--label',prefix+'_comparaison'],0),
        ('famille_taille_200',['scripts/test_instances.py','--family','R1','--size','200','--seconds','5','--label',prefix+'_R1_200'],0),
        ('sans_reference',['scripts/test_instances.py','--instance','C101','--size','25','--seconds','5',
            '--reference','none','--label',prefix+'_sans_reference'],0),
        ('echec_reel_pyvrp',['scripts/test_instances.py','--instances','R2_10_8','--method','pyvrp','--seconds','.001','--label',prefix+'_echec'],1),
        ('garde_fou',['scripts/test_instances.py','--instances','C101','--method','ils','--seconds','.01',
            '--max-seconds','.05','--label',prefix+'_limite'],1),
        ('deux_processus',['scripts/test_instances.py','--instances','C101','C201','--size','25','--seconds','1',
            '--workers','2','--label',prefix+'_parallele'],0),
        ('selection_familles',['scripts/test_instances.py','--families','C1','C2','R1','R2','RC1','RC2','--size','100','--dry-run'],0),
        ('relecture',['scripts/test_instances.py','--show-results',prefix+'_comparaison','--show-routes'],0),
        ('gaps_terminal',['scripts/test_instances.py','--show-results','--label',prefix+'_100','--gaps-only'],0)]
    jobs=checks if args.phase=='checks' else runs if args.phase=='runs' else checks+runs
    records=[]
    for name,argv,expected in jobs:
        target=folder/(name+'.json')
        if target.exists():
            records.append(json.loads(target.read_text(encoding='utf-8')));print('Conservé : '+name,flush=True);continue
        env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
        command=[sys.executable,'-X','utf8']+argv
        print('EXÉCUTION : '+' '.join(argv),flush=True)
        started=time.perf_counter()
        process=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=360)
        elapsed=time.perf_counter()-started
        (folder/(name+'.txt')).write_text(process.stdout+'\n\nSTDERR\n'+process.stderr,encoding='utf-8')
        valid=process.returncode==expected
        proof=dict(name=name,command=command,expected_exit=expected,exit=process.returncode,
            wall_s=elapsed,validated=valid,log=(folder/(name+'.txt')).relative_to(ROOT).as_posix())
        effective=re.search(r'^Label : (.+)$',process.stdout,re.MULTILINE)
        if effective:
            label=effective.group(1).strip();source=ROOT/'results/local'/label
            proof['campaign']=label
            # Les résultats utiles à la validation ne restent pas dans un dossier ignoré.
            copy=folder/'campaigns'/label;copy.mkdir(parents=True,exist_ok=True)
            for path in source.glob('*'):
                if path.is_file():shutil.copy2(path,copy/path.name)
            saved=[json.loads(path.read_text(encoding='utf-8')) for path in source.glob('*.json')
                   if path.name not in ['protocol.json','BILAN.json']]
            if name=='echec_reel_pyvrp':
                valid=valid and any(r.get('measurement',{}).get('status')=='not_found' for r in saved)
            if name=='garde_fou':
                valid=valid and any(r.get('measurement',{}).get('status')=='time_limit' for r in saved)
            if name=='sans_reference':valid=valid and 'Gap certifié                 : NON DISPONIBLE' in process.stdout
        elif name in ['echec_reel_pyvrp','garde_fou']:valid=False
        if name=='relecture':valid=valid and 'LECTURE SEULE' in process.stdout
        proof['validated']=valid
        dump(target,proof);records.append(proof)
        dump(folder/'VALIDATION.json',dict(phase=args.phase,checks=records,all_validated=all(r['validated'] for r in records)))
        print(f"{'OK' if valid else 'ÉCHEC INATTENDU'} : {name} | retour {process.returncode} | {elapsed:.3f} s",flush=True)
        if not valid:print(process.stdout[-2000:]+'\n'+process.stderr[-1000:],flush=True)
    dump(folder/'VALIDATION.json',dict(phase=args.phase,checks=records,all_validated=all(r['validated'] for r in records)))
    print('Preuves sauvegardées : '+str(folder),flush=True)
    if not all(r['validated'] for r in records):raise SystemExit(1)


if __name__=='__main__':main()
