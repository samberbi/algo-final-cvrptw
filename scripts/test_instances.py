"""Relance explicite du catalogue ; ne remplace aucune mesure publiée.

Un processus par résolution, CPU mesuré dans chaque worker. Le temps du lot
inclut le démarrage ; la somme CPU des résolutions exclut ce démarrage.
"""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS'):
    os.environ[key] = '1'
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
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def initialize():
    from algo.duration import warmup
    warmup()


def execute(job):
    """La référence est consultée uniquement après la fin du solveur."""
    from algo.data import load, reference
    from algo.verify import verify
    name, seed, method, seconds = job
    row = dict(instance=name, seed=seed, method=method, requested_seconds=seconds,
               valid=False, duration=None, reference_duration=None, delta_reference_pct=None)
    start, cpu = time.perf_counter(), time.process_time()
    try:
        ins = load(ROOT / 'data/instances' / (name + '.vrp'))
        if method == 'duration_refined':
            from algo.duration_refine import solve
            result = solve(ins, seed=seed, seconds=seconds)
        else:
            from algo.duration import solve, Settings
            result = solve(ins, Settings(seed=seed, seconds=seconds, method=method))
        if result['status'] != 'feasible':
            raise ValueError('Aucune solution réalisable : ' + result['status'])
        metrics = verify(result['routes'], ins)
        assert metrics['valid'] and abs(result['cost'] - metrics['duration'] / 10) < 1e-7
        # CPU/temps de résolution comprennent chargement et validation finale,
        # mais excluent le préchauffage et la lecture du témoin.
        row.update(wall_s=time.perf_counter()-start, cpu_s=time.process_time()-cpu)
        routes, _ = reference(ROOT / 'data/instances' / (name + '.sol'))
        control = verify(routes, ins)
        assert control['valid']
        row.update(valid=True, n=ins.n, duration=result['cost'],
                   reference_duration=control['duration']/10,
                   delta_reference_pct=100*(metrics['duration']/control['duration']-1),
                   vehicles=metrics['vehicles'])
        return row, result
    except Exception:
        row.update(error=traceback.format_exc(), wall_s=time.perf_counter()-start,
                   cpu_s=time.process_time()-cpu)
        return row, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', nargs='+', type=int, default=[100, 200, 400, 600, 800, 1000])
    parser.add_argument('--instances', nargs='+', help='Sous-lot explicite pour un test rapide')
    parser.add_argument('--seeds', nargs='+', type=int, default=[4101])
    parser.add_argument('--seconds', type=float, default=10.)
    parser.add_argument('--method', choices=['duration_refined', 'ils', 'sa', 'hybrid'], default='duration_refined')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--label', required=True, help='Nouveau nom, par exemple portable_356_v1')
    parser.add_argument('--dry-run', action='store_true', help='Afficher le nombre de résolutions sans calcul')
    args = parser.parse_args()
    if (not math.isfinite(args.seconds) or args.seconds <= 0 or args.workers < 1
            or not args.label.replace('_', '').replace('-', '').isalnum()
            or any(s < 0 or s >= 2**31 for s in args.seeds)
            or not set(args.sizes) <= {100, 200, 400, 600, 800, 1000}):
        parser.error('Budget, graines, tailles ou nom de lot invalide')
    manifest = json.loads((ROOT/'data/manifest.json').read_text())
    catalogue = manifest['reference_instances']
    known = {r['instance'] for r in catalogue}
    if args.instances and not set(args.instances) <= known:
        parser.error('Instance absente du catalogue')
    names = [r['instance'] for r in catalogue if r['n'] in args.sizes
             and (not args.instances or r['instance'] in args.instances)]
    jobs = [(name, seed, args.method, args.seconds) for name in names for seed in sorted(set(args.seeds))]
    if not jobs:
        parser.error('Sélection vide')
    print(f'{len(names)} instances ; {len(jobs)} résolutions ; {args.workers} processus', flush=True)
    if args.dry_run:
        return
    folder = ROOT/'results/local'/args.label
    if folder.exists():
        parser.error('Le dossier existe déjà : choisir un nouveau --label pour préserver les mesures')
    folder.mkdir(parents=True)
    sources = [*sorted((ROOT/'algo').glob('*.py')), Path(__file__).resolve()]
    hashes = {}
    for source in sources:
        rel = source.relative_to(ROOT)
        target = folder/'source'/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        hashes[rel.as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    protocol = dict(arguments=vars(args), jobs=jobs, python=sys.version, platform=platform.platform(),
        packages={p:importlib.metadata.version(p) for p in ['pyvrp', 'numpy', 'numba', 'scipy']},
        sources=hashes, manifest_sha256=hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest(),
        objective='sum_route_duration', departures=0,
        reference='Duration of distance-reference plan; not a proven duration optimum',
        budget='duration_refined: soft full solve limit; others: search budget plus construction/setup',
        timing='Per-run CPU excludes worker startup/warmup/reference; batch wall includes them')
    (folder/'protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    rows = []
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers, initializer=initialize) as pool:
        pending = [pool.submit(execute, job) for job in jobs]
        for future in as_completed(pending):
            row, result = future.result()
            rows.append(row)
            target = folder/f"{row['instance']}_{row['seed']}.json"
            target.write_text(json.dumps(dict(measurement=row, result=result), indent=2), encoding='utf-8')
            print(f"{len(rows)}/{len(jobs)} {row['instance']} valid={row['valid']} wall={row['wall_s']:.2f}s", flush=True)
    rows.sort(key=lambda r:(r['instance'], r['seed']))
    fields = sorted({key for r in rows for key in r})
    with (folder/'RESULTATS.csv').open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(completed=len(rows), valid=sum(r['valid'] for r in rows),
                   batch_wall_s=time.perf_counter()-started,
                   resolution_cpu_sum_s=sum(r['cpu_s'] for r in rows))
    (folder/'BILAN.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(folder, summary)
    if not all(r['valid'] for r in rows):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
