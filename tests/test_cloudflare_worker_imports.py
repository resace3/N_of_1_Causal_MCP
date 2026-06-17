from __future__ import annotations

from pathlib import Path

from patient_causal_mcp.server import TOOL_NAMES


ROOT = Path(__file__).resolve().parents[1]


def test_typescript_worker_exports_existing_durable_object_class() -> None:
    source = (ROOT / "src" / "worker.ts").read_text()

    assert "export class MyMCP" in source
    assert "export class PatientCausalMCPServer extends MyMCP" in source
    assert "N_OF_1_MCP" in source


def test_typescript_worker_documents_public_synthetic_only_surface() -> None:
    source = (ROOT / "src" / "worker.ts").read_text()

    assert 'data_policy: "bundled_synthetic_only"' in source
    assert 'caller_supplied_data_records: "disabled"' in source
    assert "Caller-supplied data_records are disabled" in source
    assert "MAX_MCP_REQUEST_BODY_BYTES = 128 * 1024" in source


def test_typescript_worker_contains_expected_tool_names() -> None:
    source = (ROOT / "src" / "worker.ts").read_text()

    for tool_name in TOOL_NAMES:
        assert f'"{tool_name}"' in source


def test_typescript_worker_cors_is_not_wildcard() -> None:
    source = (ROOT / "src" / "worker.ts").read_text()

    assert '"Access-Control-Allow-Origin": origin' in source
    assert '"Access-Control-Allow-Origin": "*"' not in source
