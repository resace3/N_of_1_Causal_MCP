const TOOL_NAMES = [
  "get_available_datasets",
  "get_available_scenarios",
  "describe_patient_data",
  "propose_causal_question",
  "estimate_causal_effect",
  "run_target_trial_emulation",
  "generate_causal_dag",
  "check_adjustment_set",
  "simulate_intervention",
  "export_dataset",
  "query_ha_states",
  "aggregate_ha_states_daily",
] as const;

type ToolName = (typeof TOOL_NAMES)[number];
type JsonRecord = Record<string, unknown>;

interface Env {
  N_OF_1_MCP: DurableObjectNamespace;
}

interface RpcRequest {
  jsonrpc?: string;
  id?: string | number | null;
  method?: string;
  params?: JsonRecord;
}

const MAX_MCP_REQUEST_BODY_BYTES = 128 * 1024;
const ALLOWED_CORS_ORIGINS = new Set([
  "http://localhost:6274",
  "http://127.0.0.1:6274",
  "http://localhost:8787",
  "http://127.0.0.1:8787",
]);
const DEFAULT_DATASET_ID = "patient_001_100_days";
const RAW_DATASET_ID = "patient_001_raw_events_30_days";
const HOMER_HA_30_ID = "homer_simpson_ha_states_30_days";
const HOMER_HA_100_ID = "homer_simpson_ha_states_100_days";
const HOMER_DAILY_100_ID = "homer_simpson_daily_100_days";
const HOMER_SQLITE_30_ID = "homer_simpson_ha_sqlite_demo_30_days";
const PUBLIC_DATA_ERROR =
  "Caller-supplied data_records are disabled on the public Cloudflare MCP endpoint. Use one of the bundled synthetic dataset_id values instead.";
const BUNDLED_DATASET_IDS = [
  DEFAULT_DATASET_ID,
  RAW_DATASET_ID,
  HOMER_HA_30_ID,
  HOMER_HA_100_ID,
  HOMER_DAILY_100_ID,
  HOMER_SQLITE_30_ID,
] as const;

const DAILY_COLUMNS = [
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
];

const SCENARIOS = [
  {
    id: "sleep_screen_time",
    causal_question: "What is the effect of reducing late-night screen time on sleep quality?",
    exposure: "late_night_screen_minutes",
    outcome: "outcome_sleep_quality",
    adjustment_variables: ["stress_score", "caffeine_mg", "prior_sleep_quality", "steps"],
    mediators: ["sleep_duration_hours", "sleep_efficiency"],
    expected_direction: "Reducing late-night screen time is expected to improve sleep quality.",
  },
  {
    id: "steps_fatigue",
    causal_question: "What is the effect of increasing daily steps on next-day fatigue?",
    exposure: "steps",
    outcome: "outcome_next_day_fatigue",
    adjustment_variables: ["prior_fatigue", "stress_score", "sleep_quality", "day_of_week"],
    mediators: ["active_minutes"],
    expected_direction: "Higher steps are expected to reduce next-day fatigue after adjustment.",
  },
  {
    id: "medication_bp",
    causal_question: "What is the effect of medication adherence on next-day blood pressure?",
    exposure: "medication_adherence",
    outcome: "outcome_bp_next_day",
    adjustment_variables: ["baseline_bp", "stress_score", "caffeine_mg", "prior_bp"],
    mediators: [],
    expected_direction: "Medication adherence is expected to lower next-day systolic blood pressure.",
  },
  {
    id: "stress_sleep",
    causal_question: "What is the effect of high stress on same-night sleep quality?",
    exposure: "stress_score",
    outcome: "outcome_sleep_quality",
    adjustment_variables: ["prior_sleep_quality", "day_of_week", "caffeine_mg"],
    mediators: ["late_night_screen_minutes", "caffeine_mg"],
    expected_direction: "Higher stress is expected to reduce sleep quality.",
  },
  {
    id: "nighttime_eating_fatigue",
    causal_question: "What is the effect of nighttime eating on morning fatigue?",
    exposure: "nighttime_eating",
    outcome: "morning_fatigue",
    adjustment_variables: ["stress_score", "late_night_screen_minutes", "prior_fatigue"],
    mediators: ["sleep_duration_hours"],
    expected_direction: "Nighttime eating is expected to increase morning fatigue.",
  },
  {
    id: "mixed_lifestyle",
    causal_question: "What is the effect of an evening reminder intervention on sleep quality?",
    exposure: "intervention_received",
    outcome: "outcome_sleep_quality",
    adjustment_variables: [
      "stress_score",
      "prior_sleep_quality",
      "prior_fatigue",
      "day_of_week",
      "baseline_phone_use",
    ],
    mediators: ["late_night_screen_minutes", "nighttime_eating"],
    expected_direction: "The reminder is expected to improve sleep quality.",
  },
];

function securityHeaders(): HeadersInit {
  return {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
  };
}

function corsHeaders(request: Request): HeadersInit {
  const origin = request.headers.get("Origin");
  if (!origin || !ALLOWED_CORS_ORIGINS.has(origin)) {
    return { Vary: "Origin" };
  }
  return {
    Vary: "Origin",
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, Mcp-Session-Id, MCP-Protocol-Version",
    "Access-Control-Expose-Headers": "Mcp-Session-Id",
  };
}

function jsonResponse(request: Request, payload: unknown, status = 200, extra: HeadersInit = {}): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...securityHeaders(),
      ...corsHeaders(request),
      ...extra,
    },
  });
}

function emptyResponse(request: Request, status = 204): Response {
  return new Response(null, {
    status,
    headers: { ...securityHeaders(), ...corsHeaders(request) },
  });
}

function healthPayload() {
  return {
    ok: true,
    name: "patient-causal-mcp",
    transport: "streamable-http",
    mcp_endpoint: "/mcp",
    auth: "none",
    data_policy: "bundled_synthetic_only",
    caller_supplied_data_records: "disabled",
    max_mcp_request_body_bytes: MAX_MCP_REQUEST_BODY_BYTES,
    tools: TOOL_NAMES,
  };
}

function rejectPreflight(request: Request): Response | null {
  const origin = request.headers.get("Origin");
  if (origin && !ALLOWED_CORS_ORIGINS.has(origin)) {
    return jsonResponse(
      request,
      {
        ok: false,
        error: "cors_origin_not_allowed",
        message: "This public MCP demo only allows browser requests from approved origins.",
      },
      403,
    );
  }
  return null;
}

function rejectBodySize(request: Request): Response | null {
  const contentLength = request.headers.get("Content-Length");
  if (!contentLength) return null;
  const length = Number(contentLength);
  if (!Number.isFinite(length)) {
    return jsonResponse(request, { ok: false, error: "invalid_content_length" }, 400);
  }
  if (length <= MAX_MCP_REQUEST_BODY_BYTES) return null;
  return jsonResponse(
    request,
    { ok: false, error: "request_body_too_large", max_bytes: MAX_MCP_REQUEST_BODY_BYTES },
    413,
  );
}

function dayDate(index: number): string {
  const date = new Date(Date.UTC(2026, 0, 1 + index));
  return date.toISOString().slice(0, 10);
}

function noise(index: number, salt: number): number {
  const value = Math.sin((index + 1) * (salt + 3) * 12.9898) * 43758.5453;
  return value - Math.floor(value);
}

