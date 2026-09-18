import re
from typing import Any, Dict, List, Optional

from app.schemas import BatteryConfig


NO_OP_HINTS = (
    "next week",
    "next month",
    "tomorrow",
    "registration",
    "library",
    "book-return",
    "book return",
    "student affairs",
    "club notices",
    "seminar room",
    "sports office",
    "cafeteria",
    "menu",
    "deadline",
)

ENERGY_HINTS = (
    "solar",
    "pv",
    "panel",
    "inverter",
    "rooftop",
    "battery",
    "charg",
    "discharge",
    "grid",
    "feeder",
    "transformer",
    "substation",
    "kwh",
    "reserve",
    "import",
    "intake",
    "tariff",
)

WORD_HOURS = {
    "midnight": 0,
    "noon": 12,
    "midday": 12,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

FRACTIONS = (
    (r"three[- ]quarters", 0.75),
    (r"one[- ]fifth", 0.2),
    (r"one[- ]quarter", 0.25),
    (r"one[- ]third", 1.0 / 3.0),
    (r"one[- ]half", 0.5),
    (r"\bhalf\b", 0.5),
    (r"\bquarter\b", 0.25),
    (r"1/5", 0.2),
    (r"1/4", 0.25),
    (r"1/3", 1.0 / 3.0),
    (r"1/2", 0.5),
)


def _normalize(text: str) -> str:
    text = text.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text.strip().lower())


def _apply_ampm(hour: int, ampm: Optional[str]) -> int:
    if not ampm:
        return hour % 24
    ampm = ampm.lower().replace(".", "")
    if ampm.startswith("p") and hour != 12:
        hour += 12
    elif ampm.startswith("a") and hour == 12:
        hour = 0
    return hour % 24


def _parse_clock(token: str, inherited_ampm: Optional[str] = None) -> Optional[int]:
    token = token.strip().lower()
    if token in WORD_HOURS:
        hour = WORD_HOURS[token]
        if token in {"noon", "midday", "midnight"}:
            return hour
        return _apply_ampm(hour, inherited_ampm)

    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?", token)
    if not match:
        return None
    hour = int(match.group(1))
    ampm = match.group(3) or inherited_ampm
    if hour > 24:
        return None
    if hour == 24:
        hour = 0
    return _apply_ampm(hour, ampm)


def _window_hours(start: int, end: int) -> List[int]:
    if end == start:
        return []
    if end < start:
        return list(range(start, 24)) + list(range(0, end))
    return list(range(start, end))


