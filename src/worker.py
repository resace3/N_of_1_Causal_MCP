"""Cloudflare Python Worker entrypoint for the N-of-1 causal MCP server."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from workers import DurableObject, Response, WorkerEntrypoint

from patient_causal_mcp.server import TOOL_NAMES, create_cloudflare_mcp_server


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": (
        "Content-Type, Authorization, Mcp-Session-Id, MCP-Protocol-Version"
    ),
    "Access-Control-Expose-Headers": "Mcp-Session-Id",
}


def json_response(payload: dict[str, Any], status: int = 200) -> Response:
    """Create a JSON Worker response with permissive CORS headers."""

    return Response(
        json.dumps(payload),
        status=status,
        headers={"Content-Type": "application/json", **CORS_HEADERS},
    )


def health_payload() -> dict[str, Any]:
    """Return service metadata for / and /health."""

    return {
        "ok": True,
        "name": "patient-causal-mcp",
        "transport": "streamable-http",
        "mcp_endpoint": "/mcp",
        "auth": "none",
        "tools": TOOL_NAMES,
    }


def setup_server() -> tuple[Any, Any]:
    """Create the Cloudflare-configured FastMCP server and ASGI app."""

    mcp = create_cloudflare_mcp_server()
    return mcp, mcp.streamable_http_app()


class PatientCausalMCPServer(DurableObject):
    """Durable Object wrapper around the FastMCP Streamable HTTP ASGI app."""

    def __init__(self, ctx: Any, env: Any):
        self.ctx = ctx
        self.env = env
        self.mcp, self.app = setup_server()

    async def fetch(self, request: Any) -> Any:
        import asgi

        return await asgi.fetch(self.app, request, self.env, self.ctx)


class Default(WorkerEntrypoint):
    """Default Python Worker entrypoint."""

    async def fetch(self, request: Any) -> Any:
        parsed = urlparse(str(request.url))
        path = parsed.path or "/"
        method = str(getattr(request, "method", "GET")).upper()

        if method == "OPTIONS":
            return json_response({"ok": True})

        if path in {"/", "/health"}:
            return json_response(health_payload())

        if path.startswith("/mcp"):
            object_id = self.env.N_OF_1_MCP.idFromName("global")
            durable_object = self.env.N_OF_1_MCP.get(object_id)
            return await durable_object.fetch(request)

        return json_response(
            {
                "ok": False,
                "error": "not_found",
                "message": "Use the Streamable HTTP MCP endpoint at /mcp.",
                "mcp_endpoint": "/mcp",
            },
            status=404,
        )
