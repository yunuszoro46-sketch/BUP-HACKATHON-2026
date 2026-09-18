import os
import json
from typing import List, Dict, Any

from openai import OpenAI

from app.interpreter import interpret_notes_locally
from app.schemas import BatteryConfig

SYSTEM_PROMPT = """
You are the GridWise operator-note interpreter. Convert each natural-language note into exactly one supported directive for a 24-hour campus energy schedule (hours 0 through 23).

Supported directive_type values and structured_adjustment shapes:
1. solar_reduction -> {"hours": [int, ...], "factor": float}
   factor is the usable fraction REMAINING. "80% reduction" => 0.2. "drop to 20%" / "one-fifth of normal" => 0.2.
2. minimum_battery_reserve -> {"hours": [int, ...], "minimum_energy_kwh": float}
   Convert "% of battery capacity" into kWh using the provided capacity.
3. no_charge_window -> {"hours": [int, ...]}
4. no_discharge_window -> {"hours": [int, ...]}
5. max_grid_window -> {"hours": [int, ...], "max_grid_kwh": float}
6. no_op -> structured_adjustment must be null

Time windows are start-inclusive and end-exclusive:
- "1 PM to 3 PM" / "1-3 PM" / "13:00 and 15:00" / "from one until three" => [13, 14]
- "6 PM until 9 PM" => [18, 19, 20]
- "noon until 2 PM" => [12, 13]

Paraphrases of the same rule must map to the same directive. Irrelevant notes (menus, deadlines, next week) are no_op.

Return JSON: {"interpretations": [ ... one object per note in note_index order ... ]}
Each object: note_index, applies, directive_type, structured_adjustment, explanation.
no_op => applies=false. Every other type => applies=true.
Do not invent demand, solar, tariff, battery limits, or unsupported directive types.
"""


def _client() -> OpenAI:
    kwargs = {"api_key": os.getenv("OPENAI_API_KEY")}
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def interpret_operator_notes(
    operator_notes: List[str],
    battery: BatteryConfig,
) -> List[Dict[str, Any]]:
    fallback = interpret_notes_locally(operator_notes, battery)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        return fallback

    user_payload = {
        "battery": {
            "capacity_kwh": battery.capacity_kwh,
            "minimum_energy_kwh": battery.minimum_energy_kwh,
        },
        "notes_to_interpret": [
            {"note_index": idx, "text": note}
            for idx, note in enumerate(operator_notes)
        ],
    }

    try:
        response = _client().chat.completions.create(
            model=os.getenv("LLM_MODEL", os.getenv("MODEL_NAME", "grok-3-mini")),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)

        if "interpretations" in parsed:
            interpretations = parsed["interpretations"]
        elif isinstance(parsed, list):
            interpretations = parsed
        else:
            interpretations = list(parsed.values())[0]

        if not isinstance(interpretations, list) or len(interpretations) != len(operator_notes):
            return fallback
        return interpretations

    except Exception:
        return fallback
