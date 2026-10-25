"""PLAN (part 1): the Weekly Exposure Score engine.

For every hour a person spends somewhere we compute
    exposure = hours * f * (0.5*PM_norm + 0.3*Heat_norm + 0.2*UV_norm)
where f = outdoor*MODE_FACTOR[mode] + (1-outdoor)*INDOOR_FACTOR
(how much of the outdoor air/heat/sun reaches the person in that block).
Sum over the week = raw. Score = 100 * (1 - exp(-raw / SCORE_SCALE))  -> 0..100.
We also keep a pure PM2.5 "dose" (ug/m3 x hours, weighted by f) as the metric for the demo.
"""
from __future__ import annotations

import math

from . import config
from .environment import Environment


def segment_factor(mode: str, outdoor: float) -> float:
    m = config.MODE_FACTOR.get(mode, config.MODE_FACTOR["indoor"])
    return outdoor * m + (1.0 - outdoor) * config.INDOOR_FACTOR


def norm_components(env_hour: dict) -> tuple:
    """Raw weather numbers -> (pm_norm, heat_norm, uv_norm), each ~0..1 (pm up to PM_CAP)."""
    pm_n = min(env_hour["pm25"] / config.PM_REF, config.PM_CAP)
    heat_n = (env_hour["apparent"] - config.HEAT_LOW) / (config.HEAT_HIGH - config.HEAT_LOW)
    heat_n = max(0.0, min(1.0, heat_n))
    uv_n = max(0.0, min(1.0, env_hour["uv"] / config.UV_MAX))
    return pm_n, heat_n, uv_n


def hourly_cost(env_hour: dict) -> float:
    """Exposure per hour of being fully outdoors (f = 1) at this moment."""
    pm_n, heat_n, uv_n = norm_components(env_hour)
    w = config.WEIGHTS
    return w["pm"] * pm_n + w["heat"] * heat_n + w["uv"] * uv_n


def _buckets(start: float, end: float):
    """Split [start, end) into (hour_index, overlap_hours) pieces."""
    t = start
    while t < end - 1e-9:
        h = int(math.floor(t + 1e-9))
        nxt = min(h + 1.0, end)
        yield min(h, 23), nxt - t
        t = nxt


def segment_exposure(env: Environment, day: int, start: float, end: float, mode: str,
                     outdoor: float, pm_scale: float = 1.0) -> dict:
    """Exposure of one block. Returns total, pm_dose and per-hour contributions."""
    f = segment_factor(mode, outdoor)
    total, pm_dose, per_hour = 0.0, 0.0, {}
    for h, ov in _buckets(start, end):
        eh = env.at(day, h)
        pm_n, heat_n, uv_n = norm_components(eh)
        pm_n *= pm_scale
        w = config.WEIGHTS
        c = ov * f * (w["pm"] * pm_n + w["heat"] * heat_n + w["uv"] * uv_n)
        total += c
        pm_dose += ov * f * eh["pm25"] * pm_scale
        per_hour[h] = per_hour.get(h, 0.0) + c
    return {"total": total, "pm_dose": pm_dose, "per_hour": per_hour}


def label_for(score: float) -> str:
    for limit, name in config.SCORE_LABELS:
        if score <= limit:
            return name
    return config.SCORE_LABELS[-1][1]


def weekly_report(env: Environment, week: list) -> dict:
    """The full exposure picture for a list of Segments."""
    raw, pm_dose = 0.0, 0.0
    by_day = [0.0] * 7
    grid = [[0.0] * 24 for _ in range(7)]
    commute_pm, commute_total = 0.0, 0.0
    seg_rows = []
    for s in week:
        e = segment_exposure(env, s.day, s.start, s.end, s.mode, s.outdoor, s.pm_scale)
        raw += e["total"]
        pm_dose += e["pm_dose"]
        by_day[s.day] += e["total"]
        for h, c in e["per_hour"].items():
            grid[s.day][h] += c
        if s.kind == "commute":
            commute_pm += e["pm_dose"]
            commute_total += e["total"]
        seg_rows.append({"day": s.day, "start": s.start, "end": s.end, "kind": s.kind, "place": s.place,
                         "mode": s.mode, "exposure": round(e["total"], 3), "pm_dose": round(e["pm_dose"], 1)})
    score = 100.0 * (1.0 - math.exp(-raw / config.SCORE_SCALE))
    top = sorted(seg_rows, key=lambda r: r["exposure"], reverse=True)[:5]
    return {
        "raw": round(raw, 3), "score": round(score, 1), "label": label_for(score),
        "pm_dose": round(pm_dose, 1), "commute_pm_dose": round(commute_pm, 1),
        "commute_exposure": round(commute_total, 3),
        "by_day": [round(x, 3) for x in by_day],
        "grid": [[round(x, 4) for x in row] for row in grid],
        "top_segments": top,
    }
