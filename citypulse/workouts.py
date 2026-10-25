"""PLAN (part 4) + ACT: auto-scheduled workout slots.

Candidates = every whole hour inside a 'free' block. Each candidate's cost is the exposure of
a 1-hour outdoor run at that hour (low PM2.5 + comfortable heat + low UV = cheap).
Cost is then adjusted by (a) how long the day's sedentary gap is, and (b) the learning memory
(buckets of the day that the user keeps ignoring get more expensive).
We pick the cheapest slots on different, preferably non-consecutive days.
If the air is very bad (PM2.5 > INDOOR_WORKOUT_PM) or it is too hot, the slot becomes an INDOOR workout.
"""
from __future__ import annotations

import math

from . import config
from .environment import Environment
from .exposure import hourly_cost, norm_components, segment_factor
from .personas import Segment


def _candidates(env: Environment, week: list, gaps: list, memory=None) -> list:
    gap_hours = {}
    for g in gaps:
        gap_hours[g["day"]] = max(gap_hours.get(g["day"], 0.0), g["hours"])
    out = []
    for s in week:
        if s.kind != "free":
            continue
        start = math.ceil(s.start - 1e-9)
        while start + config.WORKOUT_HOURS <= min(s.end, config.WORKOUT_LATEST_END) + 1e-9:
            if start >= config.WAKE_HOUR:
                eh = env.at(s.day, start)
                pm_n, heat_n, _ = norm_components(eh)
                indoor = eh["pm25"] > config.INDOOR_WORKOUT_PM or heat_n > config.INDOOR_WORKOUT_HEAT
                if indoor:
                    cost = config.WORKOUT_HOURS * segment_factor("indoor", 0.0) * 0.5
                    cost += 0.05   # small penalty: indoor needs a gym / home space
                else:
                    cost = config.WORKOUT_HOURS * config.MODE_FACTOR["run"] * hourly_cost(eh)
                cost *= 1.0 - 0.03 * min(gap_hours.get(s.day, 0.0), 8.0)   # prefer long-gap days
                if any(g["day"] == s.day and g["start"] - 1e-9 <= start and start + config.WORKOUT_HOURS <= g["end"] + 1e-9
                       for g in gaps):
                    cost *= config.GAP_SLOT_BONUS                              # slot breaks up a long sitting block
                if memory is not None:
                    cost *= memory.cost_multiplier(start)
                out.append({"day": s.day, "start": float(start), "end": float(start + config.WORKOUT_HOURS),
                            "cost": cost, "indoor": indoor, "place": s.place,
                            "pm25": eh["pm25"], "temp": eh["temp"], "uv": eh["uv"], "apparent": eh["apparent"]})
            start += 1
    return out


def schedule_workouts(env: Environment, week: list, gaps: list, memory=None,
                      count: int = config.DEFAULT_WORKOUTS) -> list:
    """Pick `count` (>= MIN_WORKOUTS) slots. Returns a list of slot dicts."""
    count = max(config.MIN_WORKOUTS, count)
    cands = sorted(_candidates(env, week, gaps, memory), key=lambda c: c["cost"])
    chosen, used_days = [], set()
    # pass 1: different days, never next to another chosen day
    for c in cands:
        if len(chosen) >= count:
            break
        if c["day"] in used_days or (c["day"] - 1) in used_days or (c["day"] + 1) in used_days:
            continue
        chosen.append(c); used_days.add(c["day"])
    # pass 2: different days (adjacent allowed)
    for c in cands:
        if len(chosen) >= count:
            break
        if c["day"] in used_days:
            continue
        chosen.append(c); used_days.add(c["day"])
    chosen.sort(key=lambda c: (c["day"], c["start"]))
    slots = []
    for c in chosen:
        slots.append({
            "id": f"workout-{c['day']}-{int(c['start'])}",
            "day": c["day"], "date": env.date_of(c["day"]).isoformat(),
            "start": c["start"], "end": c["end"],
            "type": "indoor" if c["indoor"] else "outdoor",
            "title": "Indoor workout (air is poor)" if c["indoor"] else "Outdoor run / brisk walk",
            "place": c["place"], "bucket": config.hour_bucket(c["start"]),
            "pm25": round(c["pm25"], 1), "temp": round(c["temp"], 1), "uv": round(c["uv"], 1),
            "cost": round(c["cost"], 3),
        })
    return slots


def insert_workouts(week: list, slots: list) -> list:
    """Return a NEW week where each slot replaces the free time it sits in (free block is split)."""
    new = [s.copy() for s in week]
    for w in slots:
        for i, s in enumerate(new):
            if s.day == w["day"] and s.kind == "free" and s.start - 1e-9 <= w["start"] and w["end"] <= s.end + 1e-9:
                pieces = []
                if w["start"] - s.start > 1e-9:
                    pieces.append(s.copy(end=w["start"]))
                pieces.append(Segment(day=w["day"], start=w["start"], end=w["end"], kind="workout",
                                      place=w["title"], mode="indoor" if w["type"] == "indoor" else "run",
                                      outdoor=0.0 if w["type"] == "indoor" else 1.0, active=True))
                if s.end - w["end"] > 1e-9:
                    pieces.append(s.copy(start=w["end"]))
                new[i:i + 1] = pieces
                break
    return new