function round(value: number, digits = 3): number {
  const scale = 10 ** digits;
  return Math.round(value * scale) / scale;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function dailyRecord(index: number): JsonRecord {
  const dayOfWeek = (index + 3) % 7;
  const isWeekend = dayOfWeek === 5 || dayOfWeek === 6 ? 1 : 0;
  const stress = clamp(4.5 + 1.4 * Math.sin(index / 4.5) + noise(index, 1) * 1.6, 0, 10);
  const priorSleep = clamp(6.1 + Math.sin((index - 1) / 6) - stress * 0.08, 0, 10);
  const caffeine = clamp(120 + stress * 28 + noise(index, 2) * 120 - isWeekend * 35, 0, 450);
  const lateScreen = clamp(55 + stress * 18 + noise(index, 3) * 85 + isWeekend * 35, 0, 240);
  const intervention = index >= 50 && index % 2 === 0 ? 1 : 0;
  const nighttimeEating = lateScreen > 125 && noise(index, 4) > 0.38 ? 1 : 0;
  const sleepDuration = clamp(
    7.4 - lateScreen * 0.008 - stress * 0.13 - caffeine * 0.002 + intervention * 0.28 - nighttimeEating * 0.35,
    4,
    9.4,
  );
  const sleepQuality = clamp(2.2 + sleepDuration * 0.62 - stress * 0.22 - nighttimeEating * 0.35, 0, 10);
  const steps = Math.round(clamp(6200 + noise(index, 5) * 5200 - stress * 260 + isWeekend * 900, 900, 16000));
  const fatigue = clamp(9.8 - sleepQuality * 0.72 - steps / 4800 + stress * 0.28 + nighttimeEating * 0.55, 0, 10);
  const adherence = noise(index, 6) + intervention * 0.12 > 0.23 ? 1 : 0;
  const systolic = clamp(131 + stress * 1.7 - adherence * 7 + caffeine * 0.012 + noise(index, 7) * 7, 104, 165);
  const mood = clamp(5.5 + sleepQuality * 0.28 - stress * 0.22 + noise(index, 8), 0, 10);
  const activeMinutes = Math.round(clamp(steps / 120 + noise(index, 9) * 25, 5, 180));
  const totalScreen = Math.round(lateScreen + 260 + noise(index, 10) * 170);
  const cardSpend = round(28 + isWeekend * 32 + stress * 4 + noise(index, 11) * 45, 2);

  return {
    date: dayDate(index),
    day_index: index,
    day_of_week: dayOfWeek,
    is_weekend: isWeekend,
    patient_id: "synthetic-patient-001",
    baseline_sleep_need: 7.25,
    baseline_activity_level: 6800,
    baseline_stress_tendency: 5.2,
    baseline_bp: 129,
    baseline_phone_use: 195,
    baseline_adherence: 0.82,
    sleep_duration_hours: round(sleepDuration),
    sleep_efficiency: round(clamp(72 + sleepQuality * 2.1 + noise(index, 12) * 6, 50, 99)),
    awakenings: Math.round(clamp(5 - sleepQuality * 0.28 + noise(index, 13) * 3, 0, 8)),
    wearable_device_worn_hours: round(clamp(20 + noise(index, 14) * 4, 10, 24), 2),
    heart_rate_variability_ms: round(clamp(58 - stress * 2.4 + sleepQuality * 1.8, 18, 100), 1),
    calories_burned: Math.round(1900 + steps * 0.08 + activeMinutes * 4),
    spo2_percent: round(clamp(96.2 + noise(index, 15) * 2, 92, 99.5), 1),
    skin_temperature_c: round(36.2 + noise(index, 16) * 0.7, 2),
    steps,
    sedentary_minutes: Math.round(clamp(980 - activeMinutes * 1.5 + noise(index, 17) * 80, 300, 1200)),
    active_minutes: activeMinutes,
    motion_stationary_minutes: Math.round(clamp(880 - activeMinutes + noise(index, 18) * 90, 250, 1200)),
    motion_walking_minutes: Math.round(activeMinutes * 0.72),
    motion_running_minutes: Math.round(noise(index, 19) * 18),
    motion_driving_minutes: Math.round(clamp(20 + noise(index, 20) * 75 + (isWeekend ? 15 : 0), 0, 180)),
    accelerometer_activity_counts: Math.round(steps / 10 + noise(index, 21) * 180),
    location_home_minutes: Math.round(isWeekend ? 980 + noise(index, 22) * 180 : 760 + noise(index, 22) * 220),
    location_work_minutes: Math.round(isWeekend ? noise(index, 23) * 40 : 360 + noise(index, 23) * 160),
    away_from_home_minutes: Math.round(isWeekend ? 300 + noise(index, 24) * 220 : 500 + noise(index, 24) * 180),
    home_wifi_minutes: Math.round(isWeekend ? 900 + noise(index, 25) * 220 : 700 + noise(index, 25) * 220),
    distance_traveled_km: round(noise(index, 26) * 28 + (isWeekend ? 4 : 9), 2),
    commute_minutes: Math.round(isWeekend ? noise(index, 27) * 10 : 25 + noise(index, 27) * 45),
    gps_radius_meters: Math.round(50 + noise(index, 28) * 900),
    significant_location_changes: Math.round(noise(index, 29) * 6),
    late_night_screen_minutes: round(lateScreen),
    caffeine_mg: round(caffeine),
    alcohol_units: round(clamp((isWeekend ? 0.5 : 0) + noise(index, 30) * 1.8 - intervention * 0.25, 0, 4), 2),
    medication_adherence: adherence,
    stress_score: round(stress),
    mood_score: round(mood),
    pain_score: round(clamp(2.5 + stress * 0.22 + noise(index, 31) * 2.5, 0, 10)),
    blood_pressure_systolic: round(systolic),
    blood_pressure_diastolic: round(systolic * 0.62 + 2 + noise(index, 32) * 4),
    resting_heart_rate: round(clamp(61 + stress * 2 - sleepQuality * 0.7 + noise(index, 33) * 7, 48, 96), 1),
    morning_fatigue: round(fatigue),
    nighttime_eating: nighttimeEating,
    pantry_door_opens: Math.round(2 + noise(index, 34) * 9),
    refrigerator_door_opens: Math.round(3 + noise(index, 35) * 8),
    smart_plug_tv_minutes: Math.round(25 + lateScreen * 0.28 + noise(index, 36) * 90),
    smart_plug_kettle_uses: Math.round(noise(index, 37) * 5),
    medication_cabinet_opens: adherence,
    phone_pickups: Math.round(38 + lateScreen * 0.25 + stress * 4 + noise(index, 38) * 25),
    unlocks: Math.round(30 + lateScreen * 0.22 + noise(index, 39) * 18),
    notifications: Math.round(150 + stress * 18 + noise(index, 40) * 120),
    texts_sent: Math.round(12 + noise(index, 41) * 28),
    texts_received: Math.round(18 + noise(index, 42) * 35),
    calls_made: Math.round(noise(index, 43) * 5),
    calls_received: Math.round(noise(index, 44) * 7),
    call_duration_minutes: round(noise(index, 45) * 55, 1),
    app_usage_minutes: totalScreen - 80,
    total_screen_time_minutes: totalScreen,
    social_app_minutes: Math.round(totalScreen * (0.22 + noise(index, 46) * 0.14)),
    productivity_app_minutes: Math.round(totalScreen * (0.1 + noise(index, 47) * 0.12)),
    finance_app_minutes: Math.round(5 + noise(index, 48) * 20),
    entertainment_app_minutes: Math.round(totalScreen * (0.2 + noise(index, 49) * 0.18)),
    transactions_count: Math.round(1 + noise(index, 50) * 7),
    card_spend_usd: cardSpend,
    cash_withdrawal_usd: noise(index, 51) > 0.88 ? 40 : 0,
    grocery_spend_usd: round(noise(index, 52) * 75, 2),
    restaurant_spend_usd: round((isWeekend ? 12 : 5) + noise(index, 53) * 45, 2),
    alcohol_spend_usd: round(isWeekend ? noise(index, 54) * 28 : noise(index, 54) * 8, 2),
    ride_share_spend_usd: round(noise(index, 55) > 0.72 ? 8 + noise(index, 56) * 30 : 0, 2),
    online_purchase_count: Math.round(noise(index, 57) * 5),
    work_calendar_events: Math.round(isWeekend ? noise(index, 58) * 2 : 2 + noise(index, 58) * 6),
    meeting_minutes: Math.round(isWeekend ? noise(index, 59) * 45 : 45 + noise(index, 59) * 240),
    intervention_received: intervention,
    sleep_quality: round(sleepQuality),
    prior_sleep_quality: round(priorSleep),
    prior_fatigue: round(clamp(fatigue + noise(index, 60) - 0.5, 0, 10)),
    prior_bp: round(clamp(systolic + noise(index, 61) * 4 - 2, 104, 165)),
    outcome_sleep_quality: round(clamp(sleepQuality + intervention * 0.15 - lateScreen * 0.001, 0, 10)),
    outcome_next_day_fatigue: round(clamp(fatigue + noise(index, 62) * 0.8, 0, 10)),
    outcome_mood_next_day: round(clamp(mood + sleepQuality * 0.08 - fatigue * 0.05, 0, 10)),
    outcome_bp_next_day: round(clamp(systolic - adherence * 1.2 + stress * 0.25, 104, 170)),
  };
}

function dailyRecords(): JsonRecord[] {
  return Array.from({ length: 100 }, (_, index) => dailyRecord(index));
}

function homerDailyRecord(index: number): JsonRecord {
  const base = dailyRecord(index);
  const isWorkday = Number(base.is_weekend) === 1 ? 0 : 1;
  const priorFatigue = Number(base.prior_fatigue ?? 5);
  const priorSteps = Math.round(clamp(Number(base.steps ?? 4500) - 650 + noise(index, 70) * 1300, 1200, 13000));
  const priorStress = round(clamp(Number(base.stress_score ?? 5) + noise(index, 71) - 0.5, 1, 10));
  const sleepNudge = priorFatigue > 5.8 || Number(base.prior_sleep_quality ?? 6) < 5.9 ? (noise(index, 72) > 0.28 ? 1 : 0) : 0;
  const walkNudge = priorSteps < 5200 || priorFatigue > 6 ? (noise(index, 73) > 0.35 ? 1 : 0) : 0;
  const caffeineNudge = priorFatigue > 5 || priorStress > 5.5 ? (noise(index, 74) > 0.45 ? 1 : 0) : 0;
  const steps = Math.round(clamp(Number(base.steps ?? 5000) + walkNudge * 900 - priorFatigue * 85, 1500, 13000));
  const caffeine = round(clamp(Number(base.caffeine_mg ?? 180) - caffeineNudge * 45, 0, 450));
  const lateScreen = round(clamp(Number(base.late_night_screen_minutes ?? 90) - sleepNudge * 25 + Number(base.smart_plug_tv_minutes ?? 90) * 0.12, 0, 260));
  const sleepQuality = round(clamp(Number(base.sleep_quality ?? 6) + sleepNudge * 0.28 - lateScreen * 0.004 - caffeine * 0.002, 1, 10));
  const fatigue = round(clamp(9.2 - sleepQuality * 0.58 + priorStress * 0.24 - steps / 6500, 1, 10));
  const mood = round(clamp(Number(base.mood_score ?? 5) + walkNudge * 0.22 + sleepQuality * 0.08 - fatigue * 0.06, 1, 10));
  return {
    ...base,
    patient_id: undefined,
    subject_id: "homer_simpson",
    synthetic_profile: "fictional_parody",
    is_workday: isWorkday,
    steps,
    caffeine_mg: caffeine,
    late_night_screen_minutes: lateScreen,
    tv_minutes: Math.round(Number(base.smart_plug_tv_minutes ?? 90) + noise(index, 75) * 110),
    streaming_minutes: Math.round(Number(base.smart_plug_tv_minutes ?? 90) * 0.82),
    game_app_minutes: Math.round(noise(index, 76) * 80),
    navigation_minutes: Math.round(isWorkday ? 18 + noise(index, 77) * 22 : noise(index, 77) * 45),
    avg_daytime_outdoor_illuminance: Math.round(clamp(12_000 + noise(index, 78) * 45_000 + (1 - isWorkday) * 7000, 1000, 90_000)),
    home_minutes: Number(base.location_home_minutes ?? 800),
    away_minutes: Number(base.away_from_home_minutes ?? 500),
    work_minutes: Number(base.location_work_minutes ?? 0),
    car_minutes: Number(base.motion_driving_minutes ?? 30),
    car_miles: round(Number(base.distance_traveled_km ?? 12) * 0.621, 2),
    caffeine_nudge_received: caffeineNudge,
    sleep_nudge_received: sleepNudge,
    walk_nudge_received: walkNudge,
    intervention_received: sleepNudge || walkNudge || caffeineNudge ? 1 : 0,
    intervention_type: sleepNudge ? "sleep_nudge" : walkNudge ? "walk_nudge" : caffeineNudge ? "caffeine_nudge" : "none",
    prior_steps: priorSteps,
    prior_stress_score: priorStress,
    prior_late_screen_minutes: round(clamp(lateScreen + noise(index, 79) * 40 - 20, 0, 260)),
    sleep_quality: sleepQuality,
    outcome_sleep_quality: sleepQuality,
    outcome_next_day_fatigue: fatigue,
    outcome_mood_next_day: mood,
    outcome_bp_next_day: round(clamp(Number(base.outcome_bp_next_day ?? 130) + caffeine * 0.01 + priorStress * 0.2, 110, 165)),
  };
}

function homerDailyRecords(): JsonRecord[] {
  return Array.from({ length: 100 }, (_, index) => homerDailyRecord(index));
}

const HOMER_HA_ENTITIES = [
  { metadata_id: 1, entity_id: "sensor.homer_watch_heart_rate", domain: "sensor", object_id: "homer_watch_heart_rate", unit: "bpm", source: "synthetic_wearable" },
  { metadata_id: 2, entity_id: "sensor.homer_watch_steps", domain: "sensor", object_id: "homer_watch_steps", unit: "steps", source: "synthetic_wearable" },
  { metadata_id: 3, entity_id: "device_tracker.homer_phone", domain: "device_tracker", object_id: "homer_phone", unit: null, source: "synthetic_phone" },
  { metadata_id: 4, entity_id: "switch.living_room_tv", domain: "switch", object_id: "living_room_tv", unit: null, source: "synthetic_smart_home" },
  { metadata_id: 5, entity_id: "sensor.living_room_tv_power", domain: "sensor", object_id: "living_room_tv_power", unit: "W", source: "synthetic_smart_plug" },
  { metadata_id: 6, entity_id: "binary_sensor.refrigerator_door_contact", domain: "binary_sensor", object_id: "refrigerator_door_contact", unit: null, source: "synthetic_smart_home" },
];

function homerStateAttributes(entity: (typeof HOMER_HA_ENTITIES)[number]) {
  return {
    friendly_name: entity.object_id.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase()),
    unit_of_measurement: entity.unit,
    device_class: entity.unit === "bpm" ? null : entity.unit === "W" ? "power" : null,
    state_class: entity.domain === "sensor" ? "measurement" : null,
    source: entity.source,
    synthetic_subject: "homer_simpson",
    synthetic_profile: "fictional_parody",
    privacy_level: "synthetic",
    icon: entity.entity_id.includes("heart_rate") ? "mdi:heart-pulse" : "mdi:home",
  };
}

