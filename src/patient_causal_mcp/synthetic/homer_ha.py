"""Deterministic Home Assistant-style synthetic data for a fictional parody household."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Literal
from zoneinfo import ZoneInfo

import pandas as pd


HOMER_HA_STATES_30_DAYS_ID = "homer_simpson_ha_states_30_days"
HOMER_HA_STATES_100_DAYS_ID = "homer_simpson_ha_states_100_days"
HOMER_DAILY_100_DAYS_ID = "homer_simpson_daily_100_days"
HOMER_SQLITE_DEMO_30_DAYS_ID = "homer_simpson_ha_sqlite_demo_30_days"
HOMER_DATASET_IDS = {
    HOMER_HA_STATES_30_DAYS_ID,
    HOMER_HA_STATES_100_DAYS_ID,
    HOMER_DAILY_100_DAYS_ID,
    HOMER_SQLITE_DEMO_30_DAYS_ID,
}
HOMER_METADATA_ROW_ESTIMATES = {
    HOMER_HA_STATES_30_DAYS_ID: 62_000,
    HOMER_HA_STATES_100_DAYS_ID: 250_000,
    HOMER_DAILY_100_DAYS_ID: 100,
    HOMER_SQLITE_DEMO_30_DAYS_ID: 62_000,
}

DEFAULT_SEED = 742_001
DEFAULT_START = "2026-01-01T00:00:00-05:00"
TIMEZONE = "America/New_York"
ALLOWED_ZONES = {
    "home",
    "not_home",
    "work",
    "springfield_home",
    "springfield_work",
    "moes_area",
    "kwik_e_mart_area",
    "school_area",
    "power_plant_area",
}
PROFILE = {
    "subject_id": "homer_simpson",
    "display_name": "Homer Simpson",
    "profile_type": "fictional_parody",
    "household_id": "simpson_household_synthetic",
    "timezone": TIMEZONE,
    "workplace": "springfield_nuclear_power_plant_synthetic",
    "home": "springfield_home_synthetic",
    "privacy_note": (
        "Synthetic parody data only. Not official Simpsons data and not real personal data."
    ),
}


@dataclass(frozen=True)
class EntitySpec:
    """Home Assistant-style entity metadata."""

    entity_id: str
    friendly_name: str
    source: str
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = "measurement"
    icon: str | None = None
    aggregation_rule: str = "last"

    @property
    def domain(self) -> str:
        return self.entity_id.split(".", 1)[0]

    @property
    def object_id(self) -> str:
        return self.entity_id.split(".", 1)[1]

    def attributes(self) -> dict[str, Any]:
        attrs = {
            "friendly_name": self.friendly_name,
            "unit_of_measurement": self.unit,
            "device_class": self.device_class,
            "state_class": self.state_class,
            "source": self.source,
            "synthetic_subject": PROFILE["subject_id"],
            "synthetic_profile": PROFILE["profile_type"],
            "privacy_level": "synthetic",
            "icon": self.icon,
        }
        return {key: value for key, value in attrs.items() if value is not None}


@dataclass(frozen=True)
class HADataset:
    """Generated normalized Home Assistant-style dataset."""

    dataset_id: str
    days: int
    density: str
    seed: int
    start: datetime
    states: list[dict[str, Any]]
    states_meta: list[dict[str, Any]]
    state_attributes: list[dict[str, Any]]
    flattened: list[dict[str, Any]]
    daily: list[dict[str, Any]]
    latent_days: list[dict[str, Any]]


def _sensor(
    object_id: str,
    friendly_name: str,
    source: str,
    unit: str | None = None,
    *,
    device_class: str | None = None,
    state_class: str | None = "measurement",
    icon: str | None = None,
    aggregation_rule: str = "last",
) -> EntitySpec:
    return EntitySpec(
        entity_id=f"sensor.{object_id}",
        friendly_name=friendly_name,
        source=source,
        unit=unit,
        device_class=device_class,
        state_class=state_class,
        icon=icon,
        aggregation_rule=aggregation_rule,
    )


def _binary(object_id: str, friendly_name: str, source: str, icon: str) -> EntitySpec:
    return EntitySpec(
        entity_id=f"binary_sensor.{object_id}",
        friendly_name=friendly_name,
        source=source,
        icon=icon,
        state_class=None,
        aggregation_rule="count_on",
    )


def _switch(object_id: str, friendly_name: str, source: str, icon: str) -> EntitySpec:
    return EntitySpec(
        entity_id=f"switch.{object_id}",
        friendly_name=friendly_name,
        source=source,
        icon=icon,
        state_class=None,
        aggregation_rule="duration_on",
    )


def _light(object_id: str, friendly_name: str, source: str) -> EntitySpec:
    return EntitySpec(
        entity_id=f"light.{object_id}",
        friendly_name=friendly_name,
        source=source,
        icon="mdi:lightbulb",
        state_class=None,
        aggregation_rule="duration_on",
    )


def _device_tracker(object_id: str, friendly_name: str, source: str) -> EntitySpec:
    return EntitySpec(
        entity_id=f"device_tracker.{object_id}",
        friendly_name=friendly_name,
        source=source,
        icon="mdi:map-marker",
        state_class=None,
        aggregation_rule="zone_duration",
    )


def _calendar(object_id: str, friendly_name: str, source: str) -> EntitySpec:
    return EntitySpec(
        entity_id=f"calendar.{object_id}",
        friendly_name=friendly_name,
        source=source,
        icon="mdi:calendar",
        state_class=None,
        aggregation_rule="duration_on",
    )


def _input_boolean(object_id: str, friendly_name: str, source: str) -> EntitySpec:
    return EntitySpec(
        entity_id=f"input_boolean.{object_id}",
        friendly_name=friendly_name,
        source=source,
        icon="mdi:bell",
        state_class=None,
        aggregation_rule="last",
    )


def entity_catalog() -> list[EntitySpec]:
    """Return the deterministic Homer Home Assistant entity catalog."""

    entities = [
        # Wearable
        _sensor("homer_watch_steps", "Homer Watch Steps", "synthetic_wearable", "steps", icon="mdi:walk"),
        _sensor("homer_watch_active_minutes", "Homer Watch Active Minutes", "synthetic_wearable", "min", device_class="duration", icon="mdi:run"),
        _sensor("homer_watch_sedentary_minutes", "Homer Watch Sedentary Minutes", "synthetic_wearable", "min", device_class="duration", icon="mdi:sofa"),
        _sensor("homer_watch_heart_rate", "Homer Watch Heart Rate", "synthetic_wearable", "bpm", icon="mdi:heart-pulse", aggregation_rule="mean"),
        _sensor("homer_watch_resting_heart_rate", "Homer Watch Resting Heart Rate", "synthetic_wearable", "bpm", icon="mdi:heart"),
        _sensor("homer_watch_hrv", "Homer Watch HRV", "synthetic_wearable", "ms", icon="mdi:heart-flash"),
        _sensor("homer_watch_sleep_duration", "Homer Watch Sleep Duration", "synthetic_wearable", "h", device_class="duration", icon="mdi:sleep"),
        _sensor("homer_watch_sleep_efficiency", "Homer Watch Sleep Efficiency", "synthetic_wearable", "%", icon="mdi:sleep"),
        _sensor("homer_watch_sleep_score", "Homer Watch Sleep Score", "synthetic_wearable", "score", icon="mdi:sleep"),
        _sensor("homer_watch_spo2", "Homer Watch SpO2", "synthetic_wearable", "%", icon="mdi:lungs"),
        _sensor("homer_watch_skin_temperature", "Homer Watch Skin Temperature", "synthetic_wearable", "°C", device_class="temperature", icon="mdi:thermometer"),
        _sensor("homer_watch_calories_burned", "Homer Watch Calories Burned", "synthetic_wearable", "kcal", icon="mdi:fire"),
        _sensor("homer_watch_stand_hours", "Homer Watch Stand Hours", "synthetic_wearable", "h", device_class="duration", icon="mdi:human-male-height"),
        _binary("homer_watch_worn", "Homer Watch Worn", "synthetic_wearable", "mdi:watch"),
        _sensor("homer_watch_battery_level", "Homer Watch Battery Level", "synthetic_wearable", "%", device_class="battery", icon="mdi:battery"),
        # Phone
        _sensor("homer_phone_battery_level", "Homer Phone Battery Level", "synthetic_phone", "%", device_class="battery", icon="mdi:battery"),
        _sensor("homer_phone_screen_time", "Homer Phone Screen Time", "synthetic_phone", "min", device_class="duration", icon="mdi:cellphone"),
        _sensor("homer_phone_pickups", "Homer Phone Pickups", "synthetic_phone", "count", icon="mdi:cellphone-arrow-down"),
        _sensor("homer_phone_unlocks", "Homer Phone Unlocks", "synthetic_phone", "count", icon="mdi:lock-open"),
        _sensor("homer_phone_notifications", "Homer Phone Notifications", "synthetic_phone", "count", icon="mdi:bell"),
        _sensor("homer_phone_calls_made", "Homer Phone Calls Made", "synthetic_phone", "count", icon="mdi:phone-outgoing"),
        _sensor("homer_phone_calls_received", "Homer Phone Calls Received", "synthetic_phone", "count", icon="mdi:phone-incoming"),
        _sensor("homer_phone_call_duration", "Homer Phone Call Duration", "synthetic_phone", "min", device_class="duration", icon="mdi:phone-clock"),
        _sensor("homer_phone_texts_sent", "Homer Phone Texts Sent", "synthetic_phone", "count", icon="mdi:message-arrow-right"),
        _sensor("homer_phone_texts_received", "Homer Phone Texts Received", "synthetic_phone", "count", icon="mdi:message-arrow-left"),
        _sensor("homer_phone_social_app_minutes", "Homer Phone Social App Minutes", "synthetic_phone", "min", device_class="duration", icon="mdi:message"),
        _sensor("homer_phone_entertainment_app_minutes", "Homer Phone Entertainment Minutes", "synthetic_phone", "min", device_class="duration", icon="mdi:movie"),
        _sensor("homer_phone_navigation_minutes", "Homer Phone Navigation Minutes", "synthetic_phone", "min", device_class="duration", icon="mdi:navigation"),
        _sensor("homer_phone_game_minutes", "Homer Phone Game Minutes", "synthetic_phone", "min", device_class="duration", icon="mdi:gamepad"),
        _sensor("homer_phone_productivity_minutes", "Homer Phone Productivity Minutes", "synthetic_phone", "min", device_class="duration", icon="mdi:briefcase"),
        _device_tracker("homer_phone", "Homer Phone", "synthetic_phone"),
        _sensor("homer_phone_wifi_ssid", "Homer Phone Wi-Fi SSID", "synthetic_phone", icon="mdi:wifi", state_class=None),
        _binary("homer_phone_charging", "Homer Phone Charging", "synthetic_phone", "mdi:power-plug"),
        _sensor("homer_phone_focus_mode", "Homer Phone Focus Mode", "synthetic_phone", icon="mdi:moon-waning-crescent", state_class=None),
        # Smart home presence and room sensors
        _binary("living_room_motion", "Living Room Motion", "synthetic_smart_home", "mdi:motion-sensor"),
        _binary("kitchen_motion", "Kitchen Motion", "synthetic_smart_home", "mdi:motion-sensor"),
        _binary("bedroom_motion", "Bedroom Motion", "synthetic_smart_home", "mdi:motion-sensor"),
        _binary("garage_motion", "Garage Motion", "synthetic_smart_home", "mdi:garage"),
        _binary("tv_room_occupancy", "TV Room Occupancy", "synthetic_smart_home", "mdi:television"),
        _binary("front_door_contact", "Front Door Contact", "synthetic_smart_home", "mdi:door"),
        _binary("refrigerator_door_contact", "Refrigerator Door Contact", "synthetic_smart_home", "mdi:fridge"),
        _binary("pantry_door_contact", "Pantry Door Contact", "synthetic_smart_home", "mdi:cupboard"),
        _binary("medicine_cabinet_contact", "Medicine Cabinet Contact", "synthetic_smart_home", "mdi:medical-bag"),
        _sensor("home_occupancy_count", "Home Occupancy Count", "synthetic_smart_home", "count", icon="mdi:account-group"),
        _sensor("homer_home_minutes", "Homer Home Minutes", "synthetic_location", "min", device_class="duration", icon="mdi:home"),
        _sensor("homer_away_minutes", "Homer Away Minutes", "synthetic_location", "min", device_class="duration", icon="mdi:map-marker-distance"),
        _sensor("homer_room_presence", "Homer Room Presence", "synthetic_smart_home", icon="mdi:floor-plan", state_class=None),
        # Environment
        _sensor("living_room_illuminance", "Living Room Illuminance", "synthetic_environment", "lx", device_class="illuminance", icon="mdi:brightness-5", aggregation_rule="mean"),
        _sensor("kitchen_illuminance", "Kitchen Illuminance", "synthetic_environment", "lx", device_class="illuminance", icon="mdi:brightness-5", aggregation_rule="mean"),
        _sensor("bedroom_illuminance", "Bedroom Illuminance", "synthetic_environment", "lx", device_class="illuminance", icon="mdi:brightness-4", aggregation_rule="mean"),
        _sensor("garage_illuminance", "Garage Illuminance", "synthetic_environment", "lx", device_class="illuminance", icon="mdi:brightness-4", aggregation_rule="mean"),
        _sensor("outdoor_illuminance", "Outdoor Illuminance", "synthetic_environment", "lx", device_class="illuminance", icon="mdi:white-balance-sunny", aggregation_rule="mean"),
        _sensor("living_room_temperature", "Living Room Temperature", "synthetic_environment", "°C", device_class="temperature", icon="mdi:thermometer", aggregation_rule="mean"),
        _sensor("bedroom_temperature", "Bedroom Temperature", "synthetic_environment", "°C", device_class="temperature", icon="mdi:thermometer", aggregation_rule="mean"),
        _sensor("kitchen_temperature", "Kitchen Temperature", "synthetic_environment", "°C", device_class="temperature", icon="mdi:thermometer", aggregation_rule="mean"),
        _sensor("outdoor_temperature", "Outdoor Temperature", "synthetic_environment", "°C", device_class="temperature", icon="mdi:thermometer", aggregation_rule="mean"),
        _sensor("living_room_humidity", "Living Room Humidity", "synthetic_environment", "%", device_class="humidity", icon="mdi:water-percent", aggregation_rule="mean"),
        _sensor("bedroom_humidity", "Bedroom Humidity", "synthetic_environment", "%", device_class="humidity", icon="mdi:water-percent", aggregation_rule="mean"),
        _sensor("indoor_co2", "Indoor CO2", "synthetic_environment", "ppm", device_class="carbon_dioxide", icon="mdi:molecule-co2", aggregation_rule="mean"),
        _sensor("kitchen_pm25", "Kitchen PM2.5", "synthetic_environment", "µg/m³", device_class="pm25", icon="mdi:blur", aggregation_rule="max"),
        EntitySpec("weather.springfield_synthetic", "Springfield Synthetic Weather", "synthetic_weather", icon="mdi:weather-partly-cloudy", state_class=None),
        # Appliances and media
        _switch("living_room_tv", "Living Room TV", "synthetic_media", "mdi:television"),
        _sensor("living_room_tv_power", "Living Room TV Power", "synthetic_media", "W", device_class="power", icon="mdi:flash", aggregation_rule="mean"),
        _sensor("living_room_tv_energy", "Living Room TV Energy", "synthetic_media", "kWh", device_class="energy", state_class="total_increasing", icon="mdi:flash", aggregation_rule="last"),
        EntitySpec("media_player.living_room_tv", "Living Room TV Media Player", "synthetic_media", icon="mdi:television-play", state_class=None),
        _sensor("streaming_minutes", "Streaming Minutes", "synthetic_media", "min", device_class="duration", icon="mdi:play-box"),
        _switch("kitchen_kettle", "Kitchen Kettle", "synthetic_appliance", "mdi:kettle"),
        _sensor("kettle_power", "Kettle Power", "synthetic_appliance", "W", device_class="power", icon="mdi:flash", aggregation_rule="mean"),
        _sensor("kettle_energy", "Kettle Energy", "synthetic_appliance", "kWh", device_class="energy", state_class="total_increasing", icon="mdi:flash", aggregation_rule="last"),
        _switch("microwave", "Microwave", "synthetic_appliance", "mdi:microwave"),
        _sensor("microwave_power", "Microwave Power", "synthetic_appliance", "W", device_class="power", icon="mdi:flash", aggregation_rule="mean"),
        _switch("garage_freezer", "Garage Freezer", "synthetic_appliance", "mdi:snowflake"),
        _sensor("refrigerator_power", "Refrigerator Power", "synthetic_appliance", "W", device_class="power", icon="mdi:fridge", aggregation_rule="mean"),
        _sensor("washing_machine_power", "Washing Machine Power", "synthetic_appliance", "W", device_class="power", icon="mdi:washing-machine", aggregation_rule="mean"),
        _sensor("dishwasher_power", "Dishwasher Power", "synthetic_appliance", "W", device_class="power", icon="mdi:dishwasher", aggregation_rule="mean"),
        _sensor("bedroom_lamp_power", "Bedroom Lamp Power", "synthetic_appliance", "W", device_class="power", icon="mdi:lamp", aggregation_rule="mean"),
        _light("kitchen_lights", "Kitchen Lights", "synthetic_lighting"),
        _light("living_room_lights", "Living Room Lights", "synthetic_lighting"),
        _light("bedroom_lights", "Bedroom Lights", "synthetic_lighting"),
        # Car and mobility
        _sensor("homer_car_odometer", "Homer Car Odometer", "synthetic_car", "mi", device_class="distance", state_class="total_increasing", icon="mdi:counter"),
        _sensor("homer_car_fuel_level", "Homer Car Fuel Level", "synthetic_car", "%", device_class="battery", icon="mdi:fuel"),
        _sensor("homer_car_range", "Homer Car Range", "synthetic_car", "mi", device_class="distance", icon="mdi:map-marker-distance"),
        _sensor("homer_car_speed", "Homer Car Speed", "synthetic_car", "mph", device_class="speed", icon="mdi:speedometer", aggregation_rule="mean"),
        _sensor("homer_car_engine_runtime", "Homer Car Engine Runtime", "synthetic_car", "min", device_class="duration", icon="mdi:engine"),
        _sensor("homer_car_trip_distance", "Homer Car Trip Distance", "synthetic_car", "mi", device_class="distance", icon="mdi:road"),
        _sensor("homer_car_trip_duration", "Homer Car Trip Duration", "synthetic_car", "min", device_class="duration", icon="mdi:timer"),
        _sensor("homer_car_hard_brakes", "Homer Car Hard Brakes", "synthetic_car", "count", icon="mdi:car-brake-alert"),
        _sensor("homer_car_idle_minutes", "Homer Car Idle Minutes", "synthetic_car", "min", device_class="duration", icon="mdi:car-clock"),
        _sensor("homer_car_cabin_temperature", "Homer Car Cabin Temperature", "synthetic_car", "°C", device_class="temperature", icon="mdi:car-seat"),
        _binary("homer_car_ignition", "Homer Car Ignition", "synthetic_car", "mdi:car-key"),
        _binary("homer_car_driver_door", "Homer Car Driver Door", "synthetic_car", "mdi:car-door"),
        _device_tracker("homer_car", "Homer Car", "synthetic_car"),
        # Work and calendar
        _calendar("homer_work_shift", "Homer Work Shift", "synthetic_calendar"),
        _sensor("homer_work_calendar_events", "Homer Work Calendar Events", "synthetic_calendar", "count", icon="mdi:calendar-clock"),
        _sensor("homer_meeting_minutes", "Homer Meeting Minutes", "synthetic_calendar", "min", device_class="duration", icon="mdi:calendar-clock"),
        _binary("homer_at_work", "Homer At Work", "synthetic_work", "mdi:factory"),
        _sensor("homer_work_stress_proxy", "Homer Work Stress Proxy", "synthetic_work", "score", icon="mdi:alert"),
        _sensor("power_plant_noise_level", "Power Plant Noise Level", "synthetic_work", "dB", icon="mdi:volume-high"),
        _sensor("power_plant_shift_load", "Power Plant Shift Load", "synthetic_work", "score", icon="mdi:factory"),
        # Food, drink, behavior
        _sensor("donut_box_open_count", "Donut Box Open Count", "synthetic_behavior", "count", icon="mdi:food-donut"),
        _binary("donut_box_contact", "Donut Box Contact", "synthetic_behavior", "mdi:food-donut"),
        _sensor("snack_cabinet_open_count", "Snack Cabinet Open Count", "synthetic_behavior", "count", icon="mdi:cupboard"),
        _sensor("refrigerator_open_count", "Refrigerator Open Count", "synthetic_behavior", "count", icon="mdi:fridge"),
        _sensor("caffeine_mg_estimate", "Caffeine MG Estimate", "synthetic_behavior", "mg", icon="mdi:coffee"),
        _sensor("soda_intake_count", "Soda Intake Count", "synthetic_behavior", "count", icon="mdi:bottle-soda"),
        _sensor("late_night_snack_events", "Late Night Snack Events", "synthetic_behavior", "count", icon="mdi:food"),
        _binary("nighttime_eating", "Nighttime Eating", "synthetic_behavior", "mdi:food-apple"),
        _sensor("restaurant_visit_count", "Restaurant Visit Count", "synthetic_behavior", "count", icon="mdi:silverware-fork-knife"),
        _sensor("tavern_visit_minutes", "Tavern Visit Minutes", "synthetic_behavior", "min", device_class="duration", icon="mdi:glass-mug"),
        _sensor("fast_food_visit_count", "Fast Food Visit Count", "synthetic_behavior", "count", icon="mdi:food"),
        # Health and self-report
        _sensor("homer_mood_score", "Homer Mood Score", "synthetic_health", "score", icon="mdi:emoticon"),
        _sensor("homer_stress_score", "Homer Stress Score", "synthetic_health", "score", icon="mdi:head-alert"),
        _sensor("homer_fatigue_score", "Homer Fatigue Score", "synthetic_health", "score", icon="mdi:sleep-off"),
        _sensor("homer_pain_score", "Homer Pain Score", "synthetic_health", "score", icon="mdi:medical-bag"),
        _sensor("homer_blood_pressure_systolic", "Homer Blood Pressure Systolic", "synthetic_health", "mmHg", device_class="pressure", icon="mdi:heart-pulse"),
        _sensor("homer_blood_pressure_diastolic", "Homer Blood Pressure Diastolic", "synthetic_health", "mmHg", device_class="pressure", icon="mdi:heart-pulse"),
        _sensor("homer_weight", "Homer Weight", "synthetic_health", "lb", icon="mdi:scale-bathroom"),
        _sensor("homer_sleep_quality_reported", "Homer Sleep Quality Reported", "synthetic_health", "score", icon="mdi:sleep"),
        _input_boolean("homer_received_sleep_nudge", "Homer Received Sleep Nudge", "synthetic_intervention"),
        _input_boolean("homer_received_walk_nudge", "Homer Received Walk Nudge", "synthetic_intervention"),
        _input_boolean("homer_received_caffeine_nudge", "Homer Received Caffeine Nudge", "synthetic_intervention"),
        # Daily derived sensors
        _sensor("homer_daily_steps", "Homer Daily Steps", "synthetic_daily", "steps", icon="mdi:walk"),
        _sensor("homer_daily_sleep_hours", "Homer Daily Sleep Hours", "synthetic_daily", "h", device_class="duration", icon="mdi:sleep"),
        _sensor("homer_daily_late_screen_minutes", "Homer Daily Late Screen Minutes", "synthetic_daily", "min", device_class="duration", icon="mdi:cellphone"),
        _sensor("homer_daily_tv_minutes", "Homer Daily TV Minutes", "synthetic_daily", "min", device_class="duration", icon="mdi:television"),
        _sensor("homer_daily_caffeine_mg", "Homer Daily Caffeine MG", "synthetic_daily", "mg", icon="mdi:coffee"),
        _sensor("homer_daily_home_minutes", "Homer Daily Home Minutes", "synthetic_daily", "min", device_class="duration", icon="mdi:home"),
        _sensor("homer_daily_work_minutes", "Homer Daily Work Minutes", "synthetic_daily", "min", device_class="duration", icon="mdi:factory"),
        _sensor("homer_daily_car_minutes", "Homer Daily Car Minutes", "synthetic_daily", "min", device_class="duration", icon="mdi:car"),
        _sensor("homer_daily_stress_score", "Homer Daily Stress Score", "synthetic_daily", "score", icon="mdi:head-alert"),
        _sensor("homer_daily_fatigue_next_day", "Homer Daily Fatigue Next Day", "synthetic_daily", "score", icon="mdi:sleep-off"),
        _sensor("homer_daily_sleep_quality_next_day", "Homer Daily Sleep Quality Next Day", "synthetic_daily", "score", icon="mdi:sleep"),
    ]
    return entities


CATALOG = entity_catalog()
CATALOG_BY_ENTITY_ID = {entity.entity_id: entity for entity in CATALOG}


def is_homer_dataset(dataset_id: str | None) -> bool:
    """Return True for generated Homer dataset ids."""

    return dataset_id in HOMER_DATASET_IDS


def _parse_start(start: str = DEFAULT_START) -> datetime:
    parsed = datetime.fromisoformat(start)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ZoneInfo(TIMEZONE))
    return parsed.astimezone(ZoneInfo(TIMEZONE))


def _round(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-_clamp(value, -35, 35)))


def _format_state(value: Any) -> str:
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        text = f"{value:.3f}".rstrip("0").rstrip(".")
        return text if text else "0"
    return str(value)


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_hash(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:16], 16)


def _context_id(state_id: int, timestamp: datetime, seed: int) -> str:
    basis = f"{seed}:{state_id}:{timestamp.isoformat()}"
    return f"synthetic_{hashlib.sha256(basis.encode()).hexdigest()[:24]}"


def _ts(dt: datetime) -> float:
    return float(dt.timestamp())


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _day_dt(day_start: datetime, hour: float) -> datetime:
    whole = int(hour)
    minutes = int(round((hour - whole) * 60))
    return day_start + timedelta(hours=whole, minutes=minutes)


def generate_latent_days(
    *,
    days: int,
    seed: int = DEFAULT_SEED,
    start: str = DEFAULT_START,
) -> list[dict[str, Any]]:
    """Generate deterministic day-level causal variables before state expansion."""

    rng = random.Random(seed)
    start_dt = _parse_start(start)
    latent_days: list[dict[str, Any]] = []
    prior_sleep_quality = 5.8
    prior_fatigue = 6.2
    prior_bp = 132.0
    prior_late_screen = 155.0
    prior_steps = 4500
    prior_stress = 5.6

    for day_index in range(days):
        date = start_dt.date() + timedelta(days=day_index)
        day_of_week = date.weekday()
        is_weekend = int(day_of_week >= 5)
        is_workday = int(day_of_week < 5)
        seasonal = math.sin(day_index / 14.0)

        def noise(scale: float = 1.0) -> float:
            return rng.gauss(0.0, scale)

        baseline_sleep_need = 7.3
        baseline_activity_level = 5200
        baseline_stress_tendency = 5.7
        baseline_bp = 132.0
        baseline_phone_use = 245
        baseline_adherence = 0.72

        work_shift_start = 8.0 + (rng.random() - 0.5) * 0.35 if is_workday else None
        work_shift_end = 17.0 + (rng.random() - 0.5) * 0.45 if is_workday else None
        shift_load = _clamp(4.5 + is_workday * (1.5 + rng.random() * 2.2) + noise(0.6), 1, 10)
        baseline_fatigue = _clamp(0.55 * prior_fatigue + 0.38 * (10 - prior_sleep_quality) + noise(0.7), 1, 10)
        stress_level = _clamp(
            0.45 * prior_stress
            + baseline_stress_tendency * 0.35
            + is_workday * 1.2
            + shift_load * 0.18
            + baseline_fatigue * 0.18
            + noise(0.75),
            1,
            10,
        )
        sleep_nudge_prob = _sigmoid(
            -3.2
            + 0.12 * (prior_fatigue - 6.0)
            + 0.006 * (prior_late_screen - 140.0)
            - 0.08 * (prior_sleep_quality - 6.0)
            + 0.10 * is_workday
        )
        walk_nudge_prob = _sigmoid(-1.6 + 0.00025 * (5200 - prior_steps) + 0.18 * prior_fatigue + 0.08 * is_workday)
        caffeine_nudge_prob = _sigmoid(-2.0 + 0.16 * prior_fatigue + 0.10 * prior_stress + 0.10 * is_workday)
        sleep_nudge_received = int(rng.random() < sleep_nudge_prob)
        walk_nudge_received = int(rng.random() < walk_nudge_prob)
        caffeine_nudge_received = int(rng.random() < caffeine_nudge_prob)
        intervention_received = int(
            sleep_nudge_received or walk_nudge_received or caffeine_nudge_received
        )
        intervention_types = [
            name
            for name, flag in [
                ("sleep_nudge", sleep_nudge_received),
                ("walk_nudge", walk_nudge_received),
                ("caffeine_nudge", caffeine_nudge_received),
            ]
            if flag
        ]

        caffeine_mg = _clamp(
            110 + baseline_fatigue * 26 + is_workday * 55 + stress_level * 15 - caffeine_nudge_received * 65 + noise(35),
            0,
            500,
        )
        tv_minutes = _clamp(
            80
            + is_weekend * 55
            + stress_level * 8
            + baseline_fatigue * 8
            - sleep_nudge_received * 25
            + noise(38),
            30,
            320,
        )
        late_night_screen_minutes = _clamp(
            35
            + tv_minutes * 0.32
            + stress_level * 6
            + baseline_phone_use * 0.06
            - sleep_nudge_received * 35
            + noise(28),
            0,
            240,
        )
        snack_intensity = _clamp(
            2.0 + stress_level * 0.55 + baseline_fatigue * 0.35 + tv_minutes / 90 + noise(1.0),
            0,
            12,
        )
        donut_box_open_count = int(_clamp(round(snack_intensity * 0.65 + is_workday + rng.random() * 2), 0, 15))
        snack_cabinet_open_count = int(_clamp(round(snack_intensity + rng.random() * 4), 0, 25))
        refrigerator_door_opens = int(_clamp(round(5 + snack_intensity * 0.9 + rng.random() * 7), 0, 30))
        late_night_snack_events = int(
            _clamp(round((late_night_screen_minutes > 110) + (snack_intensity > 6) + rng.random() * 2), 0, 8)
        )
        nighttime_eating = int(late_night_snack_events > 1)

        active_minutes = int(
            _clamp(28 + walk_nudge_received * 24 + is_weekend * 12 - baseline_fatigue * 2.2 + noise(15), 10, 120)
        )
        steps = int(
            _clamp(
                baseline_activity_level
                + active_minutes * 52
                + walk_nudge_received * 950
                - stress_level * 95
                + is_weekend * rng.uniform(-900, 1800)
                + noise(900),
                1500,
                13000,
            )
        )
        sedentary_minutes = int(_clamp(980 - active_minutes * 2.5 + tv_minutes * 0.38 + noise(45), 500, 1100))
        car_minutes = int(_clamp(is_workday * (48 + rng.random() * 35) + is_weekend * rng.random() * 95, 0, 180))
        car_miles = _round(_clamp(car_minutes * rng.uniform(0.28, 0.62), 0.2 if car_minutes else 0, 50), 2)
        commute_minutes = int(_clamp(is_workday * (42 + rng.random() * 35), 0, 140))
        work_minutes = int(_clamp(is_workday * (480 + noise(35)), 0, 620))
        tavern_visit_minutes = int(
            _clamp((1 if rng.random() < (0.10 + 0.04 * is_workday + 0.03 * stress_level) else 0) * rng.uniform(25, 115), 0, 180)
        )
        home_minutes = int(_clamp(1440 - work_minutes - car_minutes - tavern_visit_minutes - rng.uniform(20, 120), 360, 1320))
        away_minutes = 1440 - home_minutes
        illuminance_exposure_daytime = _clamp(18000 + is_weekend * 6500 + active_minutes * 140 + seasonal * 3200 + noise(4500), 1500, 65000)

        sleep_start = 22.4 + late_night_screen_minutes / 120 + is_weekend * 0.45 + noise(0.35)
        sleep_end = 6.1 + is_weekend * 1.1 - is_workday * 0.1 + noise(0.35)
        sleep_duration_hours = _clamp(
            7.5
            - late_night_screen_minutes * 0.009
            - caffeine_mg * 0.0024
            - stress_level * 0.12
            - nighttime_eating * 0.35
            + sleep_nudge_received * 0.28
            + active_minutes * 0.006
            + illuminance_exposure_daytime / 120000
            + noise(0.45),
            3.5,
            8.5,
        )
        sleep_efficiency = _clamp(
            88 - stress_level * 1.3 - late_night_screen_minutes * 0.035 - nighttime_eating * 3 + noise(3),
            65,
            95,
        )
        awakenings = int(_clamp(round(1.5 + stress_level * 0.25 + nighttime_eating + rng.random() * 2), 0, 10))
        sleep_quality = _clamp(
            sleep_duration_hours * 0.8
            + sleep_efficiency * 0.055
            - stress_level * 0.28
            - late_night_screen_minutes * 0.006
            - nighttime_eating * 0.55
            + active_minutes * 0.015
            + noise(0.45),
            1,
            10,
        )
        fatigue_score = _clamp(
            9.5 - sleep_quality * 0.58 + stress_level * 0.25 + late_night_screen_minutes * 0.006 + noise(0.55),
            1,
            10,
        )
        mood_score = _clamp(5.5 + sleep_quality * 0.32 - stress_level * 0.27 - fatigue_score * 0.12 + noise(0.65), 1, 10)
        pain_score = _clamp(2.5 + sedentary_minutes / 650 + stress_level * 0.12 + noise(0.6), 1, 10)
        bp_systolic = _clamp(
            baseline_bp
            + stress_level * 1.8
            + caffeine_mg * 0.018
            + sedentary_minutes * 0.015
            + snack_intensity * 0.75
            - sleep_duration_hours * 1.4
            - active_minutes * 0.035
            + noise(4.5),
            110,
            165,
        )
        bp_diastolic = _clamp(bp_systolic * 0.62 + 1.5 + noise(2.5), 70, 105)
        resting_hr = _clamp(66 + stress_level * 1.4 - sleep_quality * 0.45 + caffeine_mg * 0.009 + noise(3), 62, 88)
        hrv = _clamp(55 - stress_level * 2.2 + sleep_quality * 1.7 - caffeine_mg * 0.025 + noise(4), 18, 70)
        spo2 = _clamp(97.3 + noise(0.7), 94, 99)
        skin_temperature = _clamp(36.4 + noise(0.25), 35.8, 37.4)
        calories_burned = int(_clamp(2050 + active_minutes * 9 + steps * 0.045 + noise(130), 1900, 3500))
        phone_pickups = int(_clamp(42 + late_night_screen_minutes * 0.32 + stress_level * 5 + noise(18), 30, 180))
        unlocks = int(_clamp(phone_pickups * rng.uniform(0.65, 0.9), 20, 140))
        notifications = int(_clamp(80 + is_workday * 95 + stress_level * 18 + rng.random() * 110, 50, 450))
        total_screen_time_minutes = int(_clamp(150 + tv_minutes * 0.25 + late_night_screen_minutes + stress_level * 12 + noise(45), 120, 600))
        entertainment_app_minutes = int(_clamp(35 + total_screen_time_minutes * 0.32 + is_weekend * 35 + noise(25), 30, 300))
        social_app_minutes = int(_clamp(20 + total_screen_time_minutes * 0.16 + noise(16), 0, 180))
        productivity_app_minutes = int(_clamp(is_workday * (25 + rng.random() * 55), 0, 120))
        game_app_minutes = int(_clamp(10 + is_weekend * 35 + rng.random() * 60, 0, 180))
        navigation_minutes = int(_clamp(car_minutes * 0.55 + rng.random() * 18, 0, 90))
        app_usage_minutes = int(
            _clamp(
                social_app_minutes
                + productivity_app_minutes
                + entertainment_app_minutes
                + game_app_minutes
                + navigation_minutes,
                30,
                620,
            )
        )
        texts_sent = int(_clamp(rng.randint(4, 30) + stress_level, 0, 90))
        texts_received = int(_clamp(texts_sent + rng.randint(5, 38), 0, 140))
        calls_made = int(_clamp(rng.random() * 5 + is_workday, 0, 12))
        calls_received = int(_clamp(rng.random() * 7 + is_workday, 0, 16))
        call_duration_minutes = _round(_clamp((calls_made + calls_received) * rng.uniform(3, 12), 0, 180), 1)
        work_calendar_events = int(_clamp(is_workday * (2 + rng.random() * 5), 0, 12))
        meeting_minutes = int(_clamp(is_workday * (30 + work_calendar_events * rng.uniform(18, 42)), 0, 520))
        work_stress_proxy = _round(_clamp(stress_level + shift_load * 0.22 + noise(0.5), 1, 10))
        medicine_cabinet_opens = int(rng.random() < baseline_adherence + 0.08 * caffeine_nudge_received)
        restaurant_visit_count = int(rng.random() < (0.16 + is_weekend * 0.15 + stress_level * 0.015))
        fast_food_visit_count = int(rng.random() < (0.12 + stress_level * 0.018 + is_workday * 0.04))
        soda_intake_count = int(_clamp(round(caffeine_mg / 95 + rng.random() * 2), 0, 7))
        kettle_uses = int(_clamp(round(caffeine_mg / 180 + rng.random() * 2), 0, 6))
        microwave_uses = int(_clamp(round(1 + nighttime_eating + rng.random() * 3), 0, 8))
        car_trips = int(_clamp((2 if is_workday else 0) + (1 if car_minutes > 0 else 0) + rng.random() * 2, 0, 8))
        hard_brakes = int(_clamp(rng.random() * max(car_trips, 1) * 1.5, 0, 10))
        idle_minutes = int(_clamp(car_minutes * rng.uniform(0.08, 0.22), 0, 45))
        significant_location_changes = int(_clamp(car_trips + restaurant_visit_count + fast_food_visit_count + (tavern_visit_minutes > 0), 0, 28))
        avg_living_room_illuminance = _clamp(60 + tv_minutes * 0.7 + noise(45), 0, 900)
        avg_bedroom_illuminance = _clamp(18 + awakenings * 7 + noise(14), 0, 500)
        avg_bedroom_temperature = _clamp(20.2 + seasonal + noise(0.7), 18, 25)
        avg_indoor_co2 = _clamp(620 + home_minutes * 0.32 + tv_minutes * 0.45 + noise(110), 400, 2000)
        max_kitchen_pm25 = _clamp(8 + microwave_uses * 5 + snack_cabinet_open_count * 1.2 + noise(8), 1, 80)
        outcome_sleep_quality = _clamp(sleep_quality + noise(0.25), 1, 10)
        outcome_next_day_fatigue = _clamp(
            8.8 - outcome_sleep_quality * 0.52 + stress_level * 0.22 + late_night_screen_minutes * 0.004 - walk_nudge_received * 0.18 + noise(0.55),
            1,
            10,
        )
        outcome_mood_next_day = _clamp(mood_score + outcome_sleep_quality * 0.10 - outcome_next_day_fatigue * 0.08 + noise(0.45), 1, 10)
        outcome_bp_next_day = _clamp(bp_systolic + stress_level * 0.25 + caffeine_mg * 0.006 - sleep_duration_hours * 0.55 + noise(3.5), 110, 165)

        latent = {
            "date": date.isoformat(),
            "day_index": day_index,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "is_workday": is_workday,
            "subject_id": PROFILE["subject_id"],
            "synthetic_profile": PROFILE["profile_type"],
            "baseline_sleep_need": baseline_sleep_need,
            "baseline_activity_level": baseline_activity_level,
            "baseline_stress_tendency": baseline_stress_tendency,
            "baseline_bp": baseline_bp,
            "baseline_phone_use": baseline_phone_use,
            "baseline_adherence": baseline_adherence,
            "work_shift_start": work_shift_start,
            "work_shift_end": work_shift_end,
            "sleep_start": _round(sleep_start),
            "sleep_end": _round(sleep_end),
            "sleep_duration_hours": _round(sleep_duration_hours),
            "sleep_efficiency": _round(sleep_efficiency),
            "awakenings": awakenings,
            "baseline_fatigue": _round(baseline_fatigue),
            "stress_level": _round(stress_level),
            "mood": _round(mood_score),
            "mood_score": _round(mood_score),
            "fatigue_score": _round(fatigue_score),
            "caffeine_mg": _round(caffeine_mg),
            "snack_intensity": _round(snack_intensity),
            "tv_minutes": int(round(tv_minutes)),
            "streaming_minutes": int(round(tv_minutes * rng.uniform(0.72, 0.94))),
            "late_night_screen_minutes": _round(late_night_screen_minutes),
            "steps": steps,
            "active_minutes": active_minutes,
            "sedentary_minutes": sedentary_minutes,
            "home_minutes": home_minutes,
            "away_minutes": away_minutes,
            "work_minutes": work_minutes,
            "car_minutes": car_minutes,
            "tavern_visit_minutes": tavern_visit_minutes,
            "illuminance_exposure_daytime": _round(illuminance_exposure_daytime),
            "sleep_nudge_received": sleep_nudge_received,
            "walk_nudge_received": walk_nudge_received,
            "caffeine_nudge_received": caffeine_nudge_received,
            "intervention_received": intervention_received,
            "intervention_type": "+".join(intervention_types) if intervention_types else "none",
            "outcome_sleep_quality": _round(outcome_sleep_quality),
            "outcome_next_day_fatigue": _round(outcome_next_day_fatigue),
            "outcome_mood_next_day": _round(outcome_mood_next_day),
            "outcome_bp_next_day": _round(outcome_bp_next_day),
            "sleep_quality": _round(sleep_quality),
            "prior_sleep_quality": _round(prior_sleep_quality),
            "prior_fatigue": _round(prior_fatigue),
            "prior_bp": _round(prior_bp),
            "prior_late_screen_minutes": _round(prior_late_screen),
            "prior_steps": prior_steps,
            "prior_stress_score": _round(prior_stress),
            "wearable_device_worn_hours": _round(_clamp(18 + rng.random() * 5 - is_weekend * rng.random() * 3, 10, 24), 2),
            "heart_rate_mean": _round(_clamp(resting_hr + 12 + stress_level * 1.5 + active_minutes * 0.08, 55, 115), 1),
            "heart_rate_max": _round(_clamp(resting_hr + 35 + active_minutes * 0.18 + rng.random() * 18, 75, 135), 1),
            "resting_heart_rate": _round(resting_hr, 1),
            "heart_rate_variability_ms": _round(hrv, 1),
            "calories_burned": calories_burned,
            "spo2_percent": _round(spo2, 1),
            "skin_temperature_c": _round(skin_temperature, 2),
            "phone_pickups": phone_pickups,
            "unlocks": unlocks,
            "notifications": notifications,
            "texts_sent": texts_sent,
            "texts_received": texts_received,
            "calls_made": calls_made,
            "calls_received": calls_received,
            "call_duration_minutes": call_duration_minutes,
            "app_usage_minutes": app_usage_minutes,
            "total_screen_time_minutes": total_screen_time_minutes,
            "social_app_minutes": social_app_minutes,
            "productivity_app_minutes": productivity_app_minutes,
            "entertainment_app_minutes": entertainment_app_minutes,
            "game_app_minutes": game_app_minutes,
            "navigation_minutes": navigation_minutes,
            "living_room_motion_events": int(_clamp(5 + tv_minutes / 35 + rng.random() * 10, 0, 50)),
            "kitchen_motion_events": int(_clamp(6 + snack_cabinet_open_count + rng.random() * 12, 0, 70)),
            "bedroom_motion_events": int(_clamp(2 + awakenings + rng.random() * 6, 0, 30)),
            "front_door_opens": int(_clamp(2 + car_trips * 2 + rng.random() * 3, 0, 18)),
            "refrigerator_door_opens": refrigerator_door_opens,
            "pantry_door_opens": snack_cabinet_open_count,
            "medicine_cabinet_opens": medicine_cabinet_opens,
            "kettle_uses": kettle_uses,
            "microwave_uses": microwave_uses,
            "avg_living_room_illuminance": _round(avg_living_room_illuminance),
            "avg_bedroom_illuminance": _round(avg_bedroom_illuminance),
            "avg_daytime_outdoor_illuminance": _round(illuminance_exposure_daytime),
            "avg_bedroom_temperature": _round(avg_bedroom_temperature, 2),
            "avg_indoor_co2": _round(avg_indoor_co2),
            "max_kitchen_pm25": _round(max_kitchen_pm25),
            "car_trips": car_trips,
            "car_miles": car_miles,
            "hard_brakes": hard_brakes,
            "idle_minutes": idle_minutes,
            "commute_minutes": commute_minutes,
            "distance_traveled_miles": _round(car_miles + tavern_visit_minutes * 0.05 + rng.random() * 3, 2),
            "significant_location_changes": significant_location_changes,
            "soda_intake_count": soda_intake_count,
            "donut_box_open_count": donut_box_open_count,
            "snack_cabinet_open_count": snack_cabinet_open_count,
            "late_night_snack_events": late_night_snack_events,
            "nighttime_eating": nighttime_eating,
            "restaurant_visit_count": restaurant_visit_count,
            "fast_food_visit_count": fast_food_visit_count,
            "work_calendar_events": work_calendar_events,
            "meeting_minutes": meeting_minutes,
            "work_stress_proxy": work_stress_proxy,
            "shift_load": _round(shift_load),
            "stress_score": _round(stress_level),
            "pain_score": _round(pain_score),
            "blood_pressure_systolic": _round(bp_systolic),
            "blood_pressure_diastolic": _round(bp_diastolic),
        }
        latent_days.append(latent)
        prior_sleep_quality = outcome_sleep_quality
        prior_fatigue = outcome_next_day_fatigue
        prior_bp = outcome_bp_next_day
        prior_late_screen = late_night_screen_minutes
        prior_steps = steps
        prior_stress = stress_level
    return latent_days


class StateBuilder:
    """Build normalized Home Assistant Recorder-style state tables."""

    def __init__(self, *, seed: int):
        self.seed = seed
        self.states: list[dict[str, Any]] = []
        self.state_attributes: list[dict[str, Any]] = []
        self.attribute_ids: dict[str, int] = {}
        self.previous_state_by_entity: dict[str, str] = {}
        self.previous_state_id_by_entity: dict[str, int] = {}
        self.first_seen_by_entity: dict[str, float] = {}
        self.last_seen_by_entity: dict[str, float] = {}
        self.metadata_id_by_entity = {
            entity.entity_id: index + 1 for index, entity in enumerate(sorted(CATALOG, key=lambda e: e.entity_id))
        }

    def attributes_id(self, spec: EntitySpec) -> int:
        canonical = _canonical_json(spec.attributes())
        if canonical not in self.attribute_ids:
            attr_id = len(self.attribute_ids) + 1
            self.attribute_ids[canonical] = attr_id
            self.state_attributes.append(
                {
                    "attributes_id": attr_id,
                    "hash": _stable_hash(canonical),
                    "shared_attrs": canonical,
                }
            )
        return self.attribute_ids[canonical]

    def add(self, entity_id: str, timestamp: datetime, value: Any) -> None:
        spec = CATALOG_BY_ENTITY_ID[entity_id]
        state = _format_state(value)
        previous = self.previous_state_by_entity.get(entity_id)
        state_id = len(self.states) + 1
        timestamp_value = _ts(timestamp)
        self.first_seen_by_entity.setdefault(entity_id, timestamp_value)
        self.last_seen_by_entity[entity_id] = timestamp_value
        self.states.append(
            {
                "state_id": state_id,
                "metadata_id": self.metadata_id_by_entity[entity_id],
                "entity_id": entity_id,
                "state": state,
                "attributes_id": self.attributes_id(spec),
                "last_changed_ts": timestamp_value if previous != state else None,
                "last_updated_ts": timestamp_value,
                "last_reported_ts": timestamp_value,
                "old_state_id": self.previous_state_id_by_entity.get(entity_id),
                "context_id_bin": _context_id(state_id, timestamp, self.seed),
                "context_user_id_bin": None,
                "context_parent_id_bin": None,
                "origin_idx": 0,
                "iso_timestamp": _iso(timestamp),
                "date": timestamp.date().isoformat(),
                "source": spec.source,
                "domain": spec.domain,
                "unit": spec.unit,
            }
        )
        self.previous_state_by_entity[entity_id] = state
        self.previous_state_id_by_entity[entity_id] = state_id

    def metadata(self) -> list[dict[str, Any]]:
        rows = []
        for entity in sorted(CATALOG, key=lambda e: e.entity_id):
            rows.append(
                {
                    "metadata_id": self.metadata_id_by_entity[entity.entity_id],
                    "entity_id": entity.entity_id,
                    "domain": entity.domain,
                    "object_id": entity.object_id,
                    "first_seen_ts": self.first_seen_by_entity.get(entity.entity_id),
                    "last_seen_ts": self.last_seen_by_entity.get(entity.entity_id),
                }
            )
        return rows


def _period_minutes(density: str, base: int) -> int:
    if density == "test":
        return max(base * 4, 30)
    if density == "high":
        return max(3, int(base * 0.72))
    return base


def _add_numeric_series(
    builder: StateBuilder,
    entity_id: str,
    day_start: datetime,
    *,
    start_hour: float,
    end_hour: float,
    every_minutes: int,
    value_func: Any,
) -> None:
    current = _day_dt(day_start, start_hour)
    end = _day_dt(day_start, end_hour)
    while current <= end:
        hour = (current - day_start).total_seconds() / 3600
        builder.add(entity_id, current, value_func(hour))
        current += timedelta(minutes=every_minutes)


def _add_binary_pulse(builder: StateBuilder, entity_id: str, start: datetime, minutes: int) -> None:
    builder.add(entity_id, start, "on")
    builder.add(entity_id, start + timedelta(minutes=max(1, minutes)), "off")


def _outdoor_lux(hour: float, day_index: int) -> float:
    daylight = math.sin(math.pi * _clamp((hour - 6.2) / 11.2, 0, 1))
    seasonal = 0.82 + 0.18 * math.sin(day_index / 18)
    return _clamp(100000 * daylight * seasonal, 0, 100000)


def _zone_at_hour(day: dict[str, Any], hour: float) -> str:
    if hour < 6.8:
        return "home"
    if day["is_workday"] and 7.1 <= hour <= 7.9:
        return "not_home"
    if day["is_workday"] and 8.0 <= hour <= 16.9:
        return "work"
    if day["is_workday"] and 17.0 <= hour <= 17.8:
        return "not_home"
    if 18.1 <= hour <= 18.9 and day["fast_food_visit_count"]:
        return "kwik_e_mart_area"
    if 18.3 <= hour <= 20.8 and day["tavern_visit_minutes"] > 0:
        return "moes_area"
    return "home"


def _generate_day_states(
    builder: StateBuilder,
    day: dict[str, Any],
    *,
    day_start: datetime,
    density: str,
    rng: random.Random,
    odometer_start: float,
    fuel_start: float,
) -> tuple[float, float]:
    hr_interval = _period_minutes(density, 10)
    env_interval = _period_minutes(density, 15)
    phone_interval = _period_minutes(density, 30)
    appliance_interval = _period_minutes(density, 20)
    car_interval = _period_minutes(density, 3)
    day_index = int(day["day_index"])

    builder.add("binary_sensor.homer_watch_worn", _day_dt(day_start, 6.5), "on")
    builder.add("binary_sensor.homer_watch_worn", _day_dt(day_start, 23.2), "off")
    builder.add("sensor.homer_watch_sleep_duration", _day_dt(day_start, 7.1), day["sleep_duration_hours"])
    builder.add("sensor.homer_watch_sleep_efficiency", _day_dt(day_start, 7.1), day["sleep_efficiency"])
    builder.add("sensor.homer_watch_sleep_score", _day_dt(day_start, 7.1), day["sleep_quality"])
    builder.add("sensor.homer_watch_hrv", _day_dt(day_start, 7.05), day["heart_rate_variability_ms"])
    builder.add("sensor.homer_watch_resting_heart_rate", _day_dt(day_start, 7.05), day["resting_heart_rate"])
    builder.add("sensor.homer_watch_spo2", _day_dt(day_start, 7.1), day["spo2_percent"])
    builder.add("sensor.homer_watch_skin_temperature", _day_dt(day_start, 7.1), day["skin_temperature_c"])
    builder.add("sensor.homer_watch_calories_burned", _day_dt(day_start, 23.58), day["calories_burned"])
    builder.add("sensor.homer_watch_stand_hours", _day_dt(day_start, 23.58), _clamp(day["active_minutes"] / 12, 1, 12))
    builder.add("sensor.homer_watch_active_minutes", _day_dt(day_start, 23.58), day["active_minutes"])
    builder.add("sensor.homer_watch_sedentary_minutes", _day_dt(day_start, 23.58), day["sedentary_minutes"])

    def hr_value(hour: float) -> float:
        activity_boost = 16 if 7 <= hour <= 9 or 17 <= hour <= 19 else 0
        tv_boost = 5 if 19 <= hour <= 23 else 0
        return _round(_clamp(day["resting_heart_rate"] + activity_boost + tv_boost + rng.gauss(0, 7), 55, 135), 1)

    _add_numeric_series(
        builder,
        "sensor.homer_watch_heart_rate",
        day_start,
        start_hour=6.6,
        end_hour=23.0,
        every_minutes=hr_interval,
        value_func=hr_value,
    )

    current_steps = 0
    step_current = _day_dt(day_start, 6.8)
    step_end = _day_dt(day_start, 23.2)
    step_interval = _period_minutes(density, 30)
    while step_current <= step_end:
        hour = (step_current - day_start).total_seconds() / 3600
        pace = 1.0
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            pace = 1.7
        elif 19 <= hour <= 23:
            pace = 0.35
        increment = max(0, int((day["steps"] / 32) * pace * rng.uniform(0.2, 1.8)))
        current_steps = min(int(day["steps"]), current_steps + increment)
        builder.add("sensor.homer_watch_steps", step_current, current_steps)
        step_current += timedelta(minutes=step_interval)
    builder.add("sensor.homer_watch_steps", _day_dt(day_start, 23.55), day["steps"])

    for hour in [0, 1, 2, 3, 4, 5, 6, 7, 12, 18, 23]:
        battery = _clamp(100 - hour * 2.5 + (20 if hour < 6 else 0) + rng.gauss(0, 2), 0, 100)
        builder.add("sensor.homer_watch_battery_level", _day_dt(day_start, hour + 0.05), _round(battery, 1))

    for hour in range(0, 24):
        if hour % max(1, phone_interval // 30) == 0:
            battery = _clamp(95 - hour * 3.1 + (35 if hour < 6 else 0) + rng.gauss(0, 2.5), 0, 100)
            builder.add("sensor.homer_phone_battery_level", _day_dt(day_start, hour + 0.08), _round(battery, 1))
            builder.add("binary_sensor.homer_phone_charging", _day_dt(day_start, hour + 0.09), "on" if hour < 6 or hour > 22 else "off")
    for hour in [7.5, 12.2, 18.0, 21.7, 23.4]:
        fraction = _clamp(hour / 23.5, 0, 1)
        builder.add("sensor.homer_phone_screen_time", _day_dt(day_start, hour), int(day["total_screen_time_minutes"] * fraction))
        builder.add("sensor.homer_phone_pickups", _day_dt(day_start, hour + 0.02), int(day["phone_pickups"] * fraction))
        builder.add("sensor.homer_phone_unlocks", _day_dt(day_start, hour + 0.03), int(day["unlocks"] * fraction))
        builder.add("sensor.homer_phone_notifications", _day_dt(day_start, hour + 0.04), int(day["notifications"] * fraction))
    for entity_id, key in [
        ("sensor.homer_phone_calls_made", "calls_made"),
        ("sensor.homer_phone_calls_received", "calls_received"),
        ("sensor.homer_phone_call_duration", "call_duration_minutes"),
        ("sensor.homer_phone_texts_sent", "texts_sent"),
        ("sensor.homer_phone_texts_received", "texts_received"),
        ("sensor.homer_phone_social_app_minutes", "social_app_minutes"),
        ("sensor.homer_phone_entertainment_app_minutes", "entertainment_app_minutes"),
        ("sensor.homer_phone_navigation_minutes", "navigation_minutes"),
        ("sensor.homer_phone_game_minutes", "game_app_minutes"),
        ("sensor.homer_phone_productivity_minutes", "productivity_app_minutes"),
    ]:
        builder.add(entity_id, _day_dt(day_start, 23.5), day[key])
    for hour in [0.2, 7.0, 8.0, 12.0, 17.1, 18.4, 21.0, 23.6]:
        zone = _zone_at_hour(day, hour)
        builder.add("device_tracker.homer_phone", _day_dt(day_start, hour), zone)
        builder.add("sensor.homer_phone_wifi_ssid", _day_dt(day_start, hour + 0.01), "springfield_home_synthetic_wifi" if zone == "home" else "not_connected")
        builder.add("sensor.homer_phone_focus_mode", _day_dt(day_start, hour + 0.02), "sleep" if hour < 6.5 or hour > 23 else "off")

    for hour in [7.0, 7.35, 17.85, 18.3, 22.4]:
        _add_binary_pulse(builder, "binary_sensor.front_door_contact", _day_dt(day_start, hour), 2)
    for hour in [7.2, 18.0, 19.1, 21.7]:
        _add_binary_pulse(builder, "binary_sensor.kitchen_motion", _day_dt(day_start, hour), 8)
    for hour in [6.7, 22.7, 2.1] if day["awakenings"] else [6.7, 22.7]:
        _add_binary_pulse(builder, "binary_sensor.bedroom_motion", _day_dt(day_start, hour), 6)
    for offset in range(int(day["living_room_motion_events"] // 4) + 1):
        _add_binary_pulse(builder, "binary_sensor.living_room_motion", _day_dt(day_start, 18.4 + offset * 0.55), 7)
    _add_binary_pulse(builder, "binary_sensor.garage_motion", _day_dt(day_start, 7.45), 5)
    if day["is_workday"]:
        _add_binary_pulse(builder, "binary_sensor.garage_motion", _day_dt(day_start, 17.55), 5)
    for idx in range(int(day["refrigerator_door_opens"])):
        hour = 7 + (idx % 5) * 2.8 + rng.random() * 0.2
        _add_binary_pulse(builder, "binary_sensor.refrigerator_door_contact", _day_dt(day_start, min(hour, 23.2)), 1)
    for idx in range(int(day["pantry_door_opens"])):
        hour = 15 + (idx % 8) * 0.9 + rng.random() * 0.2
        _add_binary_pulse(builder, "binary_sensor.pantry_door_contact", _day_dt(day_start, min(hour, 23.4)), 1)
    if day["medicine_cabinet_opens"]:
        _add_binary_pulse(builder, "binary_sensor.medicine_cabinet_contact", _day_dt(day_start, 8.05), 1)
    builder.add("sensor.home_occupancy_count", _day_dt(day_start, 8), 3 if day["is_weekend"] else 1)
    builder.add("sensor.homer_home_minutes", _day_dt(day_start, 23.55), day["home_minutes"])
    builder.add("sensor.homer_away_minutes", _day_dt(day_start, 23.55), day["away_minutes"])
    builder.add("sensor.homer_room_presence", _day_dt(day_start, 20.0), "tv_room")

    for hour_step in range(0, 24 * 60, env_interval):
        hour = hour_step / 60
        outdoor = _outdoor_lux(hour, day_index)
        tv_on = 18.8 <= hour <= 18.8 + day["tv_minutes"] / 60
        kitchen_active = 6.8 <= hour <= 7.6 or 18.0 <= hour <= 19.3 or 21.4 <= hour <= 22.6
        bedroom_night = hour < 6.3 or hour > 22.5
        builder.add("sensor.outdoor_illuminance", day_start + timedelta(minutes=hour_step), _round(outdoor, 1))
        builder.add("sensor.living_room_illuminance", day_start + timedelta(minutes=hour_step + 1), _round(_clamp(15 + outdoor * 0.002 + (180 if tv_on else 0) + rng.gauss(0, 15), 0, 900), 1))
        builder.add("sensor.kitchen_illuminance", day_start + timedelta(minutes=hour_step + 2), _round(_clamp(20 + outdoor * 0.0025 + (260 if kitchen_active else 0) + rng.gauss(0, 20), 0, 900), 1))
        builder.add("sensor.bedroom_illuminance", day_start + timedelta(minutes=hour_step + 3), _round(_clamp((8 if bedroom_night else 60) + outdoor * 0.001 + rng.gauss(0, 10), 0, 500), 1))
        builder.add("sensor.garage_illuminance", day_start + timedelta(minutes=hour_step + 4), _round(_clamp(12 + outdoor * 0.0008 + rng.gauss(0, 8), 0, 400), 1))
        outdoor_temp = 6 + 7 * math.sin((hour - 7) / 24 * 2 * math.pi) + 6 * math.sin(day_index / 17)
        builder.add("sensor.outdoor_temperature", day_start + timedelta(minutes=hour_step + 5), _round(_clamp(outdoor_temp, -8, 35), 2))
        builder.add("sensor.living_room_temperature", day_start + timedelta(minutes=hour_step + 6), _round(_clamp(21 + rng.gauss(0, 0.5), 18, 25), 2))
        builder.add("sensor.bedroom_temperature", day_start + timedelta(minutes=hour_step + 7), _round(_clamp(day["avg_bedroom_temperature"] + rng.gauss(0, 0.4), 18, 25), 2))
        builder.add("sensor.kitchen_temperature", day_start + timedelta(minutes=hour_step + 8), _round(_clamp(21 + (1.5 if kitchen_active else 0) + rng.gauss(0, 0.6), 18, 27), 2))
        builder.add("sensor.living_room_humidity", day_start + timedelta(minutes=hour_step + 9), _round(_clamp(42 + rng.gauss(0, 5), 25, 65), 1))
        builder.add("sensor.bedroom_humidity", day_start + timedelta(minutes=hour_step + 10), _round(_clamp(44 + rng.gauss(0, 5), 25, 65), 1))
        builder.add("sensor.indoor_co2", day_start + timedelta(minutes=hour_step + 11), _round(_clamp(day["avg_indoor_co2"] + rng.gauss(0, 80), 400, 2000), 1))
        builder.add("sensor.kitchen_pm25", day_start + timedelta(minutes=hour_step + 12), _round(_clamp(6 + (day["max_kitchen_pm25"] if kitchen_active else 0) * rng.random() + rng.gauss(0, 4), 1, 80), 1))
    builder.add("weather.springfield_synthetic", _day_dt(day_start, 12.0), "partlycloudy")

    tv_start = _day_dt(day_start, 18.75)
    tv_end = tv_start + timedelta(minutes=int(day["tv_minutes"]))
    builder.add("switch.living_room_tv", tv_start, "on")
    builder.add("media_player.living_room_tv", tv_start + timedelta(minutes=1), "playing")
    current = tv_start
    while current <= tv_end:
        builder.add("sensor.living_room_tv_power", current, _round(_clamp(105 + rng.gauss(0, 18), 35, 210), 1))
        builder.add("sensor.living_room_tv_energy", current, _round(day["tv_minutes"] / 60 * 0.12, 3))
        builder.add("binary_sensor.tv_room_occupancy", current, "on")
        current += timedelta(minutes=appliance_interval)
    builder.add("media_player.living_room_tv", tv_end, "off")
    builder.add("switch.living_room_tv", tv_end, "off")
    builder.add("binary_sensor.tv_room_occupancy", tv_end, "off")
    builder.add("sensor.streaming_minutes", _day_dt(day_start, 23.4), day["streaming_minutes"])

    for idx in range(int(day["kettle_uses"])):
        start = _day_dt(day_start, 6.8 + idx * 0.18)
        builder.add("switch.kitchen_kettle", start, "on")
        builder.add("sensor.kettle_power", start, 1450 + rng.random() * 350)
        builder.add("switch.kitchen_kettle", start + timedelta(minutes=5), "off")
        builder.add("sensor.kettle_power", start + timedelta(minutes=5), 0)
    builder.add("sensor.kettle_energy", _day_dt(day_start, 23.5), _round(day["kettle_uses"] * 0.11, 3))
    for idx in range(int(day["microwave_uses"])):
        start = _day_dt(day_start, 18.4 + idx * 0.8)
        builder.add("switch.microwave", start, "on")
        builder.add("sensor.microwave_power", start, 900 + rng.random() * 450)
        builder.add("switch.microwave", start + timedelta(minutes=4), "off")
        builder.add("sensor.microwave_power", start + timedelta(minutes=4), 0)
    for hour_step in range(0, 24 * 60, appliance_interval):
        hour = hour_step / 60
        fridge_cycle = 85 if int(hour * 2) % 3 == 0 else 15
        builder.add("sensor.refrigerator_power", day_start + timedelta(minutes=hour_step), fridge_cycle + rng.random() * 25)
        builder.add("sensor.washing_machine_power", day_start + timedelta(minutes=hour_step + 1), 500 + rng.random() * 250 if day["is_weekend"] and 10 <= hour <= 11 else 0)
        builder.add("sensor.dishwasher_power", day_start + timedelta(minutes=hour_step + 2), 700 + rng.random() * 300 if 20 <= hour <= 21 and rng.random() < 0.15 else 0)
        builder.add("sensor.bedroom_lamp_power", day_start + timedelta(minutes=hour_step + 3), 8 if hour > 22 or hour < 6 else 0)
    builder.add("switch.garage_freezer", _day_dt(day_start, 0.1), "on")
    for entity_id, hour in [
        ("light.kitchen_lights", 18.1),
        ("light.living_room_lights", 18.6),
        ("light.bedroom_lights", 22.2),
    ]:
        builder.add(entity_id, _day_dt(day_start, hour), "on")
        builder.add(entity_id, _day_dt(day_start, min(hour + 3.2, 23.8)), "off")

    if day["car_minutes"] > 0:
        trip_windows = [(7.25, 7.25 + min(day["commute_minutes"] / 60 / 2, 0.75))]
        if day["is_workday"]:
            trip_windows.append((17.05, 17.05 + min(day["commute_minutes"] / 60 / 2, 0.75)))
        if day["tavern_visit_minutes"] > 0:
            trip_windows.append((18.0, 18.25))
            trip_windows.append((20.0, 20.25))
        for start_hour, end_hour in trip_windows:
            start = _day_dt(day_start, start_hour)
            end = _day_dt(day_start, end_hour)
            builder.add("binary_sensor.homer_car_driver_door", start - timedelta(minutes=1), "on")
            builder.add("binary_sensor.homer_car_driver_door", start, "off")
            builder.add("binary_sensor.homer_car_ignition", start, "on")
            builder.add("device_tracker.homer_car", start, "not_home")
            current = start
            while current <= end:
                builder.add("sensor.homer_car_speed", current, _round(_clamp(28 + rng.gauss(0, 14), 1, 75), 1))
                current += timedelta(minutes=car_interval)
            builder.add("sensor.homer_car_speed", end, 0)
            builder.add("binary_sensor.homer_car_ignition", end, "off")
            builder.add("device_tracker.homer_car", end, _zone_at_hour(day, end_hour))
    odometer_end = odometer_start + day["car_miles"]
    fuel_end = fuel_start - day["car_miles"] * 0.55
    if fuel_end < 12:
        fuel_end = 92 - rng.random() * 8
    builder.add("sensor.homer_car_odometer", _day_dt(day_start, 23.45), _round(odometer_end, 1))
    builder.add("sensor.homer_car_fuel_level", _day_dt(day_start, 23.45), _round(_clamp(fuel_end, 5, 100), 1))
    builder.add("sensor.homer_car_range", _day_dt(day_start, 23.45), _round(_clamp(fuel_end * 3.1, 10, 330), 1))
    builder.add("sensor.homer_car_engine_runtime", _day_dt(day_start, 23.45), day["car_minutes"])
    builder.add("sensor.homer_car_trip_distance", _day_dt(day_start, 23.45), day["car_miles"])
    builder.add("sensor.homer_car_trip_duration", _day_dt(day_start, 23.45), day["car_minutes"])
    builder.add("sensor.homer_car_hard_brakes", _day_dt(day_start, 23.45), day["hard_brakes"])
    builder.add("sensor.homer_car_idle_minutes", _day_dt(day_start, 23.45), day["idle_minutes"])
    builder.add("sensor.homer_car_cabin_temperature", _day_dt(day_start, 17.0), _round(_clamp(20 + rng.gauss(0, 5), 0, 42), 1))

    if day["is_workday"]:
        builder.add("calendar.homer_work_shift", _day_dt(day_start, day["work_shift_start"]), "on")
        builder.add("binary_sensor.homer_at_work", _day_dt(day_start, day["work_shift_start"]), "on")
        builder.add("calendar.homer_work_shift", _day_dt(day_start, day["work_shift_end"]), "off")
        builder.add("binary_sensor.homer_at_work", _day_dt(day_start, day["work_shift_end"]), "off")
    else:
        builder.add("calendar.homer_work_shift", _day_dt(day_start, 9), "off")
        builder.add("binary_sensor.homer_at_work", _day_dt(day_start, 9), "off")
    builder.add("sensor.homer_work_calendar_events", _day_dt(day_start, 17.1), day["work_calendar_events"])
    builder.add("sensor.homer_meeting_minutes", _day_dt(day_start, 17.1), day["meeting_minutes"])
    builder.add("sensor.homer_work_stress_proxy", _day_dt(day_start, 17.2), day["work_stress_proxy"])
    builder.add("sensor.power_plant_noise_level", _day_dt(day_start, 12.0), _round(62 + day["shift_load"] * 4 + rng.gauss(0, 5), 1))
    builder.add("sensor.power_plant_shift_load", _day_dt(day_start, 12.0), day["shift_load"])

    for entity_id, value in [
        ("sensor.donut_box_open_count", day["donut_box_open_count"]),
        ("sensor.snack_cabinet_open_count", day["snack_cabinet_open_count"]),
        ("sensor.refrigerator_open_count", day["refrigerator_door_opens"]),
        ("sensor.caffeine_mg_estimate", day["caffeine_mg"]),
        ("sensor.soda_intake_count", day["soda_intake_count"]),
        ("sensor.late_night_snack_events", day["late_night_snack_events"]),
        ("sensor.restaurant_visit_count", day["restaurant_visit_count"]),
        ("sensor.tavern_visit_minutes", day["tavern_visit_minutes"]),
        ("sensor.fast_food_visit_count", day["fast_food_visit_count"]),
    ]:
        builder.add(entity_id, _day_dt(day_start, 23.25), value)
    if day["donut_box_open_count"]:
        _add_binary_pulse(builder, "binary_sensor.donut_box_contact", _day_dt(day_start, 8.6), 2)
    builder.add("binary_sensor.nighttime_eating", _day_dt(day_start, 23.0), "on" if day["nighttime_eating"] else "off")

    for entity_id, value, hour in [
        ("sensor.homer_mood_score", day["mood_score"], 21.4),
        ("sensor.homer_stress_score", day["stress_score"], 21.4),
        ("sensor.homer_fatigue_score", day["fatigue_score"], 7.2),
        ("sensor.homer_pain_score", day["pain_score"], 21.4),
        ("sensor.homer_blood_pressure_systolic", day["blood_pressure_systolic"], 7.3),
        ("sensor.homer_blood_pressure_diastolic", day["blood_pressure_diastolic"], 7.3),
        ("sensor.homer_weight", 239 + rng.gauss(0, 1.2), 7.0),
        ("sensor.homer_sleep_quality_reported", day["sleep_quality"], 7.2),
    ]:
        builder.add(entity_id, _day_dt(day_start, hour), value)
    for entity_id, flag in [
        ("input_boolean.homer_received_sleep_nudge", day["sleep_nudge_received"]),
        ("input_boolean.homer_received_walk_nudge", day["walk_nudge_received"]),
        ("input_boolean.homer_received_caffeine_nudge", day["caffeine_nudge_received"]),
    ]:
        builder.add(entity_id, _day_dt(day_start, 18.0), "on" if flag else "off")

    daily_map = {
        "sensor.homer_daily_steps": day["steps"],
        "sensor.homer_daily_sleep_hours": day["sleep_duration_hours"],
        "sensor.homer_daily_late_screen_minutes": day["late_night_screen_minutes"],
        "sensor.homer_daily_tv_minutes": day["tv_minutes"],
        "sensor.homer_daily_caffeine_mg": day["caffeine_mg"],
        "sensor.homer_daily_home_minutes": day["home_minutes"],
        "sensor.homer_daily_work_minutes": day["work_minutes"],
        "sensor.homer_daily_car_minutes": day["car_minutes"],
        "sensor.homer_daily_stress_score": day["stress_score"],
        "sensor.homer_daily_fatigue_next_day": day["outcome_next_day_fatigue"],
        "sensor.homer_daily_sleep_quality_next_day": day["outcome_sleep_quality"],
    }
    for entity_id, value in daily_map.items():
        builder.add(entity_id, _day_dt(day_start, 23.92), value)
    return odometer_end, _clamp(fuel_end, 5, 100)


def _daily_rows_from_latent(latent_days: list[dict[str, Any]]) -> list[dict[str, Any]]:
    columns = [
        "date",
        "day_index",
        "day_of_week",
        "is_weekend",
        "is_workday",
        "subject_id",
        "synthetic_profile",
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
        "heart_rate_mean",
        "heart_rate_max",
        "resting_heart_rate",
        "heart_rate_variability_ms",
        "calories_burned",
        "spo2_percent",
        "skin_temperature_c",
        "steps",
        "sedentary_minutes",
        "active_minutes",
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
        "entertainment_app_minutes",
        "game_app_minutes",
        "navigation_minutes",
        "late_night_screen_minutes",
        "home_minutes",
        "away_minutes",
        "work_minutes",
        "living_room_motion_events",
        "kitchen_motion_events",
        "bedroom_motion_events",
        "front_door_opens",
        "refrigerator_door_opens",
        "pantry_door_opens",
        "medicine_cabinet_opens",
        "tv_minutes",
        "streaming_minutes",
        "kettle_uses",
        "microwave_uses",
        "avg_living_room_illuminance",
        "avg_bedroom_illuminance",
        "avg_daytime_outdoor_illuminance",
        "avg_bedroom_temperature",
        "avg_indoor_co2",
        "max_kitchen_pm25",
        "car_trips",
        "car_minutes",
        "car_miles",
        "hard_brakes",
        "idle_minutes",
        "commute_minutes",
        "distance_traveled_miles",
        "significant_location_changes",
        "caffeine_mg",
        "soda_intake_count",
        "donut_box_open_count",
        "snack_cabinet_open_count",
        "late_night_snack_events",
        "nighttime_eating",
        "restaurant_visit_count",
        "fast_food_visit_count",
        "tavern_visit_minutes",
        "work_calendar_events",
        "meeting_minutes",
        "work_stress_proxy",
        "shift_load",
        "stress_score",
        "mood_score",
        "pain_score",
        "fatigue_score",
        "blood_pressure_systolic",
        "blood_pressure_diastolic",
        "sleep_quality",
        "sleep_nudge_received",
        "walk_nudge_received",
        "caffeine_nudge_received",
        "intervention_received",
        "intervention_type",
        "prior_sleep_quality",
        "prior_fatigue",
        "prior_bp",
        "prior_late_screen_minutes",
        "prior_steps",
        "prior_stress_score",
        "outcome_sleep_quality",
        "outcome_next_day_fatigue",
        "outcome_mood_next_day",
        "outcome_bp_next_day",
    ]
    return [{column: day[column] for column in columns} for day in latent_days]


def _flatten_states(
    states: list[dict[str, Any]],
    attributes_by_id: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for state in states:
        attrs = attributes_by_id[int(state["attributes_id"])]
        rows.append(
            {
                "state_id": state["state_id"],
                "timestamp": state["iso_timestamp"],
                "last_updated_ts": state["last_updated_ts"],
                "date": state["date"],
                "entity_id": state["entity_id"],
                "domain": state["domain"],
                "state": state["state"],
                "unit": state["unit"],
                "source": state["source"],
                "attributes_json": _canonical_json(attrs),
            }
        )
    return rows


@lru_cache(maxsize=16)
def generate_homer_ha_dataset(
    dataset_id: str,
    *,
    seed: int = DEFAULT_SEED,
    start: str = DEFAULT_START,
    density: str | None = None,
) -> HADataset:
    """Generate and cache a Home Assistant-style Homer dataset."""

    if dataset_id not in HOMER_DATASET_IDS:
        raise ValueError(f"Unknown Homer dataset_id '{dataset_id}'.")
    days = 30 if dataset_id in {HOMER_HA_STATES_30_DAYS_ID, HOMER_SQLITE_DEMO_30_DAYS_ID} else 100
    actual_density = density or ("moderate" if days == 30 else "high")
    start_dt = _parse_start(start)
    latent_days = generate_latent_days(days=days, seed=seed, start=start)
    builder = StateBuilder(seed=seed)
    rng = random.Random(seed + days * 101)
    odometer = 82400.0
    fuel = 74.0
    for day in latent_days:
        day_start = start_dt + timedelta(days=int(day["day_index"]))
        odometer, fuel = _generate_day_states(
            builder,
            day,
            day_start=day_start,
            density=actual_density,
            rng=rng,
            odometer_start=odometer,
            fuel_start=fuel,
        )
    attrs_by_id = {
        int(row["attributes_id"]): json.loads(str(row["shared_attrs"]))
        for row in builder.state_attributes
    }
    states = sorted(builder.states, key=lambda row: (float(row["last_updated_ts"]), int(row["state_id"])))
    for new_id, row in enumerate(states, start=1):
        row["state_id"] = new_id
    # Recompute old_state_id after chronological sort.
    previous_by_entity: dict[str, int] = {}
    previous_state_by_entity: dict[str, str] = {}
    for row in states:
        entity_id = str(row["entity_id"])
        row["old_state_id"] = previous_by_entity.get(entity_id)
        row["last_changed_ts"] = (
            row["last_updated_ts"]
            if previous_state_by_entity.get(entity_id) != row["state"]
            else None
        )
        row["context_id_bin"] = _context_id(int(row["state_id"]), datetime.fromisoformat(str(row["iso_timestamp"])), seed)
        previous_by_entity[entity_id] = int(row["state_id"])
        previous_state_by_entity[entity_id] = str(row["state"])
    builder.states = states
    return HADataset(
        dataset_id=dataset_id,
        days=days,
        density=actual_density,
        seed=seed,
        start=start_dt,
        states=states,
        states_meta=builder.metadata(),
        state_attributes=builder.state_attributes,
        flattened=_flatten_states(states, attrs_by_id),
        daily=_daily_rows_from_latent(latent_days if days == 100 else latent_days),
        latent_days=latent_days,
    )


def _dataset_for_id(dataset_id: str) -> HADataset:
    if dataset_id == HOMER_DAILY_100_DAYS_ID:
        return generate_homer_ha_dataset(HOMER_HA_STATES_100_DAYS_ID)
    if dataset_id == HOMER_SQLITE_DEMO_30_DAYS_ID:
        return generate_homer_ha_dataset(HOMER_SQLITE_DEMO_30_DAYS_ID)
    return generate_homer_ha_dataset(dataset_id)


@lru_cache(maxsize=4)
def generate_homer_daily_rows(
    *,
    days: int = 100,
    seed: int = DEFAULT_SEED,
    start: str = DEFAULT_START,
) -> list[dict[str, Any]]:
    """Generate daily analysis-ready Homer rows without materializing raw states."""

    return _daily_rows_from_latent(generate_latent_days(days=days, seed=seed, start=start))


def homer_records_for_analysis(dataset_id: str | None) -> list[dict[str, Any]]:
    """Return daily rows suitable for existing causal-analysis tools."""

    dataset_id = dataset_id or HOMER_DAILY_100_DAYS_ID
    if dataset_id == HOMER_DAILY_100_DAYS_ID:
        return generate_homer_daily_rows()
    if dataset_id in {HOMER_HA_STATES_30_DAYS_ID, HOMER_HA_STATES_100_DAYS_ID, HOMER_SQLITE_DEMO_30_DAYS_ID}:
        return _dataset_for_id(dataset_id).daily
    raise ValueError(f"Unknown Homer dataset_id '{dataset_id}'.")


def get_homer_dataset_metadata() -> list[dict[str, Any]]:
    """Return generated Homer dataset metadata."""

    items = []
    for dataset_id in [
        HOMER_HA_STATES_30_DAYS_ID,
        HOMER_HA_STATES_100_DAYS_ID,
        HOMER_DAILY_100_DAYS_ID,
        HOMER_SQLITE_DEMO_30_DAYS_ID,
    ]:
        days = 30 if dataset_id in {HOMER_HA_STATES_30_DAYS_ID, HOMER_SQLITE_DEMO_30_DAYS_ID} else 100
        start_dt = _parse_start(DEFAULT_START)
        if dataset_id == HOMER_DAILY_100_DAYS_ID:
            rows = 100
            tables = ["daily"]
            dataset_type = "analysis_ready_daily"
        elif dataset_id == HOMER_SQLITE_DEMO_30_DAYS_ID:
            rows = HOMER_METADATA_ROW_ESTIMATES[dataset_id]
            tables = ["sql_dump", "states", "states_meta", "state_attributes"]
            dataset_type = "home_assistant_recorder_sql_demo"
        else:
            rows = HOMER_METADATA_ROW_ESTIMATES[dataset_id]
            tables = ["states", "states_meta", "state_attributes", "flattened", "daily"]
            dataset_type = "home_assistant_recorder_states"
        items.append(
            {
                "dataset_id": dataset_id,
                "dataset_type": dataset_type,
                "synthetic_subject": PROFILE["subject_id"],
                "synthetic_profile": PROFILE["profile_type"],
                "rows": rows,
                "rows_estimated_until_generated": dataset_id != HOMER_DAILY_100_DAYS_ID,
                "days": days,
                "date_range": {
                    "start": start_dt.isoformat(),
                    "end": (start_dt + timedelta(days=days) - timedelta(seconds=1)).isoformat(),
                },
                "tables_available": tables,
                "source": "Deterministic synthetic Home Assistant Recorder-inspired generator.",
                "privacy_note": PROFILE["privacy_note"],
                "seed": DEFAULT_SEED,
                "density": "moderate" if days == 30 else "high",
            }
        )
    return items


def describe_homer_dataset(dataset_id: str, variables: list[str] | None = None) -> dict[str, Any]:
    """Describe raw HA-style or daily Homer datasets."""

    if dataset_id == HOMER_DAILY_100_DAYS_ID:
        daily_rows = generate_homer_daily_rows()
        df = pd.DataFrame(daily_rows)
        selected = variables or list(df.columns)
        numeric = {
            column: {
                "n": int(pd.to_numeric(df[column], errors="coerce").notna().sum()),
                "mean": _round(pd.to_numeric(df[column], errors="coerce").mean()),
                "min": _round(pd.to_numeric(df[column], errors="coerce").min()),
                "max": _round(pd.to_numeric(df[column], errors="coerce").max()),
            }
            for column in selected
            if column in df and pd.to_numeric(df[column], errors="coerce").notna().any()
        }
        return {
            "dataset_id": dataset_id,
            "dataset_type": "analysis_ready_daily",
            "synthetic_subject": PROFILE["subject_id"],
            "number_of_days": len(daily_rows),
            "number_of_rows": len(daily_rows),
            "date_range": {"start": daily_rows[0]["date"], "end": daily_rows[-1]["date"]},
            "missingness_summary": {
                column: {
                    "missing_count": int(df[column].isna().sum()),
                    "missing_fraction": float(df[column].isna().mean()),
                }
                for column in selected
                if column in df
            },
            "numeric_summaries": numeric,
            "warning": "Synthetic parody data only; correlations are descriptive and not medical advice.",
        }

    dataset = _dataset_for_id(dataset_id)
    states_df = pd.DataFrame(dataset.states)
    numeric_states = states_df.assign(numeric_state=pd.to_numeric(states_df["state"], errors="coerce"))
    numeric_summary = (
        numeric_states.dropna(subset=["numeric_state"])
        .groupby("entity_id")["numeric_state"]
        .agg(["count", "mean", "min", "max"])
        .head(25)
        .reset_index()
    )
    binary_counts = (
        states_df[states_df["domain"].eq("binary_sensor")]
        .groupby(["entity_id", "state"])
        .size()
        .unstack(fill_value=0)
        .head(25)
        .to_dict(orient="index")
    )
    return {
        "dataset_id": dataset_id,
        "dataset_type": "home_assistant_recorder_states",
        "synthetic_subject": PROFILE["subject_id"],
        "number_of_rows": len(dataset.states),
        "states_rows": len(dataset.states),
        "unique_entities": states_df["entity_id"].nunique(),
        "states_meta_rows": len(dataset.states_meta),
        "state_attributes_rows": len(dataset.state_attributes),
        "date_range": {
            "start": dataset.states[0]["iso_timestamp"],
            "end": dataset.states[-1]["iso_timestamp"],
        },
        "domain_counts": states_df["domain"].value_counts().to_dict(),
        "top_entities_by_row_count": states_df["entity_id"].value_counts().head(15).to_dict(),
        "missingness_summary": {
            "state": {
                "missing_count": int(states_df["state"].isna().sum()),
                "missing_fraction": float(states_df["state"].isna().mean()),
            }
        },
        "numeric_summaries": numeric_summary.to_dict(orient="records"),
        "binary_counts": binary_counts,
        "warning": "Synthetic parody Home Assistant-style data only; correlations are descriptive and not medical advice.",
    }


def query_homer_ha_states(
    *,
    dataset_id: str,
    entity_id: str | None = None,
    domain: str | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int = 1000,
    include_attributes: bool = False,
    parse_numeric: bool = False,
) -> dict[str, Any]:
    """Query generated HA states."""

    dataset = _dataset_for_id(dataset_id)
    rows = dataset.states
    if entity_id:
        rows = [row for row in rows if row["entity_id"] == entity_id]
    if domain:
        rows = [row for row in rows if row["domain"] == domain]
    if start:
        start_ts = datetime.fromisoformat(start).timestamp()
        rows = [row for row in rows if float(row["last_updated_ts"]) >= start_ts]
    if end:
        end_ts = datetime.fromisoformat(end).timestamp()
        rows = [row for row in rows if float(row["last_updated_ts"]) <= end_ts]
    rows = sorted(rows, key=lambda row: float(row["last_updated_ts"]))
    truncated = len(rows) > limit
    output = [dict(row) for row in rows[:limit]]
    attrs_by_id = {
        row["attributes_id"]: json.loads(str(row["shared_attrs"]))
        for row in dataset.state_attributes
    }
    if include_attributes:
        for row in output:
            row["attributes"] = attrs_by_id[row["attributes_id"]]
    if parse_numeric:
        for row in output:
            try:
                row["numeric_state"] = float(row["state"])
            except (TypeError, ValueError):
                row["numeric_state"] = None
    return {
        "dataset_id": dataset_id,
        "table": "states",
        "entity_id": entity_id,
        "domain": domain,
        "rows_returned": len(output),
        "truncated": truncated,
        "date_range": {
            "start": dataset.start.isoformat(),
            "end": (dataset.start + timedelta(days=dataset.days) - timedelta(seconds=1)).isoformat(),
        },
        "metadata_summary": {
            "states_rows_matched": len(rows),
            "unique_entities_matched": len({row["entity_id"] for row in rows}),
        },
        "rows": output,
    }


def aggregate_homer_ha_states_daily(
    *,
    dataset_id: str,
    entity_ids: list[str] | None = None,
    aggregation_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return deterministic daily rows derived for generated HA states."""

    dataset = _dataset_for_id(dataset_id)
    return {
        "dataset_id": dataset_id,
        "source_table": "states",
        "daily_rows": dataset.daily,
        "rows_returned": len(dataset.daily),
        "aggregation_rules_used": {
            "steps": "last daily cumulative value",
            "heart_rate": "mean and max from periodic wearable states",
            "door_opens": "count off-to-on contact transitions",
            "tv_minutes": "duration of switch.living_room_tv on",
            "zone_minutes": "duration in device_tracker zones",
            "daily_outcomes": "latent causal day values aligned to generated state history",
        },
        "entity_ids_requested": entity_ids or [],
        "aggregation_config": aggregation_config or {},
        "warnings": [
            "Default Homer daily dataset has no missing values; raw non-wear/non-reporting is resolved through documented synthetic latent-day summaries."
        ],
    }


