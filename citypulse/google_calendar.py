"""OPTIONAL: insert workout slots directly into Google Calendar with the Google Calendar API.

You do NOT need this for the demo - the .ics export already works. Use it only if you have time.
Setup (details in GUIDE.md, section 'Optional: real Google Calendar'):
  1. pip install google-api-python-client google-auth-oauthlib
  2. Google Cloud Console -> new project -> enable 'Google Calendar API'
  3. OAuth consent screen (External, add your own email as a Test user)
  4. Credentials -> OAuth client ID -> Desktop app -> download JSON -> save as credentials.json in the repo root
  5. First run opens a browser to log in and creates token.json (both files are git-ignored).
"""
from __future__ import annotations

from pathlib import Path

from . import config

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def _iso(date_iso: str, hour: float) -> str:
    hh, mm = int(hour), int(round((hour - int(hour)) * 60))
    return f"{date_iso}T{hh:02d}:{mm:02d}:00"


def add_events(slots: list, credentials_path: str = "credentials.json", token_path: str = "token.json") -> list:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError("Install the optional packages: pip install google-api-python-client "
                           "google-auth-oauthlib") from exc

    creds = None
    if Path(token_path).exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES).run_local_server(port=0)
        Path(token_path).write_text(creds.to_json())

    service = build("calendar", "v3", credentials=creds)
    links = []
    for s in slots:
        body = {
            "summary": f"CityPulse: {s['title']}",
            "description": f"Forecast PM2.5 {s['pm25']} ug/m3, {s['temp']} C, UV {s['uv']}. Guidance only - not medical advice.",
            "start": {"dateTime": _iso(s["date"], s["start"]), "timeZone": config.TIMEZONE},
            "end": {"dateTime": _iso(s["date"], s["end"]), "timeZone": config.TIMEZONE},
            "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 30}]},
        }
        links.append(service.events().insert(calendarId="primary", body=body).execute().get("htmlLink"))
    return links
