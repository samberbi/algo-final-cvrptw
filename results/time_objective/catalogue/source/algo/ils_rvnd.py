"""ILS with feasible shaking, RVND and overlapping groups of complete routes.

No customer is left unassigned during the improvement phase. Capacity, hard
service-start windows and depot return are preserved by every accepted move.
"""

from dataclasses import dataclass, asdict
import math
import random
import time
import numpy as np
from .iterated import arrays, build_neighbors, construct, encode, decode
from .optimized import select_group
from .model import Instance
from .direct import walk
from .rvnd import descend
from .verify import verify


@dataclass(frozen=True)
class Settings:
    seconds: float = 40.0
    seed: int = 0
    adaptive: bool = True
    blocks: bool = True
    group_size: int = 240
    sub_seconds: float = 0.2
    tolerance: float = 0.005
    max_cycles: int = 1000000000

    def __post_init__(self):
        if not math.isfinite(self.seconds) or self.seconds <= 0:
            raise ValueError("Positive finite time required")
        if (
            self.group_size < 10
            or not math.isfinite(self.sub_seconds)
            or self.sub_seconds <= 0
        ):
            raise ValueError("Invalid group budget")
        if (
            not math.isfinite(self.tolerance)
            or not 0 <= self.tolerance <= 0.05
            or self.max_cycles < 0
        ):
            raise ValueError("Invalid search limits")


def solve(ins, settings=None, initial=None):
    cfg = settings or Settings()
    started = time.perf_counter()
    cpu_started = time.process_time()
    deadline = started + cfg.seconds
    construction_s = 0.0
    if initial is None:
        initial, info = construct(ins, cfg.seed, 12)
        construction_s = info["seconds"]
    if initial is None:
        return dict(
            status="not_found", routes=None, runtime_s=time.perf_counter() - started
        )
    checked = verify(initial, ins)
    if not checked["valid"]:
        raise ValueError("Invalid initial solution")
    current_routes = [list(route) for route in initial if route]
    best_routes = [route[:] for route in current_routes]
    initial_cost = current_cost = best_cost = checked["distance"] / 10
    rng = random.Random(cfg.seed)
    cycles = stale = improved = accepted = rejected = 0
    moves = evaluations = 0
    trace = [dict(elapsed_s=0.0, best=best_cost, current=current_cost)]
    while current_routes and cycles < cfg.max_cycles and time.perf_counter() < deadline:
        level = min(4, stale // 20) if cfg.adaptive else 0
        target = max(120, min(360, 8 * math.ceil(ins.n / len(current_routes))))
        selected = (
            select_group(ins, current_routes, rng, target)
            if ins.n > cfg.group_size
            else list(range(len(current_routes)))
        )
        selected_set = set(selected)
        mapping = [0] + [c for r in selected for c in current_routes[r]]
        reverse = {c: index for index, c in enumerate(mapping)}
        ids = np.asarray(mapping)
        fleet = min(
            ins.vehicles - len(current_routes) + len(selected),
            len(selected) + 3,
            len(mapping) - 1,
        )
        group = Instance(
            "group",
            ins.xy[ids],
            ins.demand[ids],
            ins.service[ids],
            ins.early[ids],
            ins.late[ids],
            ins.travel[np.ix_(ids, ids)],
            ins.capacity,
            fleet,
            ins.horizon,
            ins.distance[np.ix_(ids, ids)],
        )
        routes = [[reverse[c] for c in current_routes[r]] for r in selected]
        work, lengths = encode(routes, group)
        args = arrays(group)
        neighbors = build_neighbors(group, min(64, 24 + 8 * level))
        local_deadline = min(deadline, time.perf_counter() + cfg.sub_seconds)
        diagnostics = np.zeros(7, np.int64)
        # Change a complete feasible assignment through direct atomic movements.
        for _ in range(2 + 2 * level):
            if time.perf_counter() >= local_deadline:
                break
            walk(
                work,
                lengths,
                len(lengths) - 1,
                *args,
                neighbors,
                64,
                rng.randrange(2**31),
                1.0,
                0,
                diagnostics
            )
        count, tested = descend(
            work,
            lengths,
            args,
            neighbors,
            rng,
            local_deadline,
            max_moves=15,
            blocks=cfg.blocks,
        )
        moves += count
        evaluations += tested
        candidate = [
            r[:] for index, r in enumerate(current_routes) if index not in selected_set
        ]
        candidate += [[mapping[c] for c in route] for route in decode(work, lengths)]
        checked = verify(candidate, ins)
        if not checked["valid"]:
            raise AssertionError(checked)
        value = checked["distance"] / 10
        # Preserve an independent best archive while allowing controlled detours.
        allowance = cfg.tolerance * (1 + level / 2)
        if value <= best_cost * (1 + allowance) + 1e-8:
            current_routes, current_cost = candidate, value
            accepted += 1
        else:
            rejected += 1
        if value < best_cost - 1e-8:
            best_routes = [route[:] for route in candidate]
            best_cost = value
            stale = 0
            improved += 1
        else:
            stale += 1
        if stale and stale % 100 == 0:
            current_routes = [route[:] for route in best_routes]
            current_cost = best_cost
        cycles += 1
        trace.append(
            dict(
                elapsed_s=time.perf_counter() - started,
                best=best_cost,
                current=current_cost,
                level=level,
                group_n=group.n,
                accepted=accepted,
            )
        )
    checked = verify(best_routes, ins)
    if not checked["valid"] or abs(checked["distance"] / 10 - best_cost) > 1e-7:
        raise AssertionError(checked)
    return dict(
        status="feasible",
        engine="ils-rvnd-v5",
        method="ils_rvnd",
        routes=best_routes,
        cost=best_cost,
        initial_cost=initial_cost,
        vehicles=checked["vehicles"],
        metrics=checked,
        settings=asdict(cfg),
        trace=trace,
        runtime_s=time.perf_counter() - started,
        cpu_s=time.process_time() - cpu_started,
        construction_s=construction_s,
        cycles=cycles,
        improved=improved,
        accepted=accepted,
        rejected=rejected,
        local_moves=moves,
        local_evaluations=evaluations,
    )


def warmup():
    from .optimized import warmup as base_warmup

    elapsed = base_warmup()
    xy = np.array([[0, 0], [1, 0], [0, 10], [2, 0], [0, 11]], float)
    d = np.floor(10 * np.linalg.norm(xy[:, None] - xy[None, :], axis=2))
    ins = Instance(
        "warmup",
        xy,
        np.array([0, 1, 1, 1, 1]),
        np.zeros(5),
        np.zeros(5),
        np.full(5, 1000),
        d,
        3,
        3,
        1000,
    )
    solve(ins, Settings(seconds=1, max_cycles=1), [[1, 2], [3, 4]])
    return elapsed
