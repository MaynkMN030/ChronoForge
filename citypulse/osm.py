"""OpenStreetMap lookup (Overpass API): real park names near the city centre for "greener path" suggestions.

Free, no key. If the network is blocked or Overpass is slow we simply return [] and the caller uses the
curated parks list in config.py - the demo never breaks.
Data (c) OpenStreetMap contributors, ODbL.
"""
from __future__ import annotations

import requests

from . import config

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_CACHE: dict = {}


def nearby_parks(city_key: str, radius_m: int = 4000, limit: int = 5, timeout: float = 8.0, session=None) -> list:
    if city_key in _CACHE:
        return _CACHE[city_key]
    c = config.CITIES[city_key]
    query = (f'[out:json][timeout:8];(way["leisure"="park"]["name"](around:{radius_m},{c["lat"]},{c["lon"]});'
             f'relation["leisure"="park"]["name"](around:{radius_m},{c["lat"]},{c["lon"]}););out tags 30;')
    try:
        post = (session or requests).post
        r = post(OVERPASS_URL, data={"data": query}, timeout=timeout)
        r.raise_for_status()
        names, seen = [], set()
        for el in r.json().get("elements", []):
            name = (el.get("tags") or {}).get("name")
            if name and name not in seen:
                seen.add(name)
                names.append(name)
        names = names[:limit]
    except Exception:
        return []          # do not cache failures
    _CACHE[city_key] = names
    return names
