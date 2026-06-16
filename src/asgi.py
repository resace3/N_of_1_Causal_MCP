"""Minimal ASGI bridge for Cloudflare Python Workers.

Cloudflare Python Workers expose JavaScript Request/Response objects, while the
Python MCP SDK returns an ASGI application for Streamable HTTP. This module
adapts between those two interfaces without introducing a web framework.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlsplit


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


def _response_headers(headers: list[tuple[bytes, bytes]]) -> Any:
    """Create JS Headers from ASGI response headers."""

    from js import Headers

    js_headers = Headers.new()
    for key, value in headers:
        js_headers.append(key.decode("latin-1"), value.decode("latin-1"))
    return js_headers


def _append_cors(headers: Any) -> Any:
    """Append permissive CORS headers for MCP Inspector testing."""

    headers.set("Access-Control-Allow-Origin", "*")
    headers.set("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    headers.set(
        "Access-Control-Allow-Headers",
        "Content-Type, Authorization, Mcp-Session-Id, MCP-Protocol-Version",
    )
    headers.set("Access-Control-Expose-Headers", "Mcp-Session-Id")
    return headers


async def _run_asgi_collect(app: Any, scope: dict[str, Any], body: bytes) -> tuple[int, Any, bytes]:
    """Run an ASGI app and collect a non-streaming response."""

    response_status = 500
    response_headers: list[tuple[bytes, bytes]] = []
    chunks: list[bytes] = []
    received = False

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
            chunks.append(message.get("body", b""))

    await app(scope, receive, send)
    return response_status, _response_headers(response_headers), b"".join(chunks)


async def _run_asgi_stream(app: Any, scope: dict[str, Any], body: bytes, ctx: Any) -> Any:
    """Run an ASGI app into a TransformStream for event-stream responses."""

    from js import Response, TransformStream

    stream = TransformStream.new()
    writer = stream.writable.getWriter()
    response_status = 200
    response_headers: list[tuple[bytes, bytes]] = [
        (b"content-type", b"text/event-stream; charset=utf-8")
    ]
    received = False
    started = asyncio.Event()

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
            started.set()
        elif message["type"] == "http.response.body":
            chunk = message.get("body", b"")
            if chunk:
                await writer.write(chunk)
            if not message.get("more_body", False):
                await writer.close()

    task = asyncio.create_task(app(scope, receive, send))
    if ctx is not None and hasattr(ctx, "waitUntil"):
        ctx.waitUntil(task)
    await started.wait()
    headers = _append_cors(_response_headers(response_headers))
    return Response.new(stream.readable, {"status": response_status, "headers": headers})


async def fetch(app: Any, request: Any, env: Any = None, ctx: Any = None) -> Any:
    """Handle a Cloudflare Request by invoking an ASGI app."""

    from js import Response

    parsed = urlsplit(str(request.url))
    body = await _read_request_body(request)
    headers = _headers_to_scope(getattr(request, "headers", None))
    method = str(getattr(request, "method", "GET")).upper()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": parsed.scheme or "https",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": parsed.query.encode("utf-8"),
        "headers": headers,
        "server": (parsed.hostname or "worker", parsed.port or 443),
        "client": ("0.0.0.0", 0),
        "root_path": "",
    }

    accept_header = ""
    request_headers = getattr(request, "headers", None)
    if request_headers is not None and hasattr(request_headers, "get"):
        accept_header = str(request_headers.get("accept") or "")

    if "text/event-stream" in accept_header.lower():
        return await _run_asgi_stream(app, scope, body, ctx)

    status, response_headers, response_body = await _run_asgi_collect(app, scope, body)
    response_headers = _append_cors(response_headers)
    return Response.new(response_body, {"status": status, "headers": response_headers})
