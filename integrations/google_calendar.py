import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List

logger = logging.getLogger(__name__)


def get_calendar_events(
    credentials_json: str,
    token_json: str,
    days_past: int = 7,
    days_ahead: int = 7,
) -> List[dict]:
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        logger.warning("google-auth not installed, skipping calendar integration")
        return []

    try:
        creds_data = json.loads(credentials_json)
        token_data = json.loads(token_json)
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=creds_data.get("client_id"),
            client_secret=creds_data.get("client_secret"),
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        now = datetime.now(timezone.utc)
        result = service.events().list(
            calendarId="primary",
            timeMin=(now - timedelta(days=days_past)).isoformat(),
            timeMax=(now + timedelta(days=days_ahead)).isoformat(),
            maxResults=50,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        today = datetime.now(timezone.utc).date().isoformat()
        events = []
        for item in result.get("items", []):
            start = item.get("start", {})
            start_str = start.get("dateTime") or start.get("date", "")
            if not start_str:
                continue
            event_date = start_str[:10]
            time_str = ""
            if "dateTime" in start:
                try:
                    dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    time_str = dt.strftime("%H:%M")
                except ValueError:
                    pass
            events.append({
                "date": event_date,
                "time": time_str,
                "title": item.get("summary", "Untitled"),
                "is_past": event_date < today,
            })
        return events
    except Exception as e:
        logger.warning(f"Google Calendar fetch failed: {e}")
        return []
