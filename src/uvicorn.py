"""Compatibility shim for Cloudflare Python Workers.

The Python MCP SDK may import uvicorn when constructing ASGI transports. The
Cloudflare Worker does not run uvicorn; pywrangler/workerd invokes `src/worker.py`
directly. This module exists only to keep optional uvicorn imports from failing
inside the Worker runtime.
"""


def run(*args, **kwargs):  # type: ignore[no-untyped-def]
    """Fail clearly if code tries to run uvicorn inside Cloudflare Workers."""

    raise RuntimeError("uvicorn.run is not available inside Cloudflare Python Workers.")
