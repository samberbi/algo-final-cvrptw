"""Immutable validated data. Distances and travel times may differ."""
from dataclasses import dataclass, field
from enum import Enum
import math
import numpy as np

EPS = 1e-8


class Objective(str, Enum):
    DURATION = "duration"
    DISTANCE = "distance"
    LEX = "vehicles_then_distance"


@dataclass(frozen=True)
class Instance:
    name: str
    xy: np.ndarray
    demand: np.ndarray
    service: np.ndarray
    early: np.ndarray
    late: np.ndarray
    travel: np.ndarray
    capacity: float
    vehicles: int
    horizon: float
    distance: np.ndarray | None = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.vehicles, (int, np.integer)) or self.vehicles < 0:
            raise ValueError("vehicles must be a nonnegative integer")
        if not math.isfinite(self.capacity) or self.capacity <= 0:
            raise ValueError("capacity must be finite and positive")
        if not math.isfinite(self.horizon) or self.horizon <= 0:
            raise ValueError("horizon must be finite and positive")
        for name in ("xy", "demand", "service", "early", "late", "travel"):
            a = np.array(getattr(self, name), dtype=float, copy=True)
            if not np.isfinite(a).all():
                raise ValueError(f"{name}: nonfinite data")
            a.setflags(write=False)
            object.__setattr__(self, name, a)
        if self.demand.ndim != 1:
            raise ValueError('demand must be a vector')
        size = len(self.demand)
        if size < 1 or self.xy.shape != (size, 2):
            raise ValueError("xy must have shape (clients + depot, 2)")
        for name in ("demand", "service", "early", "late"):
            a = getattr(self, name)
            if a.shape != (size,) or (a < 0).any():
                raise ValueError(f"{name}: invalid shape or negative value")
        if (self.early > self.late).any() or (self.late > self.horizon + EPS).any():
            raise ValueError("invalid time windows")
        if self.demand[0] != 0 or self.service[0] != 0 or self.early[0] != 0:
            raise ValueError("depot demand/service/opening must equal zero; shift time origin first")
        if abs(self.late[0] - self.horizon) > EPS:
            raise ValueError("depot closing must equal horizon")
        dist = self.travel if self.distance is None else self.distance
        dist = np.array(dist, dtype=float, copy=True)
        for name, a in (("travel", self.travel), ("distance", dist)):
            if a.shape != (size, size) or not np.isfinite(a).all() or (a < 0).any():
                raise ValueError(f"{name}: invalid matrix")
            if not np.allclose(a, a.T, atol=EPS, rtol=0) or np.any(np.abs(a.diagonal()) > EPS):
                raise ValueError(f"{name}: symmetric matrix with zero diagonal required")
        dist.setflags(write=False)
        factor=(size+min(size,self.vehicles))*(min(size,self.vehicles)+1)+1
        if float(dist.max()) > np.finfo(float).max/factor:
            raise ValueError('distance scale would overflow objective arithmetic')
        object.__setattr__(self, "distance", dist)
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def n(self):
        return len(self.demand) - 1

    def proven_impossible(self):
        """Only necessary tests valid even for nonmetric matrices."""
        if self.n and self.vehicles == 0:
            return "no vehicles"
        if np.any(self.demand > self.capacity + EPS):
            return "indivisible demand exceeds capacity"
        if self.demand.sum() > self.capacity * self.vehicles + EPS:
            return "fleet aggregate capacity insufficient"
        return None


def route_metrics(route, ins):
    """Fast kernel; route membership is checked by the independent verifier."""
    t = distance = waiting = travel = load = 0.0
    prev = 0
    starts = []
    for i in route:
        load += float(ins.demand[i])
        arrival = t + float(ins.travel[prev, i])
        t = max(arrival, float(ins.early[i]))
        waiting += t - arrival
        if t > ins.late[i] + EPS or load > ins.capacity + EPS:
            return None
        starts.append(t)
        t += float(ins.service[i])
        distance += float(ins.distance[prev, i])
        travel += float(ins.travel[prev, i])
        prev = i
    if route:
        t += float(ins.travel[prev, 0])
        distance += float(ins.distance[prev, 0])
        travel += float(ins.travel[prev, 0])
    if t > ins.horizon + EPS:
        return None
    return dict(duration=t, distance=distance, waiting=waiting, travel=travel,
                load=load, starts=starts)


def score(routes, ins, objective):
    metrics = [route_metrics(r, ins) for r in routes if r]
    if any(m is None for m in metrics):
        raise ValueError("score requires feasible routes")
    if objective == Objective.LEX:
        return (len(metrics), sum(m["distance"] for m in metrics))
    return sum(m[objective.value] for m in metrics)


def better(a, b):
    if isinstance(a, tuple):
        return a[0] < b[0] or (a[0] == b[0] and a[1] < b[1] - EPS)
    return a < b - EPS


def energy(value, ins, objective):
    """Bounded scalar embedding used ONLY by SA, never reported as distance.

    A complete solution has at most n+K arcs. Its distance <= (n+K)*dmax.
    Therefore one vehicle dominates every feasible distance difference.
    """
    if objective == Objective.LEX:
        bound = (ins.n + min(ins.n, ins.vehicles)) * float(ins.distance.max())
        return value[0] * (bound + 1.0) + value[1]
    return float(value)
