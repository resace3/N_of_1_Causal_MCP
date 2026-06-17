"""MCP server exposing bundled patient data and causal analysis tools."""

from functools import wraps
from inspect import Signature, signature
from typing import Any

from patient_causal_mcp.causal_engine import CausalAnalysisEngine
from patient_causal_mcp.dag import check_adjustment_set as check_adjustment_set_core
from patient_causal_mcp.dag import generate_causal_dag as generate_causal_dag_core
from patient_causal_mcp.datasets import (
    DEFAULT_DATASET_ID,
    get_bundled_dataset_metadata,
    load_bundled_dataset,
)
from patient_causal_mcp.scenarios import list_scenarios
from patient_causal_mcp.schemas import (
    AggregateHaStatesDailyInput,
    CheckAdjustmentSetInput,
    DescribePatientDataInput,
    EstimateCausalEffectInput,
    ExportDatasetInput,
    GenerateDagInput,
    ProposeCausalQuestionInput,
    QueryHaStatesInput,
    SimulateInterventionInput,
    TargetTrialInput,
)
from patient_causal_mcp.synthetic.homer_ha import (
    aggregate_homer_ha_states_daily,
    describe_homer_dataset,
    export_homer_dataset,
    get_homer_dataset_metadata,
    homer_records_for_analysis,
    is_homer_dataset,
    query_homer_ha_states,
)
from patient_causal_mcp.tool_metadata import TOOL_NAMES

__all__ = ["TOOL_NAMES", "create_cloudflare_mcp_server", "create_mcp_server"]

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover - exercised only when the MCP SDK is unavailable.
    FastMCP = None  # type: ignore[assignment]


DATASET_REGISTRY: dict[str, list[dict[str, Any]]] = {}
ENGINE = CausalAnalysisEngine()
PUBLIC_SYNTHETIC_ONLY_ERROR = (
    "Caller-supplied data_records are disabled on the public Cloudflare MCP endpoint. "
    "Use one of the bundled synthetic dataset_id values instead."
)


def _ensure_bundled_datasets_loaded() -> None:
    """Load bundled static datasets into the in-memory registry if needed."""

    for item in get_bundled_dataset_metadata():
        dataset_id = item["dataset_id"]
        if dataset_id not in DATASET_REGISTRY:
            DATASET_REGISTRY[dataset_id] = load_bundled_dataset(dataset_id)


