"""Optional hard-case hybrid: short own ILS, then attributed external HGS."""
from dataclasses import asdict,dataclass
import math,time
from .iterated import construct
from .optimized import solve as ils
from .profiles import production_settings
from .hgs_tuning import solve as hgs
from .verify import verify


@dataclass(frozen=True)
class Settings:
    search_seconds:float=120.
    ils_seconds:float=20.
    neighbor_count:int=40
    seed:int=0

    def __post_init__(self):
        if any(not math.isfinite(x) or x<=0 for x in [self.search_seconds,self.ils_seconds]):
            raise ValueError('Positive finite times required')
        if type(self.neighbor_count) is not int or self.neighbor_count<1:
            raise ValueError('Positive integer neighbourhood required')


def solve(ins,settings=None,initial=None):
    cfg=settings or Settings();started=time.perf_counter();construction_s=0.
    if initial is None:
        initial,info=construct(ins,cfg.seed,12);construction_s=info['seconds']
    if initial is None:
        return dict(status='not_found',routes=None,runtime_s=time.perf_counter()-started,reason='Construction failed')
    checked=verify(initial,ins)
    if not checked['valid']:raise ValueError('Invalid initial solution')
    first_seconds=min(cfg.ils_seconds,cfg.search_seconds/2)
    first=ils(ins,production_settings('ils',seconds=first_seconds,seed=cfg.seed),initial)
    second=hgs(ins,cfg.search_seconds-first_seconds,cfg.seed+10000,first['routes'],cfg.neighbor_count)
    final=verify(second['routes'],ins)
    assert final['valid'] and second['cost']<=first['cost']+1e-7
    elapsed=time.perf_counter()-started
    trace=[dict(elapsed_s=0.,best=checked['distance']/10,phase='construction')]
    trace.extend(dict(elapsed_s=construction_s+p['elapsed_s'],best=p['best'],phase='our-ils') for p in first.get('trace',[]))
    trace.extend(dict(elapsed_s=construction_s+first['runtime_s']+p['elapsed_s'],best=p['best'],phase=p['phase']) for p in second['trace'])
    trace.append(dict(elapsed_s=elapsed,best=second['cost'],phase='final-verified'))
    return dict(status='feasible',engine='our-short-ils-then-external-hgs-v9',
        attribution='Our ILS and integration; external PyVRP HGS, not by us',
        settings=asdict(cfg),actual_ils_seconds=first_seconds,actual_hgs_seconds=cfg.search_seconds-first_seconds,
        search_budget_s=cfg.search_seconds,routes=second['routes'],cost=final['distance']/10,
        metrics=final,vehicles=final['vehicles'],components=[first,second],trace=trace,
        initial_cost=checked['distance']/10,runtime_s=elapsed,construction_s=construction_s,
        accounting='Two search shares, plus actual construction and preparation; compilation excluded by caller')
