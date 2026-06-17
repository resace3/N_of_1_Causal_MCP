"""Bundled static patient datasets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Any

import pandas as pd

from patient_causal_mcp.raw_events import RAW_EVENT_DATASET_ID
from patient_causal_mcp.utils import dataframe_to_records


DEFAULT_DATASET_ID = "patient_001_100_days"


@dataclass(frozen=True)
class BundledDataset:
    """Metadata for a dataset bundled with the package."""

    dataset_id: str
    filename: str
    metadata_filename: str


BUNDLED_DATASETS: dict[str, BundledDataset] = {
    DEFAULT_DATASET_ID: BundledDataset(
        dataset_id=DEFAULT_DATASET_ID,
        filename="patient_001_100_days.csv",
        metadata_filename="patient_001_100_days_metadata.json",
    ),
    RAW_EVENT_DATASET_ID: BundledDataset(
        dataset_id=RAW_EVENT_DATASET_ID,
        filename="patient_001_raw_events_30_days.csv",
        metadata_filename="patient_001_raw_events_30_days_metadata.json",
    ),
}


def load_bundled_dataset(dataset_id: str = DEFAULT_DATASET_ID) -> list[dict[str, Any]]:
    """Load a bundled static dataset as JSON-style records."""

    if dataset_id not in BUNDLED_DATASETS:
        valid = ", ".join(sorted(BUNDLED_DATASETS))
        raise ValueError(
            f"Unknown bundled dataset_id '{dataset_id}'. Available bundled datasets: {valid}."
        )
    dataset = BUNDLED_DATASETS[dataset_id]
    data_path = resources.files("patient_causal_mcp").joinpath("data", dataset.filename)
    with resources.as_file(data_path) as path:
        df = pd.read_csv(path)
    return dataframe_to_records(df)


def get_bundled_dataset_metadata() -> list[dict[str, Any]]:
    """Return metadata for all bundled datasets."""

    metadata: list[dict[str, Any]] = []
    for dataset in BUNDLED_DATASETS.values():
        metadata_path = resources.files("patient_causal_mcp").joinpath(
            "data", dataset.metadata_filename
        )
        with resources.as_file(metadata_path) as path:
            item = json.loads(path.read_text())
        item["dataset_id"] = dataset.dataset_id
        item["filename"] = dataset.filename
        metadata.append(item)
    return metadata