def _records_from_input(
    dataset_id: str | None, data_records: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    """Return records from explicit data or the in-memory registry."""

    if data_records is not None:
        return data_records
    if not dataset_id:
        dataset_id = DEFAULT_DATASET_ID
    if is_homer_dataset(dataset_id):
        return homer_records_for_analysis(dataset_id)
    _ensure_bundled_datasets_loaded()
    if dataset_id not in DATASET_REGISTRY:
        known = ", ".join(sorted([*DATASET_REGISTRY, *[item["dataset_id"] for item in get_homer_dataset_metadata()]])) or "none"
        raise ValueError(f"Unknown dataset_id '{dataset_id}'. Known dataset_ids: {known}.")
    return DATASET_REGISTRY[dataset_id]


def get_available_datasets() -> dict:
    """Return bundled static datasets available for analysis."""

    _ensure_bundled_datasets_loaded()
    datasets = [*get_bundled_dataset_metadata(), *get_homer_dataset_metadata()]
    return {
        "default_dataset_id": DEFAULT_DATASET_ID,
        "datasets": datasets,
        "loaded_dataset_ids": sorted([*DATASET_REGISTRY, *[item["dataset_id"] for item in get_homer_dataset_metadata()]]),
    }


def get_available_scenarios() -> dict:
    """Return descriptions of supported causal-analysis scenarios."""

    return {"scenarios": list_scenarios()}


def describe_patient_data(
    dataset_id: str = None,
    data_records: list = None,
    variables: list = None,
) -> dict:
    """Summarize a patient dataset."""

    request = DescribePatientDataInput(
        dataset_id=dataset_id,
        data_records=data_records,
        variables=variables,
    )
    if request.data_records is None and request.dataset_id and is_homer_dataset(request.dataset_id):
        return describe_homer_dataset(request.dataset_id, variables=request.variables)
    records = _records_from_input(request.dataset_id, request.data_records)
    return ENGINE.describe_patient_data(records, variables=request.variables)


def propose_causal_question(
    dataset_id: str = None,
    data_records: list = None,
    user_goal: str = None,
) -> dict:
    """Propose causal questions for a patient dataset."""

    request = ProposeCausalQuestionInput(
        dataset_id=dataset_id,
        data_records=data_records,
        user_goal=user_goal,
    )
    records = _records_from_input(request.dataset_id, request.data_records)
    return ENGINE.propose_causal_question(records, user_goal=request.user_goal)


def _homer_target_trial_defaults(
    *,
    dataset_id: str | None,
    eligibility_criteria: dict[str, Any] | None,
    treatment_strategies: list[dict[str, Any]],
    assignment_time: object,
    outcome: str,
    adjustment_variables: list[str],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], object, str, list[str]]:
    """Fill named Homer target-trial examples when strategies are omitted."""

    if not dataset_id or not is_homer_dataset(dataset_id) or treatment_strategies:
        return (
            eligibility_criteria,
            treatment_strategies,
            assignment_time,
            outcome,
            adjustment_variables,
        )
    selector = f"{assignment_time} {outcome}".lower()
    if "walk" in selector or "mood" in selector:
        return (
            eligibility_criteria
            or {"prior_steps": {"max": 6500}, "prior_fatigue": {"min": 4.0}},
            [
                {"label": "walk nudge", "variable": "walk_nudge_received", "type": "binary_variable"},
                {
                    "label": "no walk nudge",
                    "variable": "walk_nudge_received",
                    "type": "binary_variable",
                },
            ],
            "Morning low-activity nudge decision",
            outcome or "outcome_mood_next_day",
            adjustment_variables
            or [
                "prior_fatigue",
                "prior_steps",
                "prior_stress_score",
                "is_workday",
                "baseline_activity_level",
            ],
        )
    if "caffeine" in selector:
        return (
            eligibility_criteria
            or {"prior_fatigue": {"min": 5.0}, "prior_stress_score": {"min": 4.0}},
            [
                {
                    "label": "caffeine nudge",
                    "variable": "caffeine_nudge_received",
                    "type": "binary_variable",
                },
                {
                    "label": "no caffeine nudge",
                    "variable": "caffeine_nudge_received",
                    "type": "binary_variable",
                },
            ],
            "Noon caffeine-risk nudge decision",
            outcome or "outcome_sleep_quality",
            adjustment_variables
            or ["prior_fatigue", "prior_sleep_quality", "prior_stress_score", "is_workday"],
        )
    return (
        eligibility_criteria or {"prior_fatigue": {"min": 5.5}, "prior_sleep_quality": {"max": 6.0}},
        [
            {"label": "sleep nudge", "variable": "sleep_nudge_received", "type": "binary_variable"},
            {
                "label": "no sleep nudge",
                "variable": "sleep_nudge_received",
                "type": "binary_variable",
            },
        ],
        "8 PM sleep-risk nudge decision",
        outcome or "outcome_sleep_quality",
        adjustment_variables
        or ["prior_sleep_quality", "prior_fatigue", "prior_stress_score", "is_workday"],
    )