function homerHaStates(datasetId: string): JsonRecord[] {
  const days = datasetId === HOMER_HA_100_ID ? 100 : 30;
  const rows: JsonRecord[] = [];
  let stateId = 1;
  const previous: Record<string, number> = {};
  const previousState: Record<string, string> = {};
  for (let day = 0; day < days; day += 1) {
    const daily = homerDailyRecord(day);
    const date = dayDate(day);
    for (const hour of [6, 8, 10, 12, 14, 16, 18, 20, 22]) {
      const hr = Math.round(clamp(Number(daily.resting_heart_rate ?? 70) + noise(day + hour, 81) * 38, 55, 135));
      rows.push(homerHaState(stateId++, 1, date, hour, 5, String(hr), previous, previousState));
    }
    for (const hour of [7, 10, 13, 16, 19, 22]) {
      const steps = Math.round((Number(daily.steps ?? 5000) * (hour - 6)) / 17);
      rows.push(homerHaState(stateId++, 2, date, hour, 15, String(Math.max(0, steps)), previous, previousState));
    }
    for (const [hour, zone] of [
      [0, "springfield_home"],
      [8, Number(daily.is_workday) ? "power_plant_area" : "springfield_home"],
      [18, Number(daily.tv_minutes) > 150 ? "springfield_home" : "kwik_e_mart_area"],
      [22, "springfield_home"],
    ] as const) {
      rows.push(homerHaState(stateId++, 3, date, hour, 0, zone, previous, previousState));
    }
    rows.push(homerHaState(stateId++, 4, date, 19, 30, "on", previous, previousState));
    rows.push(homerHaState(stateId++, 5, date, 20, 0, String(Math.round(75 + noise(day, 82) * 80)), previous, previousState));
    rows.push(homerHaState(stateId++, 5, date, 21, 0, String(Math.round(75 + noise(day, 83) * 80)), previous, previousState));
    rows.push(homerHaState(stateId++, 4, date, 22, 30, "off", previous, previousState));
    rows.push(homerHaState(stateId++, 6, date, 21, 45, "on", previous, previousState));
    rows.push(homerHaState(stateId++, 6, date, 21, 46, "off", previous, previousState));
  }
  return rows.sort((left, right) => Number(left.last_updated_ts) - Number(right.last_updated_ts));
}

function homerHaState(
  stateId: number,
  metadataId: number,
  date: string,
  hour: number,
  minute: number,
  state: string,
  previous: Record<string, number>,
  previousState: Record<string, string>,
): JsonRecord {
  const entity = HOMER_HA_ENTITIES.find((item) => item.metadata_id === metadataId) ?? HOMER_HA_ENTITIES[0];
  const timestamp = `${date}T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00-05:00`;
  const epoch = Date.parse(timestamp) / 1000;
  const oldStateId = previous[entity.entity_id] ?? null;
  const changed = previousState[entity.entity_id] !== state;
  previous[entity.entity_id] = stateId;
  previousState[entity.entity_id] = state;
  return {
    state_id: stateId,
    metadata_id: metadataId,
    entity_id: entity.entity_id,
    state,
    attributes_id: metadataId,
    last_changed_ts: changed ? epoch : null,
    last_updated_ts: epoch,
    last_reported_ts: epoch,
    old_state_id: oldStateId,
    context_id_bin: `synthetic_${String(stateId).padStart(16, "0")}`,
    context_user_id_bin: null,
    context_parent_id_bin: null,
    origin_idx: 0,
    iso_timestamp: timestamp,
    date,
    source: entity.source,
    domain: entity.domain,
    unit: entity.unit,
  };
}

