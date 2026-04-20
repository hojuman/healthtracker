import logging
from typing import Optional
from .metrics import DailyMetrics, ActivityMetrics

logger = logging.getLogger(__name__)


def parse_daily_metrics(
    date_str: str,
    sleep_data: dict,
    hrv_data: dict,
    rhr_data: dict,
    stats_data: dict,
) -> DailyMetrics:
    m = DailyMetrics(date=date_str)
    _parse_sleep(m, sleep_data)
    _parse_hrv(m, hrv_data)
    _parse_rhr(m, rhr_data, stats_data)
    _parse_stats(m, stats_data)
    return m


def _parse_sleep(m: DailyMetrics, data: dict):
    dto = data.get("dailySleepDTO") or {}
    if not dto:
        return

    scores = dto.get("sleepScores") or {}
    m.sleep_score = _int((scores.get("overall") or {}).get("value"))

    total_secs = dto.get("sleepTimeSeconds")
    if total_secs:
        m.sleep_duration_hours = round(total_secs / 3600, 2)

    deep = dto.get("deepSleepSeconds") or 0
    rem = dto.get("remSleepSeconds") or 0
    light = dto.get("lightSleepSeconds") or 0
    total = deep + rem + light
    if total > 0:
        m.deep_sleep_pct = round(deep / total * 100, 1)
        m.rem_sleep_pct = round(rem / total * 100, 1)
        m.light_sleep_pct = round(light / total * 100, 1)

    m.awake_count = _int((scores.get("awakeCount") or {}).get("value"))
    m.overnight_hr_avg = _int(dto.get("averageHeartRateValue"))

    for note_key in ("notes", "note", "userNote", "sleepNote"):
        note = dto.get(note_key)
        if note:
            m.sleep_notes = str(note).strip()
            break


def _parse_hrv(m: DailyMetrics, data: dict):
    summary = data.get("hrvSummary") or {}
    if not summary:
        return
    m.hrv_status = summary.get("status")
    m.hrv_last_night = _int(summary.get("lastNight"))
    m.hrv_5day_avg = _int(summary.get("weeklyAvg") or summary.get("fiveDayAvg"))


def _parse_rhr(m: DailyMetrics, rhr_data: dict, stats_data: dict):
    m.resting_hr = (
        _int(rhr_data.get("restingHeartRate"))
        or _int(stats_data.get("restingHeartRate"))
        or _int(stats_data.get("minHeartRate"))
    )


def _parse_stats(m: DailyMetrics, data: dict):
    if not data:
        return
    m.avg_stress = _int(data.get("averageStressLevel"))
    m.body_battery_morning = _int(
        data.get("bodyBatteryHighestValue") or data.get("bodyBatteryChargedValue")
    )
    if not m.overnight_hr_avg:
        m.overnight_hr_avg = _int(data.get("averageWellnessHeartRate"))
    m.overnight_hr_min = _int(data.get("minHeartRate"))
    m.overnight_hr_max = _int(data.get("maxHeartRate"))


def parse_activity(raw: dict) -> Optional[ActivityMetrics]:
    activity_id = str(raw.get("activityId", ""))
    if not activity_id:
        return None
    try:
        start = (raw.get("startTimeLocal") or "")[:10]
        duration_secs = raw.get("duration") or 0
        distance_m = raw.get("distance") or 0
        activity_type = (raw.get("activityType") or {}).get("typeKey", "unknown")
        return ActivityMetrics(
            activity_id=activity_id,
            date=start,
            name=raw.get("activityName") or "Unknown",
            activity_type=activity_type,
            duration_minutes=round(duration_secs / 60, 1),
            distance_km=round(distance_m / 1000, 2) if distance_m else None,
            avg_hr=_int(raw.get("averageHR")),
            max_hr=_int(raw.get("maxHR")),
            training_load=raw.get("aerobicTrainingEffect"),
        )
    except Exception as e:
        logger.debug(f"Could not parse activity: {e}")
        return None


def _int(value) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (ValueError, TypeError):
        return None
