"""Pilote temporel compatible, sans écraser les campagnes statiques.

Chaque BKS est lue APRÈS la résolution. L'écart est signé, jamais plafonné.
"""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS'):
    os.environ[key] = '1'
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import platform
import sys
import time
import traceback
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def execute(job):
    from algo.dabia import solve, simulate
    from mamut_routing_lib.td import load_td_instance, check_td_solution
    from mamut_routing_lib.models import BenchmarkSolution
    name, seed, seconds = job
    started, cpu = time.perf_counter(), time.process_time()
    row = dict(instance=name, seed=seed, n=25, valid=False, requested_s=seconds)
    result = None
    try:
        folder = ROOT/'data/dabia2013/n25'
        loaded = load_td_instance(folder/(name+'.vrp.json'))
        result = solve(loaded, seconds=seconds, seed=seed)
        assert result['status'] == 'feasible'
        physical = simulate(loaded, result['routes'], result['route_evaluations'])
        assert physical['valid'], physical['errors']
        solve_wall, solve_cpu = time.perf_counter()-started, time.process_time()-cpu
        # Aucun coût ou plan de référence n'a été transmis au solveur.
        ref = json.loads((folder/(name+'.bks.Duration.json')).read_text())
        checked = check_td_solution(loaded, BenchmarkSolution(instance_name=name, routes=ref['routes'], cost=ref['cost']))
        assert checked.is_valid(), checked
        info = ref.get('metadata', {}).get('optimality', {})
        row.update(valid=True, duration=result['cost'], reference_duration=checked.routing_cost,
            gap_duration_bks_pct=100*(result['cost']/checked.routing_cost-1),
            gain_construction_pct=100*(1-result['cost']/result['initial_cost']),
            initial_duration=result['initial_cost'], vehicles=len(result['routes']),
            reference_vehicles=len(ref['routes']), solver_wall_s=result['runtime_s'],
            total_wall_s=solve_wall, total_cpu_s=solve_cpu,
            travel=physical['travel'], waiting=physical['waiting'], service=physical['service'],
            reference_claims_proven=bool(info.get('proven')),
            reference_certificate_note=info.get('note', ''),
            proof_status='BKS compatible; any optimality stamp must be interpreted with its upstream arithmetic note',
            checker='mamut-routing-lib 0.12.0 td-fold/2')
        record = dict(measurement=row, result=result, independent_simulation=physical,
                      reference_check=checked.model_dump(mode='json'), reference_metadata=ref.get('metadata', {}))
    except Exception:
        row.update(error=traceback.format_exc(), total_wall_s=time.perf_counter()-started,
                   total_cpu_s=time.process_time()-cpu)
        record = dict(measurement=row, result=result)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instances', nargs='+', default=['C101', 'C201', 'R101', 'R201', 'RC101', 'RC201'])
    parser.add_argument('--seeds', nargs='+', type=int, default=[4101])
    parser.add_argument('--seconds', type=float, default=10.)
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    manifest = json.loads((ROOT/'data/dabia2013/manifest.json').read_text())
    if (not set(args.instances) <= set(manifest['instances']) or not args.label.replace('_','').isalnum()
            or not math.isfinite(args.seconds) or args.seconds <= 0 or args.workers < 1
            or any(s < 0 for s in args.seeds)):
        parser.error('Sélection ou paramètres invalides')
    # Contrôle intégral des données originales avant la première résolution.
    for name, info in manifest['files'].items():
        assert hashlib.sha256((ROOT/'data/dabia2013/n25'/name).read_bytes()).hexdigest() == info['sha256']
    root = ROOT/'results/dabia2013'
    folder = root/args.label
    suffix = 1
    while True:
        try:
            folder.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            suffix += 1
            folder = root/f'{args.label}_{suffix}'
    jobs = [(n, s, args.seconds) for n in args.instances for s in sorted(set(args.seeds))]
    sources = [ROOT/'algo/dabia.py', Path(__file__).resolve()]
    hashes = {}
    for source in sources:
        relative = source.relative_to(ROOT)
        target = folder/'source'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        hashes[relative.as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    protocol = dict(arguments=vars(args), jobs=jobs, effective_label=folder.name,
        sources=hashes, data_manifest=manifest,
        python=sys.version, platform=platform.platform(),
        packages={p:importlib.metadata.version(p) for p in ['mamut-routing-lib', 'pydantic']},
        objective='Duration = sum of route (return - optimized departure), not sum of return times',
        reference='Compatible upstream Duration BKS, not automatically a certified optimum',
        timing='Total CPU/wall includes instance loading, construction, search and final simulation; excludes interpreter startup and BKS audit',
        attribution='Own insertion/ILS/moves; MAMUT temporal evaluation and checking',
        selection='Six family representatives at n=25, development pilot; not full benchmark')
    (folder/'protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    started = time.perf_counter()
    rows = []
    print(f'{len(jobs)} resolutions Dabia2013 a 25 clients ; sorties : {folder}', flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(execute, job) for job in jobs]):
            record = future.result()
            row = record['measurement']
            rows.append(row)
            (folder/f"{row['instance']}_{row['seed']}.json").write_text(json.dumps(record, indent=2), encoding='utf-8')
            if row['valid']:
                print(f"[{len(rows)}/{len(jobs)}] {row['instance']} seed={row['seed']} REALISABLE\n"
                      f"  Duree : {row['duration']:.6f} ; reference Duration : {row['reference_duration']:.6f}\n"
                      f"  GAP BKS DURATION : {row['gap_duration_bks_pct']:+.6f} %\n"
                      f"  CPU total : {row['total_cpu_s']:.3f} s ; temps ecoule total : {row['total_wall_s']:.3f} s",
                      flush=True)
            else:
                print(row, flush=True)
    fields = sorted({k for r in rows for k in r})
    with (folder/'RESULTATS.csv').open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r:(r['instance'],r['seed'])))
    valid = [r for r in rows if r['valid']]
    summary = dict(completed=len(rows), feasible=len(valid), instances=len(set(r['instance'] for r in rows)),
        batch_wall_s=time.perf_counter()-started, mean_gap_pct=sum(r['gap_duration_bks_pct'] for r in valid)/len(valid) if valid else None,
        below_6=sum(r['gap_duration_bks_pct'] < 6 for r in valid), negatives=sum(r['gap_duration_bks_pct'] < -1e-8 for r in valid))
    (folder/'BILAN.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(summary, flush=True)
    if len(valid) != len(rows):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