function homerStatesMeta(datasetId: string): JsonRecord[] {
  const states = homerHaStates(datasetId);
  return HOMER_HA_ENTITIES.map((entity) => {
    const entityRows = states.filter((row) => row.entity_id === entity.entity_id);
    return {
      metadata_id: entity.metadata_id,
      entity_id: entity.entity_id,
      domain: entity.domain,
      object_id: entity.object_id,
      first_seen_ts: entityRows[0]?.last_updated_ts ?? null,
      last_seen_ts: entityRows[entityRows.length - 1]?.last_updated_ts ?? null,
    };
  });
}

function homerStateAttributeRows(): JsonRecord[] {
  return HOMER_HA_ENTITIES.map((entity) => ({
    attributes_id: entity.metadata_id,
    hash: Math.round(noise(entity.metadata_id, 90) * 2_000_000_000),
    shared_attrs: JSON.stringify(homerStateAttributes(entity)),
  }));
}

function rawEventRecords(): JsonRecord[] {
  const records: JsonRecord[] = [];
  const entities = [
    ["phone_battery_level", "percent", "phone", "device"],
    ["phone_screen_state", "none", "phone", "device"],
    ["phone_app_foreground_package", "none", "phone", "app_usage"],
    ["phone_zone_label", "none", "phone", "location"],
    ["wearable_heart_rate", "bpm", "wearable", "health"],
    ["wearable_steps", "steps", "wearable", "activity"],
    ["pantry_door_contact_state", "none", "smart_home", "contact"],
    ["refrigerator_door_contact_state", "none", "smart_home", "contact"],
    ["medication_cabinet_contact_state", "none", "smart_home", "contact"],
    ["smart_plug_tv_power", "watt", "smart_home", "power"],
    ["calendar_busy_minutes", "minutes", "calendar", "calendar"],
  ];
  for (let day = 0; day < 30; day += 1) {
    const daily = dailyRecord(day);
    for (let sample = 0; sample < 9; sample += 1) {
      for (const [entity, unit, source, domain] of entities) {
        const hour = String((sample * 2 + Math.floor(noise(day, sample) * 2)) % 24).padStart(2, "0");
        const minute = String(Math.floor(noise(day + sample, 2) * 60)).padStart(2, "0");
        let state: string | number = "off";
        if (entity === "phone_battery_level") state = Math.round(30 + noise(day + sample, 3) * 70);
        else if (entity === "phone_screen_state") state = noise(day + sample, 4) > 0.55 ? "on" : "off";
        else if (entity === "phone_app_foreground_package") state = ["com.messages", "com.browser", "com.music", "com.health"][sample % 4];
        else if (entity === "phone_zone_label") state = ["springfield_home", "power_plant_area", "moes_area", "kwik_e_mart_area"][sample % 4];
        else if (entity === "wearable_heart_rate") state = Math.round(Number(daily.resting_heart_rate) + noise(day + sample, 7) * 35);
        else if (entity === "wearable_steps") state = Math.round(Number(daily.steps) / 9 + noise(day + sample, 8) * 200);
        else if (entity.includes("contact_state")) state = noise(day + sample, 9) > 0.72 ? "open" : "closed";
        else if (entity === "smart_plug_tv_power") state = Math.round(noise(day + sample, 10) * 140);
        else if (entity === "calendar_busy_minutes") state = Math.round(Number(daily.meeting_minutes) / 9);
        records.push({
          timestamp: `${dayDate(day)} ${hour}:${minute}:00`,
          patient_id: "synthetic-patient-001",
          entity_id: entity,
          state,
          unit,
          source,
          domain,
        });
      }
    }
  }
  return records;
}

function datasetRecords(datasetId?: unknown): JsonRecord[] {
  const id = typeof datasetId === "string" ? datasetId : DEFAULT_DATASET_ID;
  if (id === DEFAULT_DATASET_ID) return dailyRecords();
  if (id === RAW_DATASET_ID) return rawEventRecords();
  if (id === HOMER_DAILY_100_ID) return homerDailyRecords();
  if (id === HOMER_HA_30_ID || id === HOMER_SQLITE_30_ID || id === HOMER_HA_100_ID) {
    return homerDailyRecords();
  }
  throw new Error(`Unknown dataset_id '${String(id)}'. Known dataset_ids: ${BUNDLED_DATASET_IDS.join(", ")}.`);
}

