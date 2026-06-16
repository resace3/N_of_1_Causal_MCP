from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from patient_causal_mcp.datasets import DEFAULT_DATASET_ID, load_bundled_dataset
from patient_causal_mcp.scenarios import VARIABLE_DESCRIPTIONS


DATASET_PATH = Path("src/patient_causal_mcp/data/patient_001_100_days.csv")

EXPECTED_COLUMNS = [
    "date",
    "day_index",
    "day_of_week",
    "is_weekend",
    "patient_id",
    "baseline_sleep_need",
    "baseline_activity_level",
    "baseline_stress_tendency",
    "baseline_bp",
    "baseline_phone_use",
    "baseline_adherence",
    "sleep_duration_hours",
    "sleep_efficiency",
    "awakenings",
    "wearable_device_worn_hours",
    "heart_rate_variability_ms",
    "calories_burned",
    "spo2_percent",
    "skin_temperature_c",
    "steps",
    "sedentary_minutes",
    "active_minutes",
    "motion_stationary_minutes",
    "motion_walking_minutes",
    "motion_running_minutes",
    "motion_driving_minutes",
    "accelerometer_activity_counts",
    "location_home_minutes",
    "location_work_minutes",
    "away_from_home_minutes",
    "home_wifi_minutes",
    "distance_traveled_km",
    "commute_minutes",
    "gps_radius_meters",
    "significant_location_changes",
    "late_night_screen_minutes",
    "caffeine_mg",
    "alcohol_units",
    "medication_adherence",
    "stress_score",
    "mood_score",
    "pain_score",
    "blood_pressure_systolic",
    "blood_pressure_diastolic",
    "resting_heart_rate",
    "morning_fatigue",
    "nighttime_eating",
    "pantry_door_opens",
    "refrigerator_door_opens",
    "smart_plug_tv_minutes",
    "smart_plug_kettle_uses",
    "medication_cabinet_opens",
    "phone_pickups",
    "unlocks",
    "notifications",
    "texts_sent",
    "texts_received",
    "calls_made",
    "calls_received",
    "call_duration_minutes",
    "app_usage_minutes",
    "total_screen_time_minutes",
    "social_app_minutes",
    "productivity_app_minutes",
    "finance_app_minutes",
    "entertainment_app_minutes",
    "transactions_count",
    "card_spend_usd",
    "cash_withdrawal_usd",
    "grocery_spend_usd",
    "restaurant_spend_usd",
    "alcohol_spend_usd",
    "ride_share_spend_usd",
    "online_purchase_count",
    "work_calendar_events",
    "meeting_minutes",
    "intervention_received",
    "sleep_quality",
    "prior_sleep_quality",
    "prior_fatigue",
    "prior_bp",
    "outcome_sleep_quality",
    "outcome_next_day_fatigue",
    "outcome_mood_next_day",
    "outcome_bp_next_day",
]

