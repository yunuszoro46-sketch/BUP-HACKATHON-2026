# GridWise Smart Campus Energy Optimization

The repository now includes an integrated browser dashboard. Start the FastAPI service and open `http://localhost:8000/`; the dashboard calls the same-origin `/optimize-energy` endpoint and visualizes the returned plan.

## Run the integrated demo

```bash
cd gridwise-solution
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open <http://localhost:8000/>. No separate frontend server is required.

The frontend submits the API's real request shape, displays total grid energy, total cost, peak grid draw, guarded directive interpretations, and the complete 24-hour dispatch plan. `PuLP` is included in `requirements.txt` because `app/optimizer.py` imports it for the CBC optimization solver. `CORS_ORIGINS` can be set to comma-separated origins when developing a separate frontend.

