"""Direct Python example for exercising the MCP tool functions without a client."""

from __future__ import annotations

from patient_causal_mcp.server import (
    estimate_causal_effect,
    generate_causal_dag,
    get_available_datasets,
    simulate_intervention,
)


def main() -> None:
    datasets = get_available_datasets()
    dataset_id = datasets["default_dataset_id"]
    print(f"Dataset: {dataset_id}")
    print(generate_causal_dag("sleep_screen_time")["mermaid"])

    estimate = estimate_causal_effect(
        dataset_id=dataset_id,
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
    print(estimate["plain_language_interpretation"])

    intervention = simulate_intervention(
        dataset_id=dataset_id,
        intervention_name="Reduce late-night screen time by 60 minutes",
        intervention_rule={"operation": "add"},
        target_variable="late_night_screen_minutes",
        expected_change=-60,
        outcome="outcome_sleep_quality",
        adjustment_variables=["stress_score", "caffeine_mg", "prior_sleep_quality", "steps"],
    )
    print(intervention["plain_language_summary"])


if __name__ == "__main__":
    main()