def estimate_causal_effect(
    dataset_id: str = None,
    data_records: list = None,
    exposure: str = "",
    outcome: str = "",
    treatment_rule: dict = None,
    adjustment_variables: list = None,
    method: str = "regression_adjustment",
    lag_exposure_days: int = 0,
    lag_outcome_days: int = 0,
    bootstrap: bool = False,
    n_bootstrap: int = 200,
    model_type: str = "linear",
    contrast: dict = None,
) -> dict:
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
    dataset_id: str = None,
    data_records: list = None,
    eligibility_criteria: dict = None,
    treatment_strategies: list = None,
    assignment_time: object = "8 PM reminder decision",
    follow_up_days: int = 1,
    outcome: str = "",
    adjustment_variables: list = None,
    method: str = "g_formula",
) -> dict:
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
    (
        request.eligibility_criteria,
        request.treatment_strategies,
        request.assignment_time,
        request.outcome,
        request.adjustment_variables,
    ) = _homer_target_trial_defaults(
        dataset_id=request.dataset_id,
        eligibility_criteria=request.eligibility_criteria,
        treatment_strategies=request.treatment_strategies,
        assignment_time=request.assignment_time,
        outcome=request.outcome,
        adjustment_variables=request.adjustment_variables,
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
    variables: list = None,
) -> dict:
    """Return scenario DAG nodes, edges, adjustment guidance, DOT, and Mermaid text."""

    request = GenerateDagInput(scenario=scenario, variables=variables)
    return generate_causal_dag_core(scenario=request.scenario, variables=request.variables)


def check_adjustment_set(
    dag_edges: list,
    exposure: str,
    outcome: str,
    adjustment_variables: list = None,
) -> dict:
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
    dataset_id: str = None,
    data_records: list = None,
    intervention_name: str = "",
    intervention_rule: dict = None,
    target_variable: str = "",
    expected_change: float = 0.0,
    outcome: str = "",
    method: str = "g_formula",
    adjustment_variables: list = None,
) -> dict:
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
    dataset_id: str = None,
    data_records: list = None,
    format: str = "csv",
    table: str = "daily",
) -> dict:
    """Export a dataset as CSV text, JSON records, or a generated SQL dump."""

    request = ExportDatasetInput(
        dataset_id=dataset_id,
        data_records=data_records,
        format=format,  # type: ignore[arg-type]
        table=table,
    )
    if request.data_records is None and request.dataset_id and is_homer_dataset(request.dataset_id):
        return export_homer_dataset(
            dataset_id=request.dataset_id,
            format=request.format,
            table=request.table,
        )
    records = _records_from_input(request.dataset_id, request.data_records)
    if request.format == "sql":
        raise ValueError("SQL export is only supported for Homer Home Assistant-style datasets.")
    return ENGINE.export_dataset(records, format=request.format)


def query_ha_states(
    dataset_id: str = None,
    data_records: list = None,
    entity_id: str = None,
    domain: str = None,
    start: str = None,
    end: str = None,
    limit: int = 1000,
    include_attributes: bool = False,
    parse_numeric: bool = False,
) -> dict:
    """Query Homer Home Assistant-style state history by entity, domain, and time."""

    request = QueryHaStatesInput(
        dataset_id=dataset_id,
        data_records=data_records,
        entity_id=entity_id,
        domain=domain,
        start=start,
        end=end,
        limit=limit,
        include_attributes=include_attributes,
        parse_numeric=parse_numeric,
    )
    if request.data_records is not None:
        raise ValueError("query_ha_states only supports bundled synthetic HA-style datasets.")
    if not request.dataset_id or not is_homer_dataset(request.dataset_id):
        raise ValueError("query_ha_states currently supports only Homer synthetic HA-style dataset IDs.")
    return query_homer_ha_states(
        dataset_id=request.dataset_id,
        entity_id=request.entity_id,
        domain=request.domain,
        start=request.start,
        end=request.end,
        limit=request.limit,
        include_attributes=request.include_attributes,
        parse_numeric=request.parse_numeric,
    )


def aggregate_ha_states_daily(
    dataset_id: str = None,
    data_records: list = None,
    entity_ids: list = None,
    aggregation_config: dict = None,
) -> dict:
    """Aggregate Homer Home Assistant-style state history into daily analysis rows."""

    request = AggregateHaStatesDailyInput(
        dataset_id=dataset_id,
        data_records=data_records,
        entity_ids=entity_ids,
        aggregation_config=aggregation_config,
    )
    if request.data_records is not None:
        raise ValueError("aggregate_ha_states_daily only supports bundled synthetic HA-style datasets.")
    if not request.dataset_id or not is_homer_dataset(request.dataset_id):
        raise ValueError(
            "aggregate_ha_states_daily currently supports only Homer synthetic HA-style dataset IDs."
        )
    return aggregate_homer_ha_states_daily(
        dataset_id=request.dataset_id,
        entity_ids=request.entity_ids,
        aggregation_config=request.aggregation_config,
    )


