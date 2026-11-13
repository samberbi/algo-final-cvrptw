"""Trois reprises difficiles à neuf : qualité et CPU évalués séparément.

Pas de lecture des témoins avant résolution, pas de modification des archives.
La limite 120 s est contrôlée a posteriori ; ce script n'est pas un watchdog.
"""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS'):
    os.environ[key] = '1'
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run(job):
    import psutil
    from algo.duration import warmup
    from algo.duration_refine import solve as construct
    from algo.hgs_tuning import solve as hgs
    from algo.data import load, reference
    from algo.verify import verify
    name, seed, core = job
    psutil.Process().cpu_affinity([core])
    # Préchauffage mesuré séparément ; le CPU de bout en bout l'inclut aussi.
    end_to_end_cpu = time.process_time()
    end_to_end_wall = time.perf_counter()
    warmup()
    warm_cpu = time.process_time()-end_to_end_cpu
    started, cpu = time.perf_counter(), time.process_time()
    ins = load(ROOT/'data/instances'/(name+'.vrp'))
    result = construct(ins, seed=seed, seconds=10.)
    assert result['status'] == 'feasible'
    stages = [dict(phase='construction_local_pool', cost=result['cost'], runtime_s=result['runtime_s'])]
    for seconds, neighbors, offset in [(30., 80, 30000), (20., 120, 60000)]:
        previous = result['cost']
        result = hgs(ins, seconds, seed+offset, result['routes'], neighbors, objective='duration')
        assert result['cost'] <= previous+1e-7
        stages.append(dict(phase='external_HGS', cost=result['cost'], runtime_s=result['runtime_s'],
                           seconds=seconds, neighbors=neighbors, seed=seed+offset))
    metrics = verify(result['routes'], ins)
    assert metrics['valid'] and abs(metrics['duration']/10-result['cost']) < 1e-7
    solve_cpu = time.process_time()-cpu
    solve_wall = time.perf_counter()-started
    complete_cpu = time.process_time()-end_to_end_cpu
    complete_wall = time.perf_counter()-end_to_end_wall
    # La référence sert uniquement au bilan, après la fin de toutes les recherches.
    routes, _ = reference(ROOT/'data/instances'/(name+'.sol'))
    control = verify(routes, ins)
    assert control['valid']
    delta = 100*(metrics['duration']/control['duration']-1)
    return dict(instance=name, seed=seed, valid=True, duration=result['cost'],
        delta_reference_pct=delta, reference_kind='Duration of distance-reference plan; not time optimum',
        solve_cpu_s=solve_cpu, solve_wall_s=solve_wall, warmup_cpu_s=warm_cpu,
        total_including_warmup_cpu_s=complete_cpu, total_including_warmup_wall_s=complete_wall,
        below_6=delta<6, below_120_cpu=complete_cpu<120,
        routes=result['routes'], stages=stages,
        attribution='Own constructors/orchestration/route pool; external PyVRP Local Search and HGS')


def main():
    import psutil
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label.replace('_', '').isalnum():
        parser.error('Nom de lot invalide')
    folder = ROOT/'results/local'/args.label
    if folder.exists():
        parser.error('Choisir un nouveau nom de lot')
    folder.mkdir(parents=True)
    pairs = [('C2_10_2', 4101), ('C2_10_7', 4101), ('C2_10_7', 4102)]
    cores = psutil.Process().cpu_affinity()[::2][:3]
    jobs = [(name, seed, cores[i % len(cores)]) for i, (name, seed) in enumerate(pairs)]
    sources = [*sorted((ROOT/'algo').glob('*.py')), Path(__file__).resolve()]
    hashes = {}
    for source in sources:
        relative = source.relative_to(ROOT)
        target = folder/'source'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        hashes[relative.as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    (folder/'protocol.json').write_text(json.dumps(dict(jobs=jobs, sources=hashes,
        selection='Three historically slow selected pairs; exploratory replay, not independent validation',
        phases='10s soft construction then external HGS 30s/80 neighbors and 20s/120 neighbors',
        limit_kind='Post-hoc CPU check, including measured warmup, excluding interpreter startup'), indent=2))
    rows = []
    with ProcessPoolExecutor(max_workers=len(cores)) as pool:
        for future in as_completed([pool.submit(run, job) for job in jobs]):
            record = future.result()
            (folder/f"{record['instance']}_{record['seed']}.json").write_text(json.dumps(record, indent=2))
            rows.append(record)
            from scripts.test_instances import show_quality_result
            show_quality_result(record)
    (folder/'summary.json').write_text(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
