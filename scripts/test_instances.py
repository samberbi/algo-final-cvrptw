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


def show_result(row, completed, total):
    """Affiche le résultat dès sa réception, sans masquer un échec."""
    print(f"\n[{completed}/{total}] {row['instance']} | graine {row['seed']} | {row['method']}", flush=True)
    print(f"  Faisabilite : {'OUI' if row['valid'] else 'NON'}", flush=True)
    if row['valid']:
        delta = row['delta_reference_pct']
        print(f"  Duree solution : {row['duration']:.2f} u.t.\n"
              f"  Duree temoin   : {row['reference_duration']:.2f} u.t.\n"
              f"  GAP DUREE / PLAN TEMOIN : {delta:+.4f} %\n"
              f"  Ecart au temoin < +6 % : {'OUI' if delta < 6 else 'NON'} (pas une preuve d'optimalite)\n"
              f"  Vehicules : {row['vehicles']}", flush=True)
        if 'travel' in row:
            print('  Decomposition              Solution       Temoin\n'
                  f"  Trajets              : {row['travel']:12.2f} {row['reference_travel']:12.2f}\n"
                  f"  Attentes             : {row['waiting']:12.2f} {row['reference_waiting']:12.2f}\n"
                  f"  Services             : {row['service']:12.2f} {row['reference_service']:12.2f}\n"
                  f"  Vehicules            : {row['vehicles']:12d} {row['reference_vehicles']:12d}\n"
                  f"  Fin du dernier camion: {row['makespan']:12.2f} {row['reference_makespan']:12.2f}", flush=True)
        if delta < 0:
            print("  Ecart negatif : meilleure duree cumulee que le temoin DISTANCE,\n"
                  "  sans preuve d'amelioration sur un optimum temporel.", flush=True)
    else:
        print('  Duree et ecart : indisponibles\n  Erreur : '+row.get('error', 'Echec non detaille'), flush=True)
    print(f"  Temps ecoule : {row['wall_s']:.3f} s | CPU resolution : {row['cpu_s']:.3f} s", flush=True)


def show_quality_result(record):
    """Même libellé de gap pour les reprises longues, avec leur CPU cumulé."""
    delta = record['delta_reference_pct']
    print(f"\n{record['instance']} | graine {record['seed']}\n"
          f"  Faisabilite : {'OUI' if record['valid'] else 'NON'}\n"
          f"  Duree solution : {record['duration']:.2f} u.t.\n"
          f"  GAP DUREE / PLAN TEMOIN : {delta:+.4f} %\n"
          f"  Critere gap < +6 % : {'OUI' if delta < 6 else 'NON'}\n"
          f"  CPU cumule : {record['total_including_warmup_cpu_s']:.3f} s / 120 s\n"
          f"  Temps ecoule cumule : {record['total_including_warmup_wall_s']:.3f} s",
          flush=True)


def execute(job):
    """La référence est consultée uniquement après la fin du solveur."""
    from algo.data import load, reference
    from algo.verify import verify
    name, seed, method, seconds = job
    row = dict(instance=name, seed=seed, method=method, requested_seconds=seconds,
               valid=False, duration=None, reference_duration=None, delta_reference_pct=None,
               gap_duree_pct=None)
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
                   gap_duree_pct=100*(metrics['duration']/control['duration']-1),
                   travel=metrics['travel']/10, waiting=metrics['waiting']/10,
                   service=float(ins.service.sum())/10, makespan=metrics['makespan']/10,
                   reference_travel=control['travel']/10, reference_waiting=control['waiting']/10,
                   reference_service=float(ins.service.sum())/10,
                   reference_vehicles=control['vehicles'], reference_makespan=control['makespan']/10,
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
    parser.add_argument('--label', required=True, help='Nom du lot ; suffixe numerote automatique si deja utilise')
    parser.add_argument('--dry-run', action='store_true', help='Afficher le nombre de résolutions sans calcul')
    parser.add_argument('--show-results', action='store_true', help='Afficher un lot existant sans relancer les calculs')
    args = parser.parse_args()
    if (not math.isfinite(args.seconds) or args.seconds <= 0 or args.workers < 1
            or not args.label.replace('_', '').replace('-', '').isalnum()
            or any(s < 0 or s >= 2**31 for s in args.seeds)
            or not set(args.sizes) <= {100, 200, 400, 600, 800, 1000}):
        parser.error('Budget, graines, tailles ou nom de lot invalide')
    if args.show_results:
        folder = ROOT/'results/local'/args.label
        records = []
        for path in sorted(folder.glob('*.json')):
            record = json.loads(path.read_text(encoding='utf-8'))
            if 'measurement' in record:
                records.append(record['measurement'])
        if not records:
            parser.error('Aucun resultat de test_instances dans ce lot')
        for index, row in enumerate(records, 1):
            show_result(row, index, len(records))
        print("Gap = 100 * (duree solution / duree temoin - 1), pas un optimum temporel.", flush=True)
        return
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
    suffix = 1
    while True:
        try:
            # Création atomique : deux lancements simultanés ne partagent pas un dossier.
            folder.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            suffix += 1
            folder = ROOT/'results/local'/f'{args.label}_{suffix}'
    if folder.name != args.label:
        print(f"Lot '{args.label}' deja present : nouveau lot '{folder.name}'. "
              "Les anciens resultats sont conserves.", flush=True)
    print(f"Dossier de cette execution : {folder}", flush=True)
    sources = [*sorted((ROOT/'algo').glob('*.py')), Path(__file__).resolve()]
    hashes = {}
    for source in sources:
        rel = source.relative_to(ROOT)
        target = folder/'source'/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        hashes[rel.as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    protocol = dict(arguments=vars(args), effective_label=folder.name, jobs=jobs, python=sys.version, platform=platform.platform(),
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
            show_result(row, len(rows), len(jobs))
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
    print(f"\nBILAN : {summary['valid']}/{summary['completed']} solutions realisables\n"
          f"Temps ecoule du lot : {summary['batch_wall_s']:.3f} s\n"
          f"Somme CPU des resolutions : {summary['resolution_cpu_sum_s']:.3f} s\n"
          "Le CPU ci-dessus exclut le demarrage et le prechauffage des workers.\n"
          "L'ecart porte sur le plan temoin reevalue, pas sur un optimum en duree.\n"
          f"Tableau CSV : {folder/'RESULTATS.csv'}\n"
          f"Tournees et protocole : {folder}", flush=True)
    if not all(r['valid'] for r in rows):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
