"""Scenario metadata for synthetic patient causal simulations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Edge = tuple[str, str]


@dataclass(frozen=True)
class ScenarioDefinition:
    """Describes one simulation and analysis scenario."""

    name: str
    description: str
    causal_question: str
    exposure: str
    outcome: str
    confounders: list[str]
    mediators: list[str] = field(default_factory=list)
    colliders: list[str] = field(default_factory=list)
    expected_direction: str = ""
    example_interpretation: str = ""
    dag_edges: list[Edge] = field(default_factory=list)
    variables_not_to_adjust_for: list[str] = field(default_factory=list)

    @property
    def adjustment_set(self) -> list[str]:
        """Return the default practical adjustment set."""

        return list(dict.fromkeys(self.confounders))

    def to_public_dict(self) -> dict[str, Any]:
        """Return metadata suitable for MCP tool responses."""

        return {
            "scenario": self.name,
            "description": self.description,
            "causal_question": self.causal_question,
            "exposure_variable": self.exposure,
            "outcome_variable": self.outcome,
            "confounders": self.confounders,
            "mediators": self.mediators,
            "colliders": self.colliders,
            "adjustment_set": self.adjustment_set,
            "variables_not_to_adjust_for": self.variables_not_to_adjust_for,
            "expected_direction_of_effect": self.expected_direction,
            "example_interpretation": self.example_interpretation,
        }


SCENARIOS: dict[str, ScenarioDefinition] = {
    "sleep_screen_time": ScenarioDefinition(
        name="sleep_screen_time",
        description="Late-night screen use affects same-night sleep quality and next-day fatigue.",
        causal_question="What is the effect of reducing late-night screen time on next-day sleep quality?",
        exposure="late_night_screen_minutes",
        outcome="outcome_sleep_quality",
        confounders=["stress_score", "caffeine_mg", "prior_sleep_quality", "steps"],
        expected_direction="Reducing late-night screen time is expected to improve sleep quality.",
        example_interpretation=(
            "Lower late-night screen time should increase same-night sleep quality after accounting "
            "for stress, caffeine, activity, and prior sleep."
        ),
        dag_edges=[
            ("stress_score", "late_night_screen_minutes"),
            ("stress_score", "outcome_sleep_quality"),
            ("caffeine_mg", "outcome_sleep_quality"),
            ("steps", "outcome_sleep_quality"),
            ("prior_sleep_quality", "late_night_screen_minutes"),
            ("prior_sleep_quality", "outcome_sleep_quality"),
            ("late_night_screen_minutes", "outcome_sleep_quality"),
        ],
    ),
    "steps_fatigue": ScenarioDefinition(
        name="steps_fatigue",
        description="Daily activity may affect next-day fatigue, with wellness and prior fatigue confounding.",
        causal_question="What is the effect of increasing daily steps on next-day fatigue?",
        exposure="steps",
        outcome="outcome_next_day_fatigue",
        confounders=["prior_fatigue", "stress_score", "sleep_quality", "day_of_week"],
        expected_direction="Higher daily steps are expected to reduce next-day fatigue at moderate levels.",
        example_interpretation=(
            "More steps may reduce next-day fatigue, but estimates need adjustment because better days "
            "can cause both higher activity and lower fatigue."
        ),
        dag_edges=[
            ("prior_fatigue", "steps"),
            ("prior_fatigue", "outcome_next_day_fatigue"),
            ("stress_score", "steps"),
            ("stress_score", "outcome_next_day_fatigue"),
            ("sleep_quality", "steps"),
            ("sleep_quality", "outcome_next_day_fatigue"),
            ("day_of_week", "steps"),
            ("steps", "outcome_next_day_fatigue"),
        ],
    ),
    "medication_bp": ScenarioDefinition(
        name="medication_bp",
        description="Medication adherence affects next-day systolic blood pressure.",
        causal_question="What is the effect of medication adherence on next-day blood pressure?",
        exposure="medication_adherence",
        outcome="outcome_bp_next_day",
        confounders=["baseline_bp", "stress_score", "caffeine_mg", "prior_bp"],
        expected_direction="Better medication adherence is expected to lower next-day systolic blood pressure.",
        example_interpretation=(
            "Adherent days should have lower next-day blood pressure, though stress and prior blood "
            "pressure can affect both adherence and the outcome."
        ),
        dag_edges=[
            ("baseline_bp", "outcome_bp_next_day"),
            ("stress_score", "medication_adherence"),
            ("stress_score", "outcome_bp_next_day"),
            ("caffeine_mg", "outcome_bp_next_day"),
            ("prior_bp", "medication_adherence"),
            ("prior_bp", "outcome_bp_next_day"),
            ("medication_adherence", "outcome_bp_next_day"),
        ],
    ),
    "stress_sleep": ScenarioDefinition(
        name="stress_sleep",
        description="Daily stress affects phone use, caffeine intake, sleep duration, and sleep quality.",
        causal_question="What is the effect of high stress on same-night sleep quality?",
        exposure="stress_score",
        outcome="outcome_sleep_quality",
        confounders=["prior_sleep_quality", "prior_fatigue", "day_of_week"],
        mediators=["late_night_screen_minutes", "caffeine_mg"],
        expected_direction="Higher stress is expected to worsen sleep quality.",
        example_interpretation=(
            "Stress is expected to reduce sleep quality directly and through higher phone use and caffeine."
        ),
        dag_edges=[
            ("prior_sleep_quality", "stress_score"),
            ("prior_sleep_quality", "outcome_sleep_quality"),
            ("prior_fatigue", "stress_score"),
            ("prior_fatigue", "outcome_sleep_quality"),
            ("day_of_week", "stress_score"),
            ("stress_score", "late_night_screen_minutes"),
            ("stress_score", "caffeine_mg"),
            ("stress_score", "outcome_sleep_quality"),
            ("late_night_screen_minutes", "outcome_sleep_quality"),
            ("caffeine_mg", "outcome_sleep_quality"),
        ],
        variables_not_to_adjust_for=["late_night_screen_minutes", "caffeine_mg"],
    ),
    "nighttime_eating_fatigue": ScenarioDefinition(
        name="nighttime_eating_fatigue",
        description="Nighttime eating affects morning fatigue through disrupted sleep.",
        causal_question="What is the effect of nighttime eating on morning fatigue?",
        exposure="nighttime_eating",
        outcome="morning_fatigue",
        confounders=[
            "stress_score",
            "late_night_screen_minutes",
            "prior_fatigue",
            "sleep_duration_hours",
        ],
        mediators=["sleep_duration_hours"],
        expected_direction="Nighttime eating is expected to increase morning fatigue.",
        example_interpretation=(
            "Nighttime eating should increase morning fatigue, partly because it can reduce sleep duration."
        ),
        dag_edges=[
            ("stress_score", "nighttime_eating"),
            ("stress_score", "morning_fatigue"),
            ("late_night_screen_minutes", "nighttime_eating"),
            ("late_night_screen_minutes", "sleep_duration_hours"),
            ("prior_fatigue", "nighttime_eating"),
            ("prior_fatigue", "morning_fatigue"),
            ("sleep_duration_hours", "morning_fatigue"),
            ("nighttime_eating", "morning_fatigue"),
        ],
        variables_not_to_adjust_for=["sleep_duration_hours"],
    ),
    "mixed_lifestyle": ScenarioDefinition(
        name="mixed_lifestyle",
        description="Combined lifestyle scenario with stress, sleep, activity, medication, eating, and sensors.",
        causal_question="What is the effect of an evening reminder intervention on sleep quality?",
        exposure="intervention_received",
        outcome="outcome_sleep_quality",
        confounders=[
            "stress_score",
            "prior_sleep_quality",
            "prior_fatigue",
            "day_of_week",
            "baseline_phone_use",
        ],
        mediators=["late_night_screen_minutes", "nighttime_eating"],
        expected_direction=(
            "Receiving an intervention reminder is expected to improve sleep quality by reducing "
            "late-night screen time and nighttime eating."
        ),
        example_interpretation=(
            "The reminder should improve sleep quality, but screen time and nighttime eating are mediators "
            "and should not be adjusted for when estimating the total effect."
        ),
        dag_edges=[
            ("stress_score", "intervention_received"),
            ("stress_score", "late_night_screen_minutes"),
            ("stress_score", "nighttime_eating"),
            ("stress_score", "outcome_sleep_quality"),
            ("prior_sleep_quality", "intervention_received"),
            ("prior_sleep_quality", "outcome_sleep_quality"),
            ("prior_fatigue", "intervention_received"),
            ("prior_fatigue", "outcome_sleep_quality"),
            ("day_of_week", "intervention_received"),
            ("baseline_phone_use", "intervention_received"),
            ("baseline_phone_use", "late_night_screen_minutes"),
            ("intervention_received", "late_night_screen_minutes"),
            ("intervention_received", "nighttime_eating"),
            ("intervention_received", "outcome_sleep_quality"),
            ("late_night_screen_minutes", "outcome_sleep_quality"),
            ("nighttime_eating", "morning_fatigue"),
        ],
        variables_not_to_adjust_for=["late_night_screen_minutes", "nighttime_eating"],
    ),
}


VARIABLE_DESCRIPTIONS: dict[str, str] = {
    "date": "Calendar date for the bundled daily record.",
    "day_index": "Zero-based study day index.",
    "day_of_week": "Day of week encoded Monday=0 through Sunday=6.",
    "is_weekend": "Indicator for Saturday or Sunday.",
    "patient_id": "Synthetic patient identifier.",
    "baseline_sleep_need": "Patient-level latent sleep need in hours.",
    "baseline_activity_level": "Patient-level latent activity tendency.",
    "baseline_stress_tendency": "Patient-level latent stress tendency.",
    "baseline_bp": "Patient-level latent systolic blood pressure tendency.",
    "baseline_phone_use": "Patient-level latent phone use tendency.",
    "baseline_adherence": "Patient-level latent medication adherence tendency.",
    "sleep_duration_hours": "Total sleep duration for the night ending on this date.",
    "sleep_efficiency": "Estimated percentage of time in bed spent sleeping.",
    "awakenings": "Number of nighttime awakenings.",
    "wearable_device_worn_hours": "Hours that the wearable device was detected as worn.",
    "heart_rate_variability_ms": "Daily heart-rate variability estimate in milliseconds.",
    "calories_burned": "Estimated daily calories burned from wearable activity data.",
    "spo2_percent": "Daily oxygen saturation estimate from wearable data.",
    "skin_temperature_c": "Daily average skin temperature estimate in Celsius.",
    "steps": "Daily step count.",
    "sedentary_minutes": "Daily sedentary minutes.",
    "active_minutes": "Daily active minutes.",
    "motion_stationary_minutes": "Phone or wearable motion classifier minutes spent stationary.",
    "motion_walking_minutes": "Motion classifier minutes spent walking.",
    "motion_running_minutes": "Motion classifier minutes spent running.",
    "motion_driving_minutes": "Motion classifier minutes spent driving or riding in a vehicle.",
    "accelerometer_activity_counts": "Daily aggregate accelerometer activity count.",
    "location_home_minutes": "Estimated minutes spent at home from location signals.",
    "location_work_minutes": "Estimated minutes spent at work from location signals.",
    "away_from_home_minutes": "Estimated minutes away from home.",
    "home_wifi_minutes": "Minutes connected to home Wi-Fi.",
    "distance_traveled_km": "Estimated daily distance traveled from location signals.",
    "commute_minutes": "Estimated commute or travel minutes.",
    "gps_radius_meters": "Approximate radius of daily location movement.",
    "significant_location_changes": "Count of significant location transitions.",
    "late_night_screen_minutes": "Screen time after the patient's intended wind-down time.",
    "caffeine_mg": "Daily caffeine intake in milligrams, emphasizing afternoon/evening intake.",
    "alcohol_units": "Alcohol units consumed that day.",
    "medication_adherence": "Binary indicator for whether prescribed medication was taken as planned.",
    "stress_score": "Daily stress score from 0 to 10.",
    "mood_score": "Daily mood score from 0 to 10, higher is better.",
    "pain_score": "Daily pain score from 0 to 10.",
    "blood_pressure_systolic": "Daily systolic blood pressure estimate.",
    "blood_pressure_diastolic": "Daily diastolic blood pressure estimate.",
    "resting_heart_rate": "Daily resting heart rate in beats per minute.",
    "morning_fatigue": "Morning fatigue score from 0 to 10.",
    "nighttime_eating": "Binary indicator for eating during the late evening/night window.",
    "pantry_door_opens": "Synthetic count of pantry door opens, representing a Home Assistant-style sensor.",
    "refrigerator_door_opens": "Synthetic count of refrigerator door opens.",
    "smart_plug_tv_minutes": "Estimated TV use minutes from a smart plug.",
    "smart_plug_kettle_uses": "Estimated electric kettle uses from smart plug current signatures.",
    "medication_cabinet_opens": "Medication cabinet sensor open count.",
    "phone_pickups": "Daily phone pickup count.",
    "unlocks": "Daily phone unlock count.",
    "notifications": "Daily phone notification count.",
    "texts_sent": "Daily SMS or messaging texts sent.",
    "texts_received": "Daily SMS or messaging texts received.",
    "calls_made": "Daily outgoing call count.",
    "calls_received": "Daily incoming call count.",
    "call_duration_minutes": "Total daily call duration in minutes.",
    "app_usage_minutes": "Daily app usage minutes.",
    "total_screen_time_minutes": "Total phone screen time minutes.",
    "social_app_minutes": "Minutes spent in social or messaging apps.",
    "productivity_app_minutes": "Minutes spent in productivity apps.",
    "finance_app_minutes": "Minutes spent in finance or banking apps.",
    "entertainment_app_minutes": "Minutes spent in entertainment apps.",
    "transactions_count": "Daily synthetic financial transaction count.",
    "card_spend_usd": "Daily synthetic card spend in US dollars.",
    "cash_withdrawal_usd": "Daily synthetic cash withdrawal amount in US dollars.",
    "grocery_spend_usd": "Daily synthetic grocery spend in US dollars.",
    "restaurant_spend_usd": "Daily synthetic restaurant spend in US dollars.",
    "alcohol_spend_usd": "Daily synthetic alcohol-related spend in US dollars.",
    "ride_share_spend_usd": "Daily synthetic rideshare spend in US dollars.",
    "online_purchase_count": "Daily synthetic online purchase count.",
    "work_calendar_events": "Daily work calendar event count.",
    "meeting_minutes": "Daily meeting minutes from calendar data.",
    "intervention_received": "Binary indicator for an evening reminder or digital intervention.",
    "sleep_quality": "Derived same-night sleep quality score from 0 to 10.",
    "prior_sleep_quality": "Previous day's sleep quality.",
    "prior_fatigue": "Previous day's morning fatigue.",
    "prior_bp": "Previous day's systolic blood pressure.",
    "outcome_sleep_quality": "Outcome sleep quality score aligned to the exposure day.",
    "outcome_next_day_fatigue": "Next-day fatigue outcome aligned to the exposure day.",
    "outcome_mood_next_day": "Next-day mood outcome aligned to the exposure day.",
    "outcome_bp_next_day": "Next-day systolic blood pressure outcome aligned to the exposure day.",
}


def get_scenario(name: str | None) -> ScenarioDefinition:
    """Return a scenario definition, defaulting to mixed_lifestyle."""

    scenario_name = name or "mixed_lifestyle"
    if scenario_name not in SCENARIOS:
        valid = ", ".join(sorted(SCENARIOS))
        raise ValueError(f"Unknown scenario '{scenario_name}'. Supported scenarios: {valid}.")
    return SCENARIOS[scenario_name]


def list_scenarios() -> list[dict[str, Any]]:
    """Return all scenario descriptions."""

    return [scenario.to_public_dict() for scenario in SCENARIOS.values()]
