# GridWise Smart Campus Energy Optimization

GridWise is an AI-assisted smart-campus energy optimizer for the BUP CSE Fest 2026 preliminary. It interprets 1–3 operator notes, applies deterministic safety guardrails, solves a 24-hour solar/grid/battery schedule with PuLP/CBC, replay-validates the result, and presents the plan in an integrated browser dashboard.

## Architecture

```text
operator notes → LLM/local interpreter → guardrails → PuLP/CBC optimizer → replay validation → dashboard/API
```

## Run the integrated demo

```bash
cd gridwise-solution
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000/>. The dashboard uses the real `POST /optimize-energy` endpoint; no separate frontend server is required.

## API

- `GET /health` — readiness check
- `POST /optimize-energy` — accepts a scenario, 1–3 operator notes, exactly 24 hourly records, and battery settings

The response contains guarded directive interpretations, the replay-validated 24-hour plan, total grid energy, total cost in BDT, peak grid usage, and a summary.

## Docker

```bash
docker build -t gridwise-solution:local .
docker run --rm -p 8000:8000 --env-file .env gridwise-solution:local
```

Do not commit `.env` or API keys. Leave `OPENAI_API_KEY` empty to use the deterministic local interpreter.
