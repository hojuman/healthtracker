import os
from dotenv import load_dotenv

load_dotenv()

GARMIN_EMAIL = os.getenv("GARMIN_EMAIL", "")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")

GOOGLE_CALENDAR_CREDENTIALS = os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "")
GOOGLE_CALENDAR_TOKEN = os.getenv("GOOGLE_CALENDAR_TOKEN", "")

HISTORY_DAYS = int(os.getenv("HISTORY_DAYS", "14"))
NOTIFY_ON_HEALTHY = os.getenv("NOTIFY_ON_HEALTHY", "false").lower() == "true"
