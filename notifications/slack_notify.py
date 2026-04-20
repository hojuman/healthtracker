import json
import urllib.request


def send_slack(webhook_url, assessment, today_metrics, target_date) -> bool:
    if not webhook_url:
        return False
    try:
        payload = _build_payload(assessment, today_metrics, target_date)
        data = json.dumps(payload).encode()
        req = urllib.request.Request(webhook_url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"Slack notification failed: {e}")
        return False


def _build_payload(assessment, metrics, target_date):
    status = assessment.get("status", "UNKNOWN")
    icons = {"HEALTHY": "\u2705", "MONITOR": "\U0001f440", "EASY_DAY": "\U0001f7e1", "REST_DAY": "\U0001f534", "SEEK_CARE": "\U0001f6a8"}
    colors = {"HEALTHY": "#2eb886", "MONITOR": "#daa038", "EASY_DAY": "#daa038", "REST_DAY": "#cc0000", "SEEK_CARE": "#cc0000"}
    icon = icons.get(status, "\u2753")
    color = colors.get(status, "#888888")

    metric_parts = []
    for key, label, unit in [
        ("sleep_score", "Sleep", "/100"),
        ("hrv_last_night", "HRV", " ms"),
        ("resting_hr", "RHR", " bpm"),
        ("body_battery_morning", "Battery", "%"),
    ]:
        val = metrics.get(key)
        if val is not None:
            metric_parts.append(f"*{label}:* {val}{unit}")
    metrics_text = "  |  ".join(metric_parts) or "No data"

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{icon} Health Check \u2014 {target_date}: {status}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": assessment.get("summary", "")}},
        {"type": "section", "text": {"type": "mrkdwn", "text": metrics_text}},
    ]

    if metrics.get("sleep_notes"):
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"_\"{metrics['sleep_notes']}\"_"}})

    concerns = assessment.get("concerns", [])
    if concerns:
        concern_text = "\n".join(f"\u2022 {c}" for c in concerns)
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*\u26a0\ufe0f Concerns*\n{concern_text}"}})

    rec = assessment.get("recommendation", "")
    if rec:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*Recommendation*\n{rec}"}})

    return {"attachments": [{"color": color, "blocks": blocks}]}
