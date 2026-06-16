"""Pydantic input schemas used by the MCP server and examples."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DataInput(BaseModel):
    """Common optional dataset selector."""

    dataset_id: str | None = None
    data_records: list[dict[str, Any]] | None = None


class SimulatePatientDataInput(BaseModel):
    patient_id: str | None = None
    n_days: int = Field(default=180, gt=0)
    start_date: str | None = None
    seed: int | None = None
    scenario: str = "mixed_lifestyle"


class DescribePatientDataInput(DataInput):
    variables: list[str] | None = None


class ProposeCausalQuestionInput(DataInput):
    user_goal: str | None = None


class EstimateCausalEffectInput(DataInput):
    exposure: str
    outcome: str
    treatment_rule: dict[str, Any]
    adjustment_variables: list[str] = Field(default_factory=list)
    method: Literal["regression_adjustment", "ipw", "g_formula", "doubly_robust"] = "regression_adjustment"
    lag_exposure_days: int = 0
    lag_outcome_days: int = 0
    bootstrap: bool = False
    n_bootstrap: int = 200
    model_type: Literal["linear", "logistic"] = "linear"
    contrast: dict[str, Any] | None = None


class TargetTrialInput(DataInput):
    eligibility_criteria: dict[str, Any] | None = None
    treatment_strategies: list[dict[str, Any]]
    assignment_time: str | dict[str, Any]
    follow_up_days: int = Field(default=1, ge=1)
    outcome: str
    adjustment_variables: list[str] = Field(default_factory=list)
    method: Literal["regression_adjustment", "ipw", "g_formula", "doubly_robust"] = "g_formula"


class GenerateDagInput(BaseModel):
    scenario: str = "mixed_lifestyle"
    variables: list[str] | None = None


class CheckAdjustmentSetInput(BaseModel):
    dag_edges: list[dict[str, str]]
    exposure: str
    outcome: str
    adjustment_variables: list[str] = Field(default_factory=list)


class SimulateInterventionInput(DataInput):
    intervention_name: str
    intervention_rule: dict[str, Any]
    target_variable: str
    expected_change: float
    outcome: str
    method: Literal["regression_adjustment", "ipw", "g_formula", "doubly_robust"] = "g_formula"
    adjustment_variables: list[str] | None = None


class ExportDatasetInput(DataInput):
    format: Literal["csv", "json"] = "csv"
