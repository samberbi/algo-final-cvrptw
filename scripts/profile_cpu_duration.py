"""Profilage local et mesuré du profil renforcé avant optimisation CPU."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):
    os.environ[key]='1'
from pathlib import Path
import cProfile,io,json,pstats,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from algo.data import load
from algo.duration_refine import solve
from algo.iterated import arrays
from algo.savings import savings_construct
from algo.sequential import sequential_insert


def main():
    folder=ROOT/'results/time_objective/cpu_optimization'
    (folder/'source_before/algo').mkdir(parents=True,exist_ok=True)
    for name in ['duration_refine','route_pool','savings','sequential','verify']:
        source=ROOT/'algo'/(name+'.py')
        target=folder/'source_before/algo'/source.name
        if target.exists():assert target.read_bytes()==source.read_bytes()
        else:target.write_bytes(source.read_bytes())
    warm=load(ROOT/'data/instances/C101.vrp')
    savings_construct(*arrays(warm),warm.vehicles,0,0.)
    sequential_insert(*arrays(warm),warm.vehicles,0,1.,.5,0)
    ins=load(ROOT/'data/instances/C1_10_6.vrp')
    profiler=cProfile.Profile()
    wall=time.perf_counter();cpu=time.process_time()
    profiler.enable()
    result=solve(ins,4101,seconds=60,restarts=4)
    profiler.disable()
    elapsed=time.perf_counter()-wall;consumed=time.process_time()-cpu
    profiler.dump_stats(str(folder/'before.prof'))
    stream=io.StringIO()
    pstats.Stats(profiler,stream=stream).strip_dirs().sort_stats('cumtime').print_stats(35)
    (folder/'PROFIL_AVANT.txt').write_text(stream.getvalue(),encoding='utf-8')
    (folder/'profiling_before.json').write_text(json.dumps(dict(instance=ins.name,seed=4101,
        wall_s=elapsed,cpu_s=consumed,result=result,scope='Instrumented profiling; not an unbiased runtime benchmark'),indent=2),encoding='utf-8')
    print(stream.getvalue())
    print(dict(wall_s=elapsed,cpu_s=consumed,duration=result.get('cost')))


if __name__=='__main__':main()
