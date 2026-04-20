import json
import urllib.request

NTFY_URL = "https://ntfy.sh"


def send_ntfy(topic, title, message, priority="default") -> bool:
    if not topic:
        return False
    try:
        data = json.dumps({"topic": topic, "title": title, "message": message, "priority": priority}).encode()
        req = urllib.request.Request(
            f"{NTFY_URL}/{topic}", data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"ntfy notification failed: {e}")
        return False


def format_ntfy(assessment, target_date):
    status = assessment.get("status", "UNKNOWN")
    priority_map = {"HEALTHY": "low", "MONITOR": "default", "EASY_DAY": "default", "REST_DAY": "high", "SEEK_CARE": "urgent"}
    title = f"Health Check {target_date}: {status}"
    message = assessment.get("summary", "")
    rec = assessment.get("recommendation", "")
    if rec:
        message += f"\n\n{rec}"
    return title, message, priority_map.get(status, "default")
