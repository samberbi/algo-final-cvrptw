"""Personal ALNS: adaptive pair selection, SA and bounded local search."""
from dataclasses import dataclass, asdict
import math
import random
import time
from algo.model import Objective, score, better, energy
from .insertion import construct, repair
from .operators import destroy
from .local import improve
from algo.verify import verify


@dataclass(frozen=True)
class Settings:
    objective: Objective = Objective.DURATION
    iterations: int = 500
    time_limit: float | None = 5.
    construction: str = 'regret2'
    attempts: int = 3
    destructions: tuple = ('random','r1','worst','route')
    repairs: tuple = ('greedy','regret2','regret3')
    fraction: float = .2
    related_weights: tuple = (.4,.2,.2,.2)
    adaptation: bool = True
    rho: float = .1
    exploration: float = .1
    annealing: bool = True
    initial_acceptance: float = .5
    initial_degradation: float = .02
    final_temperature_ratio: float = .01
    local_search: bool = True
    local_evaluations: int = 80
    local_moves: tuple = ('relocate','swap','2opt','2opt_star')
    candidate_limit: int | None = 16

    def __post_init__(self):
        object.__setattr__(self, 'objective', Objective(self.objective))
        if self.iterations < 0 or self.attempts < 1 or not 0 < self.fraction <= 1:
            raise ValueError('invalid iterations, attempts, fraction')
        if self.time_limit is not None and (not math.isfinite(self.time_limit) or self.time_limit <= 0):
            raise ValueError('time limit must be finite and positive')
        if not 0 <= self.rho <= 1 or not 0 <= self.exploration <= 1:
            raise ValueError('rho/exploration must be in [0,1]')
        if not 0 < self.initial_acceptance < 1 or not 0 < self.final_temperature_ratio <= 1 or self.initial_degradation <= 0:
            raise ValueError('invalid temperature configuration')
        if not self.destructions or not self.repairs or not self.local_moves:
            raise ValueError('operator lists must be nonempty')
        if not set(self.destructions) <= {'random','r0','r1','r2','worst','route'}:
            raise ValueError('unknown destruction')
        if not set(self.repairs) <= {'greedy','regret2','regret3'}:
            raise ValueError('unknown repair')
        if self.construction not in {'greedy','edd','random','regret2','regret3'}:
            raise ValueError('unknown construction')
        if not set(self.local_moves) <= {'relocate','swap','2opt','2opt_star'}:
            raise ValueError('unknown local move')
        if self.candidate_limit is not None and (not isinstance(self.candidate_limit,int) or self.candidate_limit<1):
            raise ValueError('candidate limit must be a positive integer or None')


def solve(ins, settings=None, seed=0, initial=None):
    cfg = settings or Settings()
    started = time.perf_counter()
    deadline = started + cfg.time_limit if cfg.time_limit is not None else math.inf
    result = dict(status='not_found', routes=None, seed=seed, settings=asdict(cfg),
                  trace=[], operators={}, construction={}, objective=cfg.objective.value)
    impossible = ins.proven_impossible()
    if impossible:
        result.update(status='proven_infeasible', reason=impossible, runtime_s=time.perf_counter()-started)
        return result
    rng = random.Random(seed)
    if initial is None:
        # Reserve time for search; a construction timeout is not infeasibility.
        construction_deadline = min(deadline, started + cfg.time_limit * .45) if cfg.time_limit else deadline
        initial, info = construct(ins, cfg.objective, rng, cfg.construction, cfg.attempts,
                                  construction_deadline, cfg.candidate_limit)
        result['construction'] = info
    if initial is None:
        result.update(reason='construction failed or budget exhausted',runtime_s=time.perf_counter()-started)
        return result
    check = verify(initial, ins)
    if not check['valid']:
        raise ValueError(f'invalid initial solution: {check["errors"]}')
    current = [list(r) for r in initial if r]
    best = [r[:] for r in current]
    current_cost = best_cost = score(best, ins, cfg.objective)
    result['initial_score'] = best_cost
    pairs = [(d,r) for d in cfg.destructions for r in cfg.repairs]
    weights = {p:1. for p in pairs}
    counts = {p:dict(selected=0,accepted=0,improved=0,failed=0) for p in pairs}
    # For lexicographic mode calibrate within-fleet distance exploration.
    scale = best_cost[1] if cfg.objective == Objective.LEX else best_cost
    t0 = max(1e-12, -cfg.initial_degradation * max(scale,1.) / math.log(cfg.initial_acceptance))
    search_start = time.perf_counter()
    def log(step, temperature, operator='', accepted=False):
        result['trace'].append(dict(iteration=step,elapsed_s=time.perf_counter()-started,
             best=best_cost,current=current_cost,temperature=temperature,operator=operator,
             accepted=accepted,weights={f'{d}/{r}':w for (d,r),w in weights.items()}))
    log(0,t0)
    for step in range(cfg.iterations):
        if time.perf_counter() >= deadline:
            break
        if rng.random() < cfg.exploration:
            pair = rng.choice(pairs)
        else:
            pair = rng.choices(pairs,weights=[weights[p] for p in pairs],k=1)[0]
        counts[pair]['selected'] += 1
        progress = step / max(1,cfg.iterations-1)
        if cfg.time_limit:
            progress = max(progress,(time.perf_counter()-search_start)/max(deadline-search_start,1e-12))
        temperature = t0 * cfg.final_temperature_ratio ** min(1.,progress)
        partial, removed = destroy(current,ins,rng,pair[0],cfg.fraction,cfg.related_weights,cfg.objective)
        candidate = repair(partial,removed,ins,cfg.objective,rng,pair[1],deadline,cfg.candidate_limit)
        reward, accepted = .05, False
        if candidate is not None:
            if cfg.local_search:
                candidate,_ = improve(candidate,ins,cfg.objective,rng,cfg.local_moves,cfg.local_evaluations,deadline)
            value = score(candidate,ins,cfg.objective)
            delta = energy(value,ins,cfg.objective)-energy(current_cost,ins,cfg.objective)
            accepted = delta <= 0 or (cfg.annealing and rng.random() < math.exp(-min(745.,delta/max(temperature,1e-12))))
            if accepted:
                reward = 1. if better(value,current_cost) else .2
                current, current_cost = candidate, value
                counts[pair]['accepted'] += 1
            if better(value,best_cost):
                best,best_cost = [r[:] for r in candidate],value
                reward = 5.
                counts[pair]['improved'] += 1
        else:
            counts[pair]['failed'] += 1
        if cfg.adaptation:
            weights[pair] = (1-cfg.rho)*weights[pair]+cfg.rho*reward
        log(step+1,temperature,'/'.join(pair),accepted)
    check = verify(best,ins)
    if not check['valid']:
        raise AssertionError(check['errors'])
    result.update(status='feasible',routes=best,score=best_cost,metrics=check,
                  runtime_s=time.perf_counter()-started,
                  operators={'/'.join(p):dict(**counts[p],weight=weights[p]) for p in pairs})
    return result
