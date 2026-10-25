"""LEARN: remember which suggestions the user followed or ignored, and adapt next week's plan.

Privacy by design: we store only slot ids, a time-of-day bucket, accepted/ignored status, week start and score.
No GPS trail, no raw location history.

How adaptation works (explain this in the viva):
    for each time-of-day bucket (early / morning / afternoon / evening / night):
        rate = (ignored + 1) / (accepted + ignored + 2)        # Laplace smoothing: 0.5 when no data
        cost_multiplier = exp(LEARN_STRENGTH * (rate - 0.5))   # ~0.29 .. 3.5, equals 1.0 with no data
    A slot in a bucket the user keeps ignoring becomes several times more 'expensive', so the planner
    picks other times next week. Buckets the user follows become cheaper (preferred).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from . import config


class Memory:
    def __init__(self, user_id: str, directory: Path | None = None, persist: bool = True):
        self.user_id = user_id
        self.persist = persist
        self.dir = Path(directory) if directory else config.MEMORY_DIR
        self.path = self.dir / f"{user_id}.json"
        self.data = {"weeks": [], "buckets": {}}
        if persist and self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.data = {"weeks": [], "buckets": {}}

    # ----- persistence -----
    def save(self) -> None:
        if not self.persist:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    # ----- recording -----
    def record_plan(self, week_start: str, score: float, items: list) -> None:
        """items: [{'id','bucket','kind'}] - suggestions we just made (status 'pending')."""
        self.data["weeks"].append({
            "week_start": week_start, "score": score,
            "items": [{"id": i["id"], "bucket": i["bucket"], "kind": i["kind"], "status": "pending"} for i in items],
        })
        self.save()

    def record_feedback(self, item_id: str, accepted: bool) -> bool:
        """Mark the most recent pending item with this id. Returns False if not found."""
        for week in reversed(self.data["weeks"]):
            for it in week["items"]:
                if it["id"] == item_id and it["status"] == "pending":
                    it["status"] = "accepted" if accepted else "ignored"
                    b = self.data["buckets"].setdefault(it["bucket"], {"accepted": 0, "ignored": 0})
                    b["accepted" if accepted else "ignored"] += 1
                    self.save()
                    return True
        return False

    # ----- reading -----
    def stats(self) -> dict:
        acc = sum(b["accepted"] for b in self.data["buckets"].values())
        ign = sum(b["ignored"] for b in self.data["buckets"].values())
        total = acc + ign
        return {"accepted": acc, "ignored": ign,
                "acceptance_rate": round(acc / total, 3) if total else None,
                "buckets": self.data["buckets"], "weeks_planned": len(self.data["weeks"])}

    def cost_multiplier(self, hour: float) -> float:
        b = self.data["buckets"].get(config.hour_bucket(hour), {"accepted": 0, "ignored": 0})
        rate = (b["ignored"] + 1) / (b["accepted"] + b["ignored"] + 2)
        return math.exp(config.LEARN_STRENGTH * (rate - 0.5))

    def learned_notes(self) -> list:
        """Human-readable adaptations, e.g. 'Fewer early-morning slots (you skipped 3 of 3)'."""
        notes = []
        for bucket, b in self.data["buckets"].items():
            n = b["accepted"] + b["ignored"]
            if n >= 2 and b["ignored"] / n >= 0.6:
                notes.append({"bucket": bucket, "ignored": b["ignored"], "total": n})
        return notes
