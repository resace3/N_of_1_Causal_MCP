from __future__ import annotations

import json
import stat
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_toml_parses() -> None:
    parsed = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert parsed["project"]["name"] == "patient-causal-mcp"
    assert parsed["project"]["requires-python"] == ">=3.12,<3.13"


def test_package_json_parses() -> None:
    parsed = json.loads((ROOT / "package.json").read_text())

    assert parsed["scripts"]["deploy"] == "bash scripts/cf-deploy.sh"
    assert parsed["scripts"]["dev"] == "uv run pywrangler dev"


def test_wrangler_jsonc_contains_cloudflare_worker_settings() -> None:
    text = (ROOT / "wrangler.jsonc").read_text()

    for expected in [
        '"name": "remote-mcp-server-authless"',
        '"main": "src/worker.py"',
        '"compatibility_date": "2026-06-17"',
        '"python_workers"',
        '"name": "N_OF_1_MCP"',
        '"class_name": "PatientCausalMCPServer"',
        '"new_sqlite_classes": ["PatientCausalMCPServer"]',
    ]:
        assert expected in text


def test_cloudflare_deploy_script_exists_and_is_executable() -> None:
    script = ROOT / "scripts" / "cf-deploy.sh"

    assert script.exists()
    assert script.read_text().startswith("#!/usr/bin/env bash\n")
    assert script.stat().st_mode & stat.S_IXUSR
