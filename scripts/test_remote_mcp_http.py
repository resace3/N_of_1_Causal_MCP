"""Smoke-test a Streamable HTTP MCP endpoint.

Usage:
    python scripts/test_remote_mcp_http.py
    python scripts/test_remote_mcp_http.py http://localhost:8787/mcp
"""

from __future__ import annotations

import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from patient_causal_mcp.server import TOOL_NAMES


DEFAULT_URL = "http://localhost:8787/mcp"


async def main(url: str) -> None:
    async with streamablehttp_client(url) as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            expected = set(TOOL_NAMES)
            if names != expected:
                raise SystemExit(f"Unexpected tools: {sorted(names)} != {sorted(expected)}")
            result = await session.call_tool("get_available_datasets", arguments={})
            if not result.content:
                raise SystemExit("get_available_datasets returned no content")
            print(f"Connected to {url}")
            print("Tools:", ", ".join(TOOL_NAMES))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL))
