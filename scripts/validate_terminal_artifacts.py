"""Contrôle CSV/JSON, horaires et provenance des essais de commandes enregistrés."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
from algo.verify import verify
from scripts.terminal_support import catalog,load_case,sha


def main():
    base=ROOT/'results/terminal_validation'
    command_count=0
    for name in ['commandes_terminal_checks','commandes_terminal_runs']:
        receipt=json.loads((base/name/'VALIDATION.json').read_text())
        assert receipt['all_validated'] and all(c['validated'] for c in receipt['checks'])
        command_count+=len(receipt['checks'])
    index=json.loads((base/'SOURCE_INDEX.json').read_text())
    entries={(r['instance'],r['n']):r for r in catalog()}
    count=success=failed=0
    for label,sources in index.items():
        candidates=list(base.glob('*/campaigns/'+label))+list((base/'complements').glob(label))
        assert len(candidates)==1,label
        folder=candidates[0];protocol=json.loads((folder/'protocol.json').read_text())
        for rel,digest in protocol['sources'].items():assert sha(ROOT/sources[rel])==digest
        rows=pd.read_csv(folder/'RESULTATS.csv')
        seen=set()
        for path in folder.glob('*.json'):
            record=json.loads(path.read_text(encoding='utf-8'))
            if 'measurement' not in record:continue
            m=record['measurement'];count+=1
            key=(m['instance'],m['n'],m['method'],m['seed']);assert key not in seen;seen.add(key)
            row=rows[(rows.instance==key[0]) & (rows.n==key[1]) & (rows.method==key[2]) & (rows.seed==key[3])]
            assert len(row)==1;row=row.iloc[0]
            ins=load_case(entries[(key[0],key[1])])
            assert bool(row.valid)==m['valid']
            assert pd.isna(row.certified_gap_pct) and m['certified_gap_pct'] is None
            if m['valid']:
                checked=verify(record['result']['routes'],ins)
                assert checked['valid']
                for metric in ['duration','travel','waiting']:
                    assert abs(checked[metric]/10-m[metric])<1e-7
                    assert abs(row[metric]-m[metric])<1e-7
                assert abs(m['service']-ins.service.sum()/10)<1e-7
                assert abs(m['duration']-m['travel']-m['waiting']-m['service'])<1e-7
                success+=1
            else:
                assert m['duration'] is None and m['delta_reference_pct'] is None
                assert pd.isna(row.duration) and pd.isna(row.delta_reference_pct)
                assert m['status'] in ['not_found','time_limit','worker_error','error','proven_infeasible']
                failed+=1
            reference=record['reference']
            if reference['duration'] is not None:
                source=ROOT/reference['source']
                if source.suffix=='.sol':
                    from algo.data import reference as public
                    routes,_=public(source)
                else:
                    independent=json.loads(source.read_text())
                    assert independent['method']=='ortools'
                    routes=independent['result']['routes']
                refcheck=verify(routes,ins);assert refcheck['valid']
                assert abs(refcheck['duration']/10-reference['duration'])<1e-7
                if m['valid']:
                    delta=100*(m['duration']/reference['duration']-1)
                    assert abs(delta-m['delta_reference_pct'])<1e-7
                    assert abs(delta-row.delta_reference_pct)<1e-7
            else:assert m['delta_reference_pct'] is None
        assert len(rows)==len(seen)
    receipt=dict(validated=True,automated_commands_verified=command_count,campaigns=len(index),
        recorded_resolutions_checked=count,feasible=success,expected_unsuccessful=failed,
        verified='Actual saved routes, schedules, duration decomposition, signed deltas, CSV/JSON and frozen source hashes',
        limitation='CLI validation campaigns, not a new exhaustive quality benchmark; certified duration gap unavailable')
    (ROOT/'livraison/VALIDATION_COMMANDES_TERMINAL.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
