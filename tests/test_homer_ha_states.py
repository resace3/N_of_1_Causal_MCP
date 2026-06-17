from __future__ import annotations

import json

import pytest

from patient_causal_mcp.synthetic.homer_ha import (
    ALLOWED_ZONES,
    HOMER_HA_STATES_30_DAYS_ID,
    generate_homer_ha_dataset,
    query_homer_ha_states,
    stable_dataset_hash,
)


@pytest.fixture(scope="module")
def homer_30():
    return generate_homer_ha_dataset(HOMER_HA_STATES_30_DAYS_ID)


def test_homer_ha_schema_and_row_volume(homer_30) -> None:
    required = {
        "state_id",
        "metadata_id",
        "entity_id",
        "state",
        "attributes_id",
        "last_updated_ts",
        "old_state_id",
        "context_id_bin",
        "origin_idx",
        "iso_timestamp",
        "date",
        "domain",
        "unit",
    }

    assert len(homer_30.states) >= 25_000
    assert len(homer_30.states_meta) >= 80
    assert required.issubset(homer_30.states[0])
    assert len({row["entity_id"] for row in homer_30.states_meta}) == len(homer_30.states_meta)


def test_homer_ha_foreign_keys_and_old_state_links(homer_30) -> None:
    metadata_ids = {row["metadata_id"] for row in homer_30.states_meta}
    attribute_ids = {row["attributes_id"] for row in homer_30.state_attributes}
    states_by_id = {row["state_id"]: row for row in homer_30.states}

    assert [row["state_id"] for row in homer_30.states] == list(range(1, len(homer_30.states) + 1))
    for row in homer_30.states:
        assert row["metadata_id"] in metadata_ids
        assert row["attributes_id"] in attribute_ids
        old_state_id = row["old_state_id"]
        if old_state_id is not None:
            old = states_by_id[old_state_id]
            assert old["state_id"] < row["state_id"]
            assert old["entity_id"] == row["entity_id"]


def test_homer_attributes_reuse_and_mark_synthetic(homer_30) -> None:
    assert len(homer_30.state_attributes) < len(homer_30.states_meta) + 5
    for row in homer_30.state_attributes:
        attrs = json.loads(row["shared_attrs"])
        assert attrs["synthetic_subject"] == "homer_simpson"
        assert attrs["synthetic_profile"] == "fictional_parody"
        assert attrs["privacy_level"] == "synthetic"


def test_homer_value_ranges_and_state_domains(homer_30) -> None:
    battery_rows = [row for row in homer_30.states if "battery_level" in row["entity_id"]]
    for row in battery_rows:
        assert 0 <= float(row["state"]) <= 100

    for row in homer_30.states:
        if row["domain"] == "binary_sensor":
            assert row["state"] in {"on", "off"}
        if row["domain"] == "device_tracker":
            assert row["state"] in ALLOWED_ZONES

    heart_rates = [
        float(row["state"])
        for row in homer_30.states
        if row["entity_id"] == "sensor.homer_watch_heart_rate"
    ]
    assert min(heart_rates) >= 55
    assert max(heart_rates) <= 135


def test_homer_generation_is_deterministic_and_seeded() -> None:
    assert stable_dataset_hash(HOMER_HA_STATES_30_DAYS_ID) == stable_dataset_hash(
        HOMER_HA_STATES_30_DAYS_ID
    )
    default = generate_homer_ha_dataset(HOMER_HA_STATES_30_DAYS_ID)
    different = generate_homer_ha_dataset(HOMER_HA_STATES_30_DAYS_ID, seed=742_002)
    assert default.states[25]["state"] != different.states[25]["state"]


def test_homer_query_filters_entity_time_and_attributes() -> None:
    result = query_homer_ha_states(
        dataset_id=HOMER_HA_STATES_30_DAYS_ID,
        entity_id="sensor.homer_watch_heart_rate",
        start="2026-01-02T00:00:00-05:00",
        end="2026-01-03T23:59:59-05:00",
        limit=10,
        include_attributes=True,
        parse_numeric=True,
    )

    assert result["rows_returned"] == 10
    assert result["truncated"] is True
    assert all(row["entity_id"] == "sensor.homer_watch_heart_rate" for row in result["rows"])
    assert all(row["attributes"]["synthetic_subject"] == "homer_simpson" for row in result["rows"])
    assert all(isinstance(row["numeric_state"], float) for row in result["rows"])