RANGES = {
    "sleep_duration_hours": (4, 10),
    "sleep_efficiency": (60, 98),
    "awakenings": (0, 12),
    "wearable_device_worn_hours": (12, 24),
    "heart_rate_variability_ms": (18, 105),
    "calories_burned": (1350, 3900),
    "spo2_percent": (92, 100),
    "skin_temperature_c": (35.7, 37.6),
    "steps": (500, 20000),
    "sedentary_minutes": (240, 1100),
    "active_minutes": (5, 240),
    "motion_stationary_minutes": (220, 1150),
    "motion_walking_minutes": (0, 220),
    "motion_running_minutes": (0, 70),
    "motion_driving_minutes": (0, 190),
    "accelerometer_activity_counts": (60, 1800),
    "location_home_minutes": (360, 1320),
    "location_work_minutes": (0, 650),
    "away_from_home_minutes": (60, 1080),
    "home_wifi_minutes": (180, 1400),
    "distance_traveled_km": (0.2, 85),
    "commute_minutes": (0, 140),
    "gps_radius_meters": (35, 4200),
    "significant_location_changes": (0, 28),
    "late_night_screen_minutes": (0, 260),
    "caffeine_mg": (0, 500),
    "alcohol_units": (0, 8),
    "stress_score": (0, 10),
    "mood_score": (0, 10),
    "pain_score": (0, 10),
    "blood_pressure_systolic": (95, 170),
    "blood_pressure_diastolic": (55, 105),
    "resting_heart_rate": (48, 105),
    "morning_fatigue": (0, 10),
    "pantry_door_opens": (0, 25),
    "refrigerator_door_opens": (0, 30),
    "smart_plug_tv_minutes": (0, 300),
    "smart_plug_kettle_uses": (0, 9),
    "medication_cabinet_opens": (0, 3),
    "phone_pickups": (5, 180),
    "unlocks": (3, 190),
    "notifications": (15, 520),
    "texts_sent": (0, 90),
    "texts_received": (0, 140),
    "calls_made": (0, 12),
    "calls_received": (0, 16),
    "call_duration_minutes": (0, 180),
    "app_usage_minutes": (15, 620),
    "total_screen_time_minutes": (30, 780),
    "social_app_minutes": (0, 320),
    "productivity_app_minutes": (0, 260),
    "finance_app_minutes": (0, 65),
    "entertainment_app_minutes": (0, 360),
    "transactions_count": (0, 22),
    "card_spend_usd": (0, 260),
    "cash_withdrawal_usd": (0, 80),
    "grocery_spend_usd": (0, 145),
    "restaurant_spend_usd": (0, 125),
    "alcohol_spend_usd": (0, 90),
    "ride_share_spend_usd": (0, 120),
    "online_purchase_count": (0, 8),
    "work_calendar_events": (0, 12),
    "meeting_minutes": (0, 520),
    "sleep_quality": (0, 10),
    "prior_sleep_quality": (0, 10),
    "prior_fatigue": (0, 10),
    "prior_bp": (95, 170),
    "outcome_sleep_quality": (0, 10),
    "outcome_next_day_fatigue": (0, 10),
    "outcome_mood_next_day": (0, 10),
    "outcome_bp_next_day": (95, 170),
}

BINARY_COLUMNS = [
    "is_weekend",
    "medication_adherence",
    "nighttime_eating",
    "intervention_received",
]

INTEGER_COLUMNS = [
    "day_index",
    "day_of_week",
    "is_weekend",
    "awakenings",
    "steps",
    "sedentary_minutes",
    "active_minutes",
    "calories_burned",
    "motion_stationary_minutes",
    "motion_walking_minutes",
    "motion_running_minutes",
    "motion_driving_minutes",
    "accelerometer_activity_counts",
    "location_home_minutes",
    "location_work_minutes",
    "away_from_home_minutes",
    "home_wifi_minutes",
    "commute_minutes",
    "gps_radius_meters",
    "significant_location_changes",
    "medication_adherence",
    "nighttime_eating",
    "pantry_door_opens",
    "refrigerator_door_opens",
    "smart_plug_tv_minutes",
    "smart_plug_kettle_uses",
    "medication_cabinet_opens",
    "phone_pickups",
    "unlocks",
    "notifications",
    "texts_sent",
    "texts_received",
    "calls_made",
    "calls_received",
    "app_usage_minutes",
    "total_screen_time_minutes",
    "social_app_minutes",
    "productivity_app_minutes",
    "finance_app_minutes",
    "entertainment_app_minutes",
    "transactions_count",
    "online_purchase_count",
    "work_calendar_events",
    "meeting_minutes",
    "intervention_received",
]


@pytest.fixture(scope="module")
def dataframe() -> pd.DataFrame:
    return pd.read_csv(DATASET_PATH)


def test_dataset_file_exists() -> None:
    assert DATASET_PATH.exists()


def test_dataset_has_expected_shape(dataframe: pd.DataFrame) -> None:
    assert dataframe.shape == (100, 85)


