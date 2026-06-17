# Deploy N_of_1_Causal_MCP as a Cloudflare remote MCP server

This deploys a public, synthetic-only remote MCP server on Cloudflare Workers.

The local stdio MCP server remains the Python implementation in `src/patient_causal_mcp/server.py`. The public Cloudflare endpoint uses `src/worker.ts`, a dependency-free TypeScript Worker that keeps the same MCP tool names and deterministic synthetic data while fitting Cloudflare Workers free-plan size limits.

It provides:

- Authless remote MCP access for demonstration.
- Streamable HTTP at `/mcp`.
- Health JSON at `/` and `/health`.
- Public tool schemas that omit `data_records`.
- Runtime rejection of caller-supplied `data_records`.
- Deterministic synthetic datasets only.
- Homer Simpson fictional/parody Home Assistant-style dataset metadata, daily rows, and a compact queryable HA-state subset with fictional zone labels only.
- A 128 KiB MCP request body limit.
- Browser CORS headers only for approved local development origins.

The configured Worker name is `remote-mcp-server-authless`, preserving this production URL:

```text
https://remote-mcp-server-authless.resace3.workers.dev/mcp
```

## Prerequisites

- Node 18 or newer.
- `npm` or `npx`.
- Cloudflare login locally, or `CLOUDFLARE_API_TOKEN` in the environment.
- Python 3.12 and `uv` only for the local stdio MCP server and Python tests.

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

This starts the Python stdio MCP server for MCP hosts that launch local tools.

## Local Cloudflare Worker Test

```bash
npm run dev
```

The local development URL is usually:

```text
http://localhost:8787/mcp
```

Use the exact port printed by Wrangler if it chooses a different one.

## MCP Inspector Test

```bash
npx @modelcontextprotocol/inspector@latest
```

Use:

```text
Transport: Streamable HTTP
URL: http://localhost:8787/mcp
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
- `query_ha_states`
- `aggregate_ha_states_daily`

You can also run the local HTTP smoke script:

```bash
uv run python scripts/test_remote_mcp_http.py http://localhost:8787/mcp
```

## Deployment

Deploy with:

```bash
npm run deploy
```

The npm script runs:

```bash
npx wrangler deploy
```

The Worker keeps the existing deployed Durable Object class name `MyMCP` because Cloudflare requires already-migrated Durable Object classes to remain exported unless a migration deletes or renames them. The binding is named `N_OF_1_MCP` in `wrangler.jsonc`.

## Production Test

Expected production endpoint:

```text
https://remote-mcp-server-authless.resace3.workers.dev/mcp
```

Health endpoints:

```text
https://remote-mcp-server-authless.resace3.workers.dev/
https://remote-mcp-server-authless.resace3.workers.dev/health
```

Smoke test:

```bash
uv run python scripts/test_remote_mcp_http.py https://remote-mcp-server-authless.resace3.workers.dev/mcp
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

- `src/patient_causal_mcp/server.py` remains the Python stdio MCP implementation.
- `src/worker.ts` is the public Cloudflare Worker implementation.
- `src/patient_causal_mcp/tool_metadata.py` shares the canonical tool-name list with tests.
- The public Worker omits caller-supplied `data_records` from tool schemas and serves only bundled/generated synthetic data.
- `MyMCP` owns the public Worker MCP handler and is preserved for existing Durable Object migration compatibility.
- The public Worker is stateless for MCP responses; the Durable Object gives the deployment a stable object id and preserves compatibility with the existing Cloudflare Worker history.
- The TypeScript public Worker was chosen because the Python Worker bundle with MCP, Pydantic, NumPy, and Pandas exceeds the Cloudflare Workers free-plan size limit.

## Security Warning

This deployment is authless. Anyone who knows the URL can call the tools against deterministic synthetic datasets.

The public Cloudflare endpoint rejects caller-supplied `data_records`, enforces a 128 KiB MCP request body limit, and only emits browser CORS headers for approved local development origins. The Homer Home Assistant-style public data uses fictional identifiers and zone labels only; it does not contain real Home Assistant database rows, coordinates, addresses, phone numbers, secrets, or external API calls. These controls reduce accidental exposure and browser abuse, but they are not a substitute for authentication if real data is ever connected.

Do not connect private health, location, phone, financial, email, or Home Assistant data until authentication and authorization are added.

## Important Warnings

- `/mcp` is not a normal web page. A browser GET may not look useful.
- The public datasets are synthetic and the outputs are not medical advice.
- Causal estimates depend on modeling and adjustment assumptions.
- The TypeScript Worker uses lightweight deterministic estimators for public demonstration; use the local Python stdio server for the fuller Python analysis implementation.
