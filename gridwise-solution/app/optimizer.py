from typing import List, Dict, Any, Tuple
import pulp
from app.schemas import HourEntry, BatteryConfig, HourlyPlanEntry


def solve_energy_optimization(
        hours: List[HourEntry],
        battery: BatteryConfig,
        directives: List[Dict[str, Any]]
) -> Tuple[List[HourlyPlanEntry], float, float, float]:
    """
    Solves the 24-hour linear program to minimize total electricity cost.
    """
    prob = pulp.LpProblem("GridWise_Cost_Minimization", pulp.LpMinimize)

    # Pre-process directive adjustments
    solar_factors = {h: 1.0 for h in range(24)}
    min_reserves = {h: battery.minimum_energy_kwh for h in range(24)}
    no_charge_hours = set()
    no_discharge_hours = set()
    max_grid_caps = {h: float('inf') for h in range(24)}

    for d in directives:
        d_type = d.get("directive_type")
        adj = d.get("adjustment", {})
        target_hours = adj.get("hours", [])

        if d_type == "solar_reduction":
            factor = adj.get("factor", 1.0)
            for h in target_hours:
                solar_factors[h] = min(solar_factors[h], factor)
        elif d_type == "minimum_battery_reserve":
            min_kwh = adj.get("minimum_energy_kwh", battery.minimum_energy_kwh)
            for h in target_hours:
                min_reserves[h] = max(min_reserves[h], min_kwh)
        elif d_type == "no_charge_window":
            no_charge_hours.update(target_hours)
        elif d_type == "no_discharge_window":
            no_discharge_hours.update(target_hours)
        elif d_type == "max_grid_window":
            cap = adj.get("max_grid_kwh", float('inf'))
            for h in target_hours:
                max_grid_caps[h] = min(max_grid_caps[h], cap)

    # Decision Variables
    grid = {}
    solar_used = {}
    charge = {}
    discharge = {}
    soc = {}

    for t in range(24):
        grid[t] = pulp.LpVariable(f"grid_{t}", lowBound=0, upBound=max_grid_caps[t])
        avail_solar = hours[t].solar_kwh * solar_factors[t]
        solar_used[t] = pulp.LpVariable(f"solar_used_{t}", lowBound=0, upBound=avail_solar)

        c_max = 0.0 if t in no_charge_hours else battery.max_charge_kwh_per_hour
        d_max = 0.0 if t in no_discharge_hours else battery.max_discharge_kwh_per_hour

        charge[t] = pulp.LpVariable(f"charge_{t}", lowBound=0, upBound=c_max)
        discharge[t] = pulp.LpVariable(f"discharge_{t}", lowBound=0, upBound=d_max)
        soc[t] = pulp.LpVariable(f"soc_{t}", lowBound=min_reserves[t], upBound=battery.capacity_kwh)

    # Objective Function: Minimize total cost
    prob += pulp.lpSum([grid[t] * hours[t].tariff_bdt_per_kwh for t in range(24)])

    # Constraints
    for t in range(24):
        # Power Balance: Demand = Solar + Grid + Discharge - Charge
        prob += (solar_used[t] + grid[t] + discharge[t] - charge[t] == hours[t].demand_kwh)

        # Battery State of Charge Continuity
        prev_soc = battery.initial_energy_kwh if t == 0 else soc[t - 1]
        prob += (soc[t] == prev_soc + charge[t] - discharge[t])

    # Solve LP
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    # Format Results
    hourly_plan: List[HourlyPlanEntry] = []
    for t in range(24):
        c_val = charge[t].varValue or 0.0
        d_val = discharge[t].varValue or 0.0

        if c_val > 0.001:
            action = "charge"
            b_kwh = round(c_val, 2)
        elif d_val > 0.001:
            action = "discharge"
            b_kwh = round(d_val, 2)
        else:
            action = "idle"
            b_kwh = 0.0

        hourly_plan.append(
            HourlyPlanEntry(
                hour=t,
                grid_kwh=round(grid[t].varValue or 0.0, 2),
                solar_used_kwh=round(solar_used[t].varValue or 0.0, 2),
                battery_action=action,
                battery_kwh=b_kwh,
                battery_energy_after_kwh=round(soc[t].varValue or 0.0, 2)
            )
        )

    total_grid = round(sum(p.grid_kwh for p in hourly_plan), 2)
    total_cost = round(sum(p.grid_kwh * hours[i].tariff_bdt_per_kwh for i, p in enumerate(hourly_plan)), 2)
    peak_grid = round(max(p.grid_kwh for p in hourly_plan), 2)

    return hourly_plan, total_grid, total_cost, peak_grid
