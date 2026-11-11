"""Profile a short solve separately from the published timed experiments."""
import os
for key in ['OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:
    os.environ[key]='1'
from pathlib import Path
import cProfile
import io
import json
import pstats
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import psutil
from algo.data import load
from algo.solver import solve,warmup,production_settings

if __name__=='__main__':
    available=psutil.Process().cpu_affinity()
    psutil.Process().cpu_affinity([available[-2]])
    warmup()
    ins=load(ROOT/'data/instances/R1_10_1.vrp')
    initial=json.loads((ROOT/'results/revision_ils/initials/0520.json').read_text()) if (ROOT/'results/revision_ils/initials/0520.json').exists() else None
    if initial is None or initial['job']['instance']!='R1_10_1':
        initial=next(json.loads(p.read_text()) for p in (ROOT/'results/revision_ils/initials').glob('*.json') if json.loads(p.read_text())['job']['instance']=='R1_10_1')
    profiler=cProfile.Profile()
    result=profiler.runcall(solve,ins,production_settings('ils',seconds=3.,seed=101),initial['routes'])
    out=ROOT/'results/optimization_v2'
    profiler.dump_stats(out/'profile.pstats')
    stream=io.StringIO();pstats.Stats(profiler,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(20)
    (out/'profile.txt').write_text('Diagnostic only: profiling overhead; not a new benchmark quality result.\n'+stream.getvalue(),encoding='utf-8')
    print(stream.getvalue())
