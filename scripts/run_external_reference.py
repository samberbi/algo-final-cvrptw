"""Run an explicitly external reference, separately from the assessed ILS."""
from pathlib import Path
import argparse
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algo.data import load, reference
from algo.external_reference import solve


def main():
    parser = argparse.ArgumentParser(description='External PyVRP reference; not our ILS')
    parser.add_argument('instance')
    parser.add_argument('--seconds', type=float, default=60.)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--our-construction', action='store_true')
    args = parser.parse_args()
    if not 0 < args.seconds < float('inf'):
        parser.error('Positive finite search time required')
    path = Path(args.instance)
    if not path.exists():
        path = ROOT / 'data/instances' / (args.instance.removesuffix('.vrp') + '.vrp')
    ins = load(path)
    initial, construction, compilation = None, 0., 0.
    if args.our_construction:
        from algo.optimized import warmup
        from algo.iterated import construct
        tick = time.perf_counter()
        warmup()
        compilation = time.perf_counter() - tick
        initial, info = construct(ins, args.seed, 12)
        construction = info['seconds']
        if initial is None:
            raise RuntimeError('Our construction failed; no hidden fallback')
    result = solve(ins, args.seconds, args.seed, initial)
    record = dict(instance=ins.name, result=result, construction_s=construction,
                  compilation_s=compilation, total_s=construction+result['runtime_s'],
                  attribution='External PyVRP HGS; our optional initial construction and independent verification')
    # Reference is read only after the solve and is never passed to it.
    if path.with_suffix('.sol').exists() and result['status'] == 'feasible':
        _, bks = reference(path.with_suffix('.sol'))
        record.update(reference_distance=bks, gap_pct=100*(result['cost']/bks-1))
    folder = ROOT/'results/optimization_v7/manual'
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / (time.strftime('%Y%m%dT%H%M%S') + '_' + str(time.time_ns()) + '.json')
    output.write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(dict(engine=result.get('engine'), status=result['status'],
                         cost=result.get('cost'), gap_pct=record.get('gap_pct'),
                         total_s=record['total_s'], compilation_s=compilation,
                         output=str(output)), indent=2))


if __name__ == '__main__':
    main()
