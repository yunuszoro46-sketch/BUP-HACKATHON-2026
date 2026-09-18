from typing import List, Dict, Any, Tuple
from app.schemas import DirectiveInterpretationEntry, BatteryConfig

ALLOWED_DIRECTIVES = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op"
}


def apply_guardrails(
        raw_interpretations: List[Dict[str, Any]],
        operator_notes: List[str],
        battery_config: BatteryConfig
) -> Tuple[List[DirectiveInterpretationEntry], List[Dict[str, Any]]]:
    """
    Validates and sanitizes raw LLM output.
    Returns:
      1. Validated List[DirectiveInterpretationEntry] for API response.
      2. Validated structured directives for downstream mathematical optimizer.
    """
    validated_entries: List[DirectiveInterpretationEntry] = []
    optimizer_directives: List[Dict[str, Any]] = []

    for idx, note_text in enumerate(operator_notes):
        # Find matching raw interpretation entry
        raw = next((item for item in raw_interpretations if item.get("note_index") == idx), None)

        if not raw or not isinstance(raw, dict):
            # Fallback if entry missing
            raw = {
                "note_index": idx,
                "applies": False,
                "directive_type": "no_op",
                "structured_adjustment": None,
                "explanation": "Missing interpretation replaced with no_op."
            }

        directive_type = raw.get("directive_type", "no_op")
        if directive_type not in ALLOWED_DIRECTIVES:
            directive_type = "no_op"

        # Rule: no_op must have applies=False and structured_adjustment=None
        if directive_type == "no_op":
            applies = False
            adjustment = None
            explanation = raw.get("explanation", "Note does not affect energy schedule.")
        else:
            applies = True
            explanation = raw.get("explanation", f"Applied {directive_type} directive.")
            adjustment = raw.get("structured_adjustment", {})

            if not isinstance(adjustment, dict):
                adjustment = {}

            # --- HOURS GUARDRAIL ---
            # Unique integers 0..23 in ascending order
            hours = adjustment.get("hours", [])
            if not isinstance(hours, list):
                hours = []

            cleaned_hours = sorted(list(set(
                int(h) for h in hours if isinstance(h, (int, float)) and 0 <= int(h) <= 23
            )))

            if not cleaned_hours:
                directive_type = "no_op"
                applies = False
                adjustment = None
                explanation = "Invalid hours provided; reverted to no_op."
            elif directive_type == "solar_reduction":
                try:
                    factor = max(0.0, min(1.0, float(adjustment.get("factor", 1.0))))
                except (ValueError, TypeError):
                    factor = 1.0
                adjustment = {"hours": cleaned_hours, "factor": factor}
            elif directive_type == "minimum_battery_reserve":
                try:
                    min_kwh = max(0.0, min(battery_config.capacity_kwh, float(adjustment.get("minimum_energy_kwh", 0.0))))
                except (ValueError, TypeError):
                    min_kwh = battery_config.minimum_energy_kwh
                adjustment = {"hours": cleaned_hours, "minimum_energy_kwh": min_kwh}
            elif directive_type == "max_grid_window":
                try:
                    max_grid = max(0.0, float(adjustment.get("max_grid_kwh", 0.0)))
                except (ValueError, TypeError):
                    max_grid = 0.0
                adjustment = {"hours": cleaned_hours, "max_grid_kwh": max_grid}
            else:
                adjustment = {"hours": cleaned_hours}

        entry = DirectiveInterpretationEntry(
            note_index=idx,
            applies=applies,
            directive_type=directive_type,
            structured_adjustment=adjustment,
            explanation=explanation
        )
        validated_entries.append(entry)

        if applies and directive_type != "no_op":
            optimizer_directives.append({
                "directive_type": directive_type,
                "adjustment": adjustment
            })

    return validated_entries, optimizer_directives