def _synthetic_only_public_tool(func: Any) -> Any:
    """Wrap a tool so the public Worker cannot process caller-supplied records."""

    tool_signature = signature(func)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        bound = tool_signature.bind_partial(*args, **kwargs)
        if bound.arguments.get("data_records") is not None:
            raise ValueError(PUBLIC_SYNTHETIC_ONLY_ERROR)
        return func(*args, **kwargs)

    public_parameters = [
        parameter
        for name, parameter in tool_signature.parameters.items()
        if name != "data_records"
    ]
    wrapper.__signature__ = Signature(  # type: ignore[attr-defined]
        parameters=public_parameters,
        return_annotation=tool_signature.return_annotation,
    )
    return wrapper


def _new_fastmcp_server(
    *,
    name: str = "patient-causal-mcp",
    stateless_http: bool = False,
    json_response: bool = False,
    streamable_http_path: str | None = None,
) -> Any:
    """Construct FastMCP while tolerating older SDK keyword support."""

    if FastMCP is None:
        raise RuntimeError(
            "The MCP SDK is not installed or its import path changed. Install dependencies with "
            "`pip install -e .` and verify `mcp.server.fastmcp.FastMCP` is available."
        )

    kwargs: dict[str, Any] = {}
    if stateless_http:
        kwargs["stateless_http"] = True
    if json_response:
        kwargs["json_response"] = True
    if streamable_http_path is not None:
        kwargs["streamable_http_path"] = streamable_http_path

    try:
        return FastMCP(name, **kwargs)
    except TypeError:
        # Older Python MCP SDK versions may not support every HTTP keyword.
        # Retry with progressively smaller constructor kwargs while leaving tool
        # registration unchanged and without swallowing causal-tool runtime errors.
        fallback_keys = [
            ("stateless_http", "json_response"),
            ("stateless_http", "streamable_http_path"),
            ("json_response", "streamable_http_path"),
            ("stateless_http",),
            ("json_response",),
            ("streamable_http_path",),
            (),
        ]
        for keys in fallback_keys:
            fallback_kwargs = {key: kwargs[key] for key in keys if key in kwargs}
            try:
                return FastMCP(name, **fallback_kwargs)
            except TypeError:
                continue
        raise


def _register_tools(mcp: Any, *, allow_caller_data_records: bool = True) -> Any:
    """Register all MCP tools exactly once on a FastMCP instance."""

    def register(func: Any) -> None:
        if allow_caller_data_records:
            mcp.tool()(func)
            return
        mcp.tool()(_synthetic_only_public_tool(func))

    register(get_available_datasets)
    register(get_available_scenarios)
    register(describe_patient_data)
    register(propose_causal_question)
    register(estimate_causal_effect)
    register(run_target_trial_emulation)
    register(generate_causal_dag)
    register(check_adjustment_set)
    register(simulate_intervention)
    register(export_dataset)
    register(query_ha_states)
    register(aggregate_ha_states_daily)
    return mcp


def create_mcp_server(
    *,
    stateless_http: bool = False,
    json_response: bool = False,
    streamable_http_path: str | None = None,
    allow_caller_data_records: bool = True,
) -> Any:
    """Create the MCP server instance and register all tools."""

    mcp = _new_fastmcp_server(
        stateless_http=stateless_http,
        json_response=json_response,
        streamable_http_path=streamable_http_path,
    )
    return _register_tools(mcp, allow_caller_data_records=allow_caller_data_records)


def create_cloudflare_mcp_server() -> Any:
    """Create an MCP server configured for Cloudflare Streamable HTTP."""

    return create_mcp_server(
        stateless_http=False,
        json_response=True,
        streamable_http_path="/mcp",
        allow_caller_data_records=False,
    )


def main() -> None:
    """Run the MCP server over stdio."""

    mcp = create_mcp_server()
    mcp.run()


if __name__ == "__main__":
    main()
