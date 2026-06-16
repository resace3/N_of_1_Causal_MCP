from __future__ import annotations

import importlib

from patient_causal_mcp.server import TOOL_NAMES


def test_worker_module_imports_without_cloudflare_runtime() -> None:
    worker = importlib.import_module("worker")

    assert hasattr(worker, "setup_server")
    assert hasattr(worker, "PatientCausalMCPServer")
    assert worker._health_payload()["mcp_endpoint"] == "/mcp"  # noqa: SLF001


def test_worker_setup_server_returns_fastmcp_and_asgi_app() -> None:
    worker = importlib.import_module("worker")

    mcp, app = worker.setup_server()

    assert mcp is not None
    assert app is not None
    assert hasattr(mcp, "streamable_http_app")
    assert set(mcp._tool_manager._tools) == set(TOOL_NAMES)  # noqa: SLF001


def test_worker_health_payload_documents_remote_mcp_surface() -> None:
    worker = importlib.import_module("worker")

    payload = worker._health_payload()  # noqa: SLF001

    assert payload["ok"] is True
    assert payload["name"] == "patient-causal-mcp"
    assert payload["transport"] == "streamable-http"
    assert payload["mcp_endpoint"] == "/mcp"
    assert payload["tools"] == TOOL_NAMES
    assert payload["auth"] == "authless-demo"


def test_worker_cors_exposes_mcp_session_id_for_inspector() -> None:
    worker = importlib.import_module("worker")

    assert worker.CORS_HEADERS["Access-Control-Allow-Origin"] == "*"
    assert "Mcp-Session-Id" in worker.CORS_HEADERS["Access-Control-Allow-Headers"]
    assert worker.CORS_HEADERS["Access-Control-Expose-Headers"] == "Mcp-Session-Id"
