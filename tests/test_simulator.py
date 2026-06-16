from patient_causal_mcp.scenarios import SCENARIOS
from patient_causal_mcp.simulator import PatientSimulator


def test_simulator_returns_requested_number_of_rows() -> None:
    result = PatientSimulator().simulate(n_days=90, seed=123, scenario="sleep_screen_time")
    assert result["n_days"] == 90
    assert len(result["full_data"]) == 90
    assert result["dataset_id"]


def test_simulated_variables_within_realistic_bounds() -> None:
    result = PatientSimulator().simulate(n_days=180, seed=123, scenario="mixed_lifestyle")
    rows = result["full_data"]
    assert all(4 <= row["sleep_duration_hours"] <= 10 for row in rows)
    assert all(60 <= row["sleep_efficiency"] <= 98 for row in rows)
    assert all(500 <= row["steps"] <= 20000 for row in rows)
    assert all(0 <= row["caffeine_mg"] <= 500 for row in rows)
    assert all(0 <= row["stress_score"] <= 10 for row in rows)
    assert all(0 <= row["mood_score"] <= 10 for row in rows)
    assert all(0 <= row["morning_fatigue"] <= 10 for row in rows)
    assert all(95 <= row["blood_pressure_systolic"] <= 170 for row in rows)
    assert all(55 <= row["blood_pressure_diastolic"] <= 105 for row in rows)


def test_each_scenario_has_dag_edges() -> None:
    for scenario in SCENARIOS.values():
        assert scenario.dag_edges, scenario.name
        assert scenario.exposure
        assert scenario.outcome
