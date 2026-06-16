"""Causal analysis estimators for longitudinal synthetic patient data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd

from patient_causal_mcp.scenarios import VARIABLE_DESCRIPTIONS
from patient_causal_mcp.utils import (
    clean_numeric_frame,
    dataframe_to_records,
    infer_binary,
    numeric_summary,
    records_to_dataframe,
    summarize_binary,
    validate_columns,
)


MethodName = Literal["regression_adjustment", "ipw", "g_formula", "doubly_robust"]


@dataclass(frozen=True)
class TreatmentDefinition:
    """Internal representation of a binary treatment contrast."""

    treatment_column: str
    label_a: str
    label_b: str
    value_a: float
    value_b: float
    transformed_data: pd.DataFrame


@dataclass(frozen=True)
class LinearModelResult:
    """Small OLS result object used to avoid compiled statistical dependencies."""

    params: pd.Series
    bse: pd.Series
    fitted_values: np.ndarray
    residuals: np.ndarray
    condition_number: float

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        """Predict from a design matrix with columns matching the fitted model."""

        aligned = x.loc[:, list(self.params.index)]
        return aligned.to_numpy(dtype=float) @ self.params.to_numpy(dtype=float)


class CausalAnalysisEngine:
    """Run descriptive summaries and practical causal estimators."""

    def describe_patient_data(
        self,
        records: list[dict[str, Any]] | pd.DataFrame,
        variables: list[str] | None = None,
    ) -> dict[str, Any]:
        """Summarize a simulated longitudinal patient dataset."""

        df = records_to_dataframe(records)
        selected = list(variables) if variables else list(df.columns)
        validate_columns(df, selected, context="describe_patient_data")

        date_range = None
        if "date" in df.columns:
            dates = pd.to_datetime(df["date"], errors="coerce")
            date_range = {
                "start": dates.min().strftime("%Y-%m-%d") if dates.notna().any() else None,
                "end": dates.max().strftime("%Y-%m-%d") if dates.notna().any() else None,
            }

        missingness = {
            column: {
                "missing_count": int(df[column].isna().sum()),
                "missing_fraction": float(df[column].isna().mean()),
            }
            for column in selected
        }

        numeric_columns = [
            column
            for column in selected
            if column in df.columns and pd.api.types.is_numeric_dtype(pd.to_numeric(df[column], errors="coerce"))
        ]
        numeric_summaries: dict[str, Any] = {}
        binary_counts: dict[str, Any] = {}
        for column in numeric_columns:
            numeric = pd.to_numeric(df[column], errors="coerce")
            if infer_binary(numeric):
                binary_counts[column] = summarize_binary(numeric)
            else:
                numeric_summaries[column] = numeric_summary(numeric)

        correlation_highlights = self._correlation_highlights(df, numeric_columns)
        time_trend_highlights = self._time_trend_highlights(df, numeric_columns)

        return {
            "number_of_days": int(df.shape[0]),
            "date_range": date_range,
            "missingness_summary": missingness,
            "numeric_summaries": numeric_summaries,
            "binary_counts": binary_counts,
            "correlation_highlights": correlation_highlights,
            "time_trend_highlights": time_trend_highlights,
            "warning": "Correlation and time trends are descriptive only; they do not prove causation.",
        }

    def propose_causal_question(
        self,
        records: list[dict[str, Any]] | pd.DataFrame,
        user_goal: str | None = None,
    ) -> dict[str, Any]:
        """Propose clinically meaningful causal questions based on available columns."""

        df = records_to_dataframe(records)
        columns = set(df.columns)
        candidates = [
            {
                "question": (
                    "What would happen to next-day sleep quality if this patient reduced "
                    "late-night screen time below 30 minutes compared with days above 90 minutes?"
                ),
                "exposure": "late_night_screen_minutes",
                "outcome": "outcome_sleep_quality",
                "time_zero_definition": "Evening of each eligible day before the sleep episode.",
                "follow_up_window": "Same-night sleep quality aligned to the exposure day.",
                "adjustment_variables": ["stress_score", "caffeine_mg", "prior_sleep_quality", "steps"],
                "possible_confounders": ["stress_score", "caffeine_mg", "prior_sleep_quality", "steps"],
                "variables_to_avoid_adjusting_for": ["sleep_duration_hours", "sleep_efficiency"],
                "why_meaningful": "Screen time is modifiable and often captured passively by phone sensors.",
            },
            {
                "question": (
                    "What would happen to next-day fatigue if this patient increased steps above "
                    "8000 compared with days below 4000?"
                ),
                "exposure": "steps",
                "outcome": "outcome_next_day_fatigue",
                "time_zero_definition": "End of each calendar day after observing total steps.",
                "follow_up_window": "Next morning fatigue.",
                "adjustment_variables": ["prior_fatigue", "stress_score", "sleep_quality", "day_of_week"],
                "possible_confounders": ["prior_fatigue", "stress_score", "sleep_quality", "day_of_week"],
                "variables_to_avoid_adjusting_for": ["active_minutes"],
                "why_meaningful": "Activity is a common behavioral target, but better days can also cause more steps.",
            },
            {
                "question": "What is the effect of medication adherence on next-day systolic blood pressure?",
                "exposure": "medication_adherence",
                "outcome": "outcome_bp_next_day",
                "time_zero_definition": "Medication decision point on each day.",
                "follow_up_window": "Next-day systolic blood pressure.",
                "adjustment_variables": ["baseline_bp", "stress_score", "caffeine_mg", "prior_bp"],
                "possible_confounders": ["baseline_bp", "stress_score", "caffeine_mg", "prior_bp"],
                "variables_to_avoid_adjusting_for": ["blood_pressure_diastolic"],
                "why_meaningful": "Adherence is actionable and blood pressure is a clinically meaningful marker.",
            },
            {
                "question": "What is the effect of nighttime eating on morning fatigue?",
                "exposure": "nighttime_eating",
                "outcome": "morning_fatigue",
                "time_zero_definition": "Late evening/night eating window.",
                "follow_up_window": "Morning fatigue the next morning.",
                "adjustment_variables": ["stress_score", "late_night_screen_minutes", "prior_fatigue"],
                "possible_confounders": ["stress_score", "late_night_screen_minutes", "prior_fatigue"],
                "variables_to_avoid_adjusting_for": ["sleep_duration_hours"],
                "why_meaningful": "Nighttime eating can be proxied by kitchen sensors and may be behaviorally modifiable.",
            },
            {
                "question": "What is the total effect of an evening reminder on same-night sleep quality?",
                "exposure": "intervention_received",
                "outcome": "outcome_sleep_quality",
                "time_zero_definition": "The planned 8 PM reminder decision time.",
                "follow_up_window": "Same-night sleep quality.",
                "adjustment_variables": [
                    "stress_score",
                    "prior_sleep_quality",
                    "prior_fatigue",
                    "day_of_week",
                    "baseline_phone_use",
                ],
                "possible_confounders": [
                    "stress_score",
                    "prior_sleep_quality",
                    "prior_fatigue",
                    "day_of_week",
                    "baseline_phone_use",
                ],
                "variables_to_avoid_adjusting_for": ["late_night_screen_minutes", "nighttime_eating"],
                "why_meaningful": "It directly evaluates a digital intervention strategy.",
            },
        ]

        available = [
            candidate
            for candidate in candidates
            if candidate["exposure"] in columns
            and candidate["outcome"] in columns
            and all(variable in columns for variable in candidate["adjustment_variables"])
        ]
        if user_goal:
            goal_lower = user_goal.lower()
            available.sort(
                key=lambda candidate: int(
                    any(token in candidate["question"].lower() for token in goal_lower.split())
                ),
                reverse=True,
            )
        return {
            "user_goal": user_goal,
            "proposed_questions": available[:5],
            "note": "Question proposals assume correct temporal alignment and sufficient within-person variation.",
        }

    def estimate_causal_effect(
        self,
        records: list[dict[str, Any]] | pd.DataFrame,
        *,
        exposure: str,
        outcome: str,
        treatment_rule: dict[str, Any],
        adjustment_variables: list[str],
        method: MethodName = "regression_adjustment",
        lag_exposure_days: int = 0,
        lag_outcome_days: int = 0,
        bootstrap: bool = False,
        n_bootstrap: int = 200,
        model_type: Literal["linear", "logistic"] = "linear",
        contrast: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Estimate a causal contrast using a practical method."""

        if method not in {"regression_adjustment", "ipw", "g_formula", "doubly_robust"}:
            raise ValueError(
                "method must be one of: regression_adjustment, ipw, g_formula, doubly_robust."
            )
        if model_type != "linear":
            raise ValueError("Only linear outcome models are currently implemented for causal estimates.")

        analysis_df = self._prepare_lagged_data(
            records=records,
            exposure=exposure,
            outcome=outcome,
            adjustment_variables=adjustment_variables,
            lag_exposure_days=lag_exposure_days,
            lag_outcome_days=lag_outcome_days,
        )
        treatment = self._build_treatment(
            analysis_df,
            exposure=exposure,
            treatment_rule=treatment_rule,
            contrast=contrast,
        )
        estimation_df = treatment.transformed_data
        required = [treatment.treatment_column, "_analysis_outcome", *adjustment_variables]
        original_rows = len(records_to_dataframe(records))
        model_df = clean_numeric_frame(estimation_df, required)
        rows_dropped = int(original_rows - model_df.shape[0])
        if model_df.shape[0] < max(20, len(adjustment_variables) + 5):
            raise ValueError(
                "Not enough complete rows for the requested analysis after lagging and missing-data removal."
            )

        estimate_result = self._estimate_once(
            model_df,
            treatment=treatment,
            adjustment_variables=adjustment_variables,
            method=method,
        )

        interval = None
        if bootstrap:
            interval = self._bootstrap_ci(
                model_df,
                treatment=treatment,
                adjustment_variables=adjustment_variables,
                method=method,
                n_bootstrap=n_bootstrap,
            )

        warnings = estimate_result["diagnostic_warnings"]
        warnings.extend(self._variation_warnings(model_df[treatment.treatment_column], treatment))
        return {
            "method": method,
            "exposure": exposure,
            "outcome": outcome,
            "treatment_definition": {
                "rule": treatment_rule,
                "comparison": f"{treatment.label_a} versus {treatment.label_b}",
                "treatment_column": treatment.treatment_column,
            },
            "adjustment_variables": adjustment_variables,
            "estimated_effect": estimate_result["estimated_effect"],
            "effect_scale": (
                f"Mean difference in {outcome} for {treatment.label_a} compared with {treatment.label_b}."
            ),
            "confidence_interval": interval,
            "standard_error": estimate_result.get("standard_error"),
            "sample_size_used": int(model_df.shape[0]),
            "rows_dropped": rows_dropped,
            "assumptions": [
                "Consistency: the observed exposure version matches the treatment definition.",
                "Conditional exchangeability: no unmeasured confounding after adjustment.",
                "Positivity: both treatment conditions occur across covariate patterns.",
                "Correct model specification for the selected estimator.",
                "Temporal alignment is correct for exposure, confounders, and outcome.",
            ],
            "limitations": [
                "This prototype uses simple parametric models.",
                "Single-patient datasets can have limited variation and unstable estimates.",
                "Synthetic observational data still require causal assumptions.",
            ],
            "plain_language_interpretation": self._plain_language_interpretation(
                effect=estimate_result["estimated_effect"],
                exposure=exposure,
                outcome=outcome,
                treatment=treatment,
                adjustment_variables=adjustment_variables,
                method=method,
            ),
            "diagnostic_warnings": warnings,
        }

    def run_target_trial_emulation(
        self,
        records: list[dict[str, Any]] | pd.DataFrame,
        *,
        eligibility_criteria: dict[str, Any] | None,
        treatment_strategies: list[dict[str, Any]],
        assignment_time: str | dict[str, Any],
        follow_up_days: int,
        outcome: str,
        adjustment_variables: list[str],
        method: MethodName,
    ) -> dict[str, Any]:
        """Emulate a simple target trial from repeated daily decision points."""

        if len(treatment_strategies) != 2:
            raise ValueError("Exactly two treatment strategies are required.")
        df = records_to_dataframe(records)
        eligible_df = self._apply_eligibility(df, eligibility_criteria)
        if eligible_df.empty:
            raise ValueError("No rows met the eligibility criteria.")

        strategy_a, strategy_b = treatment_strategies
        treatment_rule = self._trial_strategies_to_rule(strategy_a, strategy_b)
        result = self.estimate_causal_effect(
            eligible_df,
            exposure=treatment_rule.get("variable", strategy_a.get("variable", "")),
            outcome=outcome,
            treatment_rule=treatment_rule,
            adjustment_variables=adjustment_variables,
            method=method,
            lag_outcome_days=max(0, follow_up_days - 1),
            bootstrap=False,
        )
        poor_time_zero = not assignment_time or assignment_time in {"", "after outcome"}
        warnings = []
        if poor_time_zero:
            warnings.append(
                "Time zero is poorly defined. Immortal time bias is possible if treatment is assigned after follow-up begins."
            )

        return {
            "trial_protocol": {
                "design": "Repeated daily N-of-1 target trial emulation",
                "assignment_time": assignment_time,
                "follow_up_days": follow_up_days,
                "outcome": outcome,
            },
            "eligibility_criteria": eligibility_criteria or {},
            "treatment_strategies": treatment_strategies,
            "time_zero_definition": assignment_time,
            "follow_up_window": f"{follow_up_days} day(s)",
            "number_eligible": int(eligible_df.shape[0]),
            "causal_estimate": result,
            "interpretation": (
                f"Among eligible person-days, {result['plain_language_interpretation']}"
            ),
            "immortal_time_bias_warning": warnings or [
                "Time zero appears explicit; residual immortal time bias depends on whether data were aligned correctly."
            ],
            "limitations": [
                "Eligibility, assignment, and follow-up are simplified daily rules.",
                "Treatment strategies must be well-defined before the outcome window starts.",
                "Repeated days from one patient are correlated; this prototype does not fit clustered models.",
            ],
        }

    def simulate_intervention(
        self,
        records: list[dict[str, Any]] | pd.DataFrame,
        *,
        intervention_name: str,
        intervention_rule: dict[str, Any],
        target_variable: str,
        expected_change: float,
        outcome: str,
        method: MethodName = "g_formula",
        adjustment_variables: list[str] | None = None,
    ) -> dict[str, Any]:
        """Simulate an intervention using an adjusted outcome model."""

        df = records_to_dataframe(records)
        adjustment_variables = adjustment_variables or self._default_adjustments(df, target_variable, outcome)
        validate_columns(df, [target_variable, outcome, *adjustment_variables], context="simulate_intervention")
        model_columns = [target_variable, outcome, *adjustment_variables]
        model_df = clean_numeric_frame(df, model_columns)
        if model_df.shape[0] < max(20, len(adjustment_variables) + 5):
            raise ValueError("Not enough complete rows to simulate the intervention.")

        y = model_df[outcome].astype(float)
        x = self._design_matrix(model_df, [target_variable, *adjustment_variables])
        model = self._fit_ols(y, x)

        baseline_predictions = model.predict(x)
        intervention_df = model_df.copy()
        intervention_df[target_variable] = self._apply_expected_change(
            intervention_df[target_variable],
            intervention_rule=intervention_rule,
            expected_change=expected_change,
        )
        x_intervention = self._design_matrix(intervention_df, [target_variable, *adjustment_variables])
        intervention_predictions = model.predict(x_intervention)
        difference = float(intervention_predictions.mean() - baseline_predictions.mean())

        return {
            "intervention_name": intervention_name,
            "target_variable": target_variable,
            "outcome": outcome,
            "method": method,
            "baseline_predicted_outcome": float(baseline_predictions.mean()),
            "intervention_predicted_outcome": float(intervention_predictions.mean()),
            "estimated_difference": difference,
            "uncertainty": "Not computed for this simple intervention simulation.",
            "assumptions": [
                "The adjusted outcome model captures the relationship between the target and outcome.",
                "The intervention changes only the target variable unless specified in future extensions.",
                "No new confounding is introduced by the intervention.",
            ],
            "plain_language_summary": (
                f"Under '{intervention_name}', the model predicts {outcome} would change by "
                f"{difference:.3f} units on average compared with the observed baseline pattern."
            ),
            "caution": "These are simulated estimates for research prototyping and are not medical advice.",
        }

    def export_dataset(
        self,
        records: list[dict[str, Any]] | pd.DataFrame,
        *,
        format: Literal["csv", "json"],
    ) -> dict[str, Any]:
        """Serialize a dataset to CSV or JSON-compatible records."""

        df = records_to_dataframe(records)
        if format == "csv":
            serialized: str | list[dict[str, Any]] = df.to_csv(index=False)
            extension = "csv"
        elif format == "json":
            serialized = dataframe_to_records(df)
            extension = "json"
        else:
            raise ValueError("format must be 'csv' or 'json'.")
        patient = str(df["patient_id"].iloc[0]) if "patient_id" in df.columns and not df.empty else "patient"
        return {
            "serialized_dataset": serialized,
            "filename_suggestion": f"{patient}_synthetic_patient_data.{extension}",
            "variable_dictionary": {
                column: VARIABLE_DESCRIPTIONS.get(column, "No description available.")
                for column in df.columns
            },
        }

    def _prepare_lagged_data(
        self,
        *,
        records: list[dict[str, Any]] | pd.DataFrame,
        exposure: str,
        outcome: str,
        adjustment_variables: list[str],
        lag_exposure_days: int,
        lag_outcome_days: int,
    ) -> pd.DataFrame:
        """Apply optional exposure and outcome lagging."""

        if lag_exposure_days < 0 or lag_outcome_days < 0:
            raise ValueError("lag_exposure_days and lag_outcome_days must be non-negative.")
        df = records_to_dataframe(records)
        validate_columns(df, [exposure, outcome, *adjustment_variables], context="estimate_causal_effect")
        analysis_df = df.copy()
        analysis_df["_analysis_exposure"] = analysis_df[exposure].shift(lag_exposure_days)
        analysis_df["_analysis_outcome"] = analysis_df[outcome].shift(-lag_outcome_days)
        return analysis_df

    def _build_treatment(
        self,
        df: pd.DataFrame,
        *,
        exposure: str,
        treatment_rule: dict[str, Any],
        contrast: dict[str, Any] | None,
    ) -> TreatmentDefinition:
        """Create a binary treatment column from a supported rule."""

        rule_type = treatment_rule.get("type")
        variable = treatment_rule.get("variable", exposure)
        if variable != exposure and variable not in df.columns:
            raise ValueError(f"Treatment variable '{variable}' is not in the dataset.")
        if rule_type == "binary_threshold":
            threshold = treatment_rule.get("threshold")
            condition = treatment_rule.get("treated_condition", "<=")
            if threshold is None:
                raise ValueError("binary_threshold treatment_rule requires 'threshold'.")
            source = pd.to_numeric(df["_analysis_exposure"], errors="coerce")
            if condition == "<=":
                treatment = (source <= float(threshold)).astype(float)
                label_a = f"{exposure} <= {threshold}"
                label_b = f"{exposure} > {threshold}"
            elif condition == "<":
                treatment = (source < float(threshold)).astype(float)
                label_a = f"{exposure} < {threshold}"
                label_b = f"{exposure} >= {threshold}"
            elif condition == ">=":
                treatment = (source >= float(threshold)).astype(float)
                label_a = f"{exposure} >= {threshold}"
                label_b = f"{exposure} < {threshold}"
            elif condition == ">":
                treatment = (source > float(threshold)).astype(float)
                label_a = f"{exposure} > {threshold}"
                label_b = f"{exposure} <= {threshold}"
            else:
                raise ValueError("treated_condition must be one of '<=', '<', '>=', '>'.")
            transformed = df.copy()
            transformed["_treatment"] = treatment
            return TreatmentDefinition("_treatment", label_a, label_b, 1.0, 0.0, transformed)

        if rule_type == "binary_variable":
            source = pd.to_numeric(df["_analysis_exposure"], errors="coerce")
            non_missing = source.dropna()
            if not set(non_missing.unique()).issubset({0, 1, 0.0, 1.0}):
                raise ValueError("binary_variable treatment_rule requires a 0/1 exposure variable.")
            transformed = df.copy()
            transformed["_treatment"] = source.astype(float)
            return TreatmentDefinition(
                "_treatment",
                f"{exposure}=1",
                f"{exposure}=0",
                1.0,
                0.0,
                transformed,
            )

        if rule_type == "set_value":
            value_a = treatment_rule.get("value_a")
            value_b = treatment_rule.get("value_b")
            if value_a is None or value_b is None:
                raise ValueError("set_value treatment_rule requires 'value_a' and 'value_b'.")
            transformed = df.copy()
            transformed["_continuous_exposure"] = pd.to_numeric(df["_analysis_exposure"], errors="coerce")
            transformed["_treatment"] = transformed["_continuous_exposure"]
            return TreatmentDefinition(
                "_treatment",
                f"{exposure} set to {value_a}",
                f"{exposure} set to {value_b}",
                float(value_a),
                float(value_b),
                transformed,
            )

        if contrast:
            raise ValueError("contrast is reserved for future extensions; provide a treatment_rule.")
        raise ValueError(
            "Unsupported treatment_rule type. Use 'binary_threshold', 'binary_variable', or 'set_value'."
        )

    def _estimate_once(
        self,
        df: pd.DataFrame,
        *,
        treatment: TreatmentDefinition,
        adjustment_variables: list[str],
        method: MethodName,
    ) -> dict[str, Any]:
        """Estimate one causal contrast without bootstrapping."""

        if method == "regression_adjustment":
            return self._regression_adjustment(df, treatment, adjustment_variables)
        if method == "ipw":
            return self._ipw(df, treatment, adjustment_variables)
        if method == "g_formula":
            return self._g_formula(df, treatment, adjustment_variables)
        if method == "doubly_robust":
            return self._doubly_robust(df, treatment, adjustment_variables)
        raise ValueError(f"Unsupported method: {method}")

    def _regression_adjustment(
        self,
        df: pd.DataFrame,
        treatment: TreatmentDefinition,
        adjustment_variables: list[str],
    ) -> dict[str, Any]:
        """Fit outcome on treatment and adjustment variables."""

        y = df["_analysis_outcome"].astype(float)
        x = self._design_matrix(df, [treatment.treatment_column, *adjustment_variables])
        model = self._fit_ols(y, x)
        if treatment.label_a.startswith(treatment.treatment_column):
            pass
        if treatment.value_a in {0.0, 1.0} and treatment.value_b in {0.0, 1.0}:
            coefficient = float(model.params[treatment.treatment_column])
            standard_error = float(model.bse[treatment.treatment_column])
        else:
            coefficient = float(model.params[treatment.treatment_column]) * (
                treatment.value_a - treatment.value_b
            )
            standard_error = float(model.bse[treatment.treatment_column]) * abs(
                treatment.value_a - treatment.value_b
            )
        return {
            "estimated_effect": coefficient,
            "standard_error": standard_error,
            "diagnostic_warnings": self._model_warnings(model),
        }

    def _ipw(
        self,
        df: pd.DataFrame,
        treatment: TreatmentDefinition,
        adjustment_variables: list[str],
    ) -> dict[str, Any]:
        """Estimate a binary treatment effect using inverse probability weighting."""

        self._require_binary_treatment(df[treatment.treatment_column], "IPW")
        a = df[treatment.treatment_column].astype(int)
        y = df["_analysis_outcome"].astype(float)
        ps = self._propensity_scores(df, treatment, adjustment_variables)
        marginal = float(a.mean())
        weights = np.where(a == 1, marginal / ps, (1 - marginal) / (1 - ps))
        weights = np.clip(weights, 0.05, 20.0)
        x = self._design_matrix(df, [treatment.treatment_column])
        model = self._fit_ols(y, x, weights=weights)
        return {
            "estimated_effect": float(model.params[treatment.treatment_column]),
            "standard_error": float(model.bse[treatment.treatment_column]),
            "diagnostic_warnings": [
                f"IPW weights were clipped to [0.05, 20.0]. Max final weight: {float(np.max(weights)):.3f}."
            ]
            + self._model_warnings(model),
        }

    def _g_formula(
        self,
        df: pd.DataFrame,
        treatment: TreatmentDefinition,
        adjustment_variables: list[str],
    ) -> dict[str, Any]:
        """Fit outcome model and average predicted potential outcomes."""

        y = df["_analysis_outcome"].astype(float)
        x_columns = [treatment.treatment_column, *adjustment_variables]
        x = self._design_matrix(df, x_columns)
        model = self._fit_ols(y, x)

        treated_df = df.copy()
        untreated_df = df.copy()
        treated_df[treatment.treatment_column] = treatment.value_a
        untreated_df[treatment.treatment_column] = treatment.value_b
        x_a = self._design_matrix(treated_df, x_columns)
        x_b = self._design_matrix(untreated_df, x_columns)
        potential_outcome_a = float(model.predict(x_a).mean())
        potential_outcome_b = float(model.predict(x_b).mean())
        return {
            "estimated_effect": potential_outcome_a - potential_outcome_b,
            "standard_error": float(model.bse.get(treatment.treatment_column, np.nan)),
            "potential_outcome_a": potential_outcome_a,
            "potential_outcome_b": potential_outcome_b,
            "diagnostic_warnings": self._model_warnings(model),
        }

    def _doubly_robust(
        self,
        df: pd.DataFrame,
        treatment: TreatmentDefinition,
        adjustment_variables: list[str],
    ) -> dict[str, Any]:
        """Simple AIPW estimator for binary treatments."""

        self._require_binary_treatment(df[treatment.treatment_column], "doubly_robust")
        a = df[treatment.treatment_column].astype(int).to_numpy()
        y = df["_analysis_outcome"].astype(float).to_numpy()
        ps = self._propensity_scores(df, treatment, adjustment_variables)
        ps = np.clip(ps, 0.03, 0.97)

        x_columns = [treatment.treatment_column, *adjustment_variables]
        x = self._design_matrix(df, x_columns)
        outcome_model = self._fit_ols(df["_analysis_outcome"].astype(float), x)
        mu1_df = df.copy()
        mu0_df = df.copy()
        mu1_df[treatment.treatment_column] = 1.0
        mu0_df[treatment.treatment_column] = 0.0
        mu1 = outcome_model.predict(self._design_matrix(mu1_df, x_columns))
        mu0 = outcome_model.predict(self._design_matrix(mu0_df, x_columns))

        aipw_1 = mu1 + (a / ps) * (y - mu1)
        aipw_0 = mu0 + ((1 - a) / (1 - ps)) * (y - mu0)
        influence = aipw_1 - aipw_0
        estimate = float(np.mean(influence))
        standard_error = float(np.std(influence, ddof=1) / np.sqrt(len(influence)))
        return {
            "estimated_effect": estimate,
            "standard_error": standard_error,
            "diagnostic_warnings": [
                "Doubly robust estimate uses a simple AIPW implementation for binary treatments."
            ]
            + self._model_warnings(outcome_model),
        }

    def _bootstrap_ci(
        self,
        df: pd.DataFrame,
        *,
        treatment: TreatmentDefinition,
        adjustment_variables: list[str],
        method: MethodName,
        n_bootstrap: int,
    ) -> dict[str, float | int]:
        """Compute a percentile bootstrap interval."""

        if n_bootstrap <= 0:
            raise ValueError("n_bootstrap must be positive when bootstrap=True.")
        rng = np.random.default_rng(20240616)
        estimates: list[float] = []
        for _ in range(n_bootstrap):
            indices = rng.integers(0, df.shape[0], size=df.shape[0])
            sample = df.iloc[indices].reset_index(drop=True)
            try:
                estimate = self._estimate_once(
                    sample,
                    treatment=treatment,
                    adjustment_variables=adjustment_variables,
                    method=method,
                )["estimated_effect"]
            except Exception:
                continue
            if np.isfinite(estimate):
                estimates.append(float(estimate))
        if len(estimates) < max(20, n_bootstrap // 5):
            return {
                "lower": float("nan"),
                "upper": float("nan"),
                "n_successful_bootstraps": len(estimates),
            }
        lower, upper = np.percentile(estimates, [2.5, 97.5])
        return {
            "lower": float(lower),
            "upper": float(upper),
            "n_successful_bootstraps": len(estimates),
        }

    def _propensity_scores(
        self,
        df: pd.DataFrame,
        treatment: TreatmentDefinition,
        adjustment_variables: list[str],
    ) -> np.ndarray:
        """Fit logistic propensity scores with mild regularization."""

        self._require_binary_treatment(df[treatment.treatment_column], "propensity scoring")
        if not adjustment_variables:
            a = df[treatment.treatment_column].astype(int)
            return np.full(df.shape[0], np.clip(a.mean(), 0.03, 0.97))

        x = df[adjustment_variables].astype(float)
        a = df[treatment.treatment_column].astype(int)
        if a.nunique() != 2:
            raise ValueError("Treatment must have both treated and untreated observations.")
        return self._fit_logistic_propensity(x, a)

    def _design_matrix(self, df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """Build a numeric design matrix with an intercept column."""

        matrix = df.loc[:, columns].astype(float).copy()
        matrix.insert(0, "const", 1.0)
        return matrix

    def _fit_ols(
        self,
        y: pd.Series | np.ndarray,
        x: pd.DataFrame,
        weights: np.ndarray | None = None,
    ) -> LinearModelResult:
        """Fit ordinary or weighted least squares using NumPy."""

        y_array = np.asarray(y, dtype=float)
        x_array = x.to_numpy(dtype=float)
        if weights is not None:
            weight_array = np.asarray(weights, dtype=float)
            if weight_array.shape[0] != y_array.shape[0]:
                raise ValueError("weights must have the same number of rows as y.")
            sqrt_weights = np.sqrt(np.clip(weight_array, 1e-12, np.inf))
            x_fit = x_array * sqrt_weights[:, None]
            y_fit = y_array * sqrt_weights
        else:
            x_fit = x_array
            y_fit = y_array

        beta, *_ = np.linalg.lstsq(x_fit, y_fit, rcond=None)
        fitted = x_array @ beta
        residuals = y_array - fitted
        n_rows, n_columns = x_array.shape
        degrees_freedom = max(n_rows - n_columns, 1)
        if weights is not None:
            rss = float(np.sum(np.asarray(weights, dtype=float) * residuals**2))
            xtx = x_fit.T @ x_fit
        else:
            rss = float(np.sum(residuals**2))
            xtx = x_array.T @ x_array
        sigma_squared = rss / degrees_freedom
        covariance = sigma_squared * np.linalg.pinv(xtx)
        standard_errors = np.sqrt(np.clip(np.diag(covariance), 0, np.inf))
        condition_number = float(np.linalg.cond(x_array))
        return LinearModelResult(
            params=pd.Series(beta, index=x.columns),
            bse=pd.Series(standard_errors, index=x.columns),
            fitted_values=fitted,
            residuals=residuals,
            condition_number=condition_number,
        )

    def _fit_logistic_propensity(self, x: pd.DataFrame, a: pd.Series) -> np.ndarray:
        """Fit a regularized logistic model with Newton updates."""

        x_numeric = x.astype(float)
        means = x_numeric.mean(axis=0)
        stds = x_numeric.std(axis=0, ddof=0).replace(0, 1.0)
        x_standardized = (x_numeric - means) / stds
        design = np.column_stack([np.ones(x_standardized.shape[0]), x_standardized.to_numpy()])
        target = a.to_numpy(dtype=float)
        beta = np.zeros(design.shape[1], dtype=float)
        ridge = np.eye(design.shape[1]) * 0.25
        ridge[0, 0] = 0.0

        for _ in range(100):
            linear = design @ beta
            probabilities = self._sigmoid_array(linear)
            weights = np.clip(probabilities * (1.0 - probabilities), 1e-5, np.inf)
            gradient = design.T @ (target - probabilities) - ridge @ beta
            hessian = design.T @ (design * weights[:, None]) + ridge
            try:
                step = np.linalg.solve(hessian, gradient)
            except np.linalg.LinAlgError:
                step = np.linalg.pinv(hessian) @ gradient
            beta += step
            if np.max(np.abs(step)) < 1e-6:
                break

        return np.clip(self._sigmoid_array(design @ beta), 0.03, 0.97)

    def _sigmoid_array(self, values: np.ndarray) -> np.ndarray:
        """Stable logistic transform for arrays."""

        clipped = np.clip(values, -35, 35)
        return 1.0 / (1.0 + np.exp(-clipped))

    def _require_binary_treatment(self, treatment: pd.Series, method_name: str) -> None:
        """Validate that a treatment is binary."""

        values = set(pd.Series(treatment).dropna().unique())
        if not values.issubset({0, 1, 0.0, 1.0}) or len(values) < 2:
            raise ValueError(f"{method_name} requires a binary treatment with both 0 and 1 values.")

    def _model_warnings(self, model: Any) -> list[str]:
        """Return diagnostics from a fitted linear model."""

        warnings: list[str] = []
        if hasattr(model, "condition_number") and model.condition_number > 1000:
            warnings.append(
                f"High design matrix condition number ({model.condition_number:.1f}); estimates may be unstable."
            )
        return warnings

    def _variation_warnings(
        self,
        treatment_series: pd.Series,
        treatment: TreatmentDefinition,
    ) -> list[str]:
        """Warn if treatment groups are small or continuous range is narrow."""

        warnings: list[str] = []
        if infer_binary(treatment_series):
            counts = treatment_series.value_counts()
            if counts.min() < 10:
                warnings.append("One treatment group has fewer than 10 observations.")
        else:
            if treatment_series.max() - treatment_series.min() <= 1e-6:
                warnings.append("The exposure has no usable variation.")
        return warnings

    def _correlation_highlights(self, df: pd.DataFrame, numeric_columns: list[str]) -> list[dict[str, Any]]:
        """Return strongest absolute correlations."""

        usable_columns = [
            column
            for column in numeric_columns
            if pd.to_numeric(df[column], errors="coerce").dropna().nunique() > 1
        ]
        if len(usable_columns) < 2:
            return []
        numeric = df[usable_columns].apply(pd.to_numeric, errors="coerce")
        corr = numeric.corr(numeric_only=True)
        highlights: list[dict[str, Any]] = []
        for i, left in enumerate(corr.columns):
            for right in corr.columns[i + 1 :]:
                value = corr.loc[left, right]
                if pd.notna(value) and abs(value) >= 0.35:
                    highlights.append(
                        {
                            "variable_a": left,
                            "variable_b": right,
                            "correlation": float(value),
                        }
                    )
        highlights.sort(key=lambda item: abs(item["correlation"]), reverse=True)
        return highlights[:8]

    def _time_trend_highlights(self, df: pd.DataFrame, numeric_columns: list[str]) -> list[dict[str, Any]]:
        """Return variables with notable linear time trends."""

        if "day_index" not in df.columns:
            return []
        trends: list[dict[str, Any]] = []
        day = pd.to_numeric(df["day_index"], errors="coerce")
        for column in numeric_columns:
            if column == "day_index":
                continue
            series = pd.to_numeric(df[column], errors="coerce")
            valid = pd.concat([day, series], axis=1).dropna()
            if valid.shape[0] < 10 or valid.iloc[:, 1].nunique() <= 1:
                continue
            correlation = valid.iloc[:, 0].corr(valid.iloc[:, 1])
            if pd.notna(correlation) and abs(correlation) >= 0.25:
                trends.append({"variable": column, "correlation_with_day_index": float(correlation)})
        trends.sort(key=lambda item: abs(item["correlation_with_day_index"]), reverse=True)
        return trends[:8]

    def _plain_language_interpretation(
        self,
        *,
        effect: float,
        exposure: str,
        outcome: str,
        treatment: TreatmentDefinition,
        adjustment_variables: list[str],
        method: MethodName,
    ) -> str:
        """Build a plain-language explanation for an estimate."""

        direction = "higher" if effect > 0 else "lower"
        adjustment = ", ".join(adjustment_variables) if adjustment_variables else "no covariates"
        return (
            f"On this simulated patient dataset, {treatment.label_a} was estimated to produce "
            f"{abs(effect):.3f} units {direction} {outcome} than {treatment.label_b}, using "
            f"{method} and adjusting for {adjustment}. The estimate depends on the causal assumptions "
            "and the simulated data-generating process."
        )

    def _apply_eligibility(
        self,
        df: pd.DataFrame,
        eligibility_criteria: dict[str, Any] | None,
    ) -> pd.DataFrame:
        """Apply simple eligibility filters."""

        if not eligibility_criteria:
            return df.copy()
        eligible = pd.Series(True, index=df.index)
        for variable, rule in eligibility_criteria.items():
            if variable not in df.columns:
                raise ValueError(f"Eligibility variable '{variable}' is not in the dataset.")
            if not isinstance(rule, dict):
                raise ValueError("Eligibility criteria values must be rule objects.")
            series = pd.to_numeric(df[variable], errors="coerce")
            if "min" in rule:
                eligible &= series >= float(rule["min"])
            if "max" in rule:
                eligible &= series <= float(rule["max"])
            if "equals" in rule:
                eligible &= df[variable] == rule["equals"]
        return df.loc[eligible].copy()

    def _trial_strategies_to_rule(
        self,
        strategy_a: dict[str, Any],
        strategy_b: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert two target-trial strategies into a supported treatment rule."""

        variable = strategy_a.get("variable") or strategy_b.get("variable")
        if not variable:
            raise ValueError("Each treatment strategy must identify a variable.")
        if strategy_a.get("type") == "binary_variable" or strategy_b.get("type") == "binary_variable":
            return {"type": "binary_variable", "variable": variable}
        if "value" in strategy_a and "value" in strategy_b:
            value_a = strategy_a["value"]
            value_b = strategy_b["value"]
            if {value_a, value_b}.issubset({0, 1, 0.0, 1.0}):
                return {"type": "binary_variable", "variable": variable}
            return {"type": "set_value", "variable": variable, "value_a": value_a, "value_b": value_b}
        raise ValueError(
            "Treatment strategies must use binary_variable or provide comparable 'value' entries."
        )

    def _default_adjustments(self, df: pd.DataFrame, target_variable: str, outcome: str) -> list[str]:
        """Choose conservative default adjustments from common variables."""

        candidates = [
            "stress_score",
            "prior_sleep_quality",
            "prior_fatigue",
            "caffeine_mg",
            "steps",
            "day_of_week",
            "prior_bp",
        ]
        return [column for column in candidates if column in df.columns and column not in {target_variable, outcome}]

    def _apply_expected_change(
        self,
        series: pd.Series,
        *,
        intervention_rule: dict[str, Any],
        expected_change: float,
    ) -> pd.Series:
        """Apply a simple intervention change to a target variable."""

        operation = intervention_rule.get("operation", "add")
        numeric = pd.to_numeric(series, errors="coerce")
        if operation == "add":
            changed = numeric + expected_change
        elif operation == "multiply":
            changed = numeric * expected_change
        elif operation == "set_minimum":
            changed = np.maximum(numeric, expected_change)
        elif operation == "set_maximum":
            changed = np.minimum(numeric, expected_change)
        elif operation == "set_value":
            changed = pd.Series(expected_change, index=series.index)
        else:
            raise ValueError(
                "intervention_rule.operation must be one of add, multiply, set_minimum, set_maximum, set_value."
            )
        return pd.Series(changed, index=series.index)
