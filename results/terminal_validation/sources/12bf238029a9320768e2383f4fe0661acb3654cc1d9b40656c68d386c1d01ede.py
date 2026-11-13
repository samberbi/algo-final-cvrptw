"""Commandes terminal communes : sélection sûre, références explicites, sauvegardes."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS']:
    os.environ[key]='1'
os.environ['PYTHONUTF8']='1'
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import importlib.metadata
import json
import math
import multiprocessing
import platform
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import terminal_support as support


def guarded_run(entry,method,seconds,seed,guard,target):
    import psutil
    started=time.perf_counter()
    process=multiprocessing.get_context('spawn').Process(target=support.worker,args=(entry,method,seconds,seed,str(target)))
    process.start();last_cpu=None;reason=None
    try:
        child=psutil.Process(process.pid)
        while process.is_alive():
            try:
                times=child.cpu_times();last_cpu=times.user+times.system
            except psutil.Error:pass
            if time.perf_counter()-started>=guard or (last_cpu is not None and last_cpu>=guard):
                reason='Limite CPU ou temps réel du processus atteinte (initialisation comprise)'
                process.terminate();process.join(timeout=2)
                if process.is_alive():process.kill();process.join()
                break
            process.join(timeout=.025)
        process.join()
        total=time.perf_counter()-started
        if target.exists() and reason is None:
            record=json.loads(target.read_text(encoding='utf-8'))
        else:
            record=dict(instance=entry['instance'],n=entry['n'],family=entry['family'],method=method,seed=seed,
                requested_seconds=seconds,valid=False,status='time_limit' if reason else 'worker_error',
                result=dict(routes=None,status='time_limit' if reason else 'worker_error'),
                error=reason or f'Le processus a terminé sans résultat (code {process.exitcode})',
                wall_s=total,cpu_s=last_cpu,process_wall_s=total,process_cpu_s=last_cpu,
                timing_scope='whole_process_until_guard_or_crash')
        record['guard_s']=guard
        record['process_wall_s']=total
        return record
    finally:
        if process.is_alive():process.terminate();process.join()
        process.close()


def replay(label,show_routes=False,gaps_only=False):
    if not label or not all(c.isalnum() or c in '_-' for c in label):raise ValueError('Label de campagne invalide')
    folder=ROOT/'results/local'/label
    records=[]
    for path in sorted(folder.glob('*.json')):
        record=json.loads(path.read_text(encoding='utf-8'))
        if 'measurement' in record:records.append(record)
    if not records:raise ValueError('Aucune campagne enregistrée sous ce label')
    for r in records:
        if not gaps_only:support.show(r,show_routes)
    print(support.comparison([r['measurement'] for r in records]),flush=True)
    print('LECTURE SEULE : aucune résolution relancée. Dossier : '+str(folder),flush=True)
    return records


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--instances','--instance',nargs='+')
    p.add_argument('--sizes','--size',nargs='+',type=int,choices=support.SIZES)
    p.add_argument('--families','--family',nargs='+',choices=support.FAMILIES)
    p.add_argument('--progressive',action='store_true',help='Un cas C1 par taille, sauf familles explicites')
    p.add_argument('--all',action='store_true',dest='all_cases',help='Toutes les instances correspondant à la sélection explicite')
    p.add_argument('--limit',type=int)
    p.add_argument('--method',choices=support.METHODS+['duration_refined'])
    p.add_argument('--methods',nargs='+',choices=support.METHODS+['duration_refined'])
    p.add_argument('--seconds',type=float,default=5.)
    p.add_argument('--max-seconds',type=float,default=120.,help='Garde-fou CPU et réel, processus et préchauffage compris')
    p.add_argument('--seeds',nargs='+',type=int,default=[4101])
    p.add_argument('--workers',type=int,default=1)
    p.add_argument('--reference',choices=['auto','public','independent','none'],default='auto')
    p.add_argument('--label')
    p.add_argument('--dry-run','--list',action='store_true')
    p.add_argument('--show-results',nargs='?',const='from_label')
    p.add_argument('--show-routes',action='store_true')
    p.add_argument('--gaps-only',action='store_true')
    return p


def main(argv=None):
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    p=parser();args=p.parse_args(argv)
    if args.show_results:
        try:replay(args.label if args.show_results=='from_label' else args.show_results,args.show_routes,args.gaps_only)
        except ValueError as error:p.error(str(error))
        return
    if (not math.isfinite(args.seconds) or not math.isfinite(args.max_seconds)
        or not 0<args.seconds<=args.max_seconds or args.workers<1
        or (args.limit is not None and args.limit<1) or any(not 0<=s<2**31 for s in args.seeds)):
        p.error('Budgets positifs finis, budget <= garde-fou, graines sur 31 bits et workers/limit positifs requis')
    if args.method and args.methods:p.error('Choisir --method ou --methods')
    methods=list(dict.fromkeys('refined' if m=='duration_refined' else m for m in (args.methods or [args.method or 'refined'])))
    try:
        entries=support.select_cases(support.catalog(),args.instances,args.sizes,args.families,args.progressive,args.all_cases,args.limit)
    except (ValueError,FileNotFoundError) as error:p.error(str(error))
    jobs=[(entry,method,seed) for entry in entries for seed in sorted(set(args.seeds)) for method in methods]
    print(f'{len(entries)} instances ; {len(jobs)} résolutions ; {args.workers} processus maximum',flush=True)
    print('Départs zéro ; trajets fixes/symétriques ; objectif trajets + attentes + services, retour compris.',flush=True)
    if args.dry_run:
        for entry in entries:print(f"{entry['instance']}:{entry['n']} | {entry['family']} | {entry['path']}")
        print('SÉLECTION SEULE : aucun calcul.');return
    try:folder=support.unique_folder(args.label)
    except ValueError as error:p.error(str(error))
    print('Dossier : '+str(folder),flush=True)
    print('Budget : recherche + construction pour ILS/SA/hybride/PyVRP ; total souple pour renforcé.\n'
          'CPU/réel résolution excluent le préchauffage ; le garde-fou inclut tout le processus.\n'
          'Un arrêt par surveillance peut dépasser légèrement la limite lors de l’arrêt du processus.',flush=True)
    sources={}
    paths=list((ROOT/'algo').glob('*.py'))+[Path(__file__).resolve(),ROOT/'scripts/terminal_support.py',ROOT/'scripts/test_instances.py',ROOT/'scripts/benchmark_final_static.py']
    for source in paths:
        rel=source.relative_to(ROOT);target=folder/'source'/rel;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(source.read_bytes());sources[rel.as_posix()]=support.sha(source)
    protocol=dict(schema='terminal_v2',arguments=vars(args),effective_label=folder.name,entries=entries,
        methods=methods,python=sys.executable,platform=platform.platform(),sources=sources,
        packages={name:importlib.metadata.version(name) for name in ['numpy','numba','scipy','pyvrp','psutil']},
        budget='Search plus construction/setup for ILS/SA/hybrid/PyVRP; refined soft total. Guard CPU and wall includes process startup/loading/warmup.',
        reference='Read after solve; public duration or cached independent OR-Tools. No certified Phonin gap.')
    support.dump(folder/'protocol.json',protocol)
    raw=folder/'raw';raw.mkdir()
    records=[];batch=time.perf_counter()
    def one(job):
        entry,method,seed=job
        temporary=raw/f"{entry['instance']}_{entry['n']}_{method}_{seed}.json"
        result=guarded_run(entry,method,args.seconds,seed,args.max_seconds,temporary)
        try:
            reference=support.find_reference(entry,support.load_case(entry),args.reference)
        except Exception as error:
            reference=dict(duration=None,type='NON DISPONIBLE : référence rejetée',source=None,certified=False,error=repr(error))
        row=support.row_from(result,reference)
        record=dict(schema='terminal_v2',measurement=row,result=result.get('result'),reference=reference,
                    error=result.get('error'),instance_sha256=entry['sha256'])
        target=folder/temporary.name
        support.dump(target,record)
        temporary.unlink(missing_ok=True)
        return record
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending=[pool.submit(one,job) for job in jobs]
        for future in as_completed(pending):
            record=future.result();records.append(record)
            support.show(record,args.show_routes)
            support.save_tables(folder,records,time.perf_counter()-batch)
    records.sort(key=lambda r:(r['measurement']['n'],r['measurement']['instance'],r['measurement']['seed'],r['measurement']['method']))
    print(support.save_tables(folder,records,time.perf_counter()-batch),flush=True)
    print(f"\nBILAN : {sum(r['measurement']['valid'] for r in records)}/{len(records)} réalisables.\nCSV : {folder/'RESULTATS.csv'}\nLabel : {folder.name}",flush=True)
    if any(not r['measurement']['valid'] for r in records):raise SystemExit(1)


if __name__=='__main__':main()
