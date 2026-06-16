# N-of-1 Causal MCP

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP Server](https://img.shields.io/badge/MCP-server-6f42c1.svg)](https://modelcontextprotocol.io/)
[![Tests](https://img.shields.io/badge/tests-pytest-0a7f44.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](pyproject.toml)
[![Repository](https://img.shields.io/badge/GitHub-resace3%2FN__of__1__Causal__MCP-black.svg)](https://github.com/resace3/N_of_1_Causal_MCP)

`patient-causal-mcp` is a local Model Context Protocol server for synthetic N-of-1 digital health research. It simulates one patient over time, exposes clinically interpretable causal scenarios, and lets an AI assistant run causal analyses through typed MCP tools.

The project is intended for research prototyping, demos, and education. It does not provide medical advice.

## Highlights

- Synthetic longitudinal patient simulator with daily health, behavior, and sensor-style variables.
- Scenario-specific causal graphs for sleep, screen time, steps, fatigue, medication adherence, blood pressure, stress, and nighttime eating.
- MCP tools for simulation, data summaries, DAG generation, adjustment-set checks, causal effect estimation, target trial emulation, intervention simulation, and export.
- Practical causal estimators: regression adjustment, inverse probability weighting, g-formula, and simple doubly robust AIPW.
- In-memory dataset registry for multi-step assistant workflows, plus stateless support through raw records.
- Designed for future integration with Home Assistant, Fitbit, phone sensors, smart plugs, pantry sensors, refrigerator sensors, medication cabinet sensors, and blood pressure readings.

## Quick Example

An MCP-capable assistant can run the following workflow:

1. Simulate 180 days of a patient where late-night phone use affects sleep.
2. Show the scenario DAG and suggested adjustment set.
3. Estimate the effect of reducing late-night screen time below 30 minutes.
4. Simulate an intervention that reduces late-night screen time by 60 minutes.
5. Export the synthetic dataset as CSV.

Example causal interpretation returned by the server:

```text
On this simulated patient dataset, late_night_screen_minutes <= 30 was estimated
to produce higher outcome_sleep_quality than late_night_screen_minutes > 30,
using g_formula and adjusting for stress_score, caffeine_mg,
prior_sleep_quality, and steps. The estimate depends on the causal assumptions
and the simulated data-generating process.
```

## Why MCP

MCP gives an AI assistant a disciplined interface to the simulator and causal engine. Instead of inventing data or doing informal spreadsheet reasoning, the assistant calls explicit tools with structured inputs and auditable outputs.

This makes it easier to:

- generate reproducible synthetic data with a known data-generating process
- inspect the assumed causal graph before estimating effects
- align exposures, covariates, and outcomes over time
- return assumptions, diagnostics, and plain-language explanations
- later swap synthetic data for real device or Home Assistant history data

## Installation

```bash
git clone https://github.com/resace3/N_of_1_Causal_MCP.git
cd N_of_1_Causal_MCP
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

If your environment does not support extras:

```bash
pip install -r requirements.txt
pip install -e .
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

If the SDK changes this import path, the core package still works; update `create_mcp_server()` in `src/patient_causal_mcp/server.py`.

### MCP Host Configuration

Use this configuration pattern for an MCP host that launches local stdio servers:

```json
{
  "command": "python",
  "args": ["-m", "patient_causal_mcp.server"],
  "cwd": "/path/to/N_of_1_Causal_MCP"
}
```

## Tool Inventory

| Tool | Purpose |
| --- | --- |
| `simulate_patient_data` | Generate a synthetic longitudinal N-of-1 dataset and store it in memory under a `dataset_id`. |
| `get_available_scenarios` | List supported scenarios, causal questions, exposures, outcomes, confounders, mediators, and interpretations. |
| `describe_patient_data` | Summarize missingness, numeric distributions, binary counts, correlations, and time trends. |
| `propose_causal_question` | Suggest clinically meaningful causal questions from the available variables. |
| `estimate_causal_effect` | Estimate effects using regression adjustment, IPW, g-formula, or simple doubly robust AIPW. |
| `run_target_trial_emulation` | Emulate a repeated daily target trial with explicit eligibility, strategies, time zero, and follow-up. |
| `generate_causal_dag` | Return scenario DAG nodes, edges, adjustment guidance, DOT, and Mermaid text. |
| `check_adjustment_set` | Flag missing confounders, adjusted mediators, and possible colliders in a practical adjustment set. |
| `simulate_intervention` | Predict what could happen under a behavioral or medication-related intervention. |
| `export_dataset` | Export the dataset as CSV text or JSON records. |

## Supported Scenarios

| Scenario | Exposure | Outcome | Core Question |
| --- | --- | --- | --- |
| `sleep_screen_time` | `late_night_screen_minutes` | `outcome_sleep_quality` | What is the effect of reducing late-night screen time on sleep quality? |
| `steps_fatigue` | `steps` | `outcome_next_day_fatigue` | What is the effect of increasing daily steps on next-day fatigue? |
| `medication_bp` | `medication_adherence` | `outcome_bp_next_day` | What is the effect of medication adherence on next-day blood pressure? |
| `stress_sleep` | `stress_score` | `outcome_sleep_quality` | What is the effect of high stress on same-night sleep quality? |
| `nighttime_eating_fatigue` | `nighttime_eating` | `morning_fatigue` | What is the effect of nighttime eating on morning fatigue? |
| `mixed_lifestyle` | `intervention_received` | `outcome_sleep_quality` | What is the effect of an evening reminder intervention on sleep quality? |

## Example Tool Calls

### Simulate Patient Data

```json
{
  "patient_id": "demo-patient",
  "n_days": 180,
  "start_date": "2026-01-01",
  "seed": 42,
  "scenario": "sleep_screen_time"
}
```

Returns:

- `dataset_id`
- `patient_id`
- `scenario`
- `n_days`
- `variable_descriptions`
- `causal_graph_edges`
- `data_preview`
- `full_data`
- `warnings`

### Estimate A Causal Effect

```json
{
  "dataset_id": "<dataset_id>",
  "exposure": "late_night_screen_minutes",
  "outcome": "outcome_sleep_quality",
  "treatment_rule": {
    "type": "binary_threshold",
    "variable": "late_night_screen_minutes",
    "threshold": 30,
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
```

Supported methods:

- `regression_adjustment`: fits an adjusted outcome model.
- `ipw`: estimates a propensity score for binary exposure and fits a weighted outcome contrast.
- `g_formula`: predicts potential outcomes under two treatment strategies.
- `doubly_robust`: uses a simple AIPW estimator for binary treatment.

### Generate A Causal DAG

```json
{
  "scenario": "sleep_screen_time"
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
  "dataset_id": "<dataset_id>",
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
```

### Simulate An Intervention

```json
{
  "dataset_id": "<dataset_id>",
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
```

Supported intervention operations:

- `add`
- `multiply`
- `set_minimum`
- `set_maximum`
- `set_value`

## Direct Python Example

```bash
python examples/example_client.py
```

This bypasses an MCP host and calls the same tool functions directly.

## Architecture

```text
patient-causal-mcp/
  README.md
  pyproject.toml
  requirements.txt
  examples/
    example_client.py
    example_prompts.md
  src/
    patient_causal_mcp/
      __init__.py
      server.py
      simulator.py
      scenarios.py
      causal_engine.py
      dag.py
      schemas.py
      utils.py
  tests/
    test_simulator.py
    test_causal_engine.py
    test_dag.py
```

Core modules:

- `server.py`: MCP tool registration and in-memory dataset registry.
- `simulator.py`: longitudinal synthetic patient simulator.
- `scenarios.py`: scenario metadata, variable dictionary, DAG edges, and default adjustment sets.
- `causal_engine.py`: descriptive summaries, causal estimators, target trial emulation, intervention simulation, and export.
- `dag.py`: DAG serialization and practical adjustment-set checks.
- `schemas.py`: Pydantic models for tool inputs.
- `utils.py`: shared validation and data conversion helpers.

## Simulated Variables

The simulator generates daily values such as:

- `sleep_duration_hours`
- `sleep_efficiency`
- `awakenings`
- `steps`
- `sedentary_minutes`
- `active_minutes`
- `late_night_screen_minutes`
- `caffeine_mg`
- `alcohol_units`
- `medication_adherence`
- `stress_score`
- `mood_score`
- `pain_score`
- `blood_pressure_systolic`
- `blood_pressure_diastolic`
- `resting_heart_rate`
- `morning_fatigue`
- `nighttime_eating`
- `pantry_door_opens`
- `refrigerator_door_opens`
- `phone_pickups`
- `app_usage_minutes`
- `intervention_received`
- `outcome_sleep_quality`
- `outcome_next_day_fatigue`
- `outcome_mood_next_day`
- `outcome_bp_next_day`

The generated data also include patient-level baseline traits:

- `baseline_sleep_need`
- `baseline_activity_level`
- `baseline_stress_tendency`
- `baseline_bp`
- `baseline_phone_use`
- `baseline_adherence`

## Causal Logic

The simulator includes autoregressive and lagged mechanisms:

- stress today partly depends on stress yesterday
- late-night screen time depends on stress, prior sleep, baseline phone use, and reminders
- sleep quality depends on screen time, caffeine, stress, awakenings, sleep duration, and activity
- next-day fatigue is aligned as the next row's morning fatigue
- blood pressure depends on medication adherence, stress, caffeine, activity, and prior blood pressure

The estimators are intentionally practical rather than overbuilt. OLS, weighted OLS, and logistic propensity scores are implemented with NumPy/Pandas so the package can run in constrained local environments without compiled statistical dependencies.

## Development

Run tests:

```bash
pytest
```

Run a local MCP smoke test from Python:

```bash
python - <<'PY'
import asyncio
import json
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

## Home Assistant Integration Notes

This version does not require Home Assistant. The simulator creates synthetic versions of variables that could later come from Home Assistant history, Fitbit, phone sensors, and smart-home entities.

Possible future entity mappings:

- Fitbit sleep sensors -> `sleep_duration_hours`, `sleep_efficiency`, `awakenings`
- step counters -> `steps`, `active_minutes`, `sedentary_minutes`
- phone usage sensors -> `late_night_screen_minutes`, `phone_pickups`, `app_usage_minutes`
- pantry door sensors -> `pantry_door_opens`
- refrigerator door sensors -> `refrigerator_door_opens`
- smart plug current sensors -> appliance usage markers or bedtime routine markers
- medication cabinet sensors -> `medication_adherence`
- blood pressure readings -> `blood_pressure_systolic`, `blood_pressure_diastolic`

The same causal analysis tools could later be pointed at real Home Assistant history data after time alignment, missingness handling, consent/privacy review, and unit normalization.

## Important Limitations

- This is synthetic data.
- Results are not medical advice.
- Causal estimates depend on assumptions.
- No unmeasured confounding is generally untestable.
- Time alignment matters.
- Small N-of-1 datasets can be noisy.
- The models are simple parametric prototypes.
- The adjustment-set checker is practical guidance, not a formal d-separation engine.
- Real sensor data would require careful validation, missingness handling, privacy safeguards, and clinical review.
- The tool is for demonstration, research prototyping, and educational use.
