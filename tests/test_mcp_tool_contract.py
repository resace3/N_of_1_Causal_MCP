from __future__ import annotations

import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from patient_causal_mcp.server import TOOL_NAMES, create_mcp_server


EXPECTED_TOOL_NAMES = TOOL_NAMES


def _tool_names_from_server() -> set[str]:
    server = create_mcp_server()
    return set(server._tool_manager._tools)  # noqa: SLF001 - MCP SDK stores registered tools here.


def _parse_tool_result(result: object) -> dict:
    if getattr(result, "structuredContent", None) is not None:
        return result.structuredContent
    return json.loads(result.content[0].text)


def test_tool_count_is_exact() -> None:
    assert len(_tool_names_from_server()) == len(EXPECTED_TOOL_NAMES)


def test_simulate_patient_data_tool_is_absent() -> None:
    assert "simulate_patient_data" not in _tool_names_from_server()


def test_expected_tools_are_registered_as_exact_set() -> None:
    assert _tool_names_from_server() == set(EXPECTED_TOOL_NAMES)


def test_expected_tools_are_sorted_for_docs() -> None:
    assert EXPECTED_TOOL_NAMES == [
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
    ]


def test_mcp_stdio_session_can_call_core_tools() -> None:
    async def run() -> None:
        params = StdioServerParameters(
            command="python",
            args=["-m", "patient_causal_mcp.server"],
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert names == set(EXPECTED_TOOL_NAMES)

                datasets = _parse_tool_result(
                    await session.call_tool("get_available_datasets", arguments={})
                )
                assert datasets["default_dataset_id"] == "patient_001_100_days"
                dataset_ids = {item["dataset_id"] for item in datasets["datasets"]}
                assert "patient_001_100_days" in dataset_ids
                assert "patient_001_raw_events_30_days" in dataset_ids

                summary = _parse_tool_result(
                    await session.call_tool(
                        "describe_patient_data",
                        arguments={
                            "variables": [
                                "sleep_duration_hours",
                                "steps",
                                "texts_sent",
                                "card_spend_usd",
                                "outcome_sleep_quality",
                            ]
                        },
                    )
                )
                assert summary["number_of_days"] == 100
                assert "card_spend_usd" in summary["numeric_summaries"]

                dag = _parse_tool_result(
                    await session.call_tool(
                        "generate_causal_dag",
                        arguments={"scenario": "sleep_screen_time"},
                    )
                )
                assert dag["exposure"] == "late_night_screen_minutes"
                assert dag["outcome"] == "outcome_sleep_quality"

    asyncio.run(run())
