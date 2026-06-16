"""Longitudinal synthetic N-of-1 patient data simulator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

from patient_causal_mcp.scenarios import VARIABLE_DESCRIPTIONS, ScenarioDefinition, get_scenario
from patient_causal_mcp.utils import clip, dataframe_to_records, logistic


SUPPORTED_DAY_COUNTS = {90, 180, 365}


@dataclass(frozen=True)
class PatientTraits:
    """Latent patient-specific tendencies used by the simulator."""

    baseline_sleep_need: float
    baseline_activity_level: float
    baseline_stress_tendency: float
    baseline_bp: float
    baseline_phone_use: float
    baseline_adherence: float
    baseline_pain: float


class PatientSimulator:
    """Generate realistic synthetic daily health, behavior, and sensor data."""

    def simulate(
        self,
        *,
        patient_id: str | None = None,
        n_days: int = 180,
        start_date: str | None = None,
        seed: int | None = None,
        scenario: str | None = None,
    ) -> dict[str, Any]:
        """Simulate one longitudinal patient dataset."""

        scenario_def = get_scenario(scenario)
        if n_days <= 0:
            raise ValueError("n_days must be positive.")
        if n_days not in SUPPORTED_DAY_COUNTS:
            warning = (
                f"n_days={n_days} is supported, but standard examples use 90, 180, or 365 days."
            )
        else:
            warning = ""

        rng = np.random.default_rng(seed)
        synthetic_patient_id = patient_id or f"patient-{uuid4().hex[:8]}"
        start = pd.to_datetime(start_date or date.today().isoformat()).normalize()
        traits = self._sample_traits(rng)
        df = self._simulate_daily_records(
            patient_id=synthetic_patient_id,
            n_days=n_days,
            start=start,
            rng=rng,
            traits=traits,
            scenario=scenario_def,
        )

        dataset_id = f"{synthetic_patient_id}-{scenario_def.name}-{uuid4().hex[:8]}"
        warnings = [warning] if warning else []
        return {
            "dataset_id": dataset_id,
            "patient_id": synthetic_patient_id,
            "scenario": scenario_def.name,
            "n_days": int(n_days),
            "variable_descriptions": VARIABLE_DESCRIPTIONS,
            "causal_graph_edges": [
                {"source": source, "target": target} for source, target in scenario_def.dag_edges
            ],
            "data_preview": dataframe_to_records(df.head(10)),
            "full_data": dataframe_to_records(df),
            "warnings": warnings,
        }

    def _sample_traits(self, rng: np.random.Generator) -> PatientTraits:
        """Sample stable patient-level characteristics."""

        return PatientTraits(
            baseline_sleep_need=clip(rng.normal(7.4, 0.55), 6.2, 8.8),
            baseline_activity_level=clip(rng.normal(7600, 2100), 2500, 14000),
            baseline_stress_tendency=clip(rng.normal(4.6, 1.1), 1.5, 8.5),
            baseline_bp=clip(rng.normal(126, 12), 102, 158),
            baseline_phone_use=clip(rng.normal(145, 50), 45, 320),
            baseline_adherence=clip(rng.beta(8, 3), 0.45, 0.98),
            baseline_pain=clip(rng.normal(2.6, 1.2), 0.0, 7.0),
        )

    def _simulate_daily_records(
        self,
        *,
        patient_id: str,
        n_days: int,
        start: pd.Timestamp,
        rng: np.random.Generator,
        traits: PatientTraits,
        scenario: ScenarioDefinition,
    ) -> pd.DataFrame:
        """Simulate autoregressive daily records and aligned outcomes."""

        records: list[dict[str, Any]] = []
        prev_stress = traits.baseline_stress_tendency
        prev_sleep_quality = clip(rng.normal(6.4, 1.0), 0, 10)
        prev_fatigue = clip(rng.normal(4.0, 1.3), 0, 10)
        prev_bp = traits.baseline_bp
        prev_mood = clip(rng.normal(6.5, 1.2), 0, 10)
        prev_pain = traits.baseline_pain

        for day_index in range(n_days):
            current_date = start + pd.Timedelta(days=day_index)
            day_of_week = int(current_date.dayofweek)
            is_weekend = int(day_of_week >= 5)

            seasonal = 0.35 * np.sin(2 * np.pi * day_index / 28)
            weekend_stress_relief = -0.45 if is_weekend else 0.1
            stress_score = clip(
                0.58 * prev_stress
                + 0.30 * traits.baseline_stress_tendency
                + weekend_stress_relief
                + 0.08 * prev_fatigue
                + seasonal
                + rng.normal(0, 0.9),
                0,
                10,
            )

            pain_score = clip(
                0.60 * prev_pain
                + 0.16 * stress_score
                + 0.03 * prev_fatigue
                + rng.normal(0, 0.7),
                0,
                10,
            )

            intervention_probability = self._intervention_probability(
                scenario.name,
                stress_score,
                prev_sleep_quality,
                prev_fatigue,
                day_of_week,
                traits,
            )
            intervention_received = int(rng.binomial(1, intervention_probability))

            caffeine_mg = self._simulate_caffeine(
                rng=rng,
                scenario_name=scenario.name,
                stress_score=stress_score,
                prev_fatigue=prev_fatigue,
                is_weekend=is_weekend,
            )
            alcohol_units = self._simulate_alcohol(rng, stress_score, is_weekend)
            medication_adherence = self._simulate_medication_adherence(
                rng,
                traits,
                stress_score,
                prev_bp,
                scenario.name,
            )

            steps = self._simulate_steps(
                rng=rng,
                traits=traits,
                stress_score=stress_score,
                prev_fatigue=prev_fatigue,
                prev_sleep_quality=prev_sleep_quality,
                pain_score=pain_score,
                is_weekend=is_weekend,
                scenario_name=scenario.name,
            )
            active_minutes = int(clip(steps / 105 + rng.normal(0, 12), 5, 240))
            sedentary_minutes = int(
                clip(
                    760
                    - 0.018 * steps
                    + 11 * stress_score
                    + 9 * prev_fatigue
                    + rng.normal(0, 45),
                    240,
                    1100,
                )
            )

            late_night_screen_minutes = self._simulate_late_screen_time(
                rng=rng,
                traits=traits,
                stress_score=stress_score,
                prev_sleep_quality=prev_sleep_quality,
                prev_fatigue=prev_fatigue,
                intervention_received=intervention_received,
                scenario_name=scenario.name,
            )

            app_usage_minutes = int(
                clip(
                    35
                    + traits.baseline_phone_use
                    + 1.15 * late_night_screen_minutes
                    + 12 * stress_score
                    - 24 * intervention_received
                    + rng.normal(0, 35),
                    5,
                    720,
                )
            )
            phone_pickups = int(
                clip(
                    rng.poisson(
                        max(
                            1,
                            20
                            + 0.13 * app_usage_minutes
                            + 2.3 * stress_score
                            - 4.0 * intervention_received,
                        )
                    ),
                    0,
                    220,
                )
            )

            nighttime_eating = self._simulate_nighttime_eating(
                rng=rng,
                stress_score=stress_score,
                late_night_screen_minutes=late_night_screen_minutes,
                prev_fatigue=prev_fatigue,
                intervention_received=intervention_received,
                scenario_name=scenario.name,
            )
            pantry_door_opens = int(
                clip(
                    rng.poisson(
                        max(
                            0.1,
                            1.2
                            + 2.1 * nighttime_eating
                            + 0.18 * stress_score
                            + 0.006 * late_night_screen_minutes,
                        )
                    ),
                    0,
                    25,
                )
            )
            refrigerator_door_opens = int(
                clip(
                    rng.poisson(
                        max(
                            0.1,
                            2.0
                            + 1.7 * nighttime_eating
                            + 0.13 * stress_score
                            + 0.004 * late_night_screen_minutes,
                        )
                    ),
                    0,
                    30,
                )
            )

            sleep_duration_hours = self._simulate_sleep_duration(
                rng=rng,
                traits=traits,
                stress_score=stress_score,
                caffeine_mg=caffeine_mg,
                late_night_screen_minutes=late_night_screen_minutes,
                alcohol_units=alcohol_units,
                nighttime_eating=nighttime_eating,
                steps=steps,
                scenario_name=scenario.name,
            )
            awakenings = int(
                clip(
                    rng.poisson(
                        max(
                            0.2,
                            1.0
                            + 0.23 * stress_score
                            + 0.10 * alcohol_units
                            + 0.35 * nighttime_eating
                            + 0.003 * late_night_screen_minutes,
                        )
                    ),
                    0,
                    12,
                )
            )
            sleep_efficiency = clip(
                91
                - 1.2 * stress_score
                - 0.012 * caffeine_mg
                - 0.021 * late_night_screen_minutes
                - 1.1 * alcohol_units
                - 1.6 * nighttime_eating
                - 1.2 * awakenings
                + 0.00008 * steps
                + rng.normal(0, 3.0),
                60,
                98,
            )
            sleep_quality = clip(
                0.58 * sleep_duration_hours
                + 0.065 * sleep_efficiency
                - 0.38 * awakenings
                - 0.23 * stress_score
                - 0.0048 * late_night_screen_minutes
                - 0.0025 * caffeine_mg
                + 0.00008 * steps
                - 0.22 * nighttime_eating
                + rng.normal(0, 0.55),
                0,
                10,
            )

            morning_fatigue = clip(
                0.47 * prev_fatigue
                + 6.8
                - 0.57 * sleep_quality
                + 0.26 * stress_score
                + 0.28 * nighttime_eating
                + 0.0033 * late_night_screen_minutes
                + 0.10 * pain_score
                + rng.normal(0, 0.7),
                0,
                10,
            )
            mood_score = clip(
                0.42 * prev_mood
                + 4.4
                + 0.29 * sleep_quality
                - 0.26 * stress_score
                - 0.15 * morning_fatigue
                - 0.11 * pain_score
                + rng.normal(0, 0.65),
                0,
                10,
            )
            blood_pressure_systolic = clip(
                0.32 * prev_bp
                + 0.68 * traits.baseline_bp
                + 1.25 * stress_score
                + 0.010 * caffeine_mg
                - 5.8 * medication_adherence
                - 0.00015 * steps
                + 0.7 * alcohol_units
                + rng.normal(0, 4.5),
                95,
                170,
            )
            blood_pressure_diastolic = clip(
                0.63 * blood_pressure_systolic - 3.0 + rng.normal(0, 4.5),
                55,
                105,
            )
            resting_heart_rate = clip(
                63
                + 1.2 * stress_score
                + 0.9 * morning_fatigue
                - 0.00028 * steps
                + 0.8 * alcohol_units
                + rng.normal(0, 3.5),
                48,
                105,
            )

            records.append(
                {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "day_index": day_index,
                    "day_of_week": day_of_week,
                    "is_weekend": is_weekend,
                    "patient_id": patient_id,
                    "baseline_sleep_need": round(traits.baseline_sleep_need, 3),
                    "baseline_activity_level": round(traits.baseline_activity_level, 3),
                    "baseline_stress_tendency": round(traits.baseline_stress_tendency, 3),
                    "baseline_bp": round(traits.baseline_bp, 3),
                    "baseline_phone_use": round(traits.baseline_phone_use, 3),
                    "baseline_adherence": round(traits.baseline_adherence, 3),
                    "sleep_duration_hours": round(sleep_duration_hours, 3),
                    "sleep_efficiency": round(sleep_efficiency, 3),
                    "awakenings": awakenings,
                    "steps": int(round(steps)),
                    "sedentary_minutes": sedentary_minutes,
                    "active_minutes": active_minutes,
                    "late_night_screen_minutes": round(late_night_screen_minutes, 3),
                    "caffeine_mg": round(caffeine_mg, 3),
                    "alcohol_units": round(alcohol_units, 3),
                    "medication_adherence": medication_adherence,
                    "stress_score": round(stress_score, 3),
                    "mood_score": round(mood_score, 3),
                    "pain_score": round(pain_score, 3),
                    "blood_pressure_systolic": round(blood_pressure_systolic, 3),
                    "blood_pressure_diastolic": round(blood_pressure_diastolic, 3),
                    "resting_heart_rate": round(resting_heart_rate, 3),
                    "morning_fatigue": round(morning_fatigue, 3),
                    "nighttime_eating": nighttime_eating,
                    "pantry_door_opens": pantry_door_opens,
                    "refrigerator_door_opens": refrigerator_door_opens,
                    "phone_pickups": phone_pickups,
                    "app_usage_minutes": app_usage_minutes,
                    "intervention_received": intervention_received,
                    "sleep_quality": round(sleep_quality, 3),
                    "prior_sleep_quality": round(prev_sleep_quality, 3),
                    "prior_fatigue": round(prev_fatigue, 3),
                    "prior_bp": round(prev_bp, 3),
                }
            )

            prev_stress = stress_score
            prev_sleep_quality = sleep_quality
            prev_fatigue = morning_fatigue
            prev_bp = blood_pressure_systolic
            prev_mood = mood_score
            prev_pain = pain_score

        df = pd.DataFrame.from_records(records)
        df["outcome_sleep_quality"] = df["sleep_quality"]
        df["outcome_next_day_fatigue"] = df["morning_fatigue"].shift(-1)
        df["outcome_mood_next_day"] = df["mood_score"].shift(-1)
        df["outcome_bp_next_day"] = df["blood_pressure_systolic"].shift(-1)
        return df

    def _intervention_probability(
        self,
        scenario_name: str,
        stress_score: float,
        prev_sleep_quality: float,
        prev_fatigue: float,
        day_of_week: int,
        traits: PatientTraits,
    ) -> float:
        """Probability of receiving an evening reminder."""

        base = -1.2
        if scenario_name == "mixed_lifestyle":
            base = -0.35
        elif scenario_name == "sleep_screen_time":
            base = -0.75
        logit = (
            base
            + 0.20 * stress_score
            - 0.18 * prev_sleep_quality
            + 0.08 * prev_fatigue
            + 0.20 * int(day_of_week in {0, 1, 2, 3})
            + 0.003 * (traits.baseline_phone_use - 140)
        )
        return clip(logistic(logit), 0.05, 0.92)

    def _simulate_caffeine(
        self,
        *,
        rng: np.random.Generator,
        scenario_name: str,
        stress_score: float,
        prev_fatigue: float,
        is_weekend: int,
    ) -> float:
        """Simulate caffeine intake."""

        scenario_boost = 35 if scenario_name in {"sleep_screen_time", "stress_sleep"} else 0
        caffeine = (
            rng.normal(120 + scenario_boost, 65)
            + 18 * prev_fatigue
            + 7.5 * stress_score
            - 18 * is_weekend
        )
        return clip(caffeine, 0, 500)

    def _simulate_alcohol(
        self,
        rng: np.random.Generator,
        stress_score: float,
        is_weekend: int,
    ) -> float:
        """Simulate alcohol units."""

        probability = clip(logistic(-2.4 + 0.22 * stress_score + 0.8 * is_weekend), 0.02, 0.75)
        drinks = rng.binomial(1, probability) * rng.gamma(1.6, 0.75)
        return clip(drinks, 0, 8)

    def _simulate_medication_adherence(
        self,
        rng: np.random.Generator,
        traits: PatientTraits,
        stress_score: float,
        prev_bp: float,
        scenario_name: str,
    ) -> int:
        """Simulate binary medication adherence."""

        scenario_boost = 0.35 if scenario_name == "medication_bp" else 0.0
        logit = (
            -0.4
            + 3.2 * (traits.baseline_adherence - 0.65)
            - 0.20 * stress_score
            + 0.018 * (prev_bp - traits.baseline_bp)
            + scenario_boost
        )
        probability = clip(logistic(logit), 0.03, 0.98)
        return int(rng.binomial(1, probability))

    def _simulate_steps(
        self,
        *,
        rng: np.random.Generator,
        traits: PatientTraits,
        stress_score: float,
        prev_fatigue: float,
        prev_sleep_quality: float,
        pain_score: float,
        is_weekend: int,
        scenario_name: str,
    ) -> float:
        """Simulate daily step count."""

        scenario_boost = 900 if scenario_name == "steps_fatigue" else 0
        steps = (
            traits.baseline_activity_level
            + scenario_boost
            + 210 * prev_sleep_quality
            - 250 * stress_score
            - 310 * prev_fatigue
            - 260 * pain_score
            + 650 * is_weekend
            + rng.normal(0, 1700)
        )
        return clip(steps, 500, 20000)

    def _simulate_late_screen_time(
        self,
        *,
        rng: np.random.Generator,
        traits: PatientTraits,
        stress_score: float,
        prev_sleep_quality: float,
        prev_fatigue: float,
        intervention_received: int,
        scenario_name: str,
    ) -> float:
        """Simulate late-night screen minutes."""

        scenario_boost = 25 if scenario_name in {"sleep_screen_time", "mixed_lifestyle"} else 0
        screen_minutes = (
            25
            + 0.42 * traits.baseline_phone_use
            + scenario_boost
            + 10.5 * stress_score
            - 5.5 * prev_sleep_quality
            + 3.2 * prev_fatigue
            - 42 * intervention_received
            + rng.normal(0, 28)
        )
        return clip(screen_minutes, 0, 360)

    def _simulate_nighttime_eating(
        self,
        *,
        rng: np.random.Generator,
        stress_score: float,
        late_night_screen_minutes: float,
        prev_fatigue: float,
        intervention_received: int,
        scenario_name: str,
    ) -> int:
        """Simulate nighttime eating."""

        scenario_boost = 0.55 if scenario_name == "nighttime_eating_fatigue" else 0.0
        logit = (
            -2.35
            + scenario_boost
            + 0.25 * stress_score
            + 0.008 * late_night_screen_minutes
            + 0.08 * prev_fatigue
            - 0.45 * intervention_received
        )
        probability = clip(logistic(logit), 0.02, 0.85)
        return int(rng.binomial(1, probability))

    def _simulate_sleep_duration(
        self,
        *,
        rng: np.random.Generator,
        traits: PatientTraits,
        stress_score: float,
        caffeine_mg: float,
        late_night_screen_minutes: float,
        alcohol_units: float,
        nighttime_eating: int,
        steps: float,
        scenario_name: str,
    ) -> float:
        """Simulate sleep duration with scenario-specific effects."""

        screen_penalty = 0.010 if scenario_name in {"sleep_screen_time", "mixed_lifestyle"} else 0.006
        stress_penalty = 0.11 if scenario_name == "stress_sleep" else 0.075
        sleep = (
            traits.baseline_sleep_need
            - stress_penalty * stress_score
            - 0.0027 * caffeine_mg
            - screen_penalty * late_night_screen_minutes
            - 0.10 * alcohol_units
            - 0.23 * nighttime_eating
            + 0.00006 * min(steps, 12000)
            + rng.normal(0, 0.55)
        )
        return clip(sleep, 4, 10)