function assertPublicArgs(args: JsonRecord): void {
  if (Array.isArray(args.data_records)) {
    throw new Error(PUBLIC_DATA_ERROR);
  }
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function numericValues(records: JsonRecord[], column: string): number[] {
  return records.map((record) => asNumber(record[column])).filter((value): value is number => value !== null);
}

function mean(values: number[]): number {
  if (values.length === 0) return Number.NaN;
  return values.reduce((total, value) => total + value, 0) / values.length;
}

function numericSummary(values: number[]) {
  if (values.length === 0) return { n: 0 };
  const avg = mean(values);
  const variance = values.length > 1 ? mean(values.map((value) => (value - avg) ** 2)) : 0;
  return {
    n: values.length,
    mean: round(avg),
    sd: round(Math.sqrt(variance)),
    min: round(Math.min(...values)),
    max: round(Math.max(...values)),
  };
}

function correlation(x: number[], y: number[]): number | null {
  const n = Math.min(x.length, y.length);
  if (n < 3) return null;
  const xSlice = x.slice(0, n);
  const ySlice = y.slice(0, n);
  const xMean = mean(xSlice);
  const yMean = mean(ySlice);
  let numerator = 0;
  let xDenominator = 0;
  let yDenominator = 0;
  for (let index = 0; index < n; index += 1) {
    const xd = xSlice[index] - xMean;
    const yd = ySlice[index] - yMean;
    numerator += xd * yd;
    xDenominator += xd * xd;
    yDenominator += yd * yd;
  }
  const denominator = Math.sqrt(xDenominator * yDenominator);
  return denominator === 0 ? null : numerator / denominator;
}

function slope(x: number[], y: number[]): number {
  const n = Math.min(x.length, y.length);
  if (n < 3) return 0;
  const xSlice = x.slice(0, n);
  const ySlice = y.slice(0, n);
  const xMean = mean(xSlice);
  const yMean = mean(ySlice);
  let numerator = 0;
  let denominator = 0;
  for (let index = 0; index < n; index += 1) {
    numerator += (xSlice[index] - xMean) * (ySlice[index] - yMean);
    denominator += (xSlice[index] - xMean) ** 2;
  }
  return denominator === 0 ? 0 : numerator / denominator;
}

function toolResult(payload: unknown) {
  return {
    content: [{ type: "text", text: JSON.stringify(payload) }],
    structuredContent: payload,
  };
}

function toolDefinitions() {
  const datasetProps = {
    dataset_id: {
      type: "string",
      enum: [...BUNDLED_DATASET_IDS],
      description: "Bundled synthetic dataset id. Caller-supplied records are disabled on the public endpoint.",
    },
  };
  const variableList = { type: "array", items: { type: "string" } };
  return [
    toolDef("get_available_datasets", "List bundled synthetic datasets available in the public demo.", {}),
    toolDef("get_available_scenarios", "List supported causal-analysis scenarios.", {}),
    toolDef("describe_patient_data", "Summarize a bundled synthetic patient dataset.", {
      ...datasetProps,
      variables: variableList,
    }),
    toolDef("propose_causal_question", "Suggest causal questions from available synthetic variables.", {
      ...datasetProps,
      user_goal: { type: "string" },
    }),
    toolDef("estimate_causal_effect", "Estimate a simple causal contrast on a bundled synthetic dataset.", {
      ...datasetProps,
      exposure: { type: "string" },
      outcome: { type: "string" },
      treatment_rule: { type: "object" },
      adjustment_variables: variableList,
      method: { type: "string", enum: ["regression_adjustment", "ipw", "g_formula", "doubly_robust"] },
      contrast: { type: "object" },
    }),
    toolDef("run_target_trial_emulation", "Emulate a simple repeated daily target trial on synthetic data.", {
      ...datasetProps,
      eligibility_criteria: { type: "object" },
      treatment_strategies: { type: "array", items: { type: "object" } },
      assignment_time: { type: ["string", "object"] },
      follow_up_days: { type: "number" },
      outcome: { type: "string" },
      adjustment_variables: variableList,
      method: { type: "string" },
    }),
    toolDef("generate_causal_dag", "Return scenario DAG nodes, edges, DOT, and Mermaid text.", {
      scenario: { type: "string" },
      variables: variableList,
    }),
    toolDef("check_adjustment_set", "Check a simplified DAG adjustment set.", {
      dag_edges: { type: "array", items: { type: "object" } },
      exposure: { type: "string" },
      outcome: { type: "string" },
      adjustment_variables: variableList,
    }),
    toolDef("simulate_intervention", "Simulate a behavioral intervention on synthetic data.", {
      ...datasetProps,
      intervention_name: { type: "string" },
      intervention_rule: { type: "object" },
      target_variable: { type: "string" },
      expected_change: { type: "number" },
      outcome: { type: "string" },
      method: { type: "string" },
      adjustment_variables: variableList,
    }),
    toolDef("export_dataset", "Export a bundled synthetic dataset as CSV text or JSON records.", {
      ...datasetProps,
      format: { type: "string", enum: ["csv", "json", "sql"] },
      table: { type: "string", enum: ["daily", "states", "states_meta", "state_attributes", "flattened", "normalized"] },
    }),
    toolDef("query_ha_states", "Query synthetic Home Assistant-style state history.", {
      ...datasetProps,
      entity_id: { type: "string" },
      domain: { type: "string" },
      start: { type: "string" },
      end: { type: "string" },
      limit: { type: "number" },
      include_attributes: { type: "boolean" },
      parse_numeric: { type: "boolean" },
    }),
    toolDef("aggregate_ha_states_daily", "Aggregate synthetic HA-style states into daily rows.", {
      ...datasetProps,
      entity_ids: variableList,
      aggregation_config: { type: "object" },
    }),
  ];
}

function toolDef(name: ToolName, description: string, properties: JsonRecord) {
  return {
    name,
    description,
    inputSchema: {
      type: "object",
      properties,
      additionalProperties: false,
    },
  };
}

function callTool(name: string, rawArgs: JsonRecord = {}) {
  assertPublicArgs(rawArgs);
  if (!TOOL_NAMES.includes(name as ToolName)) {
    throw new Error(`Unknown tool '${name}'.`);
  }
  switch (name as ToolName) {
    case "get_available_datasets":
      return toolResult(getAvailableDatasets());
    case "get_available_scenarios":
      return toolResult({ scenarios: SCENARIOS });
    case "describe_patient_data":
      return toolResult(describePatientData(rawArgs));
    case "propose_causal_question":
      return toolResult(proposeCausalQuestion(rawArgs));
    case "estimate_causal_effect":
      return toolResult(estimateCausalEffect(rawArgs));
    case "run_target_trial_emulation":
      return toolResult(runTargetTrial(rawArgs));
    case "generate_causal_dag":
      return toolResult(generateCausalDag(rawArgs));
    case "check_adjustment_set":
      return toolResult(checkAdjustmentSet(rawArgs));
    case "simulate_intervention":
      return toolResult(simulateIntervention(rawArgs));
    case "export_dataset":
      return toolResult(exportDataset(rawArgs));
    case "query_ha_states":
      return toolResult(queryHaStates(rawArgs));
    case "aggregate_ha_states_daily":
      return toolResult(aggregateHaStatesDaily(rawArgs));
  }
}

function getAvailableDatasets() {
  return {
    default_dataset_id: DEFAULT_DATASET_ID,
    datasets: [
      {
        dataset_id: DEFAULT_DATASET_ID,
        filename: "generated_patient_001_100_days.csv",
        dataset_type: "analysis_ready_daily",
        patient_id: "synthetic-patient-001",
        days: 100,
        date_range: { start: "2026-01-01", end: "2026-04-10" },
        columns: DAILY_COLUMNS.length,
        source: "Deterministic synthetic data generated inside the public Cloudflare Worker.",
      },
      {
        dataset_id: RAW_DATASET_ID,
        filename: "generated_patient_001_raw_events_30_days.csv",
        dataset_type: "raw_events_long_format",
        patient_id: "synthetic-patient-001",
        days: 30,
        rows: rawEventRecords().length,
        source: "Deterministic synthetic sensor/event data generated inside the public Cloudflare Worker.",
      },
      {
        dataset_id: HOMER_HA_30_ID,
        dataset_type: "home_assistant_recorder_states",
        synthetic_subject: "homer_simpson",
        synthetic_profile: "fictional_parody",
        days: 30,
        rows: 62000,
        rows_estimated_until_generated: true,
        date_range: { start: "2026-01-01T00:00:00-05:00", end: "2026-01-30T23:59:59-05:00" },
        tables_available: ["states", "states_meta", "state_attributes", "flattened", "daily"],
        source: "Synthetic Home Assistant Recorder-inspired demo data. Public Worker serves a lightweight queryable subset.",
        privacy_note: "Synthetic parody data only. Not official Simpsons data and not real personal data.",
      },
      {
        dataset_id: HOMER_HA_100_ID,
        dataset_type: "home_assistant_recorder_states",
        synthetic_subject: "homer_simpson",
        synthetic_profile: "fictional_parody",
        days: 100,
        rows: 250000,
        rows_estimated_until_generated: true,
        date_range: { start: "2026-01-01T00:00:00-05:00", end: "2026-04-10T23:59:59-05:00" },
        tables_available: ["states", "states_meta", "state_attributes", "flattened", "daily"],
        source: "Synthetic Home Assistant Recorder-inspired demo data. Public Worker serves a lightweight queryable subset.",
        privacy_note: "Synthetic parody data only. Not official Simpsons data and not real personal data.",
      },
      {
        dataset_id: HOMER_DAILY_100_ID,
        dataset_type: "analysis_ready_daily",
        synthetic_subject: "homer_simpson",
        synthetic_profile: "fictional_parody",
        days: 100,
        rows: 100,
        date_range: { start: "2026-01-01", end: "2026-04-10" },
        tables_available: ["daily"],
        source: "Deterministic synthetic Homer parody daily causal dataset.",
        privacy_note: "Synthetic parody data only. Not official Simpsons data and not real personal data.",
      },
      {
        dataset_id: HOMER_SQLITE_30_ID,
        dataset_type: "home_assistant_recorder_sql_demo",
        synthetic_subject: "homer_simpson",
        synthetic_profile: "fictional_parody",
        days: 30,
        rows: 62000,
        rows_estimated_until_generated: true,
        date_range: { start: "2026-01-01T00:00:00-05:00", end: "2026-01-30T23:59:59-05:00" },
        tables_available: ["sql_dump", "states", "states_meta", "state_attributes"],
        source: "Synthetic SQL-dump-style Home Assistant Recorder demo.",
        privacy_note: "Synthetic parody data only. Not official Simpsons data and not real personal data.",
      },
    ],
    loaded_dataset_ids: [...BUNDLED_DATASET_IDS],
    public_endpoint_note: "The public Cloudflare endpoint rejects caller-supplied data_records.",
  };
}

function describePatientData(args: JsonRecord) {
  const datasetId = typeof args.dataset_id === "string" ? args.dataset_id : DEFAULT_DATASET_ID;
  if (datasetId === HOMER_HA_30_ID || datasetId === HOMER_HA_100_ID || datasetId === HOMER_SQLITE_30_ID) {
    return describeHaDataset(datasetId);
  }
  const records = datasetRecords(args.dataset_id);
  const variables =
    Array.isArray(args.variables) && args.variables.length > 0
      ? args.variables.map(String)
      : Object.keys(records[0] ?? {});
  const numericSummaries: JsonRecord = {};
  const binaryCounts: JsonRecord = {};
  const missingness: JsonRecord = {};

  for (const variable of variables) {
    const values = records.map((record) => record[variable]);
    const missing = values.filter((value) => value === null || value === undefined || value === "").length;
    missingness[variable] = { missing_count: missing, missing_fraction: round(missing / Math.max(values.length, 1)) };
    const numbers = numericValues(records, variable);
    if (numbers.length > 0) {
      const unique = new Set(numbers);
      if ([...unique].every((value) => value === 0 || value === 1)) {
        binaryCounts[variable] = {
          "0": numbers.filter((value) => value === 0).length,
          "1": numbers.filter((value) => value === 1).length,
        };
      } else {
        numericSummaries[variable] = numericSummary(numbers);
      }
    }
  }

  const dates = records.map((record) => String(record.date ?? record.timestamp ?? "")).filter(Boolean);
  const numericVariables = variables.filter((variable) => numericValues(records, variable).length >= 10);
  const correlationHighlights = [];
  for (let left = 0; left < Math.min(numericVariables.length, 6); left += 1) {
    for (let right = left + 1; right < Math.min(numericVariables.length, 8); right += 1) {
      const value = correlation(numericValues(records, numericVariables[left]), numericValues(records, numericVariables[right]));
      if (value !== null && Math.abs(value) >= 0.55) {
        correlationHighlights.push({
          variable_a: numericVariables[left],
          variable_b: numericVariables[right],
          correlation: round(value),
        });
      }
    }
  }

  return {
    number_of_days: args.dataset_id === RAW_DATASET_ID ? 30 : records.length,
    number_of_records: records.length,
    date_range: { start: dates[0] ?? null, end: dates[dates.length - 1] ?? null },
    missingness_summary: missingness,
    numeric_summaries: numericSummaries,
    binary_counts: binaryCounts,
    correlation_highlights: correlationHighlights.slice(0, 10),
    time_trend_highlights: [],
    warning: "Correlation and time trends are descriptive only; they do not prove causation.",
  };
}

function describeHaDataset(datasetId: string) {
  const rows = homerHaStates(datasetId);
  const domainCounts: JsonRecord = {};
  const entityCounts: JsonRecord = {};
  for (const row of rows) {
    const domain = String(row.domain);
    const entity = String(row.entity_id);
    domainCounts[domain] = Number(domainCounts[domain] ?? 0) + 1;
    entityCounts[entity] = Number(entityCounts[entity] ?? 0) + 1;
  }
  return {
    dataset_id: datasetId,
    dataset_type: "home_assistant_recorder_states",
    synthetic_subject: "homer_simpson",
    states_rows: rows.length,
    unique_entities: HOMER_HA_ENTITIES.length,
    states_meta_rows: HOMER_HA_ENTITIES.length,
    state_attributes_rows: HOMER_HA_ENTITIES.length,
    date_range: {
      start: rows[0]?.iso_timestamp ?? null,
      end: rows[rows.length - 1]?.iso_timestamp ?? null,
    },
    domain_counts: domainCounts,
    top_entities_by_row_count: entityCounts,
    missingness_summary: { state: { missing_count: 0, missing_fraction: 0 } },
    numeric_summaries: {
      "sensor.homer_watch_heart_rate": numericSummary(
        rows
          .filter((row) => row.entity_id === "sensor.homer_watch_heart_rate")
          .map((row) => Number(row.state)),
      ),
      "sensor.homer_watch_steps": numericSummary(
        rows.filter((row) => row.entity_id === "sensor.homer_watch_steps").map((row) => Number(row.state)),
      ),
    },
    binary_counts: {
      "binary_sensor.refrigerator_door_contact": {
        on: rows.filter((row) => row.entity_id === "binary_sensor.refrigerator_door_contact" && row.state === "on").length,
        off: rows.filter((row) => row.entity_id === "binary_sensor.refrigerator_door_contact" && row.state === "off").length,
      },
    },
    warning: "Synthetic parody Home Assistant-style data only; correlations are descriptive.",
  };
}

function proposeCausalQuestion(args: JsonRecord) {
  const goal = typeof args.user_goal === "string" ? args.user_goal.toLowerCase() : "";
  const scenarios = [...SCENARIOS].sort((a, b) => {
    if (!goal) return 0;
    return Number(b.causal_question.toLowerCase().includes(goal)) - Number(a.causal_question.toLowerCase().includes(goal));
  });
  return {
    user_goal: args.user_goal ?? null,
    proposed_questions: scenarios.map((scenario) => ({
      question: scenario.causal_question,
      exposure: scenario.exposure,
      outcome: scenario.outcome,
      adjustment_variables: scenario.adjustment_variables,
      variables_to_avoid_adjusting_for: scenario.mediators,
      why_meaningful: scenario.expected_direction,
    })),
    note: "Question proposals assume correct temporal alignment and sufficient within-person variation.",
  };
}

function estimateCausalEffect(args: JsonRecord) {
  const records = datasetRecords(args.dataset_id);
  const exposure = String(args.exposure ?? "intervention_received");
  const outcome = String(args.outcome ?? "outcome_sleep_quality");
  const x = numericValues(records, exposure);
  const y = numericValues(records, outcome);
  if (x.length < 3 || y.length < 3) {
    throw new Error(`Exposure '${exposure}' and outcome '${outcome}' must be numeric columns in the selected dataset.`);
  }

  const rule = (args.treatment_rule && typeof args.treatment_rule === "object" ? args.treatment_rule : {}) as JsonRecord;
  const ruleType = String(rule.type ?? "binary_variable");
  let treated: number[] = [];
  let untreated: number[] = [];
  let comparison = `${exposure}=1 versus ${exposure}=0`;

  if (ruleType === "binary_threshold") {
    const threshold = asNumber(rule.threshold) ?? mean(x);
    const condition = String(rule.treated_condition ?? ">=");
    records.forEach((record) => {
      const xv = asNumber(record[exposure]);
      const yv = asNumber(record[outcome]);
      if (xv === null || yv === null) return;
      const isTreated = condition.includes("<") ? xv <= threshold : xv >= threshold;
      (isTreated ? treated : untreated).push(yv);
    });
    comparison = `${exposure} ${condition} ${round(threshold)} versus the complement`;
  } else if (ruleType === "set_value") {
    const valueA = asNumber(rule.value_a) ?? mean(x) + 1;
    const valueB = asNumber(rule.value_b) ?? mean(x) - 1;
    const estimatedEffect = slope(x, y) * (valueA - valueB);
    return {
      method: String(args.method ?? "regression_adjustment"),
      exposure,
      outcome,
      treatment_definition: { rule, comparison: `${exposure} set to ${valueA} versus ${valueB}` },
      adjustment_variables: Array.isArray(args.adjustment_variables) ? args.adjustment_variables : [],
      estimated_effect: round(estimatedEffect),
      effect_scale: `Mean difference in ${outcome}.`,
      sample_size_used: Math.min(x.length, y.length),
      assumptions: standardAssumptions(),
      diagnostic_warnings: ["Public Worker uses a lightweight deterministic estimator for the synthetic demo."],
      plain_language_interpretation: `In the synthetic public dataset, this contrast is associated with an estimated ${round(estimatedEffect)} unit change in ${outcome}.`,
    };
  } else {
    records.forEach((record) => {
      const xv = asNumber(record[exposure]);
      const yv = asNumber(record[outcome]);
      if (xv === null || yv === null) return;
      (xv >= 0.5 ? treated : untreated).push(yv);
    });
  }

  const estimatedEffect = mean(treated) - mean(untreated);
  return {
    method: String(args.method ?? "regression_adjustment"),
    exposure,
    outcome,
    treatment_definition: { rule, comparison },
    adjustment_variables: Array.isArray(args.adjustment_variables) ? args.adjustment_variables : [],
    estimated_effect: round(estimatedEffect),
    effect_scale: `Mean difference in ${outcome} for treated versus untreated synthetic days.`,
    confidence_interval: null,
    standard_error: null,
    sample_size_used: treated.length + untreated.length,
    rows_dropped: records.length - treated.length - untreated.length,
    assumptions: standardAssumptions(),
    limitations: [
      "The public Worker uses lightweight JavaScript estimators to stay within Cloudflare free plan limits.",
      "The data are synthetic and are not medical advice.",
    ],
    diagnostic_warnings: treated.length === 0 || untreated.length === 0 ? ["One treatment group has no rows."] : [],
    plain_language_interpretation: `In the synthetic public dataset, ${comparison} is associated with an estimated ${round(estimatedEffect)} unit change in ${outcome}.`,
  };
}

function standardAssumptions() {
  return [
    "Consistency: the observed exposure version matches the treatment definition.",
    "Conditional exchangeability after the stated adjustment set.",
    "Positivity: both treatment conditions occur in the synthetic dataset.",
    "Correct temporal alignment of exposure, covariates, and outcome.",
  ];
}

function runTargetTrial(args: JsonRecord) {
  const strategies = Array.isArray(args.treatment_strategies) ? args.treatment_strategies : [];
  const first = (strategies[0] ?? {}) as JsonRecord;
  const second = (strategies[1] ?? {}) as JsonRecord;
  const exposure = String(first.variable ?? second.variable ?? "intervention_received");
  const treatmentRule =
    first.threshold !== undefined
      ? { type: "binary_threshold", variable: exposure, threshold: first.threshold, treated_condition: first.condition ?? ">=" }
      : { type: "binary_variable", variable: exposure };
  const estimate = estimateCausalEffect({
    dataset_id: args.dataset_id,
    exposure,
    outcome: args.outcome ?? "outcome_sleep_quality",
    treatment_rule: treatmentRule,
    adjustment_variables: args.adjustment_variables,
    method: args.method ?? "g_formula",
  });
  return {
    trial_protocol: {
      design: "Repeated daily N-of-1 target trial emulation",
      assignment_time: args.assignment_time ?? "8 PM reminder decision",
      follow_up_days: args.follow_up_days ?? 1,
      outcome: args.outcome ?? "outcome_sleep_quality",
    },
    eligibility_criteria: args.eligibility_criteria ?? {},
    treatment_strategies: strategies,
    number_eligible: dailyRecords().length,
    causal_estimate: estimate,
    immortal_time_bias_warning: [
      "Time zero should be defined before the outcome window starts; this public demo assumes daily pre-outcome assignment.",
    ],
  };
}

function generateCausalDag(args: JsonRecord) {
  const scenario = SCENARIOS.find((item) => item.id === String(args.scenario ?? "mixed_lifestyle")) ?? SCENARIOS[5];
  const confounders = scenario.adjustment_variables.slice(0, 4);
  const edges = [
    ...confounders.flatMap((variable) => [
      { source: variable, target: scenario.exposure },
      { source: variable, target: scenario.outcome },
    ]),
    { source: scenario.exposure, target: scenario.outcome },
    ...scenario.mediators.map((mediator) => ({ source: scenario.exposure, target: mediator })),
    ...scenario.mediators.map((mediator) => ({ source: mediator, target: scenario.outcome })),
  ];
  const nodes = [...new Set(edges.flatMap((edge) => [edge.source, edge.target]))];
  return {
    scenario: scenario.id,
    exposure: scenario.exposure,
    outcome: scenario.outcome,
    nodes,
    edges,
    minimally_sufficient_adjustment_set: confounders,
    variables_not_to_adjust_for: scenario.mediators,
    dot: `digraph { ${edges.map((edge) => `"${edge.source}" -> "${edge.target}"`).join("; ")}; }`,
    mermaid: `graph TD\n${edges.map((edge) => `  ${edge.source}-->${edge.target}`).join("\n")}`,
  };
}

function checkAdjustmentSet(args: JsonRecord) {
  const edges = Array.isArray(args.dag_edges) ? (args.dag_edges as JsonRecord[]) : [];
  const exposure = String(args.exposure ?? "");
  const outcome = String(args.outcome ?? "");
  const adjustment = new Set((Array.isArray(args.adjustment_variables) ? args.adjustment_variables : []).map(String));
  const parentsOfExposure = new Set(edges.filter((edge) => edge.target === exposure).map((edge) => String(edge.source)));
  const parentsOfOutcome = new Set(edges.filter((edge) => edge.target === outcome).map((edge) => String(edge.source)));
  const likelyConfounders = [...parentsOfExposure].filter((node) => parentsOfOutcome.has(node));
  const mediators = edges
    .filter((edge) => edge.source === exposure)
    .map((edge) => String(edge.target))
    .filter((node) => edges.some((edge) => edge.source === node && edge.target === outcome));
  return {
    exposure,
    outcome,
    adjustment_variables: [...adjustment],
    likely_confounders: likelyConfounders,
    missing_likely_confounders: likelyConfounders.filter((node) => !adjustment.has(node)),
    adjusted_mediators: mediators.filter((node) => adjustment.has(node)),
    appears_reasonable:
      likelyConfounders.every((node) => adjustment.has(node)) && mediators.every((node) => !adjustment.has(node)),
    note: "This is a simplified graph check for the public synthetic demo.",
  };
}

function simulateIntervention(args: JsonRecord) {
  const records = datasetRecords(args.dataset_id);
  const target = String(args.target_variable ?? "late_night_screen_minutes");
  const outcome = String(args.outcome ?? "outcome_sleep_quality");
  const expectedChange = asNumber(args.expected_change) ?? 0;
  const baseline = mean(numericValues(records, outcome));
  const predictedDifference = slope(numericValues(records, target), numericValues(records, outcome)) * expectedChange;
  return {
    intervention_name: args.intervention_name ?? "Synthetic public intervention",
    target_variable: target,
    outcome,
    method: args.method ?? "g_formula",
    baseline_predicted_outcome: round(baseline),
    intervention_predicted_outcome: round(baseline + predictedDifference),
    estimated_difference: round(predictedDifference),
    uncertainty: "Not computed for the lightweight public Worker.",
    assumptions: standardAssumptions(),
    plain_language_summary: `In the synthetic public dataset, changing ${target} by ${expectedChange} is associated with an estimated ${round(predictedDifference)} unit change in ${outcome}.`,
    caution: "Synthetic demo output only; not medical advice.",
  };
}

function queryHaStates(args: JsonRecord) {
  const datasetId = typeof args.dataset_id === "string" ? args.dataset_id : HOMER_HA_30_ID;
  if (datasetId !== HOMER_HA_30_ID && datasetId !== HOMER_HA_100_ID && datasetId !== HOMER_SQLITE_30_ID) {
    throw new Error("query_ha_states only supports Homer synthetic HA-style dataset IDs.");
  }
  const limit = Math.max(1, Math.min(10000, Math.round(asNumber(args.limit) ?? 1000)));
  const includeAttributes = args.include_attributes === true;
  const parseNumeric = args.parse_numeric === true;
  const startTs = typeof args.start === "string" ? Date.parse(args.start) / 1000 : null;
  const endTs = typeof args.end === "string" ? Date.parse(args.end) / 1000 : null;
  let rows = homerHaStates(datasetId);
  if (typeof args.entity_id === "string") {
    rows = rows.filter((row) => row.entity_id === args.entity_id);
  }
  if (typeof args.domain === "string") {
    rows = rows.filter((row) => row.domain === args.domain);
  }
  if (startTs !== null && Number.isFinite(startTs)) {
    rows = rows.filter((row) => Number(row.last_updated_ts) >= startTs);
  }
  if (endTs !== null && Number.isFinite(endTs)) {
    rows = rows.filter((row) => Number(row.last_updated_ts) <= endTs);
  }
  const attributes = Object.fromEntries(homerStateAttributeRows().map((row) => [String(row.attributes_id), JSON.parse(String(row.shared_attrs))]));
  const output = rows.slice(0, limit).map((row) => {
    const item: JsonRecord = { ...row };
    if (includeAttributes) item.attributes = attributes[String(row.attributes_id)];
    if (parseNumeric) item.numeric_state = asNumber(row.state);
    return item;
  });
  return {
    dataset_id: datasetId,
    table: "states",
    entity_id: args.entity_id ?? null,
    domain: args.domain ?? null,
    rows_returned: output.length,
    truncated: rows.length > limit,
    date_range: {
      start: datasetId === HOMER_HA_100_ID ? "2026-01-01T00:00:00-05:00" : "2026-01-01T00:00:00-05:00",
      end: datasetId === HOMER_HA_100_ID ? "2026-04-10T23:59:59-05:00" : "2026-01-30T23:59:59-05:00",
    },
    metadata_summary: {
      states_rows_matched: rows.length,
      unique_entities_matched: new Set(rows.map((row) => row.entity_id)).size,
      public_worker_note: "The Worker serves a compact deterministic subset; the Python MCP generates the full raw table.",
    },
    rows: output,
  };
}

function aggregateHaStatesDaily(args: JsonRecord) {
  const datasetId = typeof args.dataset_id === "string" ? args.dataset_id : HOMER_HA_30_ID;
  if (datasetId !== HOMER_HA_30_ID && datasetId !== HOMER_HA_100_ID && datasetId !== HOMER_SQLITE_30_ID) {
    throw new Error("aggregate_ha_states_daily only supports Homer synthetic HA-style dataset IDs.");
  }
  const days = datasetId === HOMER_HA_100_ID ? 100 : 30;
  return {
    dataset_id: datasetId,
    source_table: "states",
    daily_rows: homerDailyRecords().slice(0, days),
    rows_returned: days,
    aggregation_rules_used: {
      steps: "last daily cumulative value",
      heart_rate: "mean and max from periodic wearable states",
      tv_minutes: "duration of switch.living_room_tv on",
      zone_minutes: "duration in fictional device_tracker zones",
    },
    entity_ids_requested: Array.isArray(args.entity_ids) ? args.entity_ids : [],
    aggregation_config: args.aggregation_config ?? {},
    warnings: [
      "Public Worker returns a compact deterministic aggregate; the Python MCP has the full raw-state aggregation.",
    ],
  };
}

function homerExportRows(datasetId: string, table: string): JsonRecord[] {
  if (table === "states") return homerHaStates(datasetId);
  if (table === "states_meta") return homerStatesMeta(datasetId);
  if (table === "state_attributes") return homerStateAttributeRows();
  if (table === "flattened") {
    const attrs = Object.fromEntries(homerStateAttributeRows().map((row) => [String(row.attributes_id), String(row.shared_attrs)]));
    return homerHaStates(datasetId).map((row) => ({
      iso_timestamp: row.iso_timestamp,
      last_updated_ts: row.last_updated_ts,
      date: row.date,
      entity_id: row.entity_id,
      domain: row.domain,
      state: row.state,
      unit: row.unit,
      source: row.source,
      attributes_json: attrs[String(row.attributes_id)],
    }));
  }
  if (table === "daily") return homerDailyRecords().slice(0, datasetId === HOMER_HA_100_ID ? 100 : 30);
  throw new Error(`Unknown Homer export table '${table}'.`);
}

function homerSqlDump(datasetId: string): string {
  const states = homerHaStates(datasetId);
  const meta = homerStatesMeta(datasetId);
  const attrs = homerStateAttributeRows();
  const lines = [
    "CREATE TABLE states_meta (metadata_id INTEGER PRIMARY KEY, entity_id TEXT UNIQUE, domain TEXT, object_id TEXT, first_seen_ts REAL, last_seen_ts REAL);",
    "CREATE TABLE state_attributes (attributes_id INTEGER PRIMARY KEY, hash INTEGER, shared_attrs TEXT);",
    "CREATE TABLE states (state_id INTEGER PRIMARY KEY, metadata_id INTEGER, entity_id TEXT, state TEXT, attributes_id INTEGER, last_changed_ts REAL, last_updated_ts REAL, last_reported_ts REAL, old_state_id INTEGER, context_id_bin TEXT, context_user_id_bin TEXT, context_parent_id_bin TEXT, origin_idx INTEGER, iso_timestamp TEXT, date TEXT, source TEXT, domain TEXT, unit TEXT);",
  ];
  for (const [table, rows] of [
    ["states_meta", meta],
    ["state_attributes", attrs],
    ["states", states],
  ] as const) {
    for (const row of rows) {
      const columns = Object.keys(row);
      lines.push(`INSERT INTO ${table} (${columns.join(", ")}) VALUES (${columns.map((column) => sqlLiteral(row[column])).join(", ")});`);
    }
  }
  return lines.join("\n");
}

function sqlLiteral(value: unknown): string {
  if (value === null || value === undefined) return "NULL";
  if (typeof value === "number") return String(value);
  return `'${String(value).replaceAll("'", "''")}'`;
}

function exportDataset(args: JsonRecord) {
  const datasetId = typeof args.dataset_id === "string" ? args.dataset_id : DEFAULT_DATASET_ID;
  const format = String(args.format ?? "csv");
  const table = String(args.table ?? "daily");
  if (datasetId === HOMER_HA_30_ID || datasetId === HOMER_HA_100_ID || datasetId === HOMER_SQLITE_30_ID) {
    if (format === "sql") {
      return {
        serialized_dataset: homerSqlDump(datasetId),
        format,
        table: "normalized",
        filename_suggestion: `${datasetId}.sql`,
        privacy_note: "Synthetic parody data only. Not official Simpsons data and not real personal data.",
      };
    }
    if (format === "json" && table === "normalized") {
      return {
        serialized_dataset: {
          states: homerHaStates(datasetId),
          states_meta: homerStatesMeta(datasetId),
          state_attributes: homerStateAttributeRows(),
        },
        format,
        table,
        filename_suggestion: `${datasetId}_normalized.json`,
      };
    }
    const records = homerExportRows(datasetId, table);
    if (format === "json") {
      return {
        serialized_dataset: records,
        format,
        table,
        filename_suggestion: `${datasetId}_${table}.json`,
      };
    }
    if (format !== "csv") throw new Error("format must be 'csv', 'json', or 'sql'.");
    return {
      serialized_dataset: csvForRecords(records),
      format,
      table,
      filename_suggestion: `${datasetId}_${table}.csv`,
    };
  }
  const records = datasetRecords(datasetId);
  if (format === "json") {
    return {
      serialized_dataset: records,
      filename_suggestion: `${datasetId}.json`,
      variable_dictionary: Object.fromEntries(Object.keys(records[0] ?? {}).map((key) => [key, "Synthetic public demo variable."])),
    };
  }
  if (format !== "csv") throw new Error("format must be 'csv' or 'json'.");
  const columns = Object.keys(records[0] ?? {});
  const rows = records.map((record) => columns.map((column) => csvCell(record[column])).join(","));
  return {
    serialized_dataset: [columns.join(","), ...rows].join("\n"),
    filename_suggestion: `${datasetId}.csv`,
    variable_dictionary: Object.fromEntries(columns.map((key) => [key, "Synthetic public demo variable."])),
  };
}

function csvForRecords(records: JsonRecord[]): string {
  const columns = Object.keys(records[0] ?? {});
  const rows = records.map((record) => columns.map((column) => csvCell(record[column])).join(","));
  return [columns.join(","), ...rows].join("\n");
}

function csvCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function rpcResponse(id: RpcRequest["id"], result: unknown) {
  return { jsonrpc: "2.0", id, result };
}

function rpcError(id: RpcRequest["id"], code: number, message: string) {
  return { jsonrpc: "2.0", id: id ?? null, error: { code, message } };
}

async function handleMcp(request: Request): Promise<Response> {
  if (request.method === "OPTIONS") {
    const rejected = rejectPreflight(request);
    return rejected ?? emptyResponse(request);
  }
  if (request.method === "DELETE") return emptyResponse(request);
  if (request.method === "GET") {
    return new Response("GET streaming is not used by this stateless public MCP demo.", {
      status: 405,
      headers: { Allow: "POST,DELETE,OPTIONS", ...securityHeaders(), ...corsHeaders(request) },
    });
  }
  if (request.method !== "POST") {
    return jsonResponse(request, { ok: false, error: "method_not_allowed" }, 405);
  }
  const sizeRejected = rejectBodySize(request);
  if (sizeRejected) return sizeRejected;

  const body = await request.text();
  if (body.length > MAX_MCP_REQUEST_BODY_BYTES) {
    return jsonResponse(request, { ok: false, error: "request_body_too_large", max_bytes: MAX_MCP_REQUEST_BODY_BYTES }, 413);
  }

  let message: RpcRequest;
  try {
    message = JSON.parse(body) as RpcRequest;
  } catch {
    return jsonResponse(request, rpcError(null, -32700, "Parse error"), 400);
  }

  if (!message.id && message.method?.startsWith("notifications/")) {
    return emptyResponse(request, 202);
  }

  try {
    if (message.method === "initialize") {
      return jsonResponse(
        request,
        rpcResponse(message.id, {
          protocolVersion: "2025-06-18",
          capabilities: { tools: { listChanged: false } },
          serverInfo: { name: "patient-causal-mcp", version: "0.1.0-cloudflare-public" },
          instructions: "Public synthetic-only MCP demo. Caller-supplied data_records are disabled.",
        }),
        200,
        { "Mcp-Session-Id": crypto.randomUUID() },
      );
    }
    if (message.method === "tools/list") {
      return jsonResponse(request, rpcResponse(message.id, { tools: toolDefinitions() }));
    }
    if (message.method === "tools/call") {
      const params = (message.params ?? {}) as JsonRecord;
      const name = String(params.name ?? "");
      const args = (params.arguments && typeof params.arguments === "object" ? params.arguments : {}) as JsonRecord;
      return jsonResponse(request, rpcResponse(message.id, callTool(name, args)));
    }
    return jsonResponse(request, rpcError(message.id, -32601, `Method not found: ${message.method ?? ""}`), 404);
  } catch (error) {
    return jsonResponse(request, rpcError(message.id, -32000, error instanceof Error ? error.message : String(error)), 200);
  }
}

export class MyMCP {
  async fetch(request: Request): Promise<Response> {
    return handleMcp(request);
  }
}

export class PatientCausalMCPServer extends MyMCP {}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      const rejected = rejectPreflight(request);
      return rejected ?? emptyResponse(request);
    }
    if (url.pathname === "/" || url.pathname === "/health") {
      if (!["GET", "HEAD"].includes(request.method)) {
        return jsonResponse(request, { ok: false, error: "method_not_allowed" }, 405);
      }
      return jsonResponse(request, healthPayload());
    }
    if (url.pathname.startsWith("/mcp")) {
      const id = env.N_OF_1_MCP.idFromName("global");
      return env.N_OF_1_MCP.get(id).fetch(request);
    }
    return jsonResponse(
      request,
      {
        ok: false,
        error: "not_found",
        message: "Use the Streamable HTTP MCP endpoint at /mcp.",
        mcp_endpoint: "/mcp",
      },
      404,
    );
  },
};
