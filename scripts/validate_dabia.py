"""Contrôle les 24 résolutions TD enregistrées et les 16 tests, sans recherche."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import sys
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from mamut_routing_lib.td import load_td_instance, check_td_solution, TD_CHECKER_CONTRACT
    from mamut_routing_lib.models import BenchmarkSolution
    from algo.dabia import simulate
    assert importlib.metadata.version('mamut-routing-lib') == '0.12.0'
    assert TD_CHECKER_CONTRACT == 'td-fold/2'
    manifest = json.loads((ROOT/'data/dabia2013/manifest.json').read_text())
    data = ROOT/'data/dabia2013/n25'
    for name, info in manifest['files'].items():
        assert hashlib.sha256((data/name).read_bytes()).hexdigest() == info['sha256']
    references = {}
    for name in manifest['instances']:
        loaded = load_td_instance(data/(name+'.vrp.json'))
        ref = json.loads((data/(name+'.bks.Duration.json')).read_text())
        check = check_td_solution(loaded, BenchmarkSolution(instance_name=name, routes=ref['routes'], cost=ref['cost']))
        assert check.is_valid()
        references[name] = (loaded, ref, check.routing_cost)
    records = []
    for label, expected in [('pilote_5s', 6), ('pilote_5s_3graines', 18)]:
        folder = ROOT/'results/dabia2013'/label
        protocol = json.loads((folder/'protocol.json').read_text())
        for relative, digest in protocol['sources'].items():
            assert hashlib.sha256((folder/'source'/relative).read_bytes()).hexdigest() == digest
            assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() == digest, relative
        files = [p for p in folder.glob('*.json') if p.name not in ['protocol.json', 'BILAN.json']]
        assert len(files) == expected
        keys = set()
        for path in files:
            record = json.loads(path.read_text())
            row, result = record['measurement'], record['result']
            keys.add((row['instance'], row['seed']))
            loaded, _, reference_cost = references[row['instance']]
            checked = check_td_solution(loaded, BenchmarkSolution(instance_name=row['instance'], routes=result['routes'], cost=result['cost']))
            assert row['valid'] and checked.is_valid()
            assert checked.routing_cost == row['duration'] == result['cost']
            assert row['reference_duration'] == reference_cost
            delta = 100*(result['cost']/reference_cost-1)
            assert delta == row['gap_duration_bks_pct']
            physical = simulate(loaded, result['routes'], result['route_evaluations'])
            assert physical['valid'] and abs(physical['duration']-result['cost']) < 1e-7
            assert result['cost'] <= result['initial_cost']
            assert all(a['best'] >= b['best'] for a,b in zip(result['trace'],result['trace'][1:]))
            assert row['total_cpu_s'] >= result['cpu_s'] >= 0
            assert row['total_wall_s'] >= result['runtime_s'] >= 0
            records.append(row)
        assert keys == {(name, seed) for name,seed,_ in protocol['jobs']}
    suite = ET.parse(ROOT/'results/dabia2013/tests.xml').getroot()
    assert not list(suite.iter('failure')) and not list(suite.iter('error')) and not list(suite.iter('skipped'))
    tests = len(list(suite.iter('testcase')))
    assert tests == 16
    main_rows = records[6:]
    receipt = dict(validated=True, original_files=18, reference_instances=6,
        recorded_resolutions=24, main_pilot_resolutions=18, main_pilot_seeds=3,
        all_feasible=True, tests_passed=tests,
        mean_gap_duration_bks_pct=sum(r['gap_duration_bks_pct'] for r in main_rows)/len(main_rows),
        max_gap_duration_bks_pct=max(r['gap_duration_bks_pct'] for r in main_rows),
        max_total_cpu_s=max(r['total_cpu_s'] for r in main_rows),
        max_total_wall_s=max(r['total_wall_s'] for r in main_rows),
        reference_recertification_notes=[name for name,(_,ref,_) in references.items()
            if 'pending' in ref.get('metadata',{}).get('optimality',{}).get('note','').lower()],
        checker='mamut-routing-lib 0.12.0 td-fold/2',
        scope='Six selected instances at n=25; BKS equality, not full-benchmark validation or new optimality proofs')
    (ROOT/'results/dabia2013/VALIDATION.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
