import json
import urllib.request

BASE_URL = "http://localhost:8000"


def test_health():
    req = urllib.request.Request(f"{BASE_URL}/health")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data.get("status") == "ok"
        print("✓ Health Check Passed")


def test_optimization_logic():
    payload = {
        "scenario_id": "STEP4-TEST",
        "operator_notes": [
            "Reduce solar by 80% between 1 PM and 3 PM.",
            "Do not charge battery from 2 PM to 4 PM."
        ],
        "hours": [
            {"hour": h, "demand_kwh": 100, "solar_kwh": 100 if 8 <= h <= 16 else 0,
             "tariff_bdt_per_kwh": 10.0 if 18 <= h <= 20 else 5.0}
            for h in range(24)
        ],
        "battery": {
            "capacity_kwh": 500,
            "initial_energy_kwh": 200,
            "minimum_energy_kwh": 50,
            "max_charge_kwh_per_hour": 100,
            "max_discharge_kwh_per_hour": 100
        }
    }

    req = urllib.request.Request(
        f"{BASE_URL}/optimize-energy",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())

        # Schema assertions
        assert "directive_interpretation" in data
        assert "hourly_plan" in data
        assert len(data["hourly_plan"]) == 24
        assert data["total_grid_kwh"] >= 0
        assert data["total_cost_bdt"] >= 0

        # Verify no-charge constraint (Hours 14 & 15 -> 2 PM to 4 PM)
        for entry in data["hourly_plan"]:
            if entry["hour"] in [14, 15]:
                assert entry["battery_action"] != "charge", f"Battery charged during restricted hour {entry['hour']}"

        print("✓ Optimization Test Passed")


if __name__ == "__main__":
    try:
        test_health()
        test_optimization_logic()
        print("\nAll integration tests passed successfully!")
    except Exception as e:
        print(f"\nTest failed: {e}")