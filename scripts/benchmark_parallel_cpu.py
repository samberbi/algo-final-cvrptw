"""Même portefeuille de départs sur 1, 2 et 4 processus, CPU Windows exact.

Les handles des seuls workers créés ici restent ouverts jusqu'après leur arrêt.
GetProcessTimes inclut alors tout leur CPU, y compris imports, initialisation
et fermeture. Aucun processus utilisateur externe n'est modifié.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):
    os.environ[key]='1'
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import ctypes
from ctypes import wintypes
import json
import multiprocessing as mp
import random
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import psutil
from algo.data import load,reference
from algo.duration_refine import solve
from algo.verify import verify

FOLDER=ROOT/'results/time_objective/cpu_optimization/parallel'
CASES=['C1_10_6','R1_10_5','RC2_10_5']
SEEDS=[9301,9302,9303,9304]
_instances={}


def init_worker(cpus,barrier,folder):
    identity=mp.current_process()._identity[0]
    cpu=cpus[(identity-1)%len(cpus)]
    psutil.Process().cpu_affinity([cpu])
    wall=time.perf_counter();consumed=time.process_time()
    from scripts.benchmark_cpu_efficiency import warmup
    warmup()
    record=dict(pid=os.getpid(),cpu=cpu,init_wall_s=time.perf_counter()-wall,
                init_cpu_s=time.process_time()-consumed)
    (Path(folder)/f'worker_{os.getpid()}.json').write_text(json.dumps(record),encoding='utf-8')
    barrier.wait(timeout=180)


def ready():
    return os.getpid()


def task(name,seed):
    if name not in _instances:_instances[name]=load(ROOT/'data/instances'/(name+'.vrp'))
    ins=_instances[name]
    wall=time.perf_counter();cpu=time.process_time()
    result=solve(ins,seed,seconds=60,restarts=4)
    checked=verify(result['routes'],ins)
    assert checked['valid']
    return dict(instance=name,seed=seed,pid=os.getpid(),duration=checked['duration']/10,
                task_wall_s=time.perf_counter()-wall,task_cpu_s=time.process_time()-cpu,
                valid=True,result=result)


class CpuHandle:
    """Mesure le CPU utilisateur + noyau, même après la fin du processus."""
    def __init__(self,pid):
        self.api=ctypes.WinDLL('kernel32',use_last_error=True)
        self.api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        self.api.OpenProcess.restype=wintypes.HANDLE
        self.api.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
        self.api.GetProcessTimes.restype=wintypes.BOOL
        self.api.CloseHandle.argtypes=[wintypes.HANDLE]
        self.handle=self.api.OpenProcess(0x1000,False,pid)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())

    def seconds(self):
        creation,exit_time,kernel,user=[wintypes.FILETIME() for _ in range(4)]
        if not self.api.GetProcessTimes(self.handle,ctypes.byref(creation),ctypes.byref(exit_time),
                                        ctypes.byref(kernel),ctypes.byref(user)):
            raise ctypes.WinError(ctypes.get_last_error())
        def value(t):return ((t.dwHighDateTime<<32)+t.dwLowDateTime)/1e7
        return value(kernel)+value(user)

    def close(self):
        if self.handle:self.api.CloseHandle(self.handle);self.handle=None


def one_batch(workers,repetition,cpus):
    output=FOLDER/f'workers{workers}_rep{repetition}'
    output.mkdir(parents=True,exist_ok=True)
    if (output/'batch.json').exists():return json.loads((output/'batch.json').read_text())
    assert not list(output.glob('worker_*.json')),'Partial batch exists; use a new output folder'
    context=mp.get_context('spawn')
    barrier=context.Barrier(workers)
    batch_wall=time.perf_counter();parent_cpu=time.process_time()
    executor=ProcessPoolExecutor(max_workers=workers,mp_context=context,initializer=init_worker,
                                 initargs=(cpus[:workers],barrier,str(output)))
    handles=[];cases=[]
    try:
        futures=[executor.submit(ready) for _ in range(workers)]
        for future in futures:future.result(timeout=240)
        initializers=[json.loads(p.read_text()) for p in output.glob('worker_*.json')]
        assert len(initializers)==workers
        handles=[CpuHandle(r['pid']) for r in initializers]
        startup_wall=time.perf_counter()-batch_wall
        order=CASES.copy();random.Random(20261113+repetition).shuffle(order)
        for name in order:
            wall=time.perf_counter();cpu_before=time.process_time()
            child_before=sum(h.seconds() for h in handles)
            futures=[executor.submit(task,name,seed) for seed in SEEDS]
            results=[f.result(timeout=180) for f in futures]
            ins=load(ROOT/'data/instances'/(name+'.vrp'))
            for r in results:assert verify(r['result']['routes'],ins)['valid']
            elapsed=time.perf_counter()-wall
            parent_spent=time.process_time()-cpu_before
            child_spent=sum(h.seconds() for h in handles)-child_before
            best=min(results,key=lambda r:r['duration'])
            refs,_=reference(ROOT/'data/instances'/(name+'.sol'))
            ref=verify(refs,ins);assert ref['valid']
            record=dict(instance=name,workers=workers,repetition=repetition,
                same_start_seeds=SEEDS,wall_s=elapsed,cpu_total_s=parent_spent+child_spent,
                parent_cpu_s=parent_spent,workers_cpu_s=child_spent,
                best_duration=best['duration'],delta_reference_pct=100*(best['duration']/(ref['duration']/10)-1),
                all_feasible=True,results=results)
            (output/(name+'.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
            cases.append({k:v for k,v in record.items() if k!='results'})
            print(cases[-1],flush=True)
        executor.shutdown(wait=True)
        lifetime_children=sum(h.seconds() for h in handles)
        record=dict(workers=workers,repetition=repetition,startup_wall_s=startup_wall,
            total_wall_s=time.perf_counter()-batch_wall,
            total_cpu_s=time.process_time()-parent_cpu+lifetime_children,
            workers_lifetime_cpu_s=lifetime_children,parent_cpu_s=time.process_time()-parent_cpu,
            cases=cases,initializers=initializers,
            cpu_scope='Exact Windows user+kernel lifetime of every worker + parent CPU; includes worker startup/warmup/shutdown')
        (output/'batch.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        return record
    finally:
        executor.shutdown(wait=True)
        for handle in handles:handle.close()


def main():
    if sys.platform!='win32':raise RuntimeError('This exact child CPU measurement is implemented for Windows')
    cpus=psutil.Process().cpu_affinity()[::2][:4]
    if len(cpus)<4:cpus=psutil.Process().cpu_affinity()[:4]
    assert len(cpus)==4,'Four permitted logical processors required'
    FOLDER.mkdir(parents=True,exist_ok=True)
    protocol=dict(cases=CASES,seeds=SEEDS,workers=[1,2,4],repetitions=2,restarts_per_task=4,
        safety_wall_s=60,work='Four independent starts per instance; same seeds and work on every worker count',
        context='spawn',permitted_cpu_ids=cpus,threads_per_process_environment=1,
        cpu_measure='Windows GetProcessTimes user+kernel, retained process handles; parent process_time',
        task_quality='best feasible duration among the same four starts',
        warm_measure='per-instance tables exclude pool startup; batch tables include complete worker startup and shutdown')
    path=FOLDER/'protocol.json'
    if path.exists():assert json.loads(path.read_text())==protocol
    else:path.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    for repetition,order in [(1,[1,4,2]),(2,[2,4,1])]:
        for workers in order:one_batch(workers,repetition,cpus)


if __name__=='__main__':main()
