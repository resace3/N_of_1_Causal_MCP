from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from patient_causal_mcp.datasets import get_bundled_dataset_metadata, load_bundled_dataset
from patient_causal_mcp.raw_events import (
    DISALLOWED_RAW_EVENT_FEATURE_COLUMNS,
    RAW_EVENT_COLUMNS,
    RAW_EVENT_DATASET_ID,
    REQUIRED_RAW_ENTITY_IDS,
)
from patient_causal_mcp.server import get_available_datasets


RAW_EVENT_PATH = Path("src/patient_causal_mcp/data/patient_001_raw_events_30_days.csv")


@pytest.fixture(scope="module")
def raw_events() -> pd.DataFrame:
    return pd.read_csv(RAW_EVENT_PATH)


def test_raw_event_file_exists() -> None:
    assert RAW_EVENT_PATH.exists()


def test_required_raw_entity_id_count_is_108() -> None:
    assert len(REQUIRED_RAW_ENTITY_IDS) == 108


def test_raw_event_file_is_long_format(raw_events: pd.DataFrame) -> None:
    assert raw_events.columns.tolist() == RAW_EVENT_COLUMNS


def test_raw_event_file_has_expected_row_count(raw_events: pd.DataFrame) -> None:
    assert raw_events.shape == (3240, 7)


def test_raw_event_file_has_at_least_100_unique_entity_ids(raw_events: pd.DataFrame) -> None:
    assert raw_events["entity_id"].nunique() >= 100


def test_raw_event_file_has_exact_required_entity_set(raw_events: pd.DataFrame) -> None:
    assert set(raw_events["entity_id"]) == set(REQUIRED_RAW_ENTITY_IDS)


def test_raw_event_file_has_no_daily_aggregate_feature_columns(raw_events: pd.DataFrame) -> None:
    assert DISALLOWED_RAW_EVENT_FEATURE_COLUMNS.isdisjoint(raw_events.columns)


def test_required_entity_ids_are_row_values_not_columns(raw_events: pd.DataFrame) -> None:
    assert set(REQUIRED_RAW_ENTITY_IDS).isdisjoint(raw_events.columns)


def test_raw_event_file_has_no_missing_required_fields(raw_events: pd.DataFrame) -> None:
    assert int(raw_events[RAW_EVENT_COLUMNS].isna().sum().sum()) == 0


def test_raw_event_file_date_range_is_30_days(raw_events: pd.DataFrame) -> None:
    timestamps = pd.to_datetime(raw_events["timestamp"])
    assert timestamps.min().strftime("%Y-%m-%d") == "2026-01-01"
    assert timestamps.max().strftime("%Y-%m-%d") == "2026-01-30"
    assert timestamps.dt.normalize().nunique() == 30


def test_raw_event_file_is_timestamp_sorted(raw_events: pd.DataFrame) -> None:
    timestamps = pd.to_datetime(raw_events["timestamp"])
    assert timestamps.is_monotonic_increasing


def test_raw_event_dataset_loader_can_load_records(raw_events: pd.DataFrame) -> None:
    records = load_bundled_dataset(RAW_EVENT_DATASET_ID)
    assert len(records) == raw_events.shape[0]
    assert set(records[0]) == set(RAW_EVENT_COLUMNS)


def test_raw_event_dataset_is_listed_in_metadata() -> None:
    metadata = {item["dataset_id"]: item for item in get_bundled_dataset_metadata()}
    assert RAW_EVENT_DATASET_ID in metadata
    assert metadata[RAW_EVENT_DATASET_ID]["dataset_type"] == "raw_events_long_format"
    assert metadata[RAW_EVENT_DATASET_ID]["n_unique_entity_ids"] == 108


def test_raw_event_dataset_is_available_from_mcp_discovery() -> None:
    result = get_available_datasets()
    dataset_ids = {item["dataset_id"] for item in result["datasets"]}
    assert RAW_EVENT_DATASET_ID in dataset_ids
    assert RAW_EVENT_DATASET_ID in result["loaded_dataset_ids"]


def test_raw_event_patient_id_is_single_patient(raw_events: pd.DataFrame) -> None:
    assert raw_events["patient_id"].nunique() == 1
    assert raw_events["patient_id"].iloc[0] == "patient-001"


def test_raw_event_sources_and_domains_are_populated(raw_events: pd.DataFrame) -> None:
    assert raw_events["source"].nunique() >= 4
    assert raw_events["domain"].nunique() >= 8
    assert (raw_events["source"].str.len() > 0).all()
    assert (raw_events["domain"].str.len() > 0).all()


@pytest.mark.parametrize("entity_id", REQUIRED_RAW_ENTITY_IDS)
def test_each_required_entity_id_appears(raw_events: pd.DataFrame, entity_id: str) -> None:
    assert entity_id in set(raw_events["entity_id"])


@pytest.mark.parametrize("entity_id", REQUIRED_RAW_ENTITY_IDS)
def test_each_required_entity_id_repeats_across_30_days(
    raw_events: pd.DataFrame,
    entity_id: str,
) -> None:
    entity_rows = raw_events.loc[raw_events["entity_id"] == entity_id]
    assert entity_rows.shape[0] == 30


@pytest.mark.parametrize("entity_id", REQUIRED_RAW_ENTITY_IDS)
def test_each_required_entity_id_has_nonempty_state(
    raw_events: pd.DataFrame,
    entity_id: str,
) -> None:
    states = raw_events.loc[raw_events["entity_id"] == entity_id, "state"].astype(str)
    assert states.str.len().min() > 0


@pytest.mark.parametrize("column", RAW_EVENT_COLUMNS)
def test_raw_event_required_column_has_values(raw_events: pd.DataFrame, column: str) -> None:
    assert raw_events[column].astype(str).str.len().min() > 0
