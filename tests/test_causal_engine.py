import pytest

from patient_causal_mcp.causal_engine import CausalAnalysisEngine
from patient_causal_mcp.server import DATASET_REGISTRY, describe_patient_data
from patient_causal_mcp.simulator import PatientSimulator


@pytest.fixture()
def simulated_records() -> list[dict]:
    return PatientSimulator().simulate(n_days=180, seed=123, scenario="sleep_screen_time")["full_data"]


def test_regression_adjustment_returns_estimate(simulated_records: list[dict]) -> None:
    result = CausalAnalysisEngine().estimate_causal_effect(
        simulated_records,
        exposure="late_night_screen_minutes",
        outcome="outcome_sleep_quality",
        treatment_rule={
            "type": "binary_threshold",
            "variable": "late_night_screen_minutes",
            "threshold": 30,
            "treated_condition": "<=",
        },
        adjustment_variables=["stress_score", "caffeine_mg", "prior_sleep_quality", "steps"],
        method="regression_adjustment",
    )
    assert isinstance(result["estimated_effect"], float)
    assert result["sample_size_used"] > 100


def test_g_formula_returns_potential_outcome_contrast(simulated_records: list[dict]) -> None:
    result = CausalAnalysisEngine().estimate_causal_effect(
        simulated_records,
        exposure="late_night_screen_minutes",
        outcome="outcome_sleep_quality",
        treatment_rule={
            "type": "binary_threshold",
            "variable": "late_night_screen_minutes",
            "threshold": 30,
            "treated_condition": "<=",
        },
        adjustment_variables=["stress_score", "caffeine_mg", "prior_sleep_quality", "steps"],
        method="g_formula",
    )
    assert isinstance(result["estimated_effect"], float)
    assert "plain_language_interpretation" in result


def test_invalid_dataset_id_gives_useful_error() -> None:
    DATASET_REGISTRY.clear()
    with pytest.raises(ValueError, match="Unknown dataset_id"):
        describe_patient_data(dataset_id="missing-dataset")


def test_invalid_variable_names_produce_useful_error(simulated_records: list[dict]) -> None:
    with pytest.raises(ValueError, match="Missing required column"):
        CausalAnalysisEngine().estimate_causal_effect(
            simulated_records,
            exposure="not_a_variable",
            outcome="outcome_sleep_quality",
            treatment_rule={"type": "binary_variable", "variable": "not_a_variable"},
            adjustment_variables=["stress_score"],
            method="regression_adjustment",
        )
