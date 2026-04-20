import logging
from typing import List, Optional
import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI health assistant analyzing wearable health data to detect early signs of illness, overtraining, and recovery needs.

You analyze Garmin metrics (sleep, HRV, heart rate, body battery) alongside Google Calendar context and the user's own sleep notes.

Key physiological signals:
- HRV drop >10% below baseline: autonomic stress (illness, overtraining, poor recovery)
- Resting HR elevated >5 bpm above baseline: classic illness/overtraining indicator
- Sleep score <60 or <6h for multiple nights: impaired recovery
- Low body battery (<40%) at wake despite adequate sleep: systemic stress
- Multiple simultaneous deviations amplify concern significantly
- HRV status: BALANCED=good, LOW=concerning, UNBALANCED=very concerning

Calendar context: recent stressors (late events, travel, deadlines) may explain metric deviations. Upcoming high-stakes events should factor into recommendations.

Sleep notes are first-person observations from the user and should be weighted heavily.

Be specific, reference actual numbers and percentage deviations. Be direct without being alarmist."""

ASSESSMENT_TOOL = {
    "name": "health_assessment",
    "description": "Structured health and recovery status assessment",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["HEALTHY", "MONITOR", "EASY_DAY", "REST_DAY", "SEEK_CARE"],
            },
            "summary": {"type": "string"},
            "observations": {"type": "array", "items": {"type": "string"}},
            "concerns": {"type": "array", "items": {"type": "string"}},
            "recommendation": {"type": "string"},
            "watch_for": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["status", "summary", "observations", "concerns", "recommendation", "watch_for"],
    },
}


class HealthAnalyzer:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def analyze(
        self,
        today: dict,
        history: List[dict],
        activities: List[dict],
        calendar_events: Optional[List[dict]] = None,
    ) -> dict:
        message = _build_message(today, history, activities, calendar_events or [])
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[ASSESSMENT_TOOL],
            tool_choice={"type": "tool", "name": "health_assessment"},
            messages=[{"role": "user", "content": message}],
        )
        for block in response.content:
            if block.type == "tool_use" and block.name == "health_assessment":
                return block.input
        raise RuntimeError("No structured assessment returned from Claude")


def _build_message(today, history, activities, calendar_events):
    baselines = _compute_baselines(history)
    sections = [
        f"## Analysis Date: {today.get('date')}",
        "",
        "### Today's Metrics",
        _fmt_metrics(today),
        "",
        "### Personal Baselines (14-day average)",
        _fmt_baselines(baselines),
        "",
        "### Deviations from Baseline",
        _fmt_deviations(today, baselines),
        "",
        "### 7-Day Trend (most recent first)",
        _fmt_trend(history[:7]),
        "",
        "### Recent Activities (last 10)",
        _fmt_activities(activities[:10]),
    ]
    if calendar_events:
        sections += ["", "### Calendar Context", _fmt_calendar(calendar_events)]
    return "\n".join(sections)


def _compute_baselines(history):
    def avg(key):
        vals = [d[key] for d in history if d.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None
    return {k: avg(k) for k in ("resting_hr", "hrv_last_night", "sleep_score", "sleep_duration_hours", "body_battery_morning", "avg_stress")}


def _fmt_metrics(m):
    lines = []
    if m.get("sleep_score") is not None:
        lines.append(f"  Sleep Score: {m['sleep_score']}/100  Duration: {m.get('sleep_duration_hours', '?')}h")
    if m.get("deep_sleep_pct") is not None:
        lines.append(f"  Sleep Stages: Deep {m['deep_sleep_pct']:.0f}%  REM {m.get('rem_sleep_pct', 0):.0f}%  Light {m.get('light_sleep_pct', 0):.0f}%")
    if m.get("hrv_last_night") is not None:
        status = f" [{m['hrv_status']}]" if m.get("hrv_status") else ""
        lines.append(f"  HRV: {m['hrv_last_night']} ms{status}  (5-day avg: {m.get('hrv_5day_avg', 'N/A')})")
    if m.get("resting_hr") is not None:
        lines.append(f"  Resting HR: {m['resting_hr']} bpm")
    if m.get("overnight_hr_avg") is not None:
        lines.append(f"  Overnight HR: min {m.get('overnight_hr_min', '?')} / avg {m['overnight_hr_avg']} / max {m.get('overnight_hr_max', '?')} bpm")
    if m.get("body_battery_morning") is not None:
        lines.append(f"  Body Battery Peak: {m['body_battery_morning']}%")
    if m.get("avg_stress") is not None:
        lines.append(f"  Avg Stress: {m['avg_stress']}/100")
    if m.get("sleep_notes"):
        lines.append(f"  Sleep Notes: \"{m['sleep_notes']}\"")
    return "\n".join(lines) or "  No data available"


def _fmt_baselines(b):
    lines = []
    for key, label, unit in [
        ("sleep_score", "Sleep Score", ""),
        ("sleep_duration_hours", "Sleep Duration", "h"),
        ("hrv_last_night", "HRV", " ms"),
        ("resting_hr", "Resting HR", " bpm"),
        ("body_battery_morning", "Body Battery Peak", "%"),
        ("avg_stress", "Avg Stress", ""),
    ]:
        val = b.get(key)
        if val is not None:
            lines.append(f"  {label}: {val}{unit}")
    return "\n".join(lines) or "  Insufficient history"


def _fmt_deviations(today, baselines):
    lines = []
    for key, label, unit, higher_is_bad in [
        ("resting_hr", "Resting HR", " bpm", True),
        ("hrv_last_night", "HRV", " ms", False),
        ("sleep_score", "Sleep Score", "", False),
        ("body_battery_morning", "Body Battery", "%", False),
        ("avg_stress", "Avg Stress", "", True),
    ]:
        tv, bv = today.get(key), baselines.get(key)
        if tv is None or bv is None:
            continue
        diff = tv - bv
        pct = (diff / bv * 100) if bv else 0
        arrow = "\u2191" if diff > 0 else "\u2193"
        is_bad = (diff > 0) == higher_is_bad
        flag = " \u26a0\ufe0f" if (abs(pct) >= 10 and is_bad) else ""
        lines.append(f"  {label}: {arrow}{abs(diff):.0f}{unit} ({pct:+.0f}%){flag}")
    return "\n".join(lines) or "  No deviation data"


def _fmt_trend(history):
    if not history:
        return "  No history"
    rows = ["  Date        Sleep  HRV  RHR  BB%", "  " + "-" * 38]
    for d in history:
        note_flag = " \U0001f4dd" if d.get("sleep_notes") else ""
        rows.append(
            f"  {d['date']}  {str(d.get('sleep_score', '--')):>5}  "
            f"{str(d.get('hrv_last_night', '--')):>3}  "
            f"{str(d.get('resting_hr', '--')):>3}  "
            f"{str(d.get('body_battery_morning', '--')):>3}"
            f"{note_flag}"
        )
    return "\n".join(rows)


def _fmt_activities(activities):
    if not activities:
        return "  No recent activities"
    lines = []
    for a in activities:
        dist = f" {a['distance_km']:.1f}km" if a.get("distance_km") else ""
        load = f" (load: {a['training_load']:.1f})" if a.get("training_load") else ""
        lines.append(f"  {a['date']} {a['name']} {a['duration_minutes']:.0f}min{dist}{load}")
    return "\n".join(lines)


def _fmt_calendar(events):
    if not events:
        return "  No calendar events"
    past = [e for e in events if e.get("is_past")]
    upcoming = [e for e in events if not e.get("is_past")]
    lines = []
    if past:
        lines.append("  Recent (last 7 days):")
        for e in past[-7:]:
            lines.append(f"    {e['date']} {e.get('time', '')} \u2014 {e['title']}")
    if upcoming:
        lines.append("  Upcoming (next 7 days):")
        for e in upcoming[:7]:
            lines.append(f"    {e['date']} {e.get('time', '')} \u2014 {e['title']}")
    return "\n".join(lines)
