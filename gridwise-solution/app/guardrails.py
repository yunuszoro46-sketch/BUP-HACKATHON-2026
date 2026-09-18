from __future__ import annotations

from typing import List

from app.schemas import GridLoad, OptimizationRequest


def validate_request(request: OptimizationRequest) -> None:
    if not request.loads:
        raise ValueError("At least one load entry is required.")

    for item in request.loads:
        if item.demand <= 0:
            raise ValueError(f"Demand for node '{item.node_id}' must be positive.")
        if item.capacity <= 0:
            raise ValueError(f"Capacity for node '{item.node_id}' must be positive.")
        if item.capacity < item.demand:
            raise ValueError(
                f"Capacity for node '{item.node_id}' cannot be smaller than its demand."
            )


def validate_solution_feasibility(request: OptimizationRequest, total_allocated: float) -> None:
    total_demand = sum(item.demand for item in request.loads)
    if total_allocated < 0:
        raise ValueError("Allocated demand cannot be negative.")

    if total_allocated > total_demand + 1e-9:
        raise ValueError("Allocated demand exceeds the total demand in the scenario.")


def summarize_guardrail_issues(request: OptimizationRequest) -> List[str]:
    issues: List[str] = []

    if not request.loads:
        issues.append("No loads were provided in the request.")

    for item in request.loads:
        if item.demand <= 0:
            issues.append(f"Node {item.node_id} has invalid demand: {item.demand}")
        if item.capacity <= 0:
            issues.append(f"Node {item.node_id} has invalid capacity: {item.capacity}")
        if item.capacity < item.demand:
            issues.append(
                f"Node {item.node_id} has demand {item.demand} greater than capacity {item.capacity}"
            )

    return issues
