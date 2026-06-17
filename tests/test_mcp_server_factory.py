from __future__ import annotations

from typing import Any

import pytest

from patient_causal_mcp.server import (
    PUBLIC_SYNTHETIC_ONLY_ERROR,
    TOOL_NAMES,
    create_cloudflare_mcp_server,
    create_mcp_server,
    describe_patient_data,
    export_dataset,
    generate_causal_dag,
    get_available_datasets,
    get_available_scenarios,
)

EXPECTED_TOOL_NAMES = [
    "get_available_datasets",
    "get_available_scenarios",
    "describe_patient_data",
    "propose_causal_question",
    "estimate_causal_effect",
    "run_target_trial_emulation",
    "generate_causal_dag",
    "check_adjustment_set",
    "simulate_intervention",
    "export_dataset",
    "query_ha_states",
    "aggregate_ha_states_daily",
]


def _registered_tool_names(server: Any) -> set[str]:
    return set(server._tool_manager._tools)  # noqa: SLF001 - FastMCP stores tools here.


def _registered_tool(server: Any, name: str) -> Any:
    return server._tool_manager._tools[name]  # noqa: SLF001 - FastMCP stores tools here.


def test_tool_names_are_exact_expected_list() -> None:
    assert TOOL_NAMES == EXPECTED_TOOL_NAMES


def test_local_mcp_server_factory_constructs_expected_tools() -> None:
    server = create_mcp_server()

    assert server is not None
    assert _registered_tool_names(server) == set(EXPECTED_TOOL_NAMES)
    assert "simulate_patient_data" not in _registered_tool_names(server)


def test_cloudflare_mcp_server_factory_constructs_expected_tools() -> None:
    server = create_cloudflare_mcp_server()

    assert server is not None
    assert _registered_tool_names(server) == set(EXPECTED_TOOL_NAMES)
    assert hasattr(server, "streamable_http_app")
    assert callable(server.streamable_http_app)


def test_cloudflare_mcp_server_rejects_caller_supplied_records() -> None:
    server = create_cloudflare_mcp_server()
    tool = _registered_tool(server, "describe_patient_data")

    assert "data_records" not in tool.parameters["properties"]

    with pytest.raises(ValueError, match="Caller-supplied data_records") as exc_info:
        tool.fn(data_records=[{"date": "2026-01-01", "steps": 1}])

    assert str(exc_info.value) == PUBLIC_SYNTHETIC_ONLY_ERROR


def test_cloudflare_mcp_server_allows_bundled_synthetic_dataset_ids() -> None:
    server = create_cloudflare_mcp_server()
    tool = _registered_tool(server, "describe_patient_data")

    summary = tool.fn(dataset_id="patient_001_100_days", variables=["steps"])

    assert summary["number_of_days"] == 100
    assert "steps" in summary["numeric_summaries"]


def test_local_mcp_server_still_accepts_caller_supplied_records() -> None:
    server = create_mcp_server()
    tool = _registered_tool(server, "describe_patient_data")

    summary = tool.fn(data_records=[{"date": "2026-01-01", "steps": 1}])

    assert summary["number_of_days"] == 1


def test_core_tool_functions_still_return_dictionaries() -> None:
    datasets = get_available_datasets()
    scenarios = get_available_scenarios()
    summary = describe_patient_data()
    dag = generate_causal_dag(scenario="mixed_lifestyle")
    exported = export_dataset(format="json")

    assert isinstance(datasets, dict)
    assert datasets["default_dataset_id"] == "patient_001_100_days"
    assert "datasets" in datasets
    assert isinstance(scenarios, dict)
    assert "scenarios" in scenarios
    assert isinstance(scenarios["scenarios"], list)
    assert isinstance(summary, dict)
    assert summary["number_of_days"] == 100
    assert isinstance(dag, dict)
    assert dag["exposure"] == "intervention_received"
    assert isinstance(exported, dict)
    assert "serialized_dataset" in exported
    assert isinstance(exported["serialized_dataset"], list)
