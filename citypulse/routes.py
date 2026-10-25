"""PLAN (part 3) + ACT: low-exposure route and timing swaps.

For each commute block we try:
  A) TIMING : shift the departure by up to +/- `flex` hours (only if the user is flexible)
  B) PATH   : take the greener / side-street path (assumed to cut PM2.5 dose by ROUTE_PM_REDUCTION)
  C) BOTH
and keep whichever lowers exposure the most. Neighbouring blocks stretch/shrink so the day still adds up.
"""
from __future__ import annotations

from . import config
from .environment import Environment
from .exposure import segment_exposure

MIN_NEIGHBOUR_HOURS = 0.5


def _day_segments(week: list, day: int) -> list:
    return sorted([i for i, s in enumerate(week) if s.day == day], key=lambda i: week[i].start)


def _neighbours(week: list, idx: int):
    order = _day_segments(week, week[idx].day)
    pos = order.index(idx)
    prev_i = order[pos - 1] if pos > 0 else None
    next_i = order[pos + 1] if pos < len(order) - 1 else None
    return prev_i, next_i


def shift_feasible(week: list, idx: int, delta: float) -> bool:
    s = week[idx]
    if s.start + delta < config.WAKE_HOUR or s.end + delta > config.SLEEP_HOUR:
        return False
    prev_i, next_i = _neighbours(week, idx)
    if prev_i is not None and week[prev_i].hours + delta < MIN_NEIGHBOUR_HOURS:
        return False
    if next_i is not None and week[next_i].hours - delta < MIN_NEIGHBOUR_HOURS:
        return False
    return True


def apply_shift(week: list, idx: int, delta: float, path: bool) -> list:
    """Return a NEW week with commute `idx` shifted by delta hours (and/or cleaner path applied)."""
    new = [s.copy() for s in week]
    prev_i, next_i = _neighbours(new, idx)
    seg = new[idx]
    seg.start += delta
    seg.end += delta
    if prev_i is not None:
        new[prev_i].end += delta
    if next_i is not None:
        new[next_i].start += delta
    if path:
        seg.pm_scale = 1.0 - config.ROUTE_PM_REDUCTION
    return new


def _fmt(h: float) -> str:
    hh, mm = int(h), int(round((h - int(h)) * 60))
    if mm == 60:
        hh, mm = hh + 1, 0
    return f"{hh:02d}:{mm:02d}"


def propose_route_swaps(env: Environment, week: list, parks: list | None = None, memory=None,
                        max_swaps: int = 6) -> tuple:
    """Returns (swaps, new_week). `new_week` has every recommended swap applied."""
    parks = parks or []
    candidates = []
    for idx, s in enumerate(week):
        if s.kind != "commute":
            continue
        base = segment_exposure(env, s.day, s.start, s.end, s.mode, s.outdoor, s.pm_scale)
        best = {"delta": 0.0, "path": False, "total": base["total"], "pm": base["pm_dose"]}
        n_steps = int(round(s.flex / 0.5))
        shifts = [0.0] + [k * 0.5 * sign for k in range(1, n_steps + 1) for sign in (-1, 1)]
        for delta in shifts:
            if delta and not shift_feasible(week, idx, delta):
                continue
            for path in ([False, True] if s.path_alt else [False]):
                if delta == 0.0 and not path:
                    continue
                e = segment_exposure(env, s.day, s.start + delta, s.end + delta, s.mode, s.outdoor,
                                     s.pm_scale * ((1 - config.ROUTE_PM_REDUCTION) if path else 1.0))
                cost = e["total"]
                if memory is not None:
                    cost *= memory.cost_multiplier(s.start + delta)
                best_cost = best["total"] * (memory.cost_multiplier(s.start + best["delta"]) if memory else 1.0)
                if cost < best_cost - 1e-9:
                    best = {"delta": delta, "path": path, "total": e["total"], "pm": e["pm_dose"]}
        saving = 1.0 - best["total"] / base["total"] if base["total"] > 0 else 0.0
        if (best["delta"] or best["path"]) and saving >= config.MIN_SWAP_SAVING:
            candidates.append({"idx": idx, "saving": saving, "best": best, "base": base})

    candidates.sort(key=lambda c: c["saving"], reverse=True)
    chosen = candidates[:max_swaps]
    swaps, new_week = [], [s.copy() for s in week]
    for rank, c in enumerate(chosen):
        s = week[c["idx"]]
        b = c["best"]
        # apply on the running copy (indexes are stable because we never add/remove segments)
        new_week = apply_shift(new_week, c["idx"], b["delta"], b["path"])
        parts = []
        if b["delta"]:
            parts.append("timing")
        if b["path"]:
            parts.append("path")
        swaps.append({
            "id": f"swap-{s.day}-{int(s.start * 60)}",
            "day": s.day, "place": s.place, "mode": s.mode,
            "old_start": s.start, "new_start": s.start + b["delta"],
            "old_window": f"{_fmt(s.start)}-{_fmt(s.end)}",
            "new_window": f"{_fmt(s.start + b['delta'])}-{_fmt(s.end + b['delta'])}",
            "type": "+".join(parts), "shift_hours": b["delta"],
            "via": (parks[rank % len(parks)] if (b["path"] and parks) else None),
            "saving_pct": round(100 * c["saving"], 1),
            "pm_before": round(c["base"]["pm_dose"], 1), "pm_after": round(b["pm"], 1),
        })
    return swaps, new_week
