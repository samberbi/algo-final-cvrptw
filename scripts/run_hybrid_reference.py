"""Explicit optional external hybrid; leaves the assessed CLI default unchanged."""
from pathlib import Path
import argparse
import json
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algo.data import load, reference
from algo.optimized import warmup
from algo.hybrid_reference import solve, Settings


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Our ILS then external PyVRP HGS, explicitly credited')
    p.add_argument('instance')
    p.add_argument('--search-seconds', type=float, default=120.)
    p.add_argument('--seed', type=int, default=2101)
    a = p.parse_args()
    cfg = Settings(search_seconds=a.search_seconds, seed=a.seed)
    instance = Path(a.instance)
    if not instance.exists():
        instance = ROOT/'data/instances'/(a.instance.removesuffix('.vrp')+'.vrp')
    ins = load(instance)
    tick = time.perf_counter()
    warmup()
    compilation_s = time.perf_counter()-tick
    result = solve(ins, cfg)
    record = dict(instance=ins.name, result=result, compilation_s=compilation_s)
    if result['status'] == 'feasible' and instance.with_suffix('.sol').exists():
        _, bks = reference(instance.with_suffix('.sol'))
        record.update(reference_distance=bks, gap_pct=100*(result['cost']/bks-1))
    directory = ROOT/'results/optimization_v7/manual'
    directory.mkdir(parents=True, exist_ok=True)
    output = directory/(str(time.time_ns())+'_hybrid.json')
    output.write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(dict(engine=result.get('engine'), status=result['status'],
        cost=result.get('cost'), gap_pct=record.get('gap_pct'), runtime_s=result['runtime_s'],
        compilation_s=compilation_s, output=str(output)), indent=2))