def parse_hours_window(text: str) -> List[int]:
    compact = re.search(
        r"(?:from\s+|between\s+)?(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
        r"(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?\s*(?:-|to)\s*"
        r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
        r"(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?",
        text,
        flags=re.IGNORECASE,
    )
    if compact:
        ampm = compact.group(6) or compact.group(3)
        start = _parse_clock(
            f"{compact.group(1)}" + (f":{compact.group(2)}" if compact.group(2) else ""),
            compact.group(3) or ampm,
        )
        end = _parse_clock(
            f"{compact.group(4)}" + (f":{compact.group(5)}" if compact.group(5) else ""),
            compact.group(6) or ampm,
        )
        if start is not None and end is not None:
            hours = _window_hours(start, end)
            if hours:
                return hours

    pattern = re.compile(
        r"(?:from|between)\s+"
        r"(noon|midnight|midday|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)"
        r"\s+(?:until|to|and|-)\s+"
        r"(noon|midnight|midday|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)",
        flags=re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        pattern = re.compile(
            r"(noon|midnight|midday|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)"
            r"\s+(?:until|to|-)\s+"
            r"(noon|midnight|midday|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)",
            flags=re.IGNORECASE,
        )
        match = pattern.search(text)
    if not match:
        return []

    left, right = match.group(1), match.group(2)
    inherited = None
    right_ampm = re.search(r"(a\.?m\.?|p\.?m\.?)", right, flags=re.IGNORECASE)
    left_ampm = re.search(r"(a\.?m\.?|p\.?m\.?)", left, flags=re.IGNORECASE)
    if right_ampm and not left_ampm:
        inherited = right_ampm.group(1)
    start = _parse_clock(left, inherited)
    end = _parse_clock(right)
    if start is None or end is None:
        return []
    return _window_hours(start, end)


def _maybe_afternoon(hours: List[int], text: str) -> List[int]:
    if not hours:
        return hours
    if re.search(r"a\.?m\.?|p\.?m\.?|\d{1,2}:\d{2}|noon|midnight|midday", text):
        return hours
    if max(hours) < 12 and any(k in text for k in ("solar", "pv", "panel", "washing", "afternoon", "rooftop")):
        return [(h + 12) % 24 for h in hours]
    return hours


def _percentages_and_fractions(text: str) -> List[float]:
    values: List[float] = []
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*%", text):
        values.append(float(match.group(1)) / 100.0)
    for pattern, value in FRACTIONS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            values.append(value)
    return values


def _first_kwh(text: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*kwh", text, flags=re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _solar_factor(text: str) -> float:
    values = _percentages_and_fractions(text)
    if not values:
        return 1.0
    pct = values[0]
    remaining_words = (
        "drop to",
        "drops to",
        "down to",
        "leave",
        "leaves",
        "left",
        "treated as",
        "usable",
        "of the forecast",
        "of normal",
        "of the forecast solar",
        "remaining",
    )
    reduction_words = ("reduction", "reduced by", "reduce", "cut by")
    if any(word in text for word in remaining_words) and not any(word in text for word in reduction_words):
        return round(pct, 4)
    if any(word in text for word in reduction_words):
        return round(max(0.0, 1.0 - pct), 4)
    return round(pct, 4)


def interpret_note(note: str, note_index: int, battery: BatteryConfig) -> Dict[str, Any]:
    text = _normalize(note)
    hours = _maybe_afternoon(parse_hours_window(text), text)

    looks_like_noise = any(hint in text for hint in NO_OP_HINTS) and not any(
        hint in text for hint in ENERGY_HINTS
    )
    if looks_like_noise:
        return {
            "note_index": note_index,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": "Note does not affect today's energy schedule.",
        }

    if any(
        k in text
        for k in (
            "must not discharge",
            "not discharge",
            "do not discharge",
            "don't discharge",
            "cannot discharge",
            "no discharge",
        )
    ):
        return {
            "note_index": note_index,
            "applies": True,
            "directive_type": "no_discharge_window",
            "structured_adjustment": {"hours": hours},
            "explanation": "Battery discharge is disabled during the stated window.",
        }

    no_charge = any(
        k in text
        for k in (
            "do not charge",
            "don't charge",
            "not charge",
            "cannot charge",
            "no charging",
            "charging is disabled",
            "charging is unavailable",
            "charger will be isolated",
            "charging circuit",
        )
    ) or (
        "charg" in text
        and any(k in text for k in ("isolat", "unavailable", "disabled", "maintenance", "inspect", "outage"))
        and "discharge" not in text
    )
    if no_charge and "discharge" not in text:
        return {
            "note_index": note_index,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": hours},
            "explanation": "Battery charging is disabled during the stated window.",
        }

    if any(k in text for k in ("grid import", "grid intake", "feeder", "transformer", "substation")) or (
        "grid" in text and any(k in text for k in ("limit", "exceed", "at or below", "cap", "must not", "must stay"))
    ):
        max_grid = _first_kwh(text) or 0.0
        return {
            "note_index": note_index,
            "applies": True,
            "directive_type": "max_grid_window",
            "structured_adjustment": {"hours": hours, "max_grid_kwh": max_grid},
            "explanation": "Grid import is capped during the stated window.",
        }

    if any(k in text for k in ("keep at least", "remain in the battery", "minimum", "reserve", "emergency")) and (
        "battery" in text or "kwh" in text or "%" in text
    ):
        percents = _percentages_and_fractions(text)
        kwh = _first_kwh(text)
        if percents and ("capacity" in text or kwh is None):
            min_kwh = percents[0] * battery.capacity_kwh
        else:
            min_kwh = kwh or battery.minimum_energy_kwh
        return {
            "note_index": note_index,
            "applies": True,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {"hours": hours, "minimum_energy_kwh": float(min_kwh)},
            "explanation": "A higher battery reserve is required during the stated window.",
        }

    solarish = any(k in text for k in ("solar", "pv", "panel", "inverter", "cloud cover", "rooftop"))
    if solarish:
        factor = _solar_factor(text)
        return {
            "note_index": note_index,
            "applies": True,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": hours, "factor": factor},
            "explanation": "Usable solar is reduced during the stated window.",
        }

    return {
        "note_index": note_index,
        "applies": False,
        "directive_type": "no_op",
        "structured_adjustment": None,
        "explanation": "Note does not affect today's energy schedule.",
    }


def interpret_notes_locally(operator_notes: List[str], battery: BatteryConfig) -> List[Dict[str, Any]]:
    return [interpret_note(note, idx, battery) for idx, note in enumerate(operator_notes)]
