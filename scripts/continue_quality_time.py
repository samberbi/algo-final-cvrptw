"""Continuation de C2_10_2 avec cumul du CPU des recherches précédentes.

Le budget est choisi sans consulter le témoin : seuls un départ réalisable et
le CPU restant sont utilisés. Le contrôle final à 120 s n'est pas un watchdog.
"""
from pathlib import Path
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import hashlib
import json
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from algo.data import load, reference
    from algo.hgs_tuning import solve
    from algo.verify import verify
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label.replace('_', '').isalnum():
        parser.error('Nom de lot invalide')
    folder = ROOT/'results/local'/args.label
    target = folder/'C2_10_2_4101_continued.json'
    if target.exists():
        parser.error('Une continuation existe déjà ; préserver son résultat')
    parent = json.loads((folder/'C2_10_2_4101.json').read_text())
    spent = parent['total_including_warmup_cpu_s']
    if spent+50 >= 115:
        parser.error('Marge insuffisante pour la continuation de 50 secondes')
    start, cpu = time.perf_counter(), time.process_time()
    ins = load(ROOT/'data/instances/C2_10_2.vrp')
    result = solve(ins, 50., 94101, parent['routes'], 80, objective='duration')
    checked = verify(result['routes'], ins)
    assert checked['valid'] and result['cost'] <= parent['duration']+1e-7
    additional_cpu = time.process_time()-cpu
    additional_wall = time.perf_counter()-start
    routes, _ = reference(ROOT/'data/instances/C2_10_2.sol')
    ref = verify(routes, ins)
    assert ref['valid']
    out = dict(parent)
    out.update(routes=result['routes'], duration=result['cost'],
        delta_reference_pct=100*(checked['duration']/ref['duration']-1),
        total_including_warmup_cpu_s=spent+additional_cpu,
        total_including_warmup_wall_s=parent['total_including_warmup_wall_s']+additional_wall,
        additional_cpu_s=additional_cpu, additional_wall_s=additional_wall,
        parent_source='C2_10_2_4101.json',
        continuation=dict(seconds=50, neighbors=80, seed=94101, attribution='external PyVRP HGS'))
    out['below_6'] = out['delta_reference_pct'] < 6
    out['below_120_cpu'] = out['total_including_warmup_cpu_s'] < 120
    target.write_text(json.dumps(out, indent=2))
    (folder/'continuation_script_sha256.txt').write_text(hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    from scripts.test_instances import show_quality_result
    show_quality_result(out)


if __name__ == '__main__':
    main()
