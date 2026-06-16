from patient_causal_mcp.dag import check_adjustment_set, generate_causal_dag


def test_generate_causal_dag_returns_edges() -> None:
    dag = generate_causal_dag(scenario="sleep_screen_time")
    assert dag["edges"]
    assert dag["dot"].startswith("digraph")
    assert "flowchart TD" in dag["mermaid"]


def test_check_adjustment_set_flags_missing_confounders() -> None:
    dag = generate_causal_dag(scenario="sleep_screen_time")
    result = check_adjustment_set(
        dag_edges=dag["edges"],
        exposure="late_night_screen_minutes",
        outcome="outcome_sleep_quality",
        adjustment_variables=["stress_score"],
    )
    assert result["is_reasonable"] is False
    assert "prior_sleep_quality" in result["likely_confounders_missing"]


def test_check_adjustment_set_accepts_default_confounders() -> None:
    dag = generate_causal_dag(scenario="sleep_screen_time")
    result = check_adjustment_set(
        dag_edges=dag["edges"],
        exposure="late_night_screen_minutes",
        outcome="outcome_sleep_quality",
        adjustment_variables=["stress_score", "caffeine_mg", "prior_sleep_quality", "steps"],
    )
    assert result["possible_mediators_adjusted_for"] == []
