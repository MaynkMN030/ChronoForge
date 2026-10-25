"""THE AGENT CORE: Observe -> Plan -> Act -> Learn.

`AgentSession` holds the state of one user's planning run and exposes every capability as a *tool*
(methods named tool_*). Two ways to drive it:

  1. run()            - deterministic pipeline: always works, no API key, same result every time.
  2. agent_llm.py     - an LLM (Claude) decides which tools to call and in what order (real tool calling).

Both use the SAME tools, so the maths is identical and testable.
"""
from __future__ import annotations

from datetime import date

from . import config, i18n
from .calendar_tools import write_ics
from .environment import Environment, get_environment
from .exposure import weekly_report
from .gaps import detect_sedentary_gaps, gaps_filled
from .memory import Memory
from .meetups import suggest_meetups
from .osm import nearby_parks
from .personas import PERSONAS, build_week, social_hours
from .routes import propose_route_swaps
from .workouts import insert_workouts, schedule_workouts


def _pct_drop(before: float, after: float) -> float:
    return round(100.0 * (before - after) / before, 1) if before > 0 else 0.0


class AgentSession:
    def __init__(self, persona: str = "office", city: str = config.DEFAULT_CITY, use_live: bool = True,
                 user_id: str | None = None, persist_memory: bool = True, memory_dir=None, output_dir=None,
                 start_date: date | None = None, env: Environment | None = None):
        if persona not in PERSONAS:
            raise KeyError(f"Unknown persona '{persona}'. Choose from {list(PERSONAS)}")
        if city not in config.CITIES:
            raise KeyError(f"Unknown city '{city}'. Choose from {list(config.CITIES)}")
        self.persona, self.city, self.use_live = persona, city, use_live
        self.start_date, self.output_dir = start_date, output_dir
        self.memory = Memory(user_id or f"{persona}-{city}", memory_dir, persist_memory)
        self.env = env
        self.week = self.week_swapped = self.final_week = None
        self.baseline = None
        self.swaps, self.workouts, self.meetups, self.gaps = [], [], None, []
        self.ics_path = None
        self.tool_log = []

    # ------------------------------------------------------------------ OBSERVE
    def observe(self) -> None:
        if self.env is None:
            self.env = get_environment(self.city, self.start_date, self.use_live)
        self.week = build_week(self.persona, self.env.start_date)
        self.week_swapped = [s.copy() for s in self.week]
        self.final_week = [s.copy() for s in self.week]
        self.baseline = weekly_report(self.env, self.week)
        self.swaps, self.workouts, self.meetups, self.ics_path = [], [], None, None
        self.gaps = detect_sedentary_gaps(self.week_swapped)

    def _ensure(self) -> None:
        if self.env is None or self.week is None:
            self.observe()

    # ------------------------------------------------------------------ TOOLS (callable by an LLM too)
    def tool_get_week_overview(self) -> dict:
        self._ensure()
        p = PERSONAS[self.persona]
        hours = {}
        for s in self.week:
            hours[s.kind] = round(hours.get(s.kind, 0.0) + s.hours, 1)
        commutes = sorted({(s.place, s.mode) for s in self.week if s.kind == "commute"})
        return {"persona": f"{p['name']} - {p['title']}", "city": config.CITIES[self.city]["name"],
                "week_starts": self.env.start_date.isoformat(), "data_source": self.env.source,
                "hours_by_kind": hours, "commutes": [{"route": r, "mode": m} for r, m in commutes],
                "social_hours": round(social_hours(self.week), 1), "interests": p["interests"]}

    def tool_get_exposure_report(self) -> dict:
        self._ensure()
        b = self.baseline
        return {"score": b["score"], "label": b["label"], "pm_dose": b["pm_dose"],
                "commute_pm_dose": b["commute_pm_dose"], "score_by_day": b["by_day"],
                "top_exposure_blocks": b["top_segments"]}

    def tool_find_sedentary_gaps(self) -> dict:
        self._ensure()
        self.gaps = detect_sedentary_gaps(self.week_swapped)
        return {"gaps": self.gaps, "count": len(self.gaps)}

    def tool_propose_route_swaps(self, apply: bool = True) -> dict:
        self._ensure()
        parks = (nearby_parks(self.city) if self.use_live else []) or config.CITIES[self.city]["parks"]
        swaps, new_week = propose_route_swaps(self.env, self.week, parks, self.memory)
        self.swaps = swaps
        if apply:
            self.week_swapped = new_week
        self.gaps = detect_sedentary_gaps(self.week_swapped)
        new = weekly_report(self.env, self.week_swapped)
        return {"swaps": swaps, "commute_pm_reduction_pct": _pct_drop(self.baseline["commute_pm_dose"], new["commute_pm_dose"]),
                "applied": apply}

    def tool_schedule_workouts(self, count: int = config.DEFAULT_WORKOUTS) -> dict:
        self._ensure()
        gaps = detect_sedentary_gaps(self.week_swapped)
        self.workouts = schedule_workouts(self.env, self.week_swapped, gaps, self.memory, int(count))
        self.final_week = insert_workouts(self.week_swapped, self.workouts)
        self.gaps = gaps
        return {"workouts": self.workouts, "gaps_filled": gaps_filled(gaps, self.workouts), "gaps_total": len(gaps)}

    def tool_suggest_meetups(self) -> dict:
        self._ensure()
        self.meetups = suggest_meetups(self.env, self.week, self.city, PERSONAS[self.persona]["interests"])
        return self.meetups

    def tool_export_calendar(self) -> dict:
        self._ensure()
        if not self.workouts:
            return {"error": "No workouts scheduled yet. Call schedule_workouts first."}
        name = f"citypulse_{self.persona}_{self.city}_{self.env.start_date.isoformat()}.ics"
        self.ics_path = write_ics(self.workouts, name, self.output_dir)
        return {"file": str(self.ics_path), "events": len(self.workouts)}

    def tool_get_learning_stats(self) -> dict:
        s = self.memory.stats()
        s["adaptations"] = self.memory.learned_notes()
        return s

    TOOLS = {
        "get_week_overview": "tool_get_week_overview", "get_exposure_report": "tool_get_exposure_report",
        "find_sedentary_gaps": "tool_find_sedentary_gaps", "propose_route_swaps": "tool_propose_route_swaps",
        "schedule_workouts": "tool_schedule_workouts", "suggest_meetups": "tool_suggest_meetups",
        "export_calendar": "tool_export_calendar", "get_learning_stats": "tool_get_learning_stats",
    }

    def call_tool(self, name: str, args: dict | None = None) -> dict:
        """Single entry point used by the LLM loop. Never raises - errors go back to the model."""
        if name not in self.TOOLS:
            return {"error": f"unknown tool '{name}'"}
        try:
            out = getattr(self, self.TOOLS[name])(**(args or {}))
        except Exception as exc:
            out = {"error": f"{type(exc).__name__}: {exc}"}
        self.tool_log.append({"tool": name, "args": args or {}})
        return out

    # ------------------------------------------------------------------ LEARN
    def give_feedback(self, item_id: str, accepted: bool) -> bool:
        return self.memory.record_feedback(item_id, accepted)

    # ------------------------------------------------------------------ pipeline + report
    def run(self, lang: str = "en", workouts: int = config.DEFAULT_WORKOUTS) -> dict:
        """OBSERVE -> PLAN -> ACT (deterministic). Records the plan in memory (for LEARN)."""
        self.observe()
        self.tool_get_exposure_report()
        self.tool_find_sedentary_gaps()
        self.tool_propose_route_swaps(apply=True)
        self.tool_schedule_workouts(workouts)
        self.tool_suggest_meetups()
        self.tool_export_calendar()
        return self.report(lang, record=True)

    def report(self, lang: str = "en", record: bool = False) -> dict:
        self._ensure()
        base = self.baseline
        swapped = weekly_report(self.env, self.week_swapped)
        final = weekly_report(self.env, self.final_week)
        gaps = detect_sedentary_gaps(self.week_swapped)
        filled = min(gaps_filled(gaps, self.workouts), len(gaps))
        learned = self.memory.learned_notes()
        stats = self.memory.stats()
        metrics = {
            "score_before": base["score"], "score_after_swaps": swapped["score"], "score_after_final": final["score"],
            "commute_pm_reduction_pct": _pct_drop(base["commute_pm_dose"], swapped["commute_pm_dose"]),
            "weekly_pm_reduction_pct_swaps_only": _pct_drop(base["pm_dose"], swapped["pm_dose"]),
            "weekly_pm_reduction_pct_incl_workouts": _pct_drop(base["pm_dose"], final["pm_dose"]),
            "gaps_total": len(gaps), "gaps_filled": filled, "workouts": len(self.workouts),
            "acceptance_rate": stats["acceptance_rate"],
        }
        rep = {
            "persona": {"key": self.persona, **PERSONAS[self.persona]},
            "city": config.CITIES[self.city]["name"], "city_key": self.city,
            "start_date": self.env.start_date.isoformat(),
            "data_source": self.env.source, "live_fraction": round(self.env.live_fraction, 3), "data_note": self.env.note,
            "baseline": base, "after_swaps": swapped, "after": final,
            "metrics": metrics, "gaps": gaps, "swaps": self.swaps, "workouts": self.workouts,
            "meetups": self.meetups or {"triggered": False, "items": [], "social_hours": round(social_hours(self.week), 1)},
            "learned": learned, "calendar_file": str(self.ics_path) if self.ics_path else None,
            "timeline": [[s.day, s.start, s.end, s.kind, s.place, s.mode] for s in self.final_week],
            "disclaimer": i18n.tr("disclaimer", lang),
        }
        rep["summary"] = i18n.build_summary(rep, lang)
        if record:
            items = [{"id": w["id"], "bucket": w["bucket"], "kind": "workout"} for w in self.workouts]
            items += [{"id": s["id"], "bucket": config.hour_bucket(s["new_start"]), "kind": "swap"} for s in self.swaps]
            self.memory.record_plan(rep["start_date"], base["score"], items)
        return rep
