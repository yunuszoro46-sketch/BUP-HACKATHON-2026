# GridWise Smart Campus Energy Optimization

HTTP API for the BUP CSE Fest 2026 preliminary: interpret 1–3 operator notes, validate them, then schedule 24 hours of campus demand using grid, solar, and a battery while minimizing grid cost.

Judge-facing endpoints (names must match exactly):

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Readiness check |
| `POST` | `/optimize-energy` | Interpret notes + return a 24-hour plan |

## Architecture

```
operator notes  →  LLM interpreter  →  deterministic guardrails  →  PuLP/CBC optimizer  →  replay checks  →  JSON plan
                      ↑
            local paraphrase fallback if the model is unreachable
```

1. **Interpret** — `app/llm.py` sends notes (plus battery capacity) to an OpenAI-compatible chat API in JSON mode. `app/interpreter.py` is a deterministic backup for the same six directive types so a model outage does not invent new types or crash.
2. **Validate** — `app/guardrails.py` forces `no_op` semantics, sorts unique hours `0..23`, clamps `factor` to `[0, 1]`, clamps reserve to `[0, capacity]`, and keeps `max_grid_kwh >= 0`.
3. **Optimize** — `app/optimizer.py` applies those directives to a mixed-integer linear program (PuLP + CBC): meet demand every hour, respect charge/discharge rates, reserves, grid caps, unused-solar curtailment, and end-of-day battery neutrality. Objective is `sum(grid_kwh[h] * tariff[h])`.
4. **Respond** — `app/replay.py` re-checks energy balance and every applied directive before the API returns.

Unsupported LLM types are discarded (`no_op`). The service never returns stack traces or API keys.

## Local quickstart

```bash
cd gridwise-solution
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# put your LLM key in .env; never commit that file
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health:

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok"}
```

Optimize (paste a public sample `input` object):

```bash
curl -s -X POST http://127.0.0.1:8000/optimize-energy \
  -H "Content-Type: application/json" \
  -d @/path/to/sample_input.json
```

Replay the ten public sample cases against interpreter + solver (no HTTP):

```bash
python scripts/validate_samples.py \
  ~/BUP_CSE_FEST_2026_Participant_Docs/BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json
```

## Docker

`.env` is not copied into the image. Pass secrets at runtime.

```bash
docker build -t gridwise-solution:local .
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY \
  -e OPENAI_BASE_URL \
  -e LLM_MODEL \
  gridwise-solution:local
```

Or:

```bash
docker compose up --build
```

Registry tag (replace with your namespace when you push):

```bash
docker tag gridwise-solution:local YOUR_REGISTRY/gridwise-solution:latest
docker push YOUR_REGISTRY/gridwise-solution:latest
```

## Environment variables

| Name | Required | Meaning |
| --- | --- | --- |
| `OPENAI_API_KEY` | For live LLM calls | Provider API key. Leave empty to use the local interpreter only. |
| `OPENAI_BASE_URL` | No | OpenAI-compatible base URL. Default in `.env.example` is `https://api.x.ai/v1`. |
| `LLM_MODEL` | No | Chat model id. Default `grok-3-mini`. |
| `MODEL_NAME` | No | Alias used if `LLM_MODEL` is unset. |
| `HOST` | No | Bind address. Default `0.0.0.0`. |
| `PORT` | No | Bind port. Default `8000`. |
| `APP_ENV` | No | `development` enables reload when running `app/main.py`. |

Do not commit `.env` or paste keys into source, README, or the Docker image.

## Request and response

`POST /optimize-energy` accepts:

- `scenario_id` string
- `operator_notes` array of 1–3 non-empty strings
- `hours` exactly 24 objects with `hour` `0..23`, `demand_kwh`, `solar_kwh`, `tariff_bdt_per_kwh`
- `battery` with `capacity_kwh`, `initial_energy_kwh`, `minimum_energy_kwh`, `max_charge_kwh_per_hour`, `max_discharge_kwh_per_hour`

Response includes `directive_interpretation` (one entry per note, `note_index` order), `hourly_plan` (24 hours), `total_grid_kwh`, `total_cost_bdt`, `peak_grid_kwh`, and `plan_summary`.

Directive types: `solar_reduction`, `minimum_battery_reserve`, `no_charge_window`, `no_discharge_window`, `max_grid_window`, `no_op`.

Time windows are start-inclusive and end-exclusive (`1 PM to 3 PM` → `[13, 14]`). For `solar_reduction`, `factor` is remaining usable solar (`80% reduction` → `0.2`).

HTTP codes: `200` success, `422` invalid request body, `500` controlled internal error.

## Solver notes

- Library: PuLP with the CBC solver (allowed by the problem statement).
- Per hour: `grid + solar_used + discharge = demand + charge`.
- `0 <= solar_used <= effective_solar` after any `solar_reduction`.
- Battery: charge/idle/discharge mutually exclusive; rate limits; `min_soc[h] <= energy_after[h] <= capacity`; `energy_after[23] = initial_energy`.
- Directives change the model only as specified: scaled solar, raised reserve, charge=0, discharge=0, or `grid <= cap`.
- Tiny peak/cycling penalties sit under the cost objective so equivalent optimal costs stay stable; the judge scores cost within `0.01`.

## Project layout

```
app/main.py           FastAPI endpoints
app/llm.py            LLM JSON-mode interpreter
app/interpreter.py    Deterministic paraphrase fallback
app/guardrails.py     Untrusted-LLM sanitizer
app/optimizer.py      24-hour MILP
app/replay.py         Post-solve validity checks
app/schemas.py        Request/response models
scripts/validate_samples.py
Dockerfile
docker-compose.yml
.env.example
```

## Deliverables still on you

- Keep secrets out of git.
- Push a public Docker image and record the tag/digest for submission.
- Record a ≤3 minute architecture/guardrail video if the participant guide requires it.
