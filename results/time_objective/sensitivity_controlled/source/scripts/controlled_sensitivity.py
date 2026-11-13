"""Étude OFAT en durée : un seul réglage diffère de la configuration témoin.

Les constructions et préfixes ILS communs sont réellement calculés une fois,
réutilisés à l'identique et facturés dans chaque profil. Les temps totaux sont
des sommes de phases mesurées, pas des chronométrages continus indépendants.
"""
import os
for variable in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):
    os.environ[variable]='1'

from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import platform
import random
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import psutil
from algo.data import load,reference
from algo.duration import construct,search,warmup
from algo.hgs_tuning import solve as hgs
from algo.verify import verify

INSTANCES=['C103','R203','RC103','C2_10_10','R1_10_5','RC2_10_5']
SEEDS=[8301,8302,8303]
CONFIGS={
    'baseline':dict(tolerance=.005,neighbors=40),
    'tolerance_0':dict(tolerance=0.,neighbors=40),
    'tolerance_002':dict(tolerance=.02,neighbors=40),
    'neighbors_80':dict(tolerance=.005,neighbors=80),
    'neighbors_120':dict(tolerance=.005,neighbors=120),
}


def write(path,record):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record,indent=2,allow_nan=False),encoding='utf-8')
    temporary.replace(path)


