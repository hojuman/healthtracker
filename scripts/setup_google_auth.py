"""One-time script to authorize Google Calendar access and generate token.

Run this locally once:
    python scripts/setup_google_auth.py

Then add the printed JSON values to GitHub Secrets:
    GOOGLE_CALENDAR_CREDENTIALS  <- contents of your credentials.json
    GOOGLE_CALENDAR_TOKEN        <- printed by this script after auth
"""
import json
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Run: pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

credentials_file = input("Path to your credentials.json (downloaded from Google Cloud Console): ").strip()

flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
creds = flow.run_local_server(port=0)

token_data = {
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "token_uri": creds.token_uri,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
    "scopes": list(creds.scopes),
}

with open(credentials_file) as f:
    creds_data = json.load(f)
client_info = creds_data.get("installed") or creds_data.get("web", {})

print("\n" + "=" * 60)
print("Add these to GitHub Secrets (Settings -> Secrets -> Actions):")
print("=" * 60)
print("\nGOOGLE_CALENDAR_CREDENTIALS:")
print(json.dumps({"token_uri": client_info.get("token_uri", "https://oauth2.googleapis.com/token"), "client_id": client_info.get("client_id"), "client_secret": client_info.get("client_secret")}))
print("\nGOOGLE_CALENDAR_TOKEN:")
print(json.dumps(token_data))
print("\nDone!")
