from __future__ import annotations

from typing import List

import numpy as np
from scipy.optimize import linprog

from app.schemas import Assignment, GridLoad, OptimizationRequest, OptimizationResponse


def solve_grid_optimization(request: OptimizationRequest) -> OptimizationResponse:
    loads: List[GridLoad] = request.loads

    n = len(loads)

    c = np.array([item.cost_per_unit for item in loads], dtype=float)

    total_demand = float(sum(item.demand for item in loads))
    upper_bounds = np.array([item.capacity for item in loads], dtype=float)
    lower_bounds = np.zeros(n, dtype=float)

    A_ub = np.ones((1, n), dtype=float)
    b_ub = np.array([total_demand], dtype=float)

    result = linprog(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub,
        bounds=list(zip(lower_bounds, upper_bounds)),
        method="highs",
    )

    if not result.success:
        raise RuntimeError(f"Optimization failed: {result.message}")

    allocations = result.x

    assignments: List[Assignment] = []
    total_allocated = 0.0
    total_unmet = 0.0

    for item, allocated in zip(loads, allocations):
        unmet = max(0.0, item.demand - allocated)
        cost = item.cost_per_unit * allocated
        assignments.append(
            Assignment(
                node_id=item.node_id,
                allocated=float(allocated),
                unmet=float(unmet),
                cost=float(cost),
            )
        )
        total_allocated += float(allocated)
        total_unmet += float(unmet)

    total_cost = float(sum(a.cost for a in assignments))

    return OptimizationResponse(
        scenario_name=request.scenario_name,
        total_cost=total_cost,
        total_demand=total_demand,
        total_allocated=total_allocated,
        total_unmet=total_unmet,
        assignments=assignments,
        status="optimal",
    )
