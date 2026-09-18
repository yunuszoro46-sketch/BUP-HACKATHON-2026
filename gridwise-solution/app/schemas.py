from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# --- REQUEST SCHEMAS ---

class HourEntry(BaseModel):
    hour: int = Field(..., ge=0, le=23, description="Unique integer from 0 to 23")[cite: 2]
    demand_kwh: float = Field(..., ge=0, description="Campus demand in kWh")[cite: 2]
    solar_kwh: float = Field(..., ge=0, description="Base available solar kWh")[cite: 2]
    tariff_bdt_per_kwh: float = Field(..., ge=0, description="Grid tariff in BDT")[cite: 2]

class BatteryConfig(BaseModel):
    capacity_kwh: float = Field(..., gt=0, description="Maximum energy capacity")[cite: 2]
    initial_energy_kwh: float = Field(..., ge=0, description="Starting battery energy")[cite: 2]
    minimum_energy_kwh: float = Field(..., ge=0, description="Base minimum reserve level")[cite: 2]
    max_charge_kwh_per_hour: float = Field(..., ge=0, description="Max hourly charge rate")[cite: 2]
    max_discharge_kwh_per_hour: float = Field(..., ge=0, description="Max hourly discharge rate")[cite: 2]

class OptimizeEnergyRequest(BaseModel):
    scenario_id: str[cite: 2]
    operator_notes: List[str] = Field(..., min_items=1, max_items=3)[cite: 2]
    hours: List[HourEntry] = Field(..., min_items=24, max_items=24)[cite: 2]
    battery: BatteryConfig[cite: 2]


# --- RESPONSE SCHEMAS ---

class DirectiveInterpretationEntry(BaseModel):
    note_index: int[cite: 2]
    applies: bool[cite: 2]
    directive_type: Literal[
        "solar_reduction",
        "minimum_battery_reserve",
        "no_charge_window",
        "no_discharge_window",
        "max_grid_window",
        "no_op"
    ][cite: 2]
    structured_adjustment: Optional[dict] = None[cite: 2]
    explanation: str[cite: 2]

class HourlyPlanEntry(BaseModel):
    hour: int[cite: 2]
    grid_kwh: float[cite: 2]
    solar_used_kwh: float[cite: 2]
    battery_action: Literal["charge", "discharge", "idle"][cite: 2]
    battery_kwh: float[cite: 2]
    battery_energy_after_kwh: float[cite: 2]

class OptimizeEnergyResponse(BaseModel):
    scenario_id: str[cite: 2]
    directive_interpretation: List[DirectiveInterpretationEntry][cite: 2]
    hourly_plan: List[HourlyPlanEntry][cite: 2]
    total_grid_kwh: float[cite: 2]
    total_cost_bdt: float[cite: 2]
    peak_grid_kwh: float[cite: 2]
    plan_summary: str[cite: 2]
