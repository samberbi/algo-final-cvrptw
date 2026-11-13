"""PyVRP seul : population native, sans initialisation par notre constructeur."""
import math
import time
import numpy as np
from .verify import verify


def solve(ins, seconds=5., seed=4101):
    import pyvrp
    from pyvrp.stop import MaxRuntime
    if not math.isfinite(seconds) or seconds<=0:raise ValueError('Budget positif requis')
    arrays=[ins.travel,ins.distance,ins.demand,ins.service,ins.early,ins.late]
    if any(not np.array_equal(a,np.rint(a)) for a in arrays):
        raise ValueError('Représentation entière exacte requise')
    if ins.capacity!=int(ins.capacity) or ins.horizon!=int(ins.horizon):
        raise ValueError('Capacité et horizon entiers requis')
    if ins.proven_impossible():
        return dict(status='proven_infeasible',routes=None,reason=ins.proven_impossible())
    started=time.perf_counter()
    clients=[pyvrp.Client(float(ins.xy[i,0]),float(ins.xy[i,1]),
        delivery=[int(ins.demand[i])],service_duration=int(ins.service[i]),
        tw_early=int(ins.early[i]),tw_late=int(ins.late[i])) for i in range(1,ins.n+1)]
    data=pyvrp.ProblemData(clients,[pyvrp.Depot(float(ins.xy[0,0]),float(ins.xy[0,1]),
        tw_early=0,tw_late=int(ins.horizon))],[pyvrp.VehicleType(num_available=ins.vehicles,
        capacity=[int(ins.capacity)],tw_early=0,tw_late=int(ins.horizon),start_late=0,
        unit_distance_cost=0,unit_duration_cost=1,fixed_cost=0)],
        [ins.distance.astype(np.int64)],[ins.travel.astype(np.int64)])
    setup=time.perf_counter()-started
    output=pyvrp.solve(data,MaxRuntime(seconds),seed=seed,collect_stats=True,display=False)
    result=dict(status='not_found',routes=None,setup_s=setup,runtime_s=time.perf_counter()-started,
        attribution='External PyVRP 0.12.2 HGS, native population and local search; own duration adapter',
        objective='duration',search_budget_s=seconds)
    if not output.is_feasible():return result
    routes=[list(map(int,r.visits())) for r in output.best.routes()]
    metrics=verify(routes,ins)
    assert metrics['valid'] and all(r.start_time()==0 for r in output.best.routes())
    assert abs(sum(r.duration() for r in output.best.routes())-metrics['duration'])<1e-7
    result.update(status='feasible',routes=routes,cost=metrics['duration']/10,metrics=metrics)
    return result
