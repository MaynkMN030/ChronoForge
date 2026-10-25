"""PLAN (part 2): sedentary-gap detection.

A *gap* is a run of back-to-back waking blocks in which the person does not move
(no walking/cycling/exercise). If it is >= SEDENTARY_GAP_HOURS long we flag it.
Inside a gap, blocks of kind 'free' are the *free slots where movement fits*.
"""
from __future__ import annotations

from . import config


def detect_sedentary_gaps(week: list, min_hours: float | None = None) -> list:
    min_hours = config.SEDENTARY_GAP_HOURS if min_hours is None else min_hours
    gaps = []
    for day in range(7):
        segs = sorted([s for s in week if s.day == day and s.end > config.WAKE_HOUR and s.start < config.SLEEP_HOUR],
                      key=lambda s: s.start)
        block = []

        def flush():
            if not block:
                return
            start, end = block[0].start, block[-1].end
            hours = end - start
            if hours >= min_hours:
                free = [(s.start, s.end) for s in block if s.kind == "free"]
                gaps.append({"day": day, "start": start, "end": end, "hours": round(hours, 2),
                             "free_slots": free, "has_free_slot": bool(free)})

        for s in segs:
            sedentary = (not s.active) and s.kind != "workout"
            contiguous = block and abs(block[-1].end - s.start) < 0.01
            if sedentary and (not block or contiguous):
                block.append(s)
            else:
                flush()
                block = [s] if sedentary else []
        flush()
    return gaps


def gaps_filled(gaps: list, workouts: list) -> int:
    """How many flagged gaps now contain a scheduled workout (same day, inside the gap window)."""
    n = 0
    for g in gaps:
        if any(w["day"] == g["day"] and g["start"] - 0.01 <= w["start"] and w["end"] <= g["end"] + 0.01
               for w in workouts):
            n += 1
    return n
