import pytest

from patient_causal_mcp.causal_engine import CausalAnalysisEngine
from patient_causal_mcp.datasets import DEFAULT_DATASET_ID, load_bundled_dataset
from patient_causal_mcp.server import DATASET_REGISTRY, describe_patient_data


@pytest.fixture()
def bundled_records() -> list[dict]:
    return load_bundled_dataset(DEFAULT_DATASET_ID)


def test_regression_adjustment_returns_estimate(bundled_records: list[dict]) -> None:
    result = CausalAnalysisEngine().estimate_causal_effect(
        bundled_records,
        exposure="late_night_screen_minutes",
        outcome="outcome_sleep_quality",
        treatment_rule={
            "type": "binary_threshold",
            "variable": "late_night_screen_minutes",
            "threshold": 120,
            "treated_condition": "<=",
        },
        adjustment_variables=["stress_score", "caffeine_mg", "prior_sleep_quality", "steps"],
        method="regression_adjustment",
    )
    assert isinstance(result["estimated_effect"], float)
    assert result["sample_size_used"] == 100


def test_g_formula_returns_potential_outcome_contrast(bundled_records: list[dict]) -> None:
    result = CausalAnalysisEngine().estimate_causal_effect(
        bundled_records,
        exposure="late_night_screen_minutes",
        outcome="outcome_sleep_quality",
        treatment_rule={
            "type": "binary_threshold",
            "variable": "late_night_screen_minutes",
            "threshold": 120,
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


def test_default_dataset_can_be_described_without_dataset_id() -> None:
    DATASET_REGISTRY.clear()
    result = describe_patient_data()
    assert result["number_of_days"] == 100


def test_invalid_variable_names_produce_useful_error(bundled_records: list[dict]) -> None:
    with pytest.raises(ValueError, match="Missing required column"):
        CausalAnalysisEngine().estimate_causal_effect(
            bundled_records,
            exposure="not_a_variable",
            outcome="outcome_sleep_quality",
            treatment_rule={"type": "binary_variable", "variable": "not_a_variable"},
            adjustment_variables=["stress_score"],
            method="regression_adjustment",
        )
