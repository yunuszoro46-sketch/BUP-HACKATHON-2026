from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal


class HourEntry(BaseModel):
    hour: int = Field(..., ge=0, le=23, description="Unique integer from 0 to 23")
    demand_kwh: float = Field(..., ge=0, description="Campus demand in kWh")
    solar_kwh: float = Field(..., ge=0, description="Base available solar kWh")
    tariff_bdt_per_kwh: float = Field(..., ge=0, description="Grid tariff in BDT")


class BatteryConfig(BaseModel):
    capacity_kwh: float = Field(..., gt=0, description="Maximum energy capacity")
    initial_energy_kwh: float = Field(..., ge=0, description="Starting battery energy")
    minimum_energy_kwh: float = Field(..., ge=0, description="Base minimum reserve level")
    max_charge_kwh_per_hour: float = Field(..., ge=0, description="Max hourly charge rate")
    max_discharge_kwh_per_hour: float = Field(..., ge=0, description="Max hourly discharge rate")


class OptimizeEnergyRequest(BaseModel):
    scenario_id: str
    operator_notes: List[str] = Field(..., min_length=1, max_length=3)
    hours: List[HourEntry] = Field(..., min_length=24, max_length=24)
    battery: BatteryConfig

    @field_validator("operator_notes")
    @classmethod
    def notes_must_be_nonempty(cls, value: List[str]) -> List[str]:
        if any(not note.strip() for note in value):
            raise ValueError("operator_notes must contain 1-3 non-empty strings")
        return value

    @field_validator("hours")
    @classmethod
    def hours_must_cover_day(cls, value: List[HourEntry]) -> List[HourEntry]:
        hour_ids = [entry.hour for entry in value]
        if sorted(hour_ids) != list(range(24)):
            raise ValueError("hours must contain exactly 24 unique entries for 0 through 23")
        return value


class DirectiveInterpretationEntry(BaseModel):
    note_index: int
    applies: bool
    directive_type: Literal[
        "solar_reduction",
        "minimum_battery_reserve",
        "no_charge_window",
        "no_discharge_window",
        "max_grid_window",
        "no_op",
    ]
    structured_adjustment: Optional[dict] = None
    explanation: str


class HourlyPlanEntry(BaseModel):
    hour: int
    grid_kwh: float
    solar_used_kwh: float
    battery_action: Literal["charge", "discharge", "idle"]
    battery_kwh: float
    battery_energy_after_kwh: float


class OptimizeEnergyResponse(BaseModel):
    scenario_id: str
    directive_interpretation: List[DirectiveInterpretationEntry]
    hourly_plan: List[HourlyPlanEntry]
    total_grid_kwh: float
    total_cost_bdt: float
    peak_grid_kwh: float
    plan_summary: str