def digest(routes):
    return hashlib.sha256(json.dumps(routes,separators=(',',':')).encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',default='sensitivity_controlled')
    parser.add_argument('--seconds',type=float,default=4.)
    args=parser.parse_args()
    if args.seconds<=0 or not args.label.replace('_','').isalnum():
        parser.error('Positive budget and simple campaign label required')
    output=ROOT/'results/time_objective'/args.label
    for name in INSTANCES:
        assert (ROOT/'data/instances'/(name+'.vrp')).exists(),name
    process=psutil.Process()
    core=process.cpu_affinity()[0]
    process.cpu_affinity([core])
    jobs=[(name,seed,config) for name in INSTANCES for seed in SEEDS for config in CONFIGS]
    random.Random(20261113).shuffle(jobs)
    hashes={}
    for path in [*sorted((ROOT/'algo').glob('*.py')),Path(__file__)]:
        relative=path.relative_to(ROOT)
        frozen=output/'source'/relative
        frozen.parent.mkdir(parents=True,exist_ok=True)
        if frozen.exists():assert frozen.read_bytes()==path.read_bytes(),relative
        else:frozen.write_bytes(path.read_bytes())
        hashes[relative.as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    protocol=dict(objective='sum_route_duration',departures=0,instances=INSTANCES,seeds=SEEDS,
        configurations=CONFIGS,search_seconds=args.seconds,ils_seconds=args.seconds/2,hgs_seconds=args.seconds/2,
        jobs=jobs,source_hashes=hashes,cpu_affinity=[core],workers=1,
        initial_attempts=12,common_initials=True,common_ils_prefixes_for_neighbor_factor=True,
        total_time_kind='Sum of actually measured construction, ILS, HGS and verification phases; shared phases charged in each profile',
        scope='Exploratory controlled parameter study, distinct from old benchmarks and best-solution archive',
        versions={name:importlib.metadata.version(name) for name in ['pyvrp','numpy','numba','scipy']},
        python=platform.python_version(),platform=platform.platform())
    protocol_path=output/'protocol.json'
    if protocol_path.exists():assert json.loads(protocol_path.read_text())==json.loads(json.dumps(protocol))
    else:write(protocol_path,protocol)
    # Préchauffage exclu des mesures, identique pour toutes les configurations.
    start=time.perf_counter()
    warmup()
    warm=load(ROOT/'data/instances/C101.vrp')
    initial,_=construct(warm,0,1)
    hgs(warm,.03,0,initial,40,objective='duration')
    write(output/'warmup.json',dict(seconds=time.perf_counter()-start,excluded=True))
    cache={}
    print(f'{len(jobs)} profils ; {len(INSTANCES)} instances ; 3 graines ; 5 configurations OFAT.',flush=True)
    for index,(name,seed,config) in enumerate(jobs,1):
        target=output/'runs'/f'{name}_{seed}_{config}.json'
        if target.exists():
            record=json.loads(target.read_text())
        else:
            started=time.perf_counter()
            parameters=CONFIGS[config]
            record=dict(instance=name,seed=seed,configuration=config,parameters=parameters,
                        objective='sum_route_duration',complete=True,valid=False)
            try:
                if name not in cache:cache[name]=load(ROOT/'data/instances'/(name+'.vrp'))
                ins=cache[name]
                initial_path=output/'initials'/f'{name}_{seed}.json'
                reused_initial=initial_path.exists()
                if reused_initial:initial_record=json.loads(initial_path.read_text())
                else:
                    initial,info=construct(ins,seed,12)
                    if initial is None:raise RuntimeError('Initial construction failed')
                    initial_record=dict(routes=initial,info=info,sha256=digest(initial))
                    write(initial_path,initial_record)
                initial=initial_record['routes']
                assert verify(initial,ins)['valid'] and digest(initial)==initial_record['sha256']
                tolerance=parameters['tolerance']
                prefix_path=output/'prefixes'/f'{name}_{seed}_{tolerance:g}.json'
                reused_prefix=prefix_path.exists()
                if reused_prefix:prefix=json.loads(prefix_path.read_text())
                else:
                    prefix=search(ins,initial,args.seconds/2,seed,'ils',tolerance)
                    write(prefix_path,prefix)
                assert verify(prefix['routes'],ins)['valid']
                result=hgs(ins,args.seconds/2,seed+10000,prefix['routes'],parameters['neighbors'],objective='duration')
                verify_start=time.perf_counter()
                checked=verify(result['routes'],ins)
                verification_s=time.perf_counter()-verify_start
                assert checked['valid'] and abs(checked['duration']/10-result['cost'])<1e-7
                assert checked['duration']<=prefix['metrics']['duration']+1e-7
                # Le témoin est lu après la résolution ; il ne pilote pas la recherche.
                refs,_=reference(ROOT/'data/instances'/(name+'.sol'))
                reference_check=verify(refs,ins)
                assert reference_check['valid']
                total=initial_record['info']['seconds']+prefix['runtime_s']+result['runtime_s']+verification_s
                record.update(n=ins.n,valid=True,duration=checked['duration']/10,
                    delta_reference_pct=100*(checked['duration']/reference_check['duration']-1),
                    reference_duration=reference_check['duration']/10,
                    travel=checked['travel']/10,waiting=checked['waiting']/10,service=float(ins.service.sum()/10),
                    vehicles=checked['vehicles'],construction_s=initial_record['info']['seconds'],
                    own_ils_s=prefix['runtime_s'],external_hgs_s=result['runtime_s'],verification_s=verification_s,
                    recomposed_total_s=total,this_job_wall_s=time.perf_counter()-started,
                    reused_initial=reused_initial,reused_prefix=reused_prefix,
                    initial_source=initial_path.relative_to(ROOT).as_posix(),
                    prefix_source=prefix_path.relative_to(ROOT).as_posix(),
                    initial_sha256=initial_record['sha256'],prefix_sha256=digest(prefix['routes']),
                    own_ils_duration=prefix['cost'],result=result,
                    attribution='Own regret construction and ILS; external PyVRP HGS including its local search; no route pool')
            except Exception:
                record.update(error=traceback.format_exc(),this_job_wall_s=time.perf_counter()-started)
            write(target,record)
        print(dict(index=index,instance=name,seed=seed,configuration=config,valid=record['valid'],
                   duration=record.get('duration'),delta=record.get('delta_reference_pct')),flush=True)


if __name__=='__main__':main()
