# patient-causal-mcp

`patient-causal-mcp` is a developer-ready MCP server that simulates a longitudinal N-of-1 patient dataset and exposes tools for causal analysis. It is designed for AI assistants that need to generate synthetic daily health data, inspect causal assumptions, estimate simple effects, emulate target trials, and explain results in clinical or digital health language.

The project is intentionally synthetic. It is for demonstration, research prototyping, and education.

## What It Does

- Simulates one synthetic patient over 90, 180, 365, or other requested day counts.
- Generates daily health, behavior, and sensor-like variables.
- Supports multiple causal scenarios:
  - `sleep_screen_time`
  - `steps_fatigue`
  - `medication_bp`
  - `stress_sleep`
  - `nighttime_eating_fatigue`
  - `mixed_lifestyle`
- Exposes MCP tools for simulation, summaries, DAG generation, adjustment checks, causal estimation, intervention simulation, target trial emulation, and export.
- Uses an in-memory dataset registry so follow-up tool calls can refer to a `dataset_id`.
- Also accepts raw records so tools can be used statelessly.

## Why MCP Is Useful Here

MCP gives an AI assistant a structured interface to the simulator and causal engine. Instead of asking an assistant to invent data or perform fragile spreadsheet reasoning, the assistant can call explicit tools with typed arguments:

- simulate data with a known data-generating process
- return a DAG and default adjustment set
- estimate a contrast using a named method
- return diagnostics, assumptions, and plain-language interpretation

This makes the workflow easier to inspect, test, and later connect to real data sources.

## Setup

```bash
cd patient-causal-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

If your environment does not support extras, use:

```bash
pip install -r requirements.txt
pip install -e .
```

## Run the MCP Server

```bash
patient-causal-mcp
```

Or:

```bash
python -m patient_causal_mcp.server
```

The server uses stdio transport through the official Python MCP SDK import path:

```python
from mcp.server.fastmcp import FastMCP
```

If the SDK changes this import path, the core package still works; update `src/patient_causal_mcp/server.py` in `create_mcp_server`.

The causal estimators use NumPy/Pandas implementations for OLS, weighted OLS, and logistic propensity scores so the package can run in constrained local environments without compiled statistical dependencies.

## MCP Tools

### `simulate_patient_data`

Generate synthetic patient data.

```json
{
  "patient_id": "demo-patient",
  "n_days": 180,
  "start_date": "2026-01-01",
  "seed": 42,
  "scenario": "sleep_screen_time"
}
```

Returns `dataset_id`, metadata, causal graph edges, a preview, and `full_data`.

### `get_available_scenarios`

Returns each scenario's causal question, exposure, outcome, confounders, mediators, expected direction, and interpretation.

### `describe_patient_data`

```json
{
  "dataset_id": "<dataset_id>"
}
```

Returns missingness, numeric summaries, binary counts, correlation highlights, and time trends.

### `propose_causal_question`

```json
{
  "dataset_id": "<dataset_id>",
  "user_goal": "I want to improve sleep"
}
```

Returns candidate causal questions with exposure, outcome, time zero, follow-up window, adjustment variables, and variables to avoid adjusting for.

### `estimate_causal_effect`

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

- `regression_adjustment`: outcome model with exposure and adjustment variables.
- `ipw`: logistic propensity score and stabilized clipped weights for binary exposure.
- `g_formula`: outcome model used to predict potential outcomes under two strategies.
- `doubly_robust`: simple AIPW estimator for binary treatment.

### `run_target_trial_emulation`

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

### `generate_causal_dag`

```json
{
  "scenario": "sleep_screen_time"
}
```

Returns nodes, edges, exposure, outcome, confounders, mediators, colliders, default adjustment set, DOT, and Mermaid.

### `check_adjustment_set`

```json
{
  "dag_edges": [
    { "source": "stress_score", "target": "late_night_screen_minutes" },
    { "source": "stress_score", "target": "outcome_sleep_quality" }
  ],
  "exposure": "late_night_screen_minutes",
  "outcome": "outcome_sleep_quality",
  "adjustment_variables": ["stress_score"]
}
```

This is a practical helper, not a full DAGitty replacement.

### `simulate_intervention`

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

### `export_dataset`

```json
{
  "dataset_id": "<dataset_id>",
  "format": "csv"
}
```

Formats: `csv`, `json`.

## Example Direct Python Run

```bash
python examples/example_client.py
```

This bypasses the MCP client and calls the same tool functions directly.

## Causal Logic

The simulator includes autoregressive and lagged patterns:

- stress today partly depends on stress yesterday
- late-night screen time depends on stress, prior sleep, baseline phone use, and reminders
- sleep quality depends on screen time, caffeine, stress, awakenings, sleep duration, and activity
- next-day fatigue is aligned as the next row's morning fatigue
- blood pressure depends on medication adherence, stress, caffeine, activity, and prior blood pressure

The generated data include patient-level baseline traits:

- `baseline_sleep_need`
- `baseline_activity_level`
- `baseline_stress_tendency`
- `baseline_bp`
- `baseline_phone_use`
- `baseline_adherence`

These traits are repeated in each row so they can be used in analyses and exported.

## Development

Run tests:

```bash
pytest
```

Project layout:

```text
patient-causal-mcp/
  README.md
  pyproject.toml
  requirements.txt
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
  examples/
    example_client.py
    example_prompts.md
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

The same causal tools could later be pointed at a real Home Assistant history export after time alignment, cleaning, missingness handling, and consent/privacy checks.

## Important Limitations

- This is synthetic data.
- Results are not medical advice.
- Causal estimates depend on assumptions.
- No unmeasured confounding is generally untestable.
- Time alignment matters.
- Small N-of-1 datasets can be noisy.
- The models are simple parametric prototypes.
- The adjustment-set checker is practical guidance, not a formal d-separation engine.
- The tool is for demonstration, research prototyping, and educational use.
