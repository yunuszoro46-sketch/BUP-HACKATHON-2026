from typing import Any, Dict, List, Optional, Tuple

import pulp

from app.schemas import BatteryConfig, HourEntry, HourlyPlanEntry


def build_effective_constraints(
    hours: List[HourEntry],
    battery: BatteryConfig,
    directives: List[Dict[str, Any]],
) -> Tuple[
    List[HourEntry],
    Dict[int, float],
    Dict[int, float],
    Dict[int, Optional[float]],
    set[int],
    set[int],
]:
    """Normalize input order and derive the constraints used by solve/replay."""
    ordered = sorted(hours, key=lambda entry: entry.hour)
    solar = {hour: entry.solar_kwh for hour, entry in ((entry.hour, entry) for entry in ordered)}
    min_soc = {hour: battery.minimum_energy_kwh for hour in range(24)}
    max_grid: Dict[int, Optional[float]] = {hour: None for hour in range(24)}
    no_charge: set[int] = set()
    no_discharge: set[int] = set()

    for directive in directives:
        directive_type = directive.get("directive_type")
        adjustment = directive.get("adjustment") or {}
        target_hours = adjustment.get("hours", [])

        if directive_type == "solar_reduction":
            factor = max(0.0, min(1.0, float(adjustment.get("factor", 1.0))))
            for hour in target_hours:
                solar[hour] *= factor
        elif directive_type == "minimum_battery_reserve":
            reserve = max(
                0.0,
                min(battery.capacity_kwh, float(adjustment.get("minimum_energy_kwh", 0.0))),
            )
            for hour in target_hours:
                min_soc[hour] = max(min_soc[hour], reserve)
        elif directive_type == "no_charge_window":
            no_charge.update(target_hours)
        elif directive_type == "no_discharge_window":
            no_discharge.update(target_hours)
        elif directive_type == "max_grid_window":
            cap = max(0.0, float(adjustment.get("max_grid_kwh", 0.0)))
            for hour in target_hours:
                max_grid[hour] = cap if max_grid[hour] is None else min(max_grid[hour], cap)

    return ordered, solar, min_soc, max_grid, no_charge, no_discharge


def solve_energy_optimization(
    hours: List[HourEntry],
    battery: BatteryConfig,
    directives: List[Dict[str, Any]],
) -> Tuple[List[HourlyPlanEntry], float, float, float]:
    """Solve the 24-hour mixed-integer cost-minimization problem."""
    ordered, effective_solar, min_soc, max_grid, no_charge, no_discharge = build_effective_constraints(
        hours, battery, directives
    )
    prob = pulp.LpProblem("GridWise_Cost_Minimization", pulp.LpMinimize)

    grid = {}
    solar_used = {}
    charge = {}
    discharge = {}
    soc = {}
    battery_mode = {}

    for t, entry in enumerate(ordered):
        hour = entry.hour
        grid[hour] = pulp.LpVariable(
            f"grid_{hour}", lowBound=0, upBound=max_grid[hour]
        )
        solar_used[hour] = pulp.LpVariable(
            f"solar_used_{hour}", lowBound=0, upBound=effective_solar[hour]
        )
        charge[hour] = pulp.LpVariable(
            f"charge_{hour}", lowBound=0,
            upBound=0.0 if hour in no_charge else battery.max_charge_kwh_per_hour,
        )
        discharge[hour] = pulp.LpVariable(
            f"discharge_{hour}", lowBound=0,
            upBound=0.0 if hour in no_discharge else battery.max_discharge_kwh_per_hour,
        )
        soc[hour] = pulp.LpVariable(
            f"soc_{hour}", lowBound=min_soc[hour], upBound=battery.capacity_kwh
        )
        # One binary mode prevents simultaneous charging and discharging.
        battery_mode[hour] = pulp.LpVariable(f"charge_mode_{hour}", cat="Binary")
        prob += charge[hour] <= battery.max_charge_kwh_per_hour * battery_mode[hour]
        prob += discharge[hour] <= battery.max_discharge_kwh_per_hour * (1 - battery_mode[hour])

    prob += pulp.lpSum(grid[entry.hour] * entry.tariff_bdt_per_kwh for entry in ordered)

    for index, entry in enumerate(ordered):
        hour = entry.hour
        previous_energy = battery.initial_energy_kwh if index == 0 else soc[ordered[index - 1].hour]
        prob += solar_used[hour] + grid[hour] + discharge[hour] - charge[hour] == entry.demand_kwh
        prob += soc[hour] == previous_energy + charge[hour] - discharge[hour]

    # The schedule is a daily cycle: the battery ends at its starting energy.
    prob += soc[23] == battery.initial_energy_kwh

    result = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[result] != "Optimal":
        raise RuntimeError(f"No feasible energy schedule found ({pulp.LpStatus[result]}).")

    hourly_plan: List[HourlyPlanEntry] = []
    for entry in ordered:
        hour = entry.hour
        charge_value = charge[hour].value() or 0.0
        discharge_value = discharge[hour].value() or 0.0
        if charge_value > 0.001:
            action, battery_value = "charge", charge_value
        elif discharge_value > 0.001:
            action, battery_value = "discharge", discharge_value
        else:
            action, battery_value = "idle", 0.0
        hourly_plan.append(
            HourlyPlanEntry(
                hour=hour,
                grid_kwh=round(grid[hour].value() or 0.0, 2),
                solar_used_kwh=round(solar_used[hour].value() or 0.0, 2),
                battery_action=action,
                battery_kwh=round(battery_value, 2),
                battery_energy_after_kwh=round(soc[hour].value() or 0.0, 2),
            )
        )

    total_grid = round(sum(item.grid_kwh for item in hourly_plan), 2)
    total_cost = round(
        sum(item.grid_kwh * entry.tariff_bdt_per_kwh for item, entry in zip(hourly_plan, ordered)),
        2,
    )
    peak_grid = round(max(item.grid_kwh for item in hourly_plan), 2)
    return hourly_plan, total_grid, total_cost, peak_grid
