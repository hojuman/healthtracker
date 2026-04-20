import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(smtp_host, smtp_port, smtp_user, smtp_password, to_email, subject, body) -> bool:
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ssl.create_default_context()) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False


def format_email(assessment, today_metrics, target_date):
    status = assessment.get("status", "UNKNOWN")
    icons = {"HEALTHY": "\u2705", "MONITOR": "\U0001f440", "EASY_DAY": "\U0001f7e1", "REST_DAY": "\U0001f534", "SEEK_CARE": "\U0001f6a8"}
    icon = icons.get(status, "\u2753")
    subject = f"[Health Check] {icon} {status} \u2014 {target_date}"

    lines = [
        f"Health Check: {target_date}",
        f"Status: {icon} {status}",
        "",
        assessment.get("summary", ""),
        "",
        "\u2500" * 50,
        "TODAY'S KEY METRICS",
        "\u2500" * 50,
    ]
    for key, label, unit in [
        ("sleep_score", "Sleep Score", "/100"),
        ("sleep_duration_hours", "Sleep Duration", "h"),
        ("hrv_last_night", "HRV Last Night", " ms"),
        ("hrv_status", "HRV Status", ""),
        ("resting_hr", "Resting HR", " bpm"),
        ("overnight_hr_avg", "Overnight HR Avg", " bpm"),
        ("body_battery_morning", "Body Battery Peak", "%"),
        ("avg_stress", "Avg Stress", "/100"),
    ]:
        val = today_metrics.get(key)
        if val is not None:
            lines.append(f"  {label}: {val}{unit}")

    if today_metrics.get("sleep_notes"):
        lines += ["", f"  Your notes: \"{today_metrics['sleep_notes']}\""]

    for section, key in [("OBSERVATIONS", "observations"), ("\u26a0\ufe0f  CONCERNS", "concerns"), ("WATCH FOR", "watch_for")]:
        items = assessment.get(key, [])
        if items:
            lines += ["", "\u2500" * 50, section, "\u2500" * 50]
            for item in items:
                lines.append(f"  \u2022 {item}")

    rec = assessment.get("recommendation", "")
    if rec:
        lines += ["", "\u2500" * 50, "RECOMMENDATION", "\u2500" * 50, f"  {rec}"]

    lines += ["", "\u2500" * 50, "Powered by Claude AI + Garmin Connect"]
    return subject, "\n".join(lines)
