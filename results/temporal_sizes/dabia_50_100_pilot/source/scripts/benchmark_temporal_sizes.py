"""Résolutions temporelles plus grandes, données et références compatibles.

Chaque résolution isolée est arrêtée en cas de dépassement CPU. Les échecs et
écarts hors objectif sont publiés ; aucun pourcentage n'est forcé dans une plage.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):
    os.environ[key] = '1'
from pathlib import Path
import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import multiprocessing as mp
import platform
import sys
import time
import traceback
import psutil
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def write(path, obj):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(obj, indent=2), encoding='utf-8')
    temporary.replace(path)


def execute(entry, seed, seconds, method, target):
    from algo.temporal_large import load_temporal, solve as scalable
    from algo.dabia import solve as pilot, simulate
    from mamut_routing_lib.models import BenchmarkSolution
    from mamut_routing_lib.td import check_td_solution
    start, cpu = time.perf_counter(), time.process_time()
    row = dict(instance=entry['instance'], n=entry['n'], family=entry['family'], benchmark=entry['benchmark'],
               seed=seed, method=method, valid=False, requested_s=seconds)
    result = None
    try:
        for file in entry['files']:
            assert hashlib.sha256((ROOT/file['path']).read_bytes()).hexdigest() == file['sha256']
        loaded = load_temporal(ROOT/entry['path'])
        load_wall, load_cpu = time.perf_counter()-start, time.process_time()-cpu
        result = (pilot if method == 'pilot' else scalable)(loaded, seconds=seconds, seed=seed)
        if result['status'] != 'feasible':
            raise ValueError(result.get('reason',result['status']))
        physical = simulate(loaded,result['routes'],result['route_evaluations'])
        assert physical['valid'],physical['errors']
        end_wall, end_cpu = time.perf_counter()-start, time.process_time()-cpu
        # Le plan témoin n'est chargé qu'après la résolution.
        source = ROOT/entry['path']
        ref = json.loads(source.with_name(entry['instance']+'.bks.Duration.json').read_text())
        check = check_td_solution(loaded,BenchmarkSolution(instance_name=entry['instance'],routes=ref['routes'],cost=ref['cost']))
        assert check.is_valid(),check
        row.update(valid=True,duration=result['cost'],reference_duration=check.routing_cost,
            gap_duration_bks_pct=100*(result['cost']/check.routing_cost-1),vehicles=len(result['routes']),
            reference_vehicles=len(ref['routes']),initial_duration=result['initial_cost'],
            gain_construction_pct=100*(1-result['cost']/result['initial_cost']),
            total_wall_s=end_wall,total_cpu_s=end_cpu,load_wall_s=load_wall,load_cpu_s=load_cpu,
            travel=physical['travel'],waiting=physical['waiting'],service=physical['service'],
            reference_certificate_note=ref.get('metadata',{}).get('optimality',{}).get('note',''),
            full_atf_serialization_hash_checked=entry['benchmark']=='Dabia2013')
        record = dict(measurement=row,result=result,physical=physical,reference_check=check.model_dump(mode='json'))
    except Exception:
        row.update(error=traceback.format_exc(),total_wall_s=time.perf_counter()-start,total_cpu_s=time.process_time()-cpu)
        record = dict(measurement=row,result=result)
    write(Path(target),record)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes',nargs='+',type=int,default=[50,100,200])
    parser.add_argument('--families',nargs='+',default=['C1','C2','R1','R2','RC1','RC2'])
    parser.add_argument('--seconds',type=float,default=20.)
    parser.add_argument('--seeds',nargs='+',type=int,default=[4101])
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--method',choices=['pilot','scalable'],default='scalable')
    parser.add_argument('--label',required=True)
    args = parser.parse_args()
    if (not math.isfinite(args.seconds) or not 0<args.seconds<=110 or args.workers<1
            or not args.label.replace('_','').isalnum()
            or not set(args.sizes)<={50,100,200,400,600,800,1000}
            or not set(args.families)<={'C1','C2','R1','R2','RC1','RC2'}):
        parser.error('Paramètres invalides ; recherche limitée à 110 s pour garder une marge de contrôle')
    entries = []
    manifests = []
    for path in sorted((ROOT/'data/temporal_sizes').glob('*/n*/manifest.json')):
        manifest = json.loads(path.read_text())
        if manifest['n'] in args.sizes:
            manifests.append(manifest)
            entries.extend(r for r in manifest['entries'] if r['family'] in args.families)
    if set(args.sizes)-{r['n'] for r in entries}:
        parser.error('Tailles non téléchargées : exécuter download_temporal_sizes.py')
    folder = ROOT/'results/temporal_sizes'/args.label
    suffix = 1
    while True:
        try:folder.mkdir(parents=True,exist_ok=False);break
        except FileExistsError:suffix+=1;folder=folder.with_name(args.label+'_'+str(suffix))
    jobs = [(entry,seed) for entry in sorted(entries,key=lambda r:(r['n'],r['instance'])) for seed in sorted(set(args.seeds))]
    files = [ROOT/'algo/dabia.py',ROOT/'algo/temporal_large.py',Path(__file__).resolve()]
    hashes = {}
    for source in files:
        rel=source.relative_to(ROOT);destination=folder/'source'/rel
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(source.read_bytes())
        hashes[rel.as_posix()]=hashlib.sha256(source.read_bytes()).hexdigest()
    write(folder/'protocol.json',dict(arguments=vars(args),jobs=jobs,data_manifests=manifests,sources=hashes,
        python=sys.version,platform=platform.platform(),
        packages={p:importlib.metadata.version(p) for p in ['mamut-routing-lib','pydantic','psutil']},
        objective='Duration, optimized departures, canonical TD-fold/2',
        timing='Per-run process CPU; loading and final check included; reference audit excluded from reported solve time',
        guards='Parent terminates at 115 measured process CPU seconds or 150 wall seconds; polls every 0.1s',
        loader='Dabia: full verified sidecar; Lera: raw/canonical category hashes checked, native IGP arc functions on demand; full ATF serialization hash not recomputed'))
    print(f'{len(jobs)} resolutions ; dossier {folder}',flush=True)
    pending=list(jobs);active=[];rows=[];started=time.perf_counter()
    context=mp.get_context('spawn')
    while pending or active:
        while pending and len(active)<args.workers:
            entry,seed=pending.pop(0)
            target=folder/f"{entry['n']}_{entry['instance']}_{seed}.json"
            process=context.Process(target=execute,args=(entry,seed,args.seconds,args.method,str(target)))
            process.start()
            active.append(dict(process=process,entry=entry,seed=seed,target=target,start=time.perf_counter(),last_cpu=0.))
        for job in active[:]:
            process=job['process']
            if process.is_alive():
                try:
                    usage=psutil.Process(process.pid).cpu_times()
                    job['last_cpu']=usage.user+usage.system
                except psutil.Error:pass
                if job['last_cpu']<115 and time.perf_counter()-job['start']<150:
                    continue
                process.terminate();process.join()
            else:process.join()
            if job['target'].exists():
                record=json.loads(job['target'].read_text())
                row=record['measurement']
            else:
                row=dict(instance=job['entry']['instance'],n=job['entry']['n'],family=job['entry']['family'],
                    benchmark=job['entry']['benchmark'],seed=job['seed'],method=args.method,valid=False,
                    error='Worker stopped by CPU/wall guard or exited without result',
                    total_cpu_s=job['last_cpu'],total_wall_s=time.perf_counter()-job['start'])
                write(job['target'],dict(measurement=row,result=None))
            rows.append(row);active.remove(job)
            gap=f"{row['gap_duration_bks_pct']:+.4f}%" if row['valid'] else 'indisponible'
            print(f"[{len(rows)}/{len(jobs)}] n={row['n']} {row['instance']} valid={row['valid']} gap={gap} CPU={row['total_cpu_s']:.2f}s",flush=True)
            fields=sorted({key for r in rows for key in r})
            with (folder/'RESULTATS.csv').open('w',newline='',encoding='utf-8-sig') as stream:
                writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
            write(folder/'progress.json',dict(completed=len(rows),total=len(jobs),batch_wall_s=time.perf_counter()-started))
        if active:time.sleep(.1)
    valid=[r for r in rows if r['valid']]
    write(folder/'BILAN.json',dict(completed=len(rows),feasible=len(valid),failed=len(rows)-len(valid),
        mean_gap_pct=sum(r['gap_duration_bks_pct'] for r in valid)/len(valid) if valid else None,
        min_gap_pct=min((r['gap_duration_bks_pct'] for r in valid),default=None),
        max_gap_pct=max((r['gap_duration_bks_pct'] for r in valid),default=None),
        batch_wall_s=time.perf_counter()-started))


if __name__=='__main__':main()