def _csv_for_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, int | float):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _sql_dump(dataset: HADataset) -> str:
    lines = [
        "CREATE TABLE states_meta (metadata_id INTEGER PRIMARY KEY, entity_id TEXT UNIQUE, domain TEXT, object_id TEXT, first_seen_ts REAL, last_seen_ts REAL);",
        "CREATE TABLE state_attributes (attributes_id INTEGER PRIMARY KEY, hash INTEGER, shared_attrs TEXT);",
        "CREATE TABLE states (state_id INTEGER PRIMARY KEY, metadata_id INTEGER, entity_id TEXT, state TEXT, attributes_id INTEGER, last_changed_ts REAL, last_updated_ts REAL, last_reported_ts REAL, old_state_id INTEGER, context_id_bin TEXT, context_user_id_bin TEXT, context_parent_id_bin TEXT, origin_idx INTEGER, iso_timestamp TEXT, date TEXT, source TEXT, domain TEXT, unit TEXT);",
    ]
    for table, rows in [
        ("states_meta", dataset.states_meta),
        ("state_attributes", dataset.state_attributes),
        ("states", dataset.states),
    ]:
        for row in rows:
            cols = list(row)
            values = ", ".join(_sql_literal(row[col]) for col in cols)
            lines.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({values});")
    return "\n".join(lines)


