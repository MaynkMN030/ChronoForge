"""ACT: club and meetup suggestions after a heavy, isolated week.

Triggered when weekly social hours < SOCIAL_HOURS_THRESHOLD.
Ranking = interest match, minus a penalty if the event is outdoors and the forecast air is bad at that time.
The dataset (data/meetups.json) is a curated SAMPLE - replace it with verified local groups before the final demo.
"""
from __future__ import annotations

import json
from datetime import timedelta

from . import config
from .environment import Environment
from .exposure import norm_components
from .personas import social_hours


def load_entries(city_key: str) -> list:
    raw = json.loads((config.DATA_DIR / "meetups.json").read_text(encoding="utf-8"))
    return [e for e in raw["entries"] if e["city"] == city_key]


def suggest_meetups(env: Environment, week: list, city_key: str, interests: list, max_items: int = 2) -> dict:
    hours = social_hours(week)
    needed = hours < config.SOCIAL_HOURS_THRESHOLD
    result = {"social_hours": round(hours, 1), "triggered": needed, "items": []}
    if not needed:
        return result
    scored = []
    for e in load_entries(city_key):
        # find the date inside the forecast window that matches this event's weekday
        day = next((d for d in range(7) if (env.start_date + timedelta(days=d)).weekday() == e["weekday"]), None)
        if day is None:
            continue
        hh, mm = e["time"].split(":")
        t = int(hh) + int(mm) / 60
        match = len(set(e["tags"]) & set(interests))
        score = match * 1.0 + (0.3 if e["indoor"] else 0.0) * 0.0
        pm_n, heat_n, _ = norm_components(env.at(day, t))
        if not e["indoor"] and (pm_n > 0.9 or heat_n > 0.85):
            score -= 1.5          # bad air / heat for an outdoor event
        scored.append((score, e, day, t, pm_n))
    scored.sort(key=lambda x: x[0], reverse=True)
    for score, e, day, t, pm_n in scored[:max_items]:
        result["items"].append({
            "id": e["id"], "name": e["name"], "type": e["type"], "indoor": e["indoor"], "cost": e["cost"],
            "day": day, "date": env.date_of(day).isoformat(), "time": e["time"],
            "matches": sorted(set(e["tags"]) & set(interests)),
            "air_ok": bool(e["indoor"] or pm_n <= 0.9),
        })
    return result
