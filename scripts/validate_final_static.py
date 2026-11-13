"""Vérifie données, solutions, références, provenance, tests et notebook exécuté.

Cette validation ne relance pas les recherches. Un échec de recherche conservé
est une observation valide ; une solution ou un coût faux est une erreur.
"""
from pathlib import Path
import hashlib
import itertools
import json
import re
import sys
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import nbformat
import numpy as np
import pandas as pd
from algo.data import load as load_full
from algo.static_small import load as load_small
from algo.model import Instance,Objective
from algo.verify import verify
from controle.exact import exact


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    for name,info in manifest['files'].items():
        assert digest(ROOT/'data/instances'/name)==info['sha256'],name
    small=json.loads((ROOT/'data/static_small/manifest.json').read_text())
    for item in small['files']:
        assert digest(ROOT/item['path'])==item['sha256']
        assert digest(ROOT/item['parent'])==item['parent_sha256']
        parent=load_full(ROOT/item['parent']);ins=load_small(ROOT/item['path']);limit=ins.n+1
        for field in ['xy','demand','service','early','late']:
            assert np.array_equal(getattr(ins,field),getattr(parent,field)[:limit])
        assert np.array_equal(ins.travel,parent.travel[:limit,:limit])
    datasets={};records=failures=0;campaigns={}
    for name in ['pilote25','couverture_progressive','confirmation_ils_v2']:
        folder=ROOT/'results/final_static'/name
        protocol=json.loads((folder/'protocol.json').read_text())
        cfg=protocol['config']
        for rel,sha in protocol['sources'].items():
            assert digest(folder/'source'/rel)==sha,(name,rel)
        expected={(case,seed,method) for case,seed,method in itertools.product(cfg['cases'],cfg['seeds'],cfg['methods'])}
        seen=set();rows=pd.read_csv(folder/'RESULTATS.csv')
        reference_costs={}
        raw=[]
        for path in (folder/'runs').glob('*.json'):
            r=json.loads(path.read_text());case=f"{r['instance']}:{r['n']}"
            key=(case,r['seed'],r['method']);assert key in expected and key not in seen
            seen.add(key);records+=1
            if case not in datasets:
                path_ins=(ROOT/f"data/static_small/n{r['n']}"/(r['instance']+'.txt') if r['n'] in [25,50]
                          else ROOT/'data/instances'/(r['instance']+'.vrp'))
                datasets[case]=(path_ins,load_small(path_ins) if r['n'] in [25,50] else load_full(path_ins))
            path_ins,ins=datasets[case]
            assert digest(path_ins)==protocol['instance_hashes'][case]
            result=r['result'];routes=result.get('routes')
            if routes is None:
                assert result['status'] in ['not_found','error','proven_infeasible'];failures+=1
            else:
                checked=verify(routes,ins)
                assert checked['valid'] and abs(checked['duration']/10-result['cost'])<1e-7
                for field in ['duration','travel','waiting','vehicles','makespan']:
                    assert abs(checked[field]-result['metrics'][field])<1e-7
                assert abs(checked['duration']-checked['travel']-checked['waiting']-ins.service.sum())<1e-7
                if r['method']=='ortools':
                    assert result['native_objective']==checked['duration']
                    reference_costs[case]=min(reference_costs.get(case,float('inf')),result['cost'])
            assert r['wall_s']>=0 and r['cpu_s']>=0
            raw.append(r)
        assert seen==expected and len(rows)==len(raw)
        for r in raw:
            row=rows[(rows.instance==r['instance']) & (rows.n==r['n']) &
                     (rows.seed==r['seed']) & (rows.method==r['method'])]
            assert len(row)==1
            row=row.iloc[0];result=r['result'];case=f"{r['instance']}:{r['n']}"
            assert bool(row.valid)==(result.get('routes') is not None)
            if row.valid and r['method']!='ortools' and case in reference_costs:
                expected_delta=100*(result['cost']/reference_costs[case]-1)
                assert abs(row.delta_independent_pct-expected_delta)<1e-7
            assert pd.isna(row.certified_gap_pct)
        campaigns[name]=dict(records=len(raw),failures=int((~rows.valid).sum()))
    # Les dix preuves historiques ne sont pas de nouveaux runs de métaheuristique.
    exact_controls=0
    for path in (ROOT/'results/time_objective/exact').glob('exact-duration-*.json'):
        r=json.loads(path.read_text());d=r['data']
        ins=Instance(r['instance'],np.array(d['xy']),np.array(d['demand']),np.array(d['service']),
            np.array(d['early']),np.array(d['late']),np.array(d['travel']),r['capacity'],r['vehicles'],r['horizon'])
        oracle=exact(ins,Objective.DURATION,max_clients=6)
        assert oracle['status']==r['solver']['status']=='optimal'
        assert abs(oracle['score']/10-r['optimum'])<1e-7
        checked=verify(r['solver']['routes'],ins)
        assert checked['valid'] and abs(checked['duration']/10-r['optimum'])<1e-7
        exact_controls+=1
    assert exact_controls==10
    for path in (ROOT/'results/final_static/exact').glob('*.json'):
        r=json.loads(path.read_text());result=r['result']
        assert result['status'] in ['optimal','time_limit','proven_infeasible','error']
        if result.get('routes') is not None:
            checked=verify(result['routes'],load_small(ROOT/'data/static_small/n25'/(r['instance']+'.txt')))
            assert checked['valid'] and abs(checked['duration']/10-result['cost'])<1e-7
            if result['lower_bound'] is not None:assert result['lower_bound']<=result['cost']+1e-7
    nb=nbformat.read(ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb',4)
    nbformat.validate(nb)
    codes=[c for c in nb.cells if c.cell_type=='code']
    assert all(c.execution_count is not None for c in codes)
    assert not any(o.output_type=='error' for c in codes for o in c.outputs)
    assert not any(c.metadata.get('dabia_extension') for c in nb.cells)
    sources=[c.source for c in nb.cells]
    assert next(i for i,s in enumerate(sources) if s.startswith('## 2. Complexité')) < next(i for i,s in enumerate(sources) if s.startswith('## 3. Modélisation'))
    assert sum(bool(c.metadata.get('final_static_results')) for c in nb.cells)==1
    for c in nb.cells:
        for image in re.findall(r'!\[[^\n]*\]\(([^)]+)\)',c.source):
            if not image.startswith(('http','attachment:')):assert (ROOT/'notebooks'/image).is_file(),image
    tests=ET.parse(ROOT/'livraison/TESTS_SOUTENANCE.xml').getroot()
    assert not list(tests.iter('failure')) and not list(tests.iter('error'))
    total_tests=len(list(tests.iter('testcase')));skipped=len(list(tests.iter('skipped')))
    receipt=dict(validated=True,scope='Static final notebook, all saved new pilot records, data hashes, ten exact controls and current test suite',
        instances_original=len(manifest['reference_instances']),original_files_checked=len(manifest['files']),
        small_instances_checked=len(small['files']),pilot_records=records,pilot_feasible=records-failures,
        pilot_unsuccessful_searches=failures,campaigns=campaigns,exact_controls=exact_controls,
        passed_tests=total_tests-skipped,skipped_tests=skipped,notebook_code_cells=len(codes),
        notebook_sha256=digest(ROOT/'notebooks/Livrable_Final_CVRPTW.ipynb'),
        mathematical_objective='Sum complete route durations, fixed symmetric travel, all departures zero',
        limitations=['No certified duration optimum on all Solomon/Homberger instances',
            'No new uniform 356-instance benchmark; short development pilots do not replace it',
            'Experimental ILS extension not selected automatically as default',
            'Historical best archive uses mixed budgets; exploratory TD outside main model'])
    (ROOT/'livraison/VALIDATION_FINALE_STATIQUE.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
