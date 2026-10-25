"""OBSERVE (part 1): hourly weather, UV and PM2.5 for a city.

Primary source : Open-Meteo forecast + Open-Meteo Air Quality API (free, no API key).
Fallback       : a deterministic synthetic day/night pattern, so the demo NEVER breaks
                 when the venue wifi is bad. The `source` field always says which was used.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import requests

from . import config

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Typical diurnal shape of urban PM2.5 (multiplier on the city's base level, per hour 0..23):
# higher at night / early morning and at rush hours, lowest in the afternoon.
PM_DIURNAL = [1.15, 1.2, 1.2, 1.2, 1.15, 1.1, 1.1, 1.2, 1.3, 1.25, 1.1, 0.95,
              0.85, 0.75, 0.7, 0.7, 0.75, 0.9, 1.1, 1.25, 1.3, 1.3, 1.25, 1.2]


def apparent_temperature(temp_c: float, rh: float) -> float:
    """Apparent ('feels like') temperature in C from temperature and relative humidity.
    Australian BoM / Steadman formula without wind: AT = T + 0.33*e - 4.0"""
    e = (rh / 100.0) * 6.105 * math.exp(17.27 * temp_c / (237.7 + temp_c))
    return temp_c + 0.33 * e - 4.0


@dataclass
class Environment:
    city_key: str
    start_date: date
    temp: list = field(default_factory=list)   # [day][hour]
    rh: list = field(default_factory=list)
    uv: list = field(default_factory=list)
    pm25: list = field(default_factory=list)
    source: str = "synthetic"       # "open-meteo" | "synthetic" | "mixed"
    live_fraction: float = 0.0      # share of hour-values that came from the live API
    note: str = ""

    def at(self, day: int, hour: float) -> dict:
        d = max(0, min(len(self.temp) - 1, day))
        h = max(0, min(23, int(math.floor(hour + 1e-9))))
        t, rh = self.temp[d][h], self.rh[d][h]
        return {"temp": t, "rh": rh, "uv": self.uv[d][h], "pm25": self.pm25[d][h],
                "apparent": apparent_temperature(t, rh)}

    def date_of(self, day: int) -> date:
        return self.start_date + timedelta(days=day)


# ----------------------------------------------------------------------------
def synthetic_environment(city_key: str, start_date: date, days: int = 7, seed: int = 7) -> Environment:
    """Deterministic fake-but-realistic data (same inputs -> same output)."""
    c = config.CITIES[city_key]
    rng = random.Random(f"{city_key}-{seed}")
    temp, rh, uv, pm = [], [], [], []
    for d in range(days):
        day_pm_noise = rng.uniform(0.8, 1.25)       # some days are dirtier
        day_t_noise = rng.uniform(-2.0, 2.0)
        cloud = rng.uniform(0.6, 1.0)               # cloud cover lowers UV
        t_row, r_row, u_row, p_row = [], [], [], []
        for h in range(24):
            # temperature peaks ~15:00, lowest ~05:00
            t = c["t_mean"] + day_t_noise + c["t_amp"] * math.sin((h - 9) / 24 * 2 * math.pi)
            r = max(25.0, min(95.0, c["rh"] - 12 * math.sin((h - 9) / 24 * 2 * math.pi)))
            u = max(0.0, c["uv_peak"] * cloud * math.sin(math.pi * (h - 6) / 12)) if 6 <= h <= 18 else 0.0
            p = c["pm_base"] * PM_DIURNAL[h] * day_pm_noise * rng.uniform(0.95, 1.05)
            t_row.append(round(t, 1)); r_row.append(round(r, 0)); u_row.append(round(u, 1)); p_row.append(round(p, 1))
        temp.append(t_row); rh.append(r_row); uv.append(u_row); pm.append(p_row)
    return Environment(city_key, start_date, temp, rh, uv, pm, source="synthetic", live_fraction=0.0,
                       note="Offline synthetic data (diurnal pattern). Not real measurements.")


def _parse_hourly(payload: dict, key: str, first_date: date, days: int):
    """Turn Open-Meteo hourly arrays into [day][hour] with None for missing values."""
    grid = [[None] * 24 for _ in range(days)]
    times = payload.get("hourly", {}).get("time", [])
    vals = payload.get("hourly", {}).get(key, [])
    for ts, v in zip(times, vals):
        dt = datetime.fromisoformat(ts)
        d = (dt.date() - first_date).days
        if 0 <= d < days:
            grid[d][dt.hour] = v
    return grid


def fetch_open_meteo(city_key: str, days: int = 7, timeout: float = 8.0, session=None) -> Environment:
    """Fetch live data. Raises on network failure (caller falls back to synthetic)."""
    c = config.CITIES[city_key]
    get = (session or requests).get
    common = {"latitude": c["lat"], "longitude": c["lon"], "timezone": config.TIMEZONE, "forecast_days": days}
    w = get(FORECAST_URL, params={**common, "hourly": "temperature_2m,relative_humidity_2m,uv_index"},
            timeout=timeout)
    w.raise_for_status()
    wj = w.json()
    a = get(AIR_URL, params={**common, "hourly": "pm2_5"}, timeout=timeout)
    a.raise_for_status()
    aj = a.json()

    first_date = datetime.fromisoformat(wj["hourly"]["time"][0]).date()
    raw = {
        "temp": _parse_hourly(wj, "temperature_2m", first_date, days),
        "rh": _parse_hourly(wj, "relative_humidity_2m", first_date, days),
        "uv": _parse_hourly(wj, "uv_index", first_date, days),
        "pm25": _parse_hourly(aj, "pm2_5", first_date, days),
    }
    # Start from synthetic and overwrite every hour that the API actually gave us.
    env = synthetic_environment(city_key, first_date, days)
    live, total = 0, 0
    for name in ("temp", "rh", "uv", "pm25"):
        target = getattr(env, name)
        for d in range(days):
            for h in range(24):
                total += 1
                v = raw[name][d][h]
                if v is not None:
                    target[d][h] = float(v)
                    live += 1
    env.live_fraction = live / total if total else 0.0
    if env.live_fraction > 0.97:
        env.source, env.note = "open-meteo", "Live Open-Meteo forecast (weather, UV) + CAMS-modelled PM2.5."
    elif env.live_fraction > 0:
        env.source, env.note = "mixed", "Partly live Open-Meteo data; missing hours filled with synthetic values."
    return env


def get_environment(city_key: str, start_date: date | None = None, use_live: bool = True, days: int = 7) -> Environment:
    """Try live data; on ANY failure silently fall back to synthetic (and say so in .note)."""
    start_date = start_date or date.today()
    if use_live:
        try:
            return fetch_open_meteo(city_key, days=days)
        except Exception as exc:  # network blocked, API down, JSON changed ...
            env = synthetic_environment(city_key, start_date, days)
            env.note = f"Live data unavailable ({type(exc).__name__}); using offline synthetic data."
            return env
    return synthetic_environment(city_key, start_date, days)
