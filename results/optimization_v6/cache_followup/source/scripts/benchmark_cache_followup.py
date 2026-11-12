"""Exploratory cache-only follow-up; reuse, never recount, baseline measurements."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS']:os.environ[key]='1'
from pathlib import Path
import json,hashlib,multiprocessing as mp,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import psutil
from scripts.benchmark_v6 import initialize,execute
from web.experiments import read_json,atomic_json


if __name__=='__main__':
    base=ROOT/'results/optimization_v6'
    reference=read_json(base/'validation/protocol.json')
    folder=base/'cache_followup'
    protocol=dict(reference)
    protocol.update(variants=['cache'],reference_label='validation',
                    role='Exploratory follow-up after combined confirmation; same cases and seeds, not an independent confirmation',
                    baseline_accounting='24 prior baseline runs reused, not executed again or counted as new',
                    sources={**reference['sources'],str(Path(__file__).relative_to(ROOT)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    if (folder/'protocol.json').exists() and read_json(folder/'protocol.json')!=protocol:raise ValueError('Frozen protocol differs')
    atomic_json(folder/'protocol.json',protocol)
    for relative,expected in protocol['sources'].items():
        source=ROOT/relative
        assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
        target=folder/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
    jobs=[(name,seed,'cache',40,str(folder),None) for name in protocol['instances'] for seed in protocol['seeds']]
    cpus=psutil.Process().cpu_affinity()[::2][:6]
    with mp.get_context('spawn').Pool(len(cpus),initializer=initialize,initargs=(cpus,)) as pool:
        for result in pool.imap_unordered(execute,jobs):print(json.dumps(result),flush=True)
