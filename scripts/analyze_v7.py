"""Recheck all complete v7 trials, including technical failures, without filtering gaps."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algo.data import load, reference
from algo.verify import verify

BASE = ROOT / 'results/optimization_v7'


def analyze(label, require_complete=True):
    folder = BASE / label
    protocol = json.loads((folder / 'protocol.json').read_text(encoding='utf-8'))
    for name, digest in protocol['sources'].items():
        assert hashlib.sha256((folder / 'source' / name).read_bytes()).hexdigest() == digest
    assert hashlib.sha256((ROOT / 'data/manifest.json').read_bytes()).hexdigest() == protocol['manifest_sha256']
    manifest = json.loads((ROOT / 'data/manifest.json').read_text(encoding='utf-8'))
    expected = {(n, s, v) for n in protocol['instances'] for s in protocol['seeds'] for v in protocol['variants']}
    rows, seen = [], set()
    instances, refs = {}, {}
    for name in protocol['instances']:
        for suffix in ['.vrp', '.sol']:
            datafile = ROOT / 'data/instances' / (name + suffix)
            assert hashlib.sha256(datafile.read_bytes()).hexdigest() == manifest['files'][name + suffix]['sha256']
        ins = load(ROOT / 'data/instances' / (name + '.vrp'))
        routes, cost = reference(ROOT / 'data/instances' / (name + '.sol'))
        checked = verify(routes, ins)
        assert checked['valid'] and abs(checked['distance']/10-cost) < 1e-7
        instances[name], refs[name] = ins, cost
    for path in sorted((folder / 'runs').glob('*.json')):
        r = json.loads(path.read_text(encoding='utf-8'))
        key = (r['instance'], r['seed'], r['variant'])
        assert r['complete'] and key in expected and key not in seen
        seen.add(key)
        ins = instances[r['instance']]
        row = dict(instance=r['instance'], clients=ins.n, seed=r['seed'], variant=r['variant'],
                   valid=r['valid'], gap_pct=None, cost=None, vehicles=None,
                   bks=refs[r['instance']], total_s=r.get('total_s'),
                   search_budget_s=r['search_budget_s'], error=r.get('error', ''),
                   source=str(path.relative_to(ROOT)))
        if 'prefix' in r:
            origin = ROOT / r['prefix']['path']
            assert hashlib.sha256(origin.read_bytes()).hexdigest() == r['prefix']['sha256']
            prior = json.loads(origin.read_text(encoding='utf-8'))
            assert prior['valid'] and prior['instance'] == r['instance'] and prior['seed'] == r['seed']
            assert prior['result']['routes'] == r['initial_routes']
            assert r['continuation_seed'] == r['seed'] + 10000
            if r['valid']:
                assert abs(r['total_s'] - prior['total_s'] - r['result']['runtime_s']) < 1e-6
                assert r['result']['cost'] <= prior['result']['cost'] + 1e-7
            row.update(reused_prefix_s=prior['total_s'], newly_executed_s=r['newly_executed_s'])
        if r['valid']:
            result = r['result']
            check = verify(result['routes'], ins)
            assert check['valid'] and abs(check['distance']/10-result['cost']) < 1e-7
            gap = 100*(result['cost']/refs[r['instance']]-1)
            assert abs(gap-r['gap_pct']) < 1e-7
            if r.get('initial_routes') is not None:
                assert verify(r['initial_routes'], ins)['valid']
            assert r['total_s'] + 1e-6 >= result['runtime_s']
            row.update(gap_pct=gap, cost=result['cost'], vehicles=check['vehicles'])
        else:
            assert r.get('error') or r.get('result', {}).get('status') != 'feasible'
        rows.append(row)
    if require_complete:
        assert seen == expected, (label, len(seen), len(expected))
    df = pd.DataFrame(rows)
    summaries = []
    for variant, group in df.groupby('variant'):
        good = group[group.valid]
        summaries.append(dict(variant=variant, planned=len(protocol['instances'])*len(protocol['seeds']),
            executed=len(group), valid=len(good), failures=len(group)-len(good),
            mean_gap=good.gap_pct.mean(), std_gap=good.gap_pct.std(ddof=1),
            best_gap=good.gap_pct.min(), worst_gap=good.gap_pct.max(),
            below_6=int((good.gap_pct < 6).sum()), mean_total_s=good.total_s.mean()))
    summary = pd.DataFrame(summaries)
    cases = df.groupby(['instance', 'variant'], as_index=False).agg(
        runs=('valid', 'size'), valid=('valid', 'sum'), mean_gap=('gap_pct', 'mean'),
        std_gap=('gap_pct', 'std'), best_gap=('gap_pct', 'min'), worst_gap=('gap_pct', 'max'),
        mean_total_s=('total_s', 'mean'))
    comparisons = []
    if 'baseline' in protocol['variants']:
        paired = df[df.valid].pivot(index=['instance', 'seed'], columns='variant', values='gap_pct')
        for variant in protocol['variants']:
            if variant == 'baseline' or variant not in paired:
                continue
            pair = paired[['baseline', variant]].dropna()
            delta = pair.baseline - pair[variant]
            means = delta.groupby(level=0).mean().to_numpy()
            if len(means):
                boot = np.random.default_rng(71111).choice(means, (10000, len(means))).mean(axis=1)
                comparisons.append(dict(variant=variant, pairs=len(delta), instances=len(means),
                    improvement_pp=float(delta.mean()), wins=int((delta > 1e-8).sum()),
                    losses=int((delta < -1e-8).sum()),
                    instance_bootstrap95=list(map(float, np.quantile(boot, [.025, .975])))))
    df.to_csv(folder/'flat.csv', index=False)
    summary.to_csv(folder/'summary.csv', index=False)
    cases.to_csv(folder/'instances.csv', index=False)
    analysis = dict(label=label, planned=len(expected), executed=len(seen),
        failures=int((~df.valid).sum()), comparisons=comparisons,
        mean_scope='All valid runs on the declared lot; failures counted separately; no gap filtering',
        uncertainty='Bootstrap across instances; two seeds are limited and old validation instances have previously been studied')
    (folder/'analysis.json').write_text(json.dumps(analysis, indent=2, allow_nan=False), encoding='utf-8')
    return df, summary, cases, analysis


if __name__ == '__main__':
    for label in sys.argv[1:]:
        _, summary, _, analysis = analyze(label)
        print(label, analysis['executed'], 'executed;', analysis['failures'], 'failures')
        print(summary.to_string(index=False))
