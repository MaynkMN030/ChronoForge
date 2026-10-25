"""Thin service layer between the agent and the web API (so it can be tested without a web server).

Every function takes/returns plain dicts. main.py only translates HTTP <-> these functions.
"""
from __future__ import annotations

from . import config, i18n, safety
from .agent import AgentSession
from .agent_llm import llm_available, run_llm_agent
from .personas import PERSONAS

SESSIONS: dict[str, AgentSession] = {}


def options() -> dict:
    return {
        "personas": {k: {"name": v["name"], "title": v["title"]} for k, v in PERSONAS.items()},
        "cities": {k: v["name"] for k, v in config.CITIES.items()},
        "languages": i18n.LANGS,
        "llm_available": llm_available(),
    }


def _key(persona: str, city: str, user_id: str | None) -> str:
    return user_id or f"{persona}-{city}"


def make_plan(persona: str = "office", city: str = config.DEFAULT_CITY, lang: str = "en",
              use_live: bool = True, user_id: str | None = None, persist_memory: bool = True,
              use_llm: bool = False, workouts: int = config.DEFAULT_WORKOUTS) -> dict:
    uid = _key(persona, city, user_id)
    sess = AgentSession(persona, city, use_live=use_live, user_id=uid, persist_memory=persist_memory)
    if use_llm:
        if not llm_available():
            raise RuntimeError("LLM mode needs `pip install anthropic` and the ANTHROPIC_API_KEY environment variable.")
        report = run_llm_agent(sess, i18n.LANGS.get(lang, "English"))
        report["summary"] = i18n.build_summary(report, lang)
    else:
        report = sess.run(lang=lang, workouts=workouts)
    SESSIONS[uid] = sess
    report["user_id"] = uid
    return report


def feedback(user_id: str, item_id: str, accepted: bool) -> dict:
    sess = SESSIONS.get(user_id)
    if sess is None:
        return {"ok": False, "error": "No active plan for this user. Generate a plan first."}
    ok = sess.give_feedback(item_id, accepted)
    return {"ok": ok, "stats": sess.memory.stats()}


def ics_path(user_id: str) -> str | None:
    sess = SESSIONS.get(user_id)
    return str(sess.ics_path) if sess and sess.ics_path else None


def chat(message: str, lang: str = "en", user_id: str | None = None) -> dict:
    """Safety first. Distress -> helpline only (the agent stops advising). Medical -> polite refusal."""
    kind = safety.classify(message)
    if kind != "ok":
        return {"kind": kind, "reply": safety.reply_for(kind, lang), "stop_advising": kind == "distress"}
    sess = SESSIONS.get(user_id or "")
    if sess is None or not sess.workouts:
        return {"kind": "ok", "reply": "Generate a plan first (pick a persona and press 'Generate plan'), then ask me about it."}
    m = message.lower()
    rep = sess.report(lang)
    if any(w in m for w in ("workout", "slot", "exercise", "run")):
        reply = "\n".join(i18n.build_summary(rep, lang)["lines"][3:3 + 1 + len(rep["workouts"])])
    elif any(w in m for w in ("commute", "route", "path", "timing")):
        reply = i18n.tr("commute", lang, pct=rep["metrics"]["commute_pm_reduction_pct"])
    elif any(w in m for w in ("score", "exposure")):
        reply = i18n.tr("score", lang, score=rep["baseline"]["score"], label=i18n.LABELS[lang if lang in i18n.LANGS else "en"][rep["baseline"]["label"]])
    else:
        reply = i18n.build_summary(rep, lang)["text"]
    return {"kind": "ok", "reply": reply}
