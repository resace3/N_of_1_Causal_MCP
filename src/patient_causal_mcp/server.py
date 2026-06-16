"""MCP server exposing synthetic patient simulation and causal analysis tools."""

from __future__ import annotations

from typing import Any

from patient_causal_mcp.causal_engine import CausalAnalysisEngine
from patient_causal_mcp.dag import check_adjustment_set as check_adjustment_set_core
from patient_causal_mcp.dag import generate_causal_dag as generate_causal_dag_core
from patient_causal_mcp.scenarios import list_scenarios
from patient_causal_mcp.schemas import (
    CheckAdjustmentSetInput,
    DescribePatientDataInput,
    EstimateCausalEffectInput,
    ExportDatasetInput,
    GenerateDagInput,
    ProposeCausalQuestionInput,
    SimulateInterventionInput,
    SimulatePatientDataInput,
    TargetTrialInput,
)
from patient_causal_mcp.simulator import PatientSimulator

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover - exercised only when the MCP SDK is unavailable.
    FastMCP = None  # type: ignore[assignment]


DATASET_REGISTRY: dict[str, list[dict[str, Any]]] = {}
SIMULATOR = PatientSimulator()
ENGINE = CausalAnalysisEngine()


def _records_from_input(dataset_id: str | None, data_records: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Return records from explicit data or the in-memory registry."""

    if data_records is not None:
        return data_records
    if not dataset_id:
        raise ValueError("Provide either dataset_id or data_records.")
    if dataset_id not in DATASET_REGISTRY:
        known = ", ".join(sorted(DATASET_REGISTRY)) or "none"
        raise ValueError(f"Unknown dataset_id '{dataset_id}'. Known dataset_ids: {known}.")
    return DATASET_REGISTRY[dataset_id]


def simulate_patient_data(
    patient_id: str | None = None,
    n_days: int = 180,
    start_date: str | None = None,
    seed: int | None = None,
    scenario: str = "mixed_lifestyle",
) -> dict[str, Any]:
    """Generate and store a synthetic longitudinal N-of-1 patient dataset."""

    request = SimulatePatientDataInput(
        patient_id=patient_id,
        n_days=n_days,
        start_date=start_date,
        seed=seed,
        scenario=scenario,
    )
    result = SIMULATOR.simulate(**request.model_dump())
    DATASET_REGISTRY[result["dataset_id"]] = result["full_data"]
    return result


def get_available_scenarios() -> dict[str, Any]:
    """Return descriptions of supported simulation scenarios."""

    return {"scenarios": list_scenarios()}


def describe_patient_data(
    dataset_id: str | None = None,
    data_records: list[dict[str, Any]] | None = None,
    variables: list[str] | None = None,
) -> dict[str, Any]:
    """Summarize a simulated patient dataset."""

    request = DescribePatientDataInput(
        dataset_id=dataset_id,
        data_records=data_records,
        variables=variables,
    )
    records = _records_from_input(request.dataset_id, request.data_records)
    return ENGINE.describe_patient_data(records, variables=request.variables)


def propose_causal_question(
    dataset_id: str | None = None,
    data_records: list[dict[str, Any]] | None = None,
    user_goal: str | None = None,
) -> dict[str, Any]:
    """Propose causal questions for a patient dataset."""

    request = ProposeCausalQuestionInput(
        dataset_id=dataset_id,
        data_records=data_records,
        user_goal=user_goal,
    )
    records = _records_from_input(request.dataset_id, request.data_records)
    return ENGINE.propose_causal_question(records, user_goal=request.user_goal)


def estimate_causal_effect(
    dataset_id: str | None = None,
    data_records: list[dict[str, Any]] | None = None,
    exposure: str = "",
    outcome: str = "",
    treatment_rule: dict[str, Any] | None = None,
    adjustment_variables: list[str] | None = None,
    method: str = "regression_adjustment",
    lag_exposure_days: int = 0,
    lag_outcome_days: int = 0,
    bootstrap: bool = False,
    n_bootstrap: int = 200,
    model_type: str = "linear",
    contrast: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Estimate a causal effect with regression adjustment, IPW, g-formula, or AIPW."""

    request = EstimateCausalEffectInput(
        dataset_id=dataset_id,
        data_records=data_records,
        exposure=exposure,
        outcome=outcome,
        treatment_rule=treatment_rule or {},
        adjustment_variables=adjustment_variables or [],
        method=method,  # type: ignore[arg-type]
        lag_exposure_days=lag_exposure_days,
        lag_outcome_days=lag_outcome_days,
        bootstrap=bootstrap,
        n_bootstrap=n_bootstrap,
        model_type=model_type,  # type: ignore[arg-type]
        contrast=contrast,
    )
    records = _records_from_input(request.dataset_id, request.data_records)
    return ENGINE.estimate_causal_effect(
        records,
        exposure=request.exposure,
        outcome=request.outcome,
        treatment_rule=request.treatment_rule,
        adjustment_variables=request.adjustment_variables,
        method=request.method,
        lag_exposure_days=request.lag_exposure_days,
        lag_outcome_days=request.lag_outcome_days,
        bootstrap=request.bootstrap,
        n_bootstrap=request.n_bootstrap,
        model_type=request.model_type,
        contrast=request.contrast,
    )


def run_target_trial_emulation(
    dataset_id: str | None = None,
    data_records: list[dict[str, Any]] | None = None,
    eligibility_criteria: dict[str, Any] | None = None,
    treatment_strategies: list[dict[str, Any]] | None = None,
    assignment_time: str | dict[str, Any] = "8 PM reminder decision",
    follow_up_days: int = 1,
    outcome: str = "",
    adjustment_variables: list[str] | None = None,
    method: str = "g_formula",
) -> dict[str, Any]:
    """Emulate a simple repeated daily target trial."""

    request = TargetTrialInput(
        dataset_id=dataset_id,
        data_records=data_records,
        eligibility_criteria=eligibility_criteria,
        treatment_strategies=treatment_strategies or [],
        assignment_time=assignment_time,
        follow_up_days=follow_up_days,
        outcome=outcome,
        adjustment_variables=adjustment_variables or [],
        method=method,  # type: ignore[arg-type]
    )
    records = _records_from_input(request.dataset_id, request.data_records)
    return ENGINE.run_target_trial_emulation(
        records,
        eligibility_criteria=request.eligibility_criteria,
        treatment_strategies=request.treatment_strategies,
        assignment_time=request.assignment_time,
        follow_up_days=request.follow_up_days,
        outcome=request.outcome,
        adjustment_variables=request.adjustment_variables,
        method=request.method,
    )


def generate_causal_dag(
    scenario: str = "mixed_lifestyle",
    variables: list[str] | None = None,
) -> dict[str, Any]:
    """Return scenario DAG nodes, edges, adjustment guidance, DOT, and Mermaid text."""

    request = GenerateDagInput(scenario=scenario, variables=variables)
    return generate_causal_dag_core(scenario=request.scenario, variables=request.variables)


def check_adjustment_set(
    dag_edges: list[dict[str, str]],
    exposure: str,
    outcome: str,
    adjustment_variables: list[str] | None = None,
) -> dict[str, Any]:
    """Check whether an adjustment set is reasonable for a simplified DAG."""

    request = CheckAdjustmentSetInput(
        dag_edges=dag_edges,
        exposure=exposure,
        outcome=outcome,
        adjustment_variables=adjustment_variables or [],
    )
    return check_adjustment_set_core(
        dag_edges=request.dag_edges,
        exposure=request.exposure,
        outcome=request.outcome,
        adjustment_variables=request.adjustment_variables,
    )


def simulate_intervention(
    dataset_id: str | None = None,
    data_records: list[dict[str, Any]] | None = None,
    intervention_name: str = "",
    intervention_rule: dict[str, Any] | None = None,
    target_variable: str = "",
    expected_change: float = 0.0,
    outcome: str = "",
    method: str = "g_formula",
    adjustment_variables: list[str] | None = None,
) -> dict[str, Any]:
    """Simulate a behavioral intervention using the fitted data relationships."""

    request = SimulateInterventionInput(
        dataset_id=dataset_id,
        data_records=data_records,
        intervention_name=intervention_name,
        intervention_rule=intervention_rule or {},
        target_variable=target_variable,
        expected_change=expected_change,
        outcome=outcome,
        method=method,  # type: ignore[arg-type]
        adjustment_variables=adjustment_variables,
    )
    records = _records_from_input(request.dataset_id, request.data_records)
    return ENGINE.simulate_intervention(
        records,
        intervention_name=request.intervention_name,
        intervention_rule=request.intervention_rule,
        target_variable=request.target_variable,
        expected_change=request.expected_change,
        outcome=request.outcome,
        method=request.method,
        adjustment_variables=request.adjustment_variables,
    )


def export_dataset(
    dataset_id: str | None = None,
    data_records: list[dict[str, Any]] | None = None,
    format: str = "csv",
) -> dict[str, Any]:
    """Export a dataset as CSV text or JSON records."""

    request = ExportDatasetInput(
        dataset_id=dataset_id,
        data_records=data_records,
        format=format,  # type: ignore[arg-type]
    )
    records = _records_from_input(request.dataset_id, request.data_records)
    return ENGINE.export_dataset(records, format=request.format)


def create_mcp_server() -> Any:
    """Create the MCP server instance and register all tools."""

    if FastMCP is None:
        raise RuntimeError(
            "The MCP SDK is not installed or its import path changed. Install dependencies with "
            "`pip install -e .` and verify `mcp.server.fastmcp.FastMCP` is available."
        )
    mcp = FastMCP("patient-causal-mcp")

    mcp.tool()(simulate_patient_data)
    mcp.tool()(get_available_scenarios)
    mcp.tool()(describe_patient_data)
    mcp.tool()(propose_causal_question)
    mcp.tool()(estimate_causal_effect)
    mcp.tool()(run_target_trial_emulation)
    mcp.tool()(generate_causal_dag)
    mcp.tool()(check_adjustment_set)
    mcp.tool()(simulate_intervention)
    mcp.tool()(export_dataset)
    return mcp


def main() -> None:
    """Run the MCP server over stdio."""

    mcp = create_mcp_server()
    mcp.run()


if __name__ == "__main__":
    main()
