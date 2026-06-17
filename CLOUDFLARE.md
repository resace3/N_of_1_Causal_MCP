# Deploy N_of_1_Causal_MCP as a Cloudflare remote MCP server

This deploys the real Python `patient-causal-mcp` tools as an authless remote MCP server on Cloudflare Python Workers.

It provides:

- Authless remote MCP access for demonstration.
- Streamable HTTP at `/mcp`.
- Health JSON at `/` and `/health`.
- The same real Python causal-analysis tools as the local stdio MCP server.

The configured Worker name is `remote-mcp-server-authless`, preserving this production URL:

```text
https://remote-mcp-server-authless.resace3.workers.dev/mcp
```

If you create a new Worker instead of reusing the existing one, rename the `name` value in `wrangler.jsonc` to something like `n-of-1-causal-mcp`.

## Prerequisites

- Python 3.12.
- `uv`.
- Node 18 or newer.
- `npm` or `npx`.
- Cloudflare login locally, or a Cloudflare dashboard build integration.

## Local Install

```bash
git clone https://github.com/resace3/N_of_1_Causal_MCP.git
cd N_of_1_Causal_MCP
python -m pip install --upgrade pip
python -m pip install uv
uv sync
npm install
```

## Local Stdio Test

```bash
uv run python -m patient_causal_mcp.server
```

This starts the original local stdio MCP server. It should continue to work for MCP hosts that launch local tools.

## Local Cloudflare Worker Test

```bash
uv run pywrangler dev
```

The local development URL is usually:

```text
http://localhost:8787/mcp
```

Use the exact port printed by `pywrangler` if it chooses a different one.

## MCP Inspector Test

```bash
npx @modelcontextprotocol/inspector@latest
```

Use:

```text
Transport: Streamable HTTP
URL: http://localhost:8787/mcp
```

Then click:

```text
Connect
List Tools
```

Expected tools:

- `get_available_datasets`
- `get_available_scenarios`
- `describe_patient_data`
- `propose_causal_question`
- `estimate_causal_effect`
- `run_target_trial_emulation`
- `generate_causal_dag`
- `check_adjustment_set`
- `simulate_intervention`
- `export_dataset`

You can also run the local HTTP smoke script:

```bash
uv run python scripts/test_remote_mcp_http.py http://localhost:8787/mcp
```

## Cloudflare Dashboard Deployment

Use these settings in Workers & Pages:

- Git repository: `resace3/N_of_1_Causal_MCP`.
- Root directory: `/`.
- Build command: leave empty.
- Deploy command: `npm run deploy`.
- Production branch: `main`.

Save and deploy.

The npm script is intentionally thin. It installs or uses `uv`, then runs:

```bash
uv run pywrangler deploy
```

## Production Test

Expected production endpoint:

```text
https://remote-mcp-server-authless.resace3.workers.dev/mcp
```

Test it with MCP Inspector:

```bash
npx @modelcontextprotocol/inspector@latest
```

Use:

```text
Transport: Streamable HTTP
URL: https://remote-mcp-server-authless.resace3.workers.dev/mcp
```

Then click:

```text
Connect
List Tools
```

The root and health endpoints return simple JSON:

```text
https://remote-mcp-server-authless.resace3.workers.dev/
https://remote-mcp-server-authless.resace3.workers.dev/health
```

## Claude Desktop Through mcp-remote

```json
{
  "mcpServers": {
    "n-of-1-causal-mcp": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://remote-mcp-server-authless.resace3.workers.dev/mcp"
      ]
    }
  }
}
```

Restart Claude Desktop after editing the configuration.

## Architecture Notes

- `src/patient_causal_mcp/server.py` remains the single source of MCP tool registration.
- `create_mcp_server()` keeps local stdio behavior.
- `create_cloudflare_mcp_server()` configures FastMCP for Streamable HTTP at `/mcp`.
- `src/worker.py` uses the current Python Workers `Default(WorkerEntrypoint)` entrypoint.
- `PatientCausalMCPServer(DurableObject)` owns the FastMCP ASGI app.
- A Durable Object binding named `N_OF_1_MCP` uses the deterministic object id `global` so the in-memory dataset registry is not tied to random isolate globals.
- `src/asgi.py` bridges Cloudflare Request/Response objects to the FastMCP ASGI app.
- `src/uvicorn.py` is a compatibility shim for optional SDK imports; the Worker does not run uvicorn.
- The dependency range uses MCP `1.12.x` because MCP `1.27+` currently requires `pydantic>=2.11`, and pywrangler/Pyodide could not resolve a usable `pydantic-core` wheel for that line during local testing. MCP `1.12.4` still exposes `FastMCP.streamable_http_app()`.

## Python Worker Limitations

- Python Workers use Pyodide.
- `pywrangler` bundles packages from `pyproject.toml`.
- The ASGI bridge currently collects finite JSON responses and does not implement long-lived event-stream resumability.
- If deployment fails due to unsupported packages, bundle size, or Pyodide issues, record the exact error.
- Do not remove real causal-analysis functionality to hide a deployment error.
- If NumPy or Pandas causes a package limitation, use a follow-up TypeScript Worker port or split architecture rather than replacing tools with stubs.

## Current Local Cloudflare Blocker

`uv run pywrangler dev` successfully resolved and installed the Python Worker packages into `python_modules` and `.venv-workers`, including MCP `1.12.4`, Pydantic `2.10.6`, NumPy, and Pandas.

In this container, Wrangler then failed before exposing `localhost:8787`:

```text
ERROR write EPIPE
```

Running the bundled local `workerd` binary directly shows the underlying loader failure:

```text
Error relocating node_modules/@cloudflare/workerd-linux-arm64/bin/workerd: fcntl64: symbol not found
Error relocating node_modules/@cloudflare/workerd-linux-arm64/bin/workerd: _dl_find_object: symbol not found
Error relocating node_modules/@cloudflare/workerd-linux-arm64/bin/workerd: fcntl64: symbol not found
```

This appears to be a local runtime binary/libc incompatibility for the installed `workerd` binary on this environment, not a Python syntax or dependency-resolution failure. Because the local dev server did not bind a port, MCP Inspector could not be used against `http://localhost:8787/mcp` in this environment.

`npm run deploy` reached Wrangler and stopped only because this non-interactive environment does not have `CLOUDFLARE_API_TOKEN` set. Run this after Cloudflare login or with a token:

```bash
export CLOUDFLARE_API_TOKEN=...
npm run deploy
```

## Security Warning

This deployment is authless. Anyone who knows the URL can call the tools.

Do not connect private health, location, phone, financial, email, or Home Assistant data until authentication and authorization are added.

## Important Warnings

- `/mcp` is not a normal web page. A browser GET may not look useful.
- The bundled data are synthetic and the outputs are not medical advice.
- Causal estimates depend on modeling and adjustment assumptions.
- Python FastMCP Workers may exceed Cloudflare Workers free plan bundle limits. If deployment fails due to bundle size, record the exact Cloudflare error and consider either a Workers paid plan, a TypeScript port of the causal engine, or running the Python MCP server elsewhere with Cloudflare as a secured proxy.
