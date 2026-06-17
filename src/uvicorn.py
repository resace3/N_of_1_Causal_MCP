"""Compatibility shim for Cloudflare Python Workers.

The Worker does not run uvicorn. This module only prevents optional imports
from failing in constrained Worker environments.
"""


def run(*args, **kwargs):  # type: ignore[no-untyped-def]
    """Fail clearly if code tries to run uvicorn inside Cloudflare Workers."""

    raise RuntimeError("uvicorn.run() is not supported inside Cloudflare Workers")
