from __future__ import annotations

from patient_causal_mcp.server import (
    aggregate_ha_states_daily,
    describe_patient_data,
    export_dataset,
    get_available_datasets,
    propose_causal_question,
    query_ha_states,
    run_target_trial_emulation,
)


def test_dataset_discovery_lists_homer_datasets() -> None:
    datasets = get_available_datasets()
    dataset_ids = {item["dataset_id"] for item in datasets["datasets"]}

    assert "homer_simpson_ha_states_30_days" in dataset_ids
    assert "homer_simpson_ha_states_100_days" in dataset_ids
    assert "homer_simpson_daily_100_days" in dataset_ids
    assert "homer_simpson_ha_sqlite_demo_30_days" in dataset_ids


def test_describe_handles_homer_raw_and_daily() -> None:
    daily = describe_patient_data(
        dataset_id="homer_simpson_daily_100_days",
        variables=["steps", "sleep_nudge_received"],
    )
    raw = describe_patient_data(dataset_id="homer_simpson_ha_states_30_days")

    assert daily["number_of_days"] == 100
    assert raw["states_rows"] >= 25_000
    assert raw["unique_entities"] >= 80
    assert "sensor" in raw["domain_counts"]


def test_export_homer_tables_csv_json_and_sql() -> None:
    meta_csv = export_dataset(
        dataset_id="homer_simpson_ha_states_30_days",
        format="csv",
        table="states_meta",
    )
    normalized = export_dataset(
        dataset_id="homer_simpson_ha_states_30_days",
        format="json",
        table="normalized",
    )
    sql = export_dataset(
        dataset_id="homer_simpson_ha_states_30_days",
        format="sql",
        table="states",
    )

    assert meta_csv["serialized_dataset"].splitlines()[0].startswith("metadata_id,entity_id")
    assert {"states", "states_meta", "state_attributes"} <= set(
        normalized["serialized_dataset"]
    )
    assert "CREATE TABLE states" in sql["serialized_dataset"]


def test_query_and_aggregate_homer_ha_states() -> None:
    query = query_ha_states(
        dataset_id="homer_simpson_ha_states_30_days",
        domain="device_tracker",
        limit=5,
    )
    aggregate = aggregate_ha_states_daily(dataset_id="homer_simpson_ha_states_30_days")

    assert query["rows_returned"] == 5
    assert all(row["domain"] == "device_tracker" for row in query["rows"])
    assert aggregate["rows_returned"] == 30
    assert aggregate["daily_rows"][0]["subject_id"] == "homer_simpson"


def test_homer_questions_and_prebuilt_target_trial() -> None:
    questions = propose_causal_question(dataset_id="homer_simpson_daily_100_days")
    trial = run_target_trial_emulation(
        dataset_id="homer_simpson_daily_100_days",
        assignment_time="walk nudge demo",
        treatment_strategies=[],
        outcome="outcome_mood_next_day",
    )

    assert any(
        item["exposure"] == "walk_nudge_received"
        for item in questions["proposed_questions"]
    )
    assert trial["trial_protocol"]["assignment_time"] == "Morning low-activity nudge decision"
    assert trial["causal_estimate"]["exposure"] == "walk_nudge_received"
