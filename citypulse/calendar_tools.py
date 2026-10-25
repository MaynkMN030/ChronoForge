"""ACT: put the workout slots into the user's calendar.

Default (always works, no login): write a standard .ics file. Import it into Google Calendar,
Apple Calendar or Outlook (or open it on a phone).
Optional: insert directly through the Google Calendar API - see citypulse/google_calendar.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config

IST = timezone(timedelta(minutes=config.UTC_OFFSET_MINUTES))


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _utc(date_iso: str, hour: float) -> str:
    y, m, d = (int(x) for x in date_iso.split("-"))
    local = datetime(y, m, d, int(hour), int(round((hour - int(hour)) * 60)), tzinfo=IST)
    return local.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics(slots: list, calendar_name: str = "CityPulse plan") -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//CityPulse//Array of Hope//EN",
             "CALSCALE:GREGORIAN", f"X-WR-CALNAME:{_esc(calendar_name)}"]
    for s in slots:
        desc = (f"{s['type'].capitalize()} slot chosen by CityPulse. "
                f"Forecast: PM2.5 {s['pm25']} ug/m3, {s['temp']} C, UV {s['uv']}. "
                "Guidance only - not medical advice.")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}@citypulse",
            f"DTSTAMP:{now}",
            f"DTSTART:{_utc(s['date'], s['start'])}",
            f"DTEND:{_utc(s['date'], s['end'])}",
            f"SUMMARY:{_esc('CityPulse: ' + s['title'])}",
            f"DESCRIPTION:{_esc(desc)}",
            "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Workout in 30 minutes", "TRIGGER:-PT30M", "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def write_ics(slots: list, filename: str, directory: Path | None = None) -> Path:
    directory = Path(directory) if directory else config.OUTPUT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_text(build_ics(slots), encoding="utf-8")
    return path
