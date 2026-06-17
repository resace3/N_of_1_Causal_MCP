"""Small ASGI bridge for Cloudflare Python Workers.

FastMCP exposes Streamable HTTP as an ASGI app. Cloudflare Python Workers expose
Fetch-style Request/Response objects. This module adapts one request at a time
without adding FastAPI or another web framework.

The bridge intentionally collects ASGI response bodies instead of implementing
long-lived event-stream resumability. The MCP server is configured with
``json_response=True`` for Cloudflare so normal MCP initialize/list/call flows
produce finite JSON responses that work with this bridge.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlsplit


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": (
        "Content-Type, Authorization, Mcp-Session-Id, MCP-Protocol-Version"
    ),
    "Access-Control-Expose-Headers": "Mcp-Session-Id",
}


def _headers_to_scope(headers: Any) -> list[tuple[bytes, bytes]]:
    """Convert a Cloudflare/JS Headers object into ASGI header tuples."""

    if headers is None:
        return []
    items: Iterable[tuple[str, str]]
    if hasattr(headers, "entries"):
        items = [(str(key), str(value)) for key, value in headers.entries()]
    elif hasattr(headers, "items"):
        items = [(str(key), str(value)) for key, value in headers.items()]
    else:
        items = []
    return [(key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in items]


async def _read_request_body(request: Any) -> bytes:
    """Read a Cloudflare Request body into bytes."""

    if getattr(request, "body", None) is None:
        return b""
    if hasattr(request, "arrayBuffer"):
        array_buffer = await request.arrayBuffer()
        try:
            from js import Uint8Array

            return bytes(Uint8Array.new(array_buffer))
        except Exception:
            return bytes(array_buffer)
    if hasattr(request, "text"):
        return (await request.text()).encode("utf-8")
    return b""


def _response_headers(headers: list[tuple[bytes, bytes]]) -> dict[str, str]:
    """Convert ASGI response headers to a plain mapping for workers.Response."""

    output: dict[str, str] = {}
    for key, value in headers:
        output[key.decode("latin-1")] = value.decode("latin-1")
    output.update(CORS_HEADERS)
    return output


def _response(body: bytes, *, status: int, headers: dict[str, str]) -> Any:
    """Create a Cloudflare Worker response."""

    try:
        from workers import Response

        return Response(body, status=status, headers=headers)
    except Exception:
        from js import Response

        return Response.new(body, {"status": status, "headers": headers})


async def fetch(app: Any, request: Any, env: Any = None, ctx: Any = None) -> Any:
    """Invoke an ASGI app for a Cloudflare Request."""

    parsed = urlsplit(str(request.url))
    body = await _read_request_body(request)
    method = str(getattr(request, "method", "GET")).upper()
    response_status = 500
    response_headers: list[tuple[bytes, bytes]] = []
    response_chunks: list[bytes] = []
    received = False

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": parsed.scheme or "https",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": parsed.query.encode("utf-8"),
        "headers": _headers_to_scope(getattr(request, "headers", None)),
        "server": (parsed.hostname or "worker", parsed.port or 443),
        "client": ("0.0.0.0", 0),
        "root_path": "",
    }

    async def receive() -> dict[str, Any]:
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        nonlocal response_status, response_headers
        if message["type"] == "http.response.start":
            response_status = int(message["status"])
            response_headers = list(message.get("headers", []))
        elif message["type"] == "http.response.body":
            response_chunks.append(message.get("body", b""))

    await app(scope, receive, send)
    return _response(
        b"".join(response_chunks),
        status=response_status,
        headers=_response_headers(response_headers),
    )
