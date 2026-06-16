from __future__ import annotations

from typing import Any

from patient_causal_mcp.server import (
    TOOL_NAMES,
    create_cloudflare_mcp_server,
    create_mcp_server,
    get_available_datasets,
    get_available_scenarios,
)


def _registered_tool_names(server: Any) -> set[str]:
    return set(server._tool_manager._tools)  # noqa: SLF001 - FastMCP stores tools here.


def test_local_mcp_server_factory_constructs_expected_tools() -> None:
    server = create_mcp_server()

    assert _registered_tool_names(server) == set(TOOL_NAMES)
    assert "simulate_patient_data" not in _registered_tool_names(server)


def test_cloudflare_mcp_server_factory_constructs_expected_tools() -> None:
    server = create_cloudflare_mcp_server()

    assert _registered_tool_names(server) == set(TOOL_NAMES)
    assert hasattr(server, "streamable_http_app")
    assert callable(server.streamable_http_app)


def test_core_tool_functions_still_return_dictionaries() -> None:
    datasets = get_available_datasets()
    scenarios = get_available_scenarios()

    assert datasets["default_dataset_id"] == "patient_001_100_days"
    assert "datasets" in datasets
    assert "scenarios" in scenarios
    assert isinstance(scenarios["scenarios"], list)
