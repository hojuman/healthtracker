import logging
import sys
from datetime import date, timedelta

import config
from garmin_health.client import GarminHealthClient
from garmin_health.parser import parse_daily_metrics, parse_activity
from ai_analysis.analyzer import HealthAnalyzer
from integrations.google_calendar import get_calendar_events
from notifications.email_notify import send_email, format_email
from notifications.slack_notify import send_slack
from notifications.ntfy_notify import send_ntfy, format_ntfy

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

STATUS_ICONS = {
    "HEALTHY": "\u2705",
    "MONITOR": "\U0001f440",
    "EASY_DAY": "\U0001f7e1",
    "REST_DAY": "\U0001f534",
    "SEEK_CARE": "\U0001f6a8",
}


def main():
    _validate_config()

    target_date = (date.today() - timedelta(days=1)).isoformat()
    print(f"Fetching Garmin data for {target_date}...")

    client = GarminHealthClient(config.GARMIN_EMAIL, config.GARMIN_PASSWORD)

    today = parse_daily_metrics(
        target_date,
        client.get_sleep_data(target_date),
        client.get_hrv_data(target_date),
        client.get_rhr(target_date),
        client.get_stats(target_date),
    ).to_dict()

    if not any(today.get(k) for k in ("sleep_score", "hrv_last_night", "resting_hr")):
        print("No meaningful data for yesterday. Watch may not have synced yet.")
        sys.exit(0)

    print(f"Fetching {config.HISTORY_DAYS} days of history for baselines...")
    history = []
    for i in range(1, config.HISTORY_DAYS + 1):
        d = (date.today() - timedelta(days=i + 1)).isoformat()
        m = parse_daily_metrics(
            d,
            client.get_sleep_data(d),
            client.get_hrv_data(d),
            client.get_rhr(d),
            client.get_stats(d),
        ).to_dict()
        history.append(m)

    activities_raw = client.get_activities(limit=14)
    activities = [a.to_dict() for raw in activities_raw if (a := parse_activity(raw))]

    calendar_events = []
    if config.GOOGLE_CALENDAR_CREDENTIALS and config.GOOGLE_CALENDAR_TOKEN:
        print("Fetching Google Calendar events...")
        calendar_events = get_calendar_events(
            config.GOOGLE_CALENDAR_CREDENTIALS,
            config.GOOGLE_CALENDAR_TOKEN,
        )
        print(f"  Found {len(calendar_events)} events")

    print("Running AI analysis...")
    analyzer = HealthAnalyzer(config.ANTHROPIC_API_KEY)
    assessment = analyzer.analyze(today, history, activities, calendar_events)

    status = assessment.get("status", "UNKNOWN")
    icon = STATUS_ICONS.get(status, "\u2753")
    print(f"\n{icon} Status: {status}")
    print(f"{assessment.get('summary', '')}\n")
    for obs in assessment.get("observations", []):
        print(f"  \u2022 {obs}")
    concerns = assessment.get("concerns", [])
    if concerns:
        print("\n\u26a0\ufe0f  Concerns:")
        for c in concerns:
            print(f"  \u2022 {c}")
    rec = assessment.get("recommendation", "")
    if rec:
        print(f"\nRecommendation: {rec}")

    should_notify = status != "HEALTHY" or config.NOTIFY_ON_HEALTHY
    if not should_notify:
        print("\nAll clear \u2014 no notification sent (set NOTIFY_ON_HEALTHY=true to always notify).")
        return

    if config.NOTIFY_EMAIL and config.SMTP_USER and config.SMTP_PASSWORD:
        subject, body = format_email(assessment, today, target_date)
        ok = send_email(config.SMTP_HOST, config.SMTP_PORT, config.SMTP_USER, config.SMTP_PASSWORD, config.NOTIFY_EMAIL, subject, body)
        print(f"\nEmail: {'sent \u2713' if ok else 'failed \u2717'}")

    if config.SLACK_WEBHOOK_URL:
        ok = send_slack(config.SLACK_WEBHOOK_URL, assessment, today, target_date)
        print(f"Slack: {'sent \u2713' if ok else 'failed \u2717'}")

    if config.NTFY_TOPIC:
        title, message, priority = format_ntfy(assessment, target_date)
        ok = send_ntfy(config.NTFY_TOPIC, title, message, priority)
        print(f"ntfy: {'sent \u2713' if ok else 'failed \u2717'}")


def _validate_config():
    missing = [k for k, v in [
        ("GARMIN_EMAIL", config.GARMIN_EMAIL),
        ("GARMIN_PASSWORD", config.GARMIN_PASSWORD),
        ("ANTHROPIC_API_KEY", config.ANTHROPIC_API_KEY),
    ] if not v]
    if missing:
        print(f"Error: Missing required config: {', '.join(missing)}", file=sys.stderr)
        print("Copy .env.example to .env and fill in your credentials.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