def export_homer_dataset(
    *,
    dataset_id: str,
    format: Literal["csv", "json", "sql"] = "csv",
    table: str = "daily",
) -> dict[str, Any]:
    """Export generated Homer tables."""

    if dataset_id == HOMER_DAILY_100_DAYS_ID:
        rows = generate_homer_daily_rows()
        if table != "daily":
            raise ValueError("homer_simpson_daily_100_days only supports table='daily'.")
        if format == "json":
            serialized: Any = rows
            extension = "json"
        elif format == "csv":
            serialized = _csv_for_rows(rows)
            extension = "csv"
        else:
            raise ValueError("format must be 'csv' or 'json' for the daily dataset.")
        return {
            "serialized_dataset": serialized,
            "format": format,
            "table": table,
            "filename_suggestion": f"{dataset_id}_{table}.{extension}",
            "privacy_note": PROFILE["privacy_note"],
        }

    dataset = _dataset_for_id(dataset_id)
    tables = {
        "states": dataset.states,
        "states_meta": dataset.states_meta,
        "state_attributes": dataset.state_attributes,
        "flattened": dataset.flattened,
        "daily": dataset.daily,
    }
    if format == "sql":
        return {
            "serialized_dataset": _sql_dump(dataset),
            "format": "sql",
            "table": "normalized",
            "filename_suggestion": f"{dataset_id}.sql",
        }
    if format == "json" and table == "normalized":
        return {
            "serialized_dataset": {
                "states": dataset.states,
                "states_meta": dataset.states_meta,
                "state_attributes": dataset.state_attributes,
            },
            "format": "json",
            "table": "normalized",
            "filename_suggestion": f"{dataset_id}_normalized.json",
        }
    if table not in tables:
        valid = ", ".join(sorted([*tables, "normalized"]))
        raise ValueError(f"Unknown table '{table}'. Valid tables: {valid}.")
    rows = tables[table]
    if format == "json":
        serialized: Any = rows
        extension = "json"
    elif format == "csv":
        serialized = _csv_for_rows(rows)
        extension = "csv"
    else:
        raise ValueError("format must be 'csv', 'json', or 'sql'.")
    return {
        "serialized_dataset": serialized,
        "format": format,
        "table": table,
        "filename_suggestion": f"{dataset_id}_{table}.{extension}",
        "privacy_note": PROFILE["privacy_note"],
    }


def stable_dataset_hash(dataset_id: str) -> str:
    """Return a stable hash for generated dataset determinism tests."""

    dataset = _dataset_for_id(dataset_id)
    payload = {
        "states": dataset.states,
        "states_meta": dataset.states_meta,
        "state_attributes": dataset.state_attributes,
        "daily": dataset.daily,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
