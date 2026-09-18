from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class GridLoad(BaseModel):
    node_id: str = Field(..., description="Identifier for a grid node or asset.")
    demand: float = Field(..., gt=0, description="Demand or load at this node.")
    capacity: float = Field(..., gt=0, description="Maximum supported load or capacity.")
    cost_per_unit: float = Field(0.0, ge=0, description="Cost to serve this node.")


class OptimizationRequest(BaseModel):
    scenario_name: str = Field(default="gridwise-scenario", description="Case name.")
    loads: List[GridLoad] = Field(..., min_length=1, description="Load points to optimize.")
    max_total_cost: Optional[float] = Field(
        default=None,
        ge=0,
        description="Optional maximum cost constraint.",
    )
    objective: str = Field(
        default="min_cost",
        description="Optimization objective. Supported values: min_cost, minimize_demand_shortfall.",
    )

    @field_validator("objective")
    @classmethod
    def validate_objective(cls, value: str) -> str:
        allowed = {"min_cost", "minimize_demand_shortfall"}
        if value not in allowed:
            raise ValueError(f"Objective must be one of: {sorted(allowed)}")
        return value


class Assignment(BaseModel):
    node_id: str
    allocated: float
    unmet: float
    cost: float


class OptimizationResponse(BaseModel):
    scenario_name: str
    total_cost: float
    total_demand: float
    total_allocated: float
    total_unmet: float
    assignments: List[Assignment]
    status: str = "optimal"


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "gridwise"
