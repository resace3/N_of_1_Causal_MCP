from __future__ import annotations

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from patient_causal_mcp.server import TOOL_NAMES


def _parse_tool_result(result: object) -> dict:
    if getattr(result, "structuredContent", None) is not None:
        return result.structuredContent
    return json.loads(result.content[0].text)


def test_stdio_mcp_server_lists_tools_and_calls_dataset_summary() -> None:
    async def run() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "patient_causal_mcp.server"],
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                assert {tool.name for tool in tools.tools} == set(TOOL_NAMES)

                datasets = _parse_tool_result(
                    await session.call_tool("get_available_datasets", arguments={})
                )
                assert datasets["default_dataset_id"] == "patient_001_100_days"

                summary = _parse_tool_result(
                    await session.call_tool("describe_patient_data", arguments={})
                )
                assert summary["number_of_days"] == 100

    asyncio.run(asyncio.wait_for(run(), timeout=30))
