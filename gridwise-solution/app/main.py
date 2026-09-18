from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from app.guardrails import validate_request
from app.optimizer import solve_grid_optimization
from app.schemas import HealthResponse, OptimizationRequest, OptimizationResponse

load_dotenv()

app = FastAPI(
    title="Gridwise Solver API",
    description="Simple optimization API for grid-demand allocation and cost planning.",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="gridwise")


@app.post("/solve", response_model=OptimizationResponse)
def solve(request: OptimizationRequest) -> OptimizationResponse:
    try:
        validate_request(request)
        return solve_grid_optimization(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/")
def root() -> dict:
    return {
        "service": "gridwise",
        "status": "running",
        "docs_url": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
