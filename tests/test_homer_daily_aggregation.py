from __future__ import annotations

import pandas as pd

from patient_causal_mcp.server import estimate_causal_effect, generate_causal_dag
from patient_causal_mcp.synthetic.homer_ha import (
    HOMER_DAILY_100_DAYS_ID,
    generate_homer_daily_rows,
)


def test_homer_daily_dataset_shape_dates_and_missingness() -> None:
    rows = generate_homer_daily_rows()

    assert len(rows) == 100
    assert rows[0]["date"] == "2026-01-01"
    assert rows[-1]["date"] == "2026-04-10"
    assert all(row["subject_id"] == "homer_simpson" for row in rows)
    assert all(row["synthetic_profile"] == "fictional_parody" for row in rows)
    for row in rows:
        assert all(value is not None for value in row.values())


def test_homer_daily_ranges_and_lag_columns() -> None:
    df = pd.DataFrame(generate_homer_daily_rows())

    assert df["steps"].between(1500, 13000).all()
    assert df["sleep_duration_hours"].between(3.5, 8.5).all()
    assert df["sleep_efficiency"].between(65, 95).all()
    assert df["heart_rate_mean"].between(55, 135).all()
    assert df["blood_pressure_systolic"].between(110, 165).all()
    assert df["blood_pressure_diastolic"].between(70, 105).all()
    assert df["caffeine_mg"].between(0, 500).all()
    assert df["prior_sleep_quality"].between(1, 10).all()
    assert df["prior_fatigue"].between(1, 10).all()
    assert df["prior_bp"].between(110, 165).all()
    assert df["prior_late_screen_minutes"].between(0, 260).all()
    assert df["prior_steps"].between(1500, 13000).all()
    assert df["prior_stress_score"].between(1, 10).all()


def test_homer_causal_sanity_confounding_and_associations() -> None:
    df = pd.DataFrame(generate_homer_daily_rows())
    high_risk = (df["prior_fatigue"] >= df["prior_fatigue"].median()).astype(int)

    assert df.loc[high_risk.eq(1), "sleep_nudge_received"].mean() > df.loc[
        high_risk.eq(0), "sleep_nudge_received"
    ].mean()
    assert df["late_night_screen_minutes"].corr(df["outcome_next_day_fatigue"]) > 0.2

    unadjusted = estimate_causal_effect(
        dataset_id=HOMER_DAILY_100_DAYS_ID,
        exposure="walk_nudge_received",
        outcome="outcome_mood_next_day",
        treatment_rule={"type": "binary_variable"},
        adjustment_variables=[],
        method="regression_adjustment",
    )
    adjusted = estimate_causal_effect(
        dataset_id=HOMER_DAILY_100_DAYS_ID,
        exposure="walk_nudge_received",
        outcome="outcome_mood_next_day",
        treatment_rule={"type": "binary_variable"},
        adjustment_variables=[
            "prior_fatigue",
            "prior_steps",
            "prior_stress_score",
            "is_workday",
            "baseline_activity_level",
        ],
        method="regression_adjustment",
    )
    assert abs(unadjusted["estimated_effect"] - adjusted["estimated_effect"]) > 0.01


def test_homer_dag_generation_includes_relevant_confounders() -> None:
    dag = generate_causal_dag(scenario="homer_walk_nudge_mood")

    assert dag["exposure"] == "walk_nudge_received"
    assert dag["outcome"] == "outcome_mood_next_day"
    assert "prior_fatigue" in dag["confounders"]
    assert "walk_nudge_received" in dag["dot"]
    assert "prior_steps" in dag["mermaid"]
