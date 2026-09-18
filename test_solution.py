import json
import urllib.request

BASE_URL = "http://localhost:8000"


def test_health():
    with urllib.request.urlopen(f"{BASE_URL}/health") as response:
        assert response.status == 200
        assert json.loads(response.read().decode())["status"] == "ok"


def test_optimization_logic():
    payload = {
        "scenario_id": "STEP4-TEST",
        "operator_notes": [
            "Reduce solar by 80% between 1 PM and 3 PM.",
            "Do not charge battery from 2 PM to 4 PM.",
        ],
        "hours": [
            {
                "hour": hour,
                "demand_kwh": 100,
                "solar_kwh": 100 if 8 <= hour <= 16 else 0,
                "tariff_bdt_per_kwh": 10.0 if 18 <= hour <= 20 else 5.0,
            }
            for hour in range(24)
        ],
        "battery": {
            "capacity_kwh": 500,
            "initial_energy_kwh": 200,
            "minimum_energy_kwh": 50,
            "max_charge_kwh_per_hour": 100,
            "max_discharge_kwh_per_hour": 100,
        },
    }
    request = urllib.request.Request(
        f"{BASE_URL}/optimize-energy",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        assert response.status == 200
        data = json.loads(response.read().decode())
        assert len(data["directive_interpretation"]) == 2
        assert len(data["hourly_plan"]) == 24
        assert data["hourly_plan"][-1]["battery_energy_after_kwh"] == 200.0
        assert data["total_grid_kwh"] >= 0
        assert data["total_cost_bdt"] >= 0
        for entry in data["hourly_plan"]:
            if entry["hour"] in [14, 15]:
                assert entry["battery_action"] != "charge"


if __name__ == "__main__":
    test_health()
    test_optimization_logic()
    print("All integration tests passed successfully!")
