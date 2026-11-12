"""Restricted set partitioning over already feasible routes.

Optimality, if proved, is only within this finite pool, never for the full VRPTW.
References and benchmark costs are deliberately absent from this module.
"""

from dataclasses import dataclass
import math
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from .verify import verify


@dataclass
class RouteColumn:
    clients: tuple
    cost: float


class RoutePool:
    def __init__(self, instance):
        self.instance = instance
        self.columns = {}
        self.best_routes = None
        self.best_cost = math.inf
        self.solutions_added = 0

    def add_solution(self, routes):
        """Ajoute les tournées d’une solution complète vérifiée au réservoir.
        Pour un même ensemble de clients, seul l’ordre réalisable le moins coûteux est gardé."""
        checked = verify(routes, self.instance)
        if not checked["valid"]:
            raise ValueError(
                "Pool accepts only complete feasible solutions: "
                + str(checked["errors"])
            )
        routes = [list(route) for route in routes if route]
        self.solutions_added += 1
        if checked["distance"] < self.best_cost:
            self.best_cost = checked["distance"]
            self.best_routes = [route[:] for route in routes]
        for route, metrics in zip(routes, checked["routes"]):
            key = frozenset(route)
            column = self.columns.get(key)
            if column is None or metrics["distance"] < column.cost - 1e-8:
                self.columns[key] = RouteColumn(tuple(route), metrics["distance"])

    def recombine(self, seconds=5.0, relative_gap=0.001):
        """Sélectionne des tournées du réservoir par partitionnement en nombres entiers.
        Chaque client est couvert exactement une fois et la borne de flotte est respectée.
        Une preuve d’optimalité ne concerne que ce réservoir fini de tournées.
        L’archive réalisable est conservée même si le solveur atteint sa limite de temps."""
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("Positive finite solver time required")
        if self.best_routes is None:
            raise ValueError("Add a feasible solution before recombination")
        started = time.perf_counter()
        ins = self.instance
        columns = list(self.columns.values())
        count = len(columns)
        costs = np.array([column.cost for column in columns])
        rows, cols, values = [], [], []
        for index, column in enumerate(columns):
            for client in column.clients:
                rows.append(client - 1)
                cols.append(index)
                values.append(1.0)
            rows.extend([ins.n, ins.n + 1])
            cols.extend([index, index])
            values.extend([1.0, column.cost])
        matrix = coo_matrix((values, (rows, cols)), shape=(ins.n + 2, count)).tocsc()
        lower = np.r_[np.ones(ins.n), 0.0, -np.inf]
        upper = np.r_[np.ones(ins.n), ins.vehicles, self.best_cost + 1e-7]
        result = milp(
            costs,
            integrality=np.ones(count, dtype=np.int32),
            bounds=Bounds(0.0, 1.0),
            constraints=LinearConstraint(matrix, lower, upper),
            options={"time_limit": float(seconds), "mip_rel_gap": float(relative_gap)},
        )
        routes = [route[:] for route in self.best_routes]
        selected = None
        if result.x is not None:
            selected = [i for i, value in enumerate(result.x) if value > 0.5]
            candidate = [list(columns[i].clients) for i in selected]
            checked = verify(candidate, ins)
            if not checked["valid"]:
                raise AssertionError(checked["errors"])
            if checked["distance"] < self.best_cost - 1e-8:
                routes = candidate
        checked = verify(routes, ins)
        assert checked["valid"] and checked["distance"] <= self.best_cost + 1e-7
        initial_cost = self.best_cost
        self.add_solution(routes)
        dual = getattr(result, "mip_dual_bound", None)
        return dict(
            status="feasible",
            routes=routes,
            cost=checked["distance"] / 10,
            initial_cost=initial_cost / 10,
            metrics=checked,
            vehicles=checked["vehicles"],
            runtime_s=time.perf_counter() - started,
            solver_status=int(result.status),
            solver_message=result.message,
            pool_columns=count,
            pool_solutions=self.solutions_added - 1,
            optimal_in_pool=bool(result.status == 0),
            pool_lower_bound=(
                float(dual) / 10 if dual is not None and math.isfinite(dual) else None
            ),
            fallback_to_archive=selected is None,
            warning="A pool bound is not a lower bound for the full CVRPTW",
        )
