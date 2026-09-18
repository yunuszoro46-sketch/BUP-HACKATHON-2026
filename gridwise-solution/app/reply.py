from typing import Any, Dict, List

from app.optimizer import build_effective_constraints
from app.schemas import BatteryConfig, HourEntry, HourlyPlanEntry

TOLERANCE = 0.01


def replay_plan(
    hours: List[HourEntry],
    battery: BatteryConfig,
    optimizer_directives: List[Dict[str, Any]],
    plan: List[HourlyPlanEntry],
) -> None:
    """Re-check energy balance, battery rules, and applied directives."""
    if len(plan) != 24:
        raise RuntimeError("hourly_plan must contain 24 entries")

    ordered, solar, min_soc, max_grid, no_charge, no_discharge = build_effective_constraints(
        hours, battery, optimizer_directives
    )

    energy = battery.initial_energy_kwh
    seen = []
    for entry, hour in zip(plan, ordered):
        seen.append(entry.hour)
        if entry.hour != hour.hour:
            raise RuntimeError("hourly_plan hours must be 0 through 23 in order")

        charge = entry.battery_kwh if entry.battery_action == "charge" else 0.0
        discharge = entry.battery_kwh if entry.battery_action == "discharge" else 0.0
        if entry.battery_action == "idle" and entry.battery_kwh > TOLERANCE:
            raise RuntimeError("idle hours must have battery_kwh = 0")
        if charge > battery.max_charge_kwh_per_hour + TOLERANCE:
            raise RuntimeError("charge exceeds hourly rate limit")
        if discharge > battery.max_discharge_kwh_per_hour + TOLERANCE:
            raise RuntimeError("discharge exceeds hourly rate limit")
        if hour.hour in no_charge and charge > TOLERANCE:
            raise RuntimeError("charge occurred inside a no_charge_window")
        if hour.hour in no_discharge and discharge > TOLERANCE:
            raise RuntimeError("discharge occurred inside a no_discharge_window")
        if entry.solar_used_kwh - solar[hour.hour] > TOLERANCE:
            raise RuntimeError("solar_used_kwh exceeds effective solar")
        if max_grid[hour.hour] is not None and entry.grid_kwh - max_grid[hour.hour] > TOLERANCE:
            raise RuntimeError("grid_kwh exceeds max_grid_window cap")

        lhs = entry.grid_kwh + entry.solar_used_kwh + discharge
        rhs = hour.demand_kwh + charge
        if abs(lhs - rhs) > TOLERANCE:
            raise RuntimeError("hourly energy balance failed")

        energy = energy + charge - discharge
        if abs(energy - entry.battery_energy_after_kwh) > TOLERANCE:
            raise RuntimeError("battery state tracking failed")
        if entry.battery_energy_after_kwh + TOLERANCE < min_soc[hour.hour]:
            raise RuntimeError("battery fell below required reserve")
        if entry.battery_energy_after_kwh - TOLERANCE > battery.capacity_kwh:
            raise RuntimeError("battery exceeded capacity")

    if sorted(seen) != list(range(24)):
        raise RuntimeError("hourly_plan hours are not unique 0..23")
    if abs(plan[-1].battery_energy_after_kwh - battery.initial_energy_kwh) > TOLERANCE:
        raise RuntimeError("end-of-day battery neutrality failed")
