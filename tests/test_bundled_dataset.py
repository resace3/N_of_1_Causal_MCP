from patient_causal_mcp.datasets import DEFAULT_DATASET_ID, get_bundled_dataset_metadata, load_bundled_dataset
from patient_causal_mcp.scenarios import SCENARIOS
from patient_causal_mcp.server import create_mcp_server, get_available_datasets


def test_bundled_dataset_has_100_days() -> None:
    records = load_bundled_dataset(DEFAULT_DATASET_ID)
    assert len(records) == 100
    assert records[0]["date"] == "2026-01-01"
    assert records[-1]["date"] == "2026-04-10"


def test_bundled_dataset_has_sensor_financial_and_phone_columns() -> None:
    row = load_bundled_dataset(DEFAULT_DATASET_ID)[0]
    expected_columns = {
        "wearable_device_worn_hours",
        "heart_rate_variability_ms",
        "location_home_minutes",
        "motion_walking_minutes",
        "texts_sent",
        "calls_made",
        "total_screen_time_minutes",
        "social_app_minutes",
        "transactions_count",
        "card_spend_usd",
        "restaurant_spend_usd",
    }
    assert expected_columns.issubset(row)


def test_bundled_dataset_values_within_realistic_bounds() -> None:
    rows = load_bundled_dataset(DEFAULT_DATASET_ID)
    assert all(4 <= row["sleep_duration_hours"] <= 10 for row in rows)
    assert all(60 <= row["sleep_efficiency"] <= 98 for row in rows)
    assert all(500 <= row["steps"] <= 20000 for row in rows)
    assert all(0 <= row["caffeine_mg"] <= 500 for row in rows)
    assert all(0 <= row["stress_score"] <= 10 for row in rows)
    assert all(0 <= row["card_spend_usd"] <= 300 for row in rows)
    assert all(0 <= row["texts_sent"] <= 120 for row in rows)


def test_get_available_datasets_returns_default_dataset() -> None:
    result = get_available_datasets()
    assert result["default_dataset_id"] == DEFAULT_DATASET_ID
    assert result["datasets"][0]["n_days"] == 100


def test_mcp_server_does_not_expose_simulation_tool() -> None:
    server = create_mcp_server()
    tool_manager = server._tool_manager  # noqa: SLF001 - MCP SDK stores registered tools here.
    assert "simulate_patient_data" not in tool_manager._tools  # noqa: SLF001
    assert "get_available_datasets" in tool_manager._tools  # noqa: SLF001


def test_each_scenario_has_dag_edges() -> None:
    for scenario in SCENARIOS.values():
        assert scenario.dag_edges, scenario.name
        assert scenario.exposure
        assert scenario.outcome


def test_bundled_dataset_metadata_loads() -> None:
    metadata = get_bundled_dataset_metadata()
    assert metadata[0]["dataset_id"] == DEFAULT_DATASET_ID
    assert "wearable" in metadata[0]["description"]
