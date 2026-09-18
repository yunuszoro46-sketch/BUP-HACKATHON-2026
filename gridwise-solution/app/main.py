import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.guardrails import apply_guardrails
from app.llm import interpret_operator_notes
from app.optimizer import solve_energy_optimization
from app.schemas import OptimizeEnergyRequest, OptimizeEnergyResponse

load_dotenv()

app = FastAPI(title="GridWise Optimization API", version="1.0.0")

# The dashboard is served by this API in production. CORS also makes local
# development from another frontend origin straightforward.
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}


@app.post("/optimize-energy", response_model=OptimizeEnergyResponse, status_code=status.HTTP_200_OK)
async def optimize_energy(payload: OptimizeEnergyRequest):
    try:
        raw_interpretations = interpret_operator_notes(payload.operator_notes, payload.battery)
        validated_interpretations, optimizer_directives = apply_guardrails(
            raw_interpretations=raw_interpretations,
            operator_notes=payload.operator_notes,
            battery_config=payload.battery,
        )

        hourly_plan, total_grid, total_cost, peak_grid = solve_energy_optimization(
            hours=payload.hours,
            battery=payload.battery,
            directives=optimizer_directives,
        )

        return OptimizeEnergyResponse(
            scenario_id=payload.scenario_id,
            directive_interpretation=validated_interpretations,
            hourly_plan=hourly_plan,
            total_grid_kwh=total_grid,
            total_cost_bdt=total_cost,
            peak_grid_kwh=peak_grid,
            plan_summary=f"Optimized schedule successfully with {len(optimizer_directives)} active directive(s).",
        )
    except Exception as exc:
        # Keep the API response controlled; do not expose a traceback or secret.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization execution error: {exc}",
        ) from exc


DASHBOARD_PATH = Path(__file__).parent / "static" / "index.html"


@app.get("/", include_in_schema=False)
async def dashboard():
    return FileResponse(DASHBOARD_PATH)
