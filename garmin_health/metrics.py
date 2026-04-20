from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class DailyMetrics:
    date: str
    sleep_score: Optional[int] = None
    sleep_duration_hours: Optional[float] = None
    deep_sleep_pct: Optional[float] = None
    rem_sleep_pct: Optional[float] = None
    light_sleep_pct: Optional[float] = None
    awake_count: Optional[int] = None
    overnight_hr_min: Optional[int] = None
    overnight_hr_avg: Optional[int] = None
    overnight_hr_max: Optional[int] = None
    hrv_status: Optional[str] = None
    hrv_last_night: Optional[int] = None
    hrv_5day_avg: Optional[int] = None
    resting_hr: Optional[int] = None
    body_battery_morning: Optional[int] = None
    avg_stress: Optional[int] = None
    sleep_notes: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ActivityMetrics:
    activity_id: str
    date: str
    name: str
    activity_type: str
    duration_minutes: float
    distance_km: Optional[float] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    training_load: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)