def test_dataset_loader_matches_file_shape(dataframe: pd.DataFrame) -> None:
    records = load_bundled_dataset(DEFAULT_DATASET_ID)
    assert len(records) == dataframe.shape[0]
    assert len(records[0]) == dataframe.shape[1]


def test_dataset_check_volume_exceeds_100() -> None:
    assert len(EXPECTED_COLUMNS) + len(RANGES) + len(INTEGER_COLUMNS) > 100


@pytest.mark.parametrize("column", EXPECTED_COLUMNS)
def test_expected_column_is_present(dataframe: pd.DataFrame, column: str) -> None:
    assert column in dataframe.columns


@pytest.mark.parametrize("column", EXPECTED_COLUMNS)
def test_column_has_variable_description(column: str) -> None:
    assert column in VARIABLE_DESCRIPTIONS
    assert len(VARIABLE_DESCRIPTIONS[column]) >= 20


@pytest.mark.parametrize("column", EXPECTED_COLUMNS)
def test_column_has_no_missing_values(dataframe: pd.DataFrame, column: str) -> None:
    assert int(dataframe[column].isna().sum()) == 0


@pytest.mark.parametrize(("column", "bounds"), RANGES.items())
def test_numeric_column_within_expected_range(
    dataframe: pd.DataFrame,
    column: str,
    bounds: tuple[float, float],
) -> None:
    lower, upper = bounds
    assert dataframe[column].between(lower, upper).all()


@pytest.mark.parametrize("column", BINARY_COLUMNS)
def test_binary_columns_are_zero_one(dataframe: pd.DataFrame, column: str) -> None:
    assert set(dataframe[column].unique()).issubset({0, 1})


@pytest.mark.parametrize("column", INTEGER_COLUMNS)
def test_integer_columns_have_integer_values(dataframe: pd.DataFrame, column: str) -> None:
    assert dataframe[column].map(lambda value: float(value).is_integer()).all()


def test_date_series_is_daily_and_ordered(dataframe: pd.DataFrame) -> None:
    dates = pd.to_datetime(dataframe["date"])
    assert dates.is_monotonic_increasing
    assert dates.iloc[0].strftime("%Y-%m-%d") == "2026-01-01"
    assert dates.iloc[-1].strftime("%Y-%m-%d") == "2026-04-10"
    assert (dates.diff().dropna().dt.days == 1).all()


def test_day_index_is_zero_based_sequence(dataframe: pd.DataFrame) -> None:
    assert dataframe["day_index"].tolist() == list(range(100))


def test_patient_id_is_single_patient(dataframe: pd.DataFrame) -> None:
    assert dataframe["patient_id"].nunique() == 1
    assert dataframe["patient_id"].iloc[0] == "patient-001"


def test_bundled_dataset_has_treatment_variation(dataframe: pd.DataFrame) -> None:
    low_screen_days = int((dataframe["late_night_screen_minutes"] <= 120).sum())
    reminder_days = int(dataframe["intervention_received"].sum())
    assert 20 <= low_screen_days <= 80
    assert 10 <= reminder_days <= 90


def test_financial_components_do_not_exceed_total_card_spend(dataframe: pd.DataFrame) -> None:
    component_spend = dataframe["grocery_spend_usd"] + dataframe["restaurant_spend_usd"]
    assert (component_spend <= dataframe["card_spend_usd"] + 150).all()


def test_phone_component_minutes_do_not_exceed_day(dataframe: pd.DataFrame) -> None:
    phone_minutes = dataframe[
        [
            "social_app_minutes",
            "productivity_app_minutes",
            "finance_app_minutes",
            "entertainment_app_minutes",
        ]
    ].sum(axis=1)
    assert (phone_minutes <= 1440).all()


def test_outcome_alignment_has_real_values(dataframe: pd.DataFrame) -> None:
    outcome_columns = [
        "outcome_sleep_quality",
        "outcome_next_day_fatigue",
        "outcome_mood_next_day",
        "outcome_bp_next_day",
    ]
    for column in outcome_columns:
        assert dataframe[column].map(math.isfinite).all()
