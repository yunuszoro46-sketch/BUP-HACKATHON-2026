import os
from fastapi import FastAPI, HTTPException, status
from dotenv import load_dotenv

from app.schemas import OptimizeEnergyRequest, OptimizeEnergyResponse
from app.llm import interpret_operator_notes
from app.guardrails import apply_guardrails
from app.optimizer import solve_energy_optimization

load_dotenv()

app = FastAPI(title="GridWise Optimization API", version="1.0.0")

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}

@app.post("/optimize-energy", response_model=OptimizeEnergyResponse, status_code=status.HTTP_200_OK)
async def optimize_energy(payload: OptimizeEnergyRequest):
    try:
        # Step 2: Interpretation & Guardrails
        raw_interpretations = interpret_operator_notes(payload.operator_notes, payload.battery)
        validated_interpretations, optimizer_directives = apply_guardrails(
            raw_interpretations=raw_interpretations,
            operator_notes=payload.operator_notes,
            battery_config=payload.battery
        )

        # Step 3: Math Optimizer
        hourly_plan, total_grid, total_cost, peak_grid = solve_energy_optimization(
            hours=payload.hours,
            battery=payload.battery,
            directives=optimizer_directives
        )

        return OptimizeEnergyResponse(
            scenario_id=payload.scenario_id,
            directive_interpretation=validated_interpretations,
            hourly_plan=hourly_plan,
            total_grid_kwh=total_grid,
            total_cost_bdt=total_cost,
            peak_grid_kwh=peak_grid,
            plan_summary=f"Optimized schedule successfully with {len(optimizer_directives)} active directive(s)."
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization execution error: {str(e)}"
        )
