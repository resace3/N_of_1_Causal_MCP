# N-of-1 Causal MCP

[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![MCP Server](https://img.shields.io/badge/MCP-server-6f42c1.svg)](https://modelcontextprotocol.io/)
[![MCP CI](https://github.com/resace3/N_of_1_Causal_MCP/actions/workflows/mcp-ci.yml/badge.svg)](https://github.com/resace3/N_of_1_Causal_MCP/actions/workflows/mcp-ci.yml)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare-Workers-F38020.svg)](https://developers.cloudflare.com/workers/)
[![Tests](https://img.shields.io/badge/tests-pytest-0a7f44.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](pyproject.toml)
[![Repository](https://img.shields.io/badge/GitHub-resace3%2FN__of__1__Causal__MCP-black.svg)](https://github.com/resace3/N_of_1_Causal_MCP)

`patient-causal-mcp` is both a local stdio Model Context Protocol server and a Cloudflare remote MCP server for N-of-1 digital health causal analysis. It ships with static synthetic patient datasets plus runtime-generated synthetic Homer Simpson parody datasets that mimic Home Assistant Recorder-style state history. MCP tools let an AI assistant summarize the data, inspect causal assumptions, query Home Assistant-style states, aggregate raw state history, run causal analyses, emulate target trials, simulate interventions, and export results.

This repository does **not** expose a `simulate_patient_data` MCP tool. The patient dataset is already present in the repo at:

```text
src/patient_causal_mcp/data/patient_001_raw_events_30_days.csv
src/patient_causal_mcp/data/patient_001_100_days.csv
```

The data are synthetic and manually bundled or deterministically generated for demonstration, research prototyping, and education. The Homer Simpson profile is fictional/parody data, is not official Simpsons data, and is not real personal data. The project does not provide medical advice.

## Highlights

- Static 30-day raw Home Assistant-like event dataset committed in the repository.
- Static 100-day N-of-1 analysis dataset committed in the repository.
- Wearable, phone, communication, location, motion, smart-home, calendar, and synthetic financial features.
- MCP tools for dataset discovery, data summaries, DAG generation, adjustment-set checks, causal effect estimation, target trial emulation, intervention simulation, and export.
- Practical causal estimators: regression adjustment, inverse probability weighting, g-formula, and simple doubly robust AIPW.
- Default dataset is loaded into memory when the MCP server starts.
- Tools also accept raw records for stateless workflows or future real-data integration.
- Designed for future integration with Home Assistant, Fitbit, phone sensors, smart plugs, pantry sensors, refrigerator sensors, medication cabinet sensors, and blood pressure readings.
- Home Assistant Recorder-inspired synthetic datasets with normalized `states`, `states_meta`, and `state_attributes` tables, flattened export, daily aggregation, and SQL dump export.

## Bundled Datasets

Raw event dataset:

```text
dataset_id: patient_001_raw_events_30_days
patient_id: patient-001
days: 30
rows: 3,240
unique entity_id values: 108
date range: 2026-01-01 to 2026-01-30
format: timestamp,patient_id,entity_id,state,unit,source,domain
```

The raw event CSV is intentionally long format. Each row is one timestamped observation for one raw sensor or event entity:

```csv
timestamp,patient_id,entity_id,state,unit,source,domain
2026-01-01 00:00:57,patient-001,phone_battery_level,72,percent,phone,device
2026-01-01 05:38:10,patient-001,phone_app_foreground_package,com.spotify.music,none,phone,app_usage
2026-01-01 15:10:22,patient-001,pantry_door_contact_state,closed,none,smart_home,contact
```

The raw file keeps entity IDs as row values in `entity_id`. It does not contain daily aggregate columns such as `total_screen_time_minutes`, `pantry_open_count`, `mean_heart_rate`, or `sleep_duration_hours`.

Analysis-ready daily dataset:

```text
dataset_id: patient_001_100_days
patient_id: patient-001
days: 100
date range: 2026-01-01 to 2026-04-10
scenario: mixed_lifestyle
```

The daily dataset contains 85 engineered columns for causal examples, including:

| Domain | Example Variables |
| --- | --- |
| Wearables | `sleep_duration_hours`, `sleep_efficiency`, `awakenings`, `steps`, `heart_rate_variability_ms`, `calories_burned`, `spo2_percent`, `skin_temperature_c` |
| Phone and apps | `phone_pickups`, `unlocks`, `notifications`, `app_usage_minutes`, `total_screen_time_minutes`, `social_app_minutes`, `productivity_app_minutes`, `finance_app_minutes`, `entertainment_app_minutes` |
| Communication | `texts_sent`, `texts_received`, `calls_made`, `calls_received`, `call_duration_minutes` |
| Location | `location_home_minutes`, `location_work_minutes`, `away_from_home_minutes`, `home_wifi_minutes`, `distance_traveled_km`, `commute_minutes`, `gps_radius_meters`, `significant_location_changes` |
| Motion sensors | `motion_stationary_minutes`, `motion_walking_minutes`, `motion_running_minutes`, `motion_driving_minutes`, `accelerometer_activity_counts` |
| Smart home | `pantry_door_opens`, `refrigerator_door_opens`, `smart_plug_tv_minutes`, `smart_plug_kettle_uses`, `medication_cabinet_opens` |
| Financial | `transactions_count`, `card_spend_usd`, `cash_withdrawal_usd`, `grocery_spend_usd`, `restaurant_spend_usd`, `alcohol_spend_usd`, `ride_share_spend_usd`, `online_purchase_count` |
| Calendar and context | `work_calendar_events`, `meeting_minutes`, `intervention_received`, `stress_score`, `mood_score`, `pain_score` |
| Outcomes | `outcome_sleep_quality`, `outcome_next_day_fatigue`, `outcome_mood_next_day`, `outcome_bp_next_day` |

### Homer Home Assistant-Style Synthetic Datasets

These generated datasets are 100 percent synthetic and centered on a fictional parody household profile:

```text
subject_id: homer_simpson
profile_type: fictional_parody
timezone: America/New_York
default start: 2026-01-01T00:00:00-05:00
fictional zones: springfield_home, springfield_work, moes_area, kwik_e_mart_area, school_area, power_plant_area
```

Dataset IDs:

| Dataset | Type | Days | Tables |
| --- | --- | --- | --- |
| `homer_simpson_ha_states_30_days` | Home Assistant Recorder-style raw states | 30 | `states`, `states_meta`, `state_attributes`, `flattened`, `daily` |
| `homer_simpson_ha_states_100_days` | Higher-density raw states | 100 | `states`, `states_meta`, `state_attributes`, `flattened`, `daily` |
| `homer_simpson_daily_100_days` | Analysis-ready daily table | 100 | `daily` |
| `homer_simpson_ha_sqlite_demo_30_days` | Minimal Recorder-style SQL dump export | 30 | SQL dump plus normalized tables |

The raw schema is Home Assistant Recorder-inspired, not an export from a real Home Assistant installation. It includes normalized `states_meta`, reusable `state_attributes`, and `states` rows where numeric states are stored as strings. Entity coverage includes wearable, phone, room motion/contact, illuminance, temperature, CO2, PM2.5, media, appliances, car, work/calendar, food/drink proxy, health self-report, and derived daily entities.

Privacy constraints for the Homer datasets:

- No real person, account, home, address, device ID, phone number, coordinate, secret, API call, or Home Assistant database is used.
- Location is represented only as fictional zone labels.
- The parody profile uses broad fictional traits only; it contains no show dialogue, episode text, official media, images, audio, or copyrighted passages.
- Deterministic generation means the same seed and parameters produce identical tables.

## Why MCP

MCP gives an AI assistant a disciplined interface to causal analysis code. Instead of inventing data or doing informal spreadsheet reasoning, the assistant calls explicit tools with structured inputs and auditable outputs.

This makes it easier to:

- discover the bundled patient dataset
- summarize the available signals before analysis
- inspect the assumed causal graph before estimating effects
- align exposures, covariates, and outcomes over time
- return assumptions, diagnostics, and plain-language explanations
- later point the same analysis tools at real device or Home Assistant history data

## Installation

```bash
git clone https://github.com/resace3/N_of_1_Causal_MCP.git
cd N_of_1_Causal_MCP
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Or with `uv`:

```bash
python -m pip install uv
uv sync
```

## Run The MCP Server

```bash
patient-causal-mcp
```

Or:

```bash
python -m patient_causal_mcp.server
```

The server uses stdio transport through the Python MCP SDK:

```python
from mcp.server.fastmcp import FastMCP
```

### MCP Host Configuration

Use this configuration pattern for an MCP host that launches local stdio servers:

```json
{
  "command": "python",
  "args": ["-m", "patient_causal_mcp.server"],
  "cwd": "/path/to/N_of_1_Causal_MCP"
}
```

## Cloudflare Remote MCP

The project also includes a public, synthetic-only Cloudflare Worker MCP endpoint using Streamable HTTP:

```text
https://remote-mcp-server-authless.resace3.workers.dev/mcp
```

The local Python stdio entrypoint remains unchanged. Cloudflare deployment is additive and uses the dependency-free TypeScript Worker at `src/worker.ts`. The Worker exposes health JSON at `/` and `/health`, then routes MCP traffic to `/mcp`.

Quick local Worker test:

```bash
npm install
npm run dev
```

Then connect MCP Inspector with:

```text
Transport: Streamable HTTP
URL: http://localhost:8787/mcp
```

Full deployment instructions are in [CLOUDFLARE.md](CLOUDFLARE.md).

Security note: the configured Worker is authless for demonstration, but the public Cloudflare implementation rejects caller-supplied `data_records` and only serves deterministic synthetic datasets. Do not connect private Home Assistant, wearable, phone, financial, or clinical datasets until authentication and authorization are added.

Implementation note: the public Worker keeps the same MCP tool names as the Python server, but uses lightweight JavaScript estimators and a compact Homer HA query subset so it fits Cloudflare Workers free-plan size limits. The local stdio MCP server remains the full Python implementation.

## Tool Inventory

| Tool | Purpose |
| --- | --- |
| `get_available_datasets` | List bundled static datasets and the default `dataset_id`. |
| `get_available_scenarios` | List supported causal scenarios, questions, exposures, outcomes, confounders, mediators, and interpretations. |
| `describe_patient_data` | Summarize missingness, numeric distributions, binary counts, correlations, and time trends. |
| `propose_causal_question` | Suggest clinically meaningful causal questions from the available variables. |
| `estimate_causal_effect` | Estimate effects using regression adjustment, IPW, g-formula, or simple doubly robust AIPW. |
| `run_target_trial_emulation` | Emulate a repeated daily target trial with explicit eligibility, strategies, time zero, and follow-up. |
| `generate_causal_dag` | Return scenario DAG nodes, edges, adjustment guidance, DOT, and Mermaid text. |
| `check_adjustment_set` | Flag missing confounders, adjusted mediators, and possible colliders in a practical adjustment set. |
| `simulate_intervention` | Predict what could happen under a behavioral or medication-related intervention. |
| `export_dataset` | Export CSV, JSON, normalized HA JSON, or Homer SQL dump data. |
| `query_ha_states` | Filter Homer Home Assistant-style state rows by entity, domain, and time. |
| `aggregate_ha_states_daily` | Derive daily analysis rows from Homer Home Assistant-style raw state history. |

## Supported Causal Scenarios

| Scenario | Exposure | Outcome | Core Question |
| --- | --- | --- | --- |
| `sleep_screen_time` | `late_night_screen_minutes` | `outcome_sleep_quality` | What is the effect of reducing late-night screen time on sleep quality? |
| `steps_fatigue` | `steps` | `outcome_next_day_fatigue` | What is the effect of increasing daily steps on next-day fatigue? |
| `medication_bp` | `medication_adherence` | `outcome_bp_next_day` | What is the effect of medication adherence on next-day blood pressure? |
| `stress_sleep` | `stress_score` | `outcome_sleep_quality` | What is the effect of high stress on same-night sleep quality? |
| `nighttime_eating_fatigue` | `nighttime_eating` | `morning_fatigue` | What is the effect of nighttime eating on morning fatigue? |
| `mixed_lifestyle` | `intervention_received` | `outcome_sleep_quality` | What is the effect of an evening reminder intervention on sleep quality? |
| `homer_late_screen_sleep` | `late_night_screen_minutes` | `outcome_next_day_fatigue` | What is the effect of late-night screen time on next-day fatigue in the synthetic Homer data? |
| `homer_walk_nudge_mood` | `walk_nudge_received` | `outcome_mood_next_day` | What is the effect of walk nudges on next-day mood in the synthetic Homer data? |
| `homer_caffeine_sleep` | `caffeine_mg` | `outcome_sleep_quality` | What is the effect of caffeine intake on sleep quality in the synthetic Homer data? |
| `homer_illuminance_sleep` | `avg_daytime_outdoor_illuminance` | `outcome_sleep_quality` | What is the effect of outdoor illuminance exposure on sleep quality? |
| `homer_tv_fatigue` | `tv_minutes` | `outcome_next_day_fatigue` | What is the effect of TV minutes on next-day fatigue? |

## Example Tool Calls

### Discover Bundled Datasets

```json
{
  "tool": "get_available_datasets",
  "arguments": {}
}
```

Example response fields:

- `default_dataset_id`
- `datasets`
- `loaded_dataset_ids`

### Summarize The Default Patient Data

`dataset_id` can be omitted to use `patient_001_100_days`.

```json
{
  "tool": "describe_patient_data",
  "arguments": {
    "variables": [
      "sleep_duration_hours",
      "steps",
      "late_night_screen_minutes",
      "texts_sent",
      "card_spend_usd",
      "outcome_sleep_quality"
    ]
  }
}
```

### Estimate A Causal Effect

```json
{
  "tool": "estimate_causal_effect",
  "arguments": {
    "dataset_id": "patient_001_100_days",
    "exposure": "late_night_screen_minutes",
    "outcome": "outcome_sleep_quality",
    "treatment_rule": {
      "type": "binary_threshold",
      "variable": "late_night_screen_minutes",
      "threshold": 120,
      "treated_condition": "<="
    },
    "adjustment_variables": [
      "stress_score",
      "caffeine_mg",
      "prior_sleep_quality",
      "steps"
    ],
    "method": "g_formula",
    "bootstrap": false
  }
}
```

Supported methods:

- `regression_adjustment`: fits an adjusted outcome model.
- `ipw`: estimates a propensity score for binary exposure and fits a weighted outcome contrast.
- `g_formula`: predicts potential outcomes under two treatment strategies.
- `doubly_robust`: uses a simple AIPW estimator for binary treatment.

### Generate A Causal DAG

```json
{
  "tool": "generate_causal_dag",
  "arguments": {
    "scenario": "sleep_screen_time"
  }
}
```

Returns:

- nodes and edges
- exposure and outcome
- confounders and mediators
- suggested adjustment set
- variables not to adjust for
- Graphviz DOT
- Mermaid diagram text

### Run A Target Trial Emulation

```json
{
  "tool": "run_target_trial_emulation",
  "arguments": {
    "dataset_id": "patient_001_100_days",
    "eligibility_criteria": {
      "prior_sleep_quality": { "max": 8 }
    },
    "treatment_strategies": [
      {
        "name": "Reminder at 8 PM",
        "type": "binary_variable",
        "variable": "intervention_received",
        "value": 1
      },
      {
        "name": "No reminder",
        "type": "binary_variable",
        "variable": "intervention_received",
        "value": 0
      }
    ],
    "assignment_time": "8 PM before the sleep episode",
    "follow_up_days": 1,
    "outcome": "outcome_sleep_quality",
    "adjustment_variables": [
      "stress_score",
      "prior_sleep_quality",
      "prior_fatigue",
      "day_of_week",
      "baseline_phone_use"
    ],
    "method": "g_formula"
  }
}
```

### Simulate An Intervention

```json
{
  "tool": "simulate_intervention",
  "arguments": {
    "dataset_id": "patient_001_100_days",
    "intervention_name": "Reduce late-night screen time by 60 minutes",
    "intervention_rule": { "operation": "add" },
    "target_variable": "late_night_screen_minutes",
    "expected_change": -60,
    "outcome": "outcome_sleep_quality",
    "adjustment_variables": [
      "stress_score",
      "caffeine_mg",
      "prior_sleep_quality",
      "steps"
    ]
  }
}
```

Supported intervention operations:

- `add`
- `multiply`
- `set_minimum`
- `set_maximum`
- `set_value`

### Query Homer Home Assistant States

```json
{
  "tool": "query_ha_states",
  "arguments": {
    "dataset_id": "homer_simpson_ha_states_30_days",
    "entity_id": "sensor.homer_watch_heart_rate",
    "start": "2026-01-02T00:00:00-05:00",
    "end": "2026-01-03T23:59:59-05:00",
    "limit": 100,
    "include_attributes": true,
    "parse_numeric": true
  }
}
```

### Export Homer Tables

CSV export of a single table:

```json
{
  "tool": "export_dataset",
  "arguments": {
    "dataset_id": "homer_simpson_ha_states_30_days",
    "format": "csv",
    "table": "states"
  }
}
```

Normalized JSON export:

```json
{
  "tool": "export_dataset",
  "arguments": {
    "dataset_id": "homer_simpson_ha_states_30_days",
    "format": "json",
    "table": "normalized"
  }
}
```

### Aggregate Homer Raw States Daily

```json
{
  "tool": "aggregate_ha_states_daily",
  "arguments": {
    "dataset_id": "homer_simpson_ha_states_30_days"
  }
}
```

### Estimate A Homer Synthetic Effect

```json
{
  "tool": "estimate_causal_effect",
  "arguments": {
    "dataset_id": "homer_simpson_daily_100_days",
    "exposure": "late_night_screen_minutes",
    "outcome": "outcome_next_day_fatigue",
    "treatment_rule": {
      "type": "set_value",
      "value_a": 180,
      "value_b": 60
    },
    "adjustment_variables": [
      "prior_sleep_quality",
      "prior_fatigue",
      "prior_stress_score",
      "is_workday",
      "caffeine_mg"
    ],
    "method": "g_formula"
  }
}
```

### Run A Homer Prebuilt Target Trial

When `treatment_strategies` is empty for the Homer daily dataset, the server can fill a prebuilt synthetic protocol based on the assignment/outcome text:

```json
{
  "tool": "run_target_trial_emulation",
  "arguments": {
    "dataset_id": "homer_simpson_daily_100_days",
    "assignment_time": "walk nudge demo",
    "treatment_strategies": [],
    "outcome": "outcome_mood_next_day",
    "method": "g_formula"
  }
}
```

## Direct Python Example

```bash
python examples/example_client.py
```

This bypasses an MCP host and calls the same tool functions directly.

## Architecture

```text
patient-causal-mcp/
  CLOUDFLARE.md
  README.md
  package.json
  pyproject.toml
  wrangler.jsonc
  examples/
    example_client.py
    example_prompts.md
  scripts/
    cf-deploy.sh
    test_remote_mcp_http.py
  src/
    worker.ts
    patient_causal_mcp/
      __init__.py
      tool_metadata.py
      server.py
      datasets.py
      simulator.py
      scenarios.py
      causal_engine.py
      dag.py
      schemas.py
      utils.py
      synthetic/
        homer_ha.py
      data/
        patient_001_raw_events_30_days.csv
        patient_001_raw_events_30_days_metadata.json
        patient_001_100_days.csv
        patient_001_100_days_metadata.json
  tests/
    test_bundled_dataset.py
    test_causal_engine.py
    test_cloudflare_worker_imports.py
    test_dag.py
    test_dataset_contract.py
    test_mcp_stdio_smoke.py
    test_mcp_server_factory.py
    test_mcp_tool_contract.py
    test_raw_event_dataset.py
    test_static_file_formatting.py
```

Core modules:

- `server.py`: MCP tool registration and in-memory dataset registry.
- `worker.ts`: Cloudflare Worker entrypoint for public synthetic-only `/`, `/health`, and `/mcp`.
- `tool_metadata.py`: shared MCP tool-name metadata used by tests and docs.
- `datasets.py`: package-data loader and bundled dataset metadata.
- `scenarios.py`: scenario metadata, variable dictionary, DAG edges, and default adjustment sets.
- `causal_engine.py`: descriptive summaries, causal estimators, target trial emulation, intervention simulation, and export.
- `dag.py`: DAG serialization and practical adjustment-set checks.
- `schemas.py`: Pydantic models for tool inputs.
- `utils.py`: shared validation and data conversion helpers.
- `synthetic/homer_ha.py`: deterministic Homer Home Assistant-style raw-state and daily dataset generator.

`simulator.py` remains as a development utility for creating synthetic data variants, but it is not registered as an MCP tool.

## Development

Run tests:

```bash
uv run pytest
```

The pytest suite includes more than 700 collected checks covering the bundled daily dataset contract, raw event dataset contract, required `entity_id` coverage, variable dictionary, realistic ranges, MCP tool registration, stdio MCP calls, causal estimators, DAG helpers, and examples.

Run a local MCP smoke test from Python:

```bash
python - <<'PY'
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(
        command="python",
        args=["-m", "patient_causal_mcp.server"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print([tool.name for tool in tools.tools])

asyncio.run(main())
PY
```

Expected tools include `get_available_datasets`; they do not include `simulate_patient_data`.

Run a local Streamable HTTP smoke test after starting `npm run dev`:

```bash
uv run python scripts/test_remote_mcp_http.py http://localhost:8787/mcp
```

## Home Assistant Integration Notes

This version does not require Home Assistant. The bundled dataset includes synthetic versions of variables that could later come from Home Assistant history, Fitbit, phone sensors, and smart-home entities.

Possible future entity mappings:

- Fitbit sleep sensors -> `sleep_duration_hours`, `sleep_efficiency`, `awakenings`
- step counters -> `steps`, `active_minutes`, `sedentary_minutes`
- phone usage sensors -> `late_night_screen_minutes`, `phone_pickups`, `app_usage_minutes`, `texts_sent`, `calls_made`
- location sensors -> `location_home_minutes`, `location_work_minutes`, `distance_traveled_km`
- motion sensors -> `motion_walking_minutes`, `motion_driving_minutes`, `accelerometer_activity_counts`
- pantry door sensors -> `pantry_door_opens`
- refrigerator door sensors -> `refrigerator_door_opens`
- smart plug current sensors -> `smart_plug_tv_minutes`, `smart_plug_kettle_uses`
- medication cabinet sensors -> `medication_adherence`, `medication_cabinet_opens`
- blood pressure readings -> `blood_pressure_systolic`, `blood_pressure_diastolic`
- financial exports -> `transactions_count`, `card_spend_usd`, `restaurant_spend_usd`

The same causal analysis tools could later be pointed at real Home Assistant history data after time alignment, missingness handling, consent/privacy review, and unit normalization.

## Important Limitations

- The bundled patient data are synthetic.
- Results are not medical advice.
- Causal estimates depend on assumptions.
- No unmeasured confounding is generally untestable.
- Time alignment matters.
- Small N-of-1 datasets can be noisy.
- The models are simple parametric prototypes.
- The adjustment-set checker is practical guidance, not a formal d-separation engine.
- Financial variables are synthetic demonstration fields, not real financial advice inputs.
- Real sensor data would require careful validation, missingness handling, privacy safeguards, and clinical review.
- The tool is for demonstration, research prototyping, and educational use.
