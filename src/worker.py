"""Cloudflare Python Worker entrypoint for the N-of-1 causal MCP server."""

from __future__ import annotations

import json
from typing import Any

from patient_causal_mcp.server import TOOL_NAMES, create_cloudflare_mcp_server

try:  # The workers module exists only in the Cloudflare Python runtime.
    from workers import DurableObject
except Exception:  # pragma: no cover - local tests import setup_server without Workers.

    class DurableObject:  # type: ignore[no-redef]
        """Local import fallback for tests outside Cloudflare Workers."""

        pass


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, Mcp-Session-Id, MCP-Protocol-Version",
    "Access-Control-Expose-Headers": "Mcp-Session-Id",
}


def setup_server() -> tuple[Any, Any]:
    """Create the Cloudflare-configured FastMCP server and ASGI app."""

    mcp = create_cloudflare_mcp_server()
    app = mcp.streamable_http_app()
    try:
        from starlette.middleware.cors import CORSMiddleware

        app = CORSMiddleware(
            app,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization", "Mcp-Session-Id", "MCP-Protocol-Version"],
            expose_headers=["Mcp-Session-Id"],
        )
    except Exception:
        # The ASGI bridge appends CORS headers even if Starlette middleware is
        # unavailable in a constrained Worker runtime.
        pass
    return mcp, app


def _json_response(payload: dict[str, Any], status: int = 200) -> Any:
    """Create a Cloudflare Response with JSON and CORS headers."""

    from js import Response

    headers = {"Content-Type": "application/json", **CORS_HEADERS}
    return Response.new(json.dumps(payload), {"status": status, "headers": headers})


def _health_payload() -> dict[str, Any]:
    """Return service metadata for / and /health."""

    return {
        "ok": True,
        "name": "patient-causal-mcp",
        "transport": "streamable-http",
        "mcp_endpoint": "/mcp",
        "tools": TOOL_NAMES,
        "auth": "authless-demo",
    }


class PatientCausalMCPServer(DurableObject):
    """Durable Object wrapper for the FastMCP ASGI app."""

    def __init__(self, ctx: Any, env: Any):
        self.ctx = ctx
        self.env = env
        self.mcp, self.app = setup_server()

    async def on_fetch(self, request: Any, env: Any, ctx: Any) -> Any:
        import asgi

        return await asgi.fetch(self.app, request, self.env, self.ctx)

    async def fetch(self, request: Any) -> Any:
        import asgi

        return await asgi.fetch(self.app, request, self.env, self.ctx)


async def on_fetch(request: Any, env: Any) -> Any:
    """Route Worker HTTP requests."""

    from js import URL

    url = URL.new(request.url)
    path = str(url.pathname)
    method = str(getattr(request, "method", "GET")).upper()

    if method == "OPTIONS":
        return _json_response({"ok": True})

    if path in {"/", "/health"}:
        return _json_response(_health_payload())

    if path.startswith("/mcp") or path.startswith("/sse"):
        object_id = env.N_OF_1_MCP.idFromName("global")
        durable_object = env.N_OF_1_MCP.get(object_id)
        if hasattr(durable_object, "fetch"):
            return await durable_object.fetch(request)
        return await durable_object.on_fetch(request, env, None)

    return _json_response(
        {
            "ok": False,
            "error": "not_found",
            "message": "Use the Streamable HTTP MCP endpoint at /mcp.",
            "mcp_endpoint": "/mcp",
        },
        status=404,
    )
