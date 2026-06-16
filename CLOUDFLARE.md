# Deploy N_of_1_Causal_MCP as a Cloudflare remote MCP server

This repository can run as a local stdio MCP server or as an authless remote MCP server on Cloudflare Python Workers. The remote endpoint uses Streamable HTTP at `/mcp` and registers the same tools as the local server.

The configured Worker name is `remote-mcp-server-authless`, which preserves this expected production URL:

```text
https://remote-mcp-server-authless.resace3.workers.dev/mcp
```

If you create a new Worker instead of reusing the existing one, rename the `name` value in `wrangler.jsonc` to something like `n-of-1-causal-mcp`.

## Local Prerequisites

- Node 18 or newer, preferably current LTS.
- Python 3.12.
- `uv`.
- `npm` or `npx`.
- A Cloudflare account for deployment.

## Local Install

```bash
git clone https://github.com/resace3/N_of_1_Causal_MCP.git
cd N_of_1_Causal_MCP
python -m pip install --upgrade pip
python -m pip install uv
uv sync
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

## Cloudflare Dashboard Deployment

Use these settings in Workers & Pages:

- Worker: open the existing `remote-mcp-server-authless` Worker, or create a new Worker.
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

## Architecture Notes

- `src/patient_causal_mcp/server.py` remains the single source of MCP tool registration.
- `create_mcp_server()` keeps local stdio behavior.
- `create_cloudflare_mcp_server()` enables Streamable HTTP settings for Cloudflare.
- `src/worker.py` is the Cloudflare Worker entrypoint.
- `src/asgi.py` bridges Cloudflare Request/Response objects to the FastMCP ASGI app.
- `src/uvicorn.py` is a compatibility shim for optional SDK imports; the Worker does not run uvicorn.
- A Durable Object binding named `N_OF_1_MCP` uses the deterministic object id `global` so the in-memory dataset registry is not tied to random isolate globals.

## Important Warnings

- `/mcp` is not a normal web page. A browser GET may not look useful.
- The Worker is authless. Anyone with the URL can call its tools.
- Do not connect private Home Assistant, wearable, phone, location, financial, or clinical datasets until authentication and authorization are added.
- The bundled data are synthetic and the outputs are not medical advice.
- Causal estimates depend on modeling and adjustment assumptions.
- Python FastMCP Workers may exceed Cloudflare Workers free plan bundle limits. If deployment fails due to bundle size, record the exact Cloudflare error and consider either a Workers paid plan or a TypeScript port of the causal engine.
