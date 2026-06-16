# Example Prompts

Use these prompts with an MCP-capable AI assistant after connecting the server.

1. Show me the bundled patient datasets.
2. Summarize the default 100-day patient dataset.
3. Show me the causal DAG for the sleep screen-time scenario.
4. Estimate the effect of reducing late-night screen time to 120 minutes or less on sleep quality.
5. Check whether adjusting for stress, caffeine, prior sleep quality, and steps is reasonable.
6. Run a target trial comparing intervention reminders versus no reminders for next-day sleep quality.
7. Simulate an intervention where late-night screen time is reduced by 60 minutes.
8. Export the current dataset as CSV.

Example tool-style inputs:

```json
{
  "tool": "get_available_datasets",
  "arguments": {}
}
```

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

```json
{
  "tool": "run_target_trial_emulation",
  "arguments": {
    "dataset_id": "patient_001_100_days",
    "eligibility_criteria": {
      "prior_sleep_quality": { "max": 8 }
    },
    "treatment_strategies": [
      { "name": "Reminder at 8 PM", "type": "binary_variable", "variable": "intervention_received", "value": 1 },
      { "name": "No reminder", "type": "binary_variable", "variable": "intervention_received", "value": 0 }
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
