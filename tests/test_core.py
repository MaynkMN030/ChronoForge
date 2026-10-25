"""CityPulse tests. Run with  `pytest -q`  (or without pytest:  `python -m tests.test_core`).
They use only offline synthetic data and fake network/LLM objects, so they never need internet or an API key."""
import json
import tempfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from citypulse import config, i18n, safety, service
from citypulse.agent import AgentSession
from citypulse.agent_llm import TOOL_SCHEMAS, run_llm_agent
from citypulse.calendar_tools import build_ics
from citypulse.environment import (Environment, apparent_temperature, fetch_open_meteo, get_environment,
                                   synthetic_environment)
from citypulse.exposure import segment_factor, weekly_report
from citypulse.gaps import detect_sedentary_gaps
from citypulse.memory import Memory
from citypulse import osm
from citypulse.personas import PERSONAS, build_week, social_hours
from citypulse.routes import propose_route_swaps
from citypulse.workouts import schedule_workouts

START = date(2026, 10, 24)  # a Saturday


def session(persona="office", city="bengaluru", tmp=None):
    tmp = tmp or tempfile.mkdtemp()
    return AgentSession(persona, city, use_live=False, persist_memory=False, start_date=START, output_dir=tmp)


# ------------------------------------------------------------------ environment
def test_apparent_temperature_rises_with_humidity():
    assert apparent_temperature(32, 80) > apparent_temperature(32, 30)


def test_synthetic_env_is_deterministic_and_shaped():
    a, b = synthetic_environment("delhi", START), synthetic_environment("delhi", START)
    assert a.pm25 == b.pm25 and len(a.pm25) == 7 and all(len(r) == 24 for r in a.pm25)
    assert a.source == "synthetic"


def test_open_meteo_parsing_with_fake_api():
    from datetime import timedelta
    times = [f"{(START + timedelta(days=d)).isoformat()}T{h:02d}:00" for d in range(7) for h in range(24)]
    n = len(times)

    class Resp:
        def __init__(self, payload): self.payload = payload
        def raise_for_status(self): pass
        def json(self): return self.payload

    class FakeSession:
        def get(self, url, params=None, timeout=None):
            if "air-quality" in url:
                return Resp({"hourly": {"time": times, "pm2_5": [77.0] * n}})
            return Resp({"hourly": {"time": times, "temperature_2m": [30.0] * n,
                                    "relative_humidity_2m": [50.0] * n, "uv_index": [4.0] * n}})

    env = fetch_open_meteo("bengaluru", session=FakeSession())
    assert env.source == "open-meteo" and env.live_fraction == 1.0
    assert env.at(2, 10)["pm25"] == 77.0 and env.at(2, 10)["temp"] == 30.0


def test_falls_back_to_synthetic_when_network_fails(monkeypatch=None):
    import citypulse.environment as E
    original = E.fetch_open_meteo
    E.fetch_open_meteo = lambda *a, **k: (_ for _ in ()).throw(ConnectionError("no wifi"))
    try:
        env = get_environment("bengaluru", START, use_live=True)
    finally:
        E.fetch_open_meteo = original
    assert env.source == "synthetic" and "unavailable" in env.note


def test_osm_parks_parsing_and_failure_fallback():
    class R:
        def raise_for_status(self): pass
        def json(self): return {"elements": [{"tags": {"name": "Test Park"}}, {"tags": {"name": "Test Park"}}, {"tags": {}}]}
    osm._CACHE.clear()
    assert osm.nearby_parks("bengaluru", session=SimpleNamespace(post=lambda *a, **k: R())) == ["Test Park"]
    osm._CACHE.clear()
    def boom(*a, **k): raise ConnectionError("blocked")
    assert osm.nearby_parks("delhi", session=SimpleNamespace(post=boom)) == []
    osm._CACHE.clear()


# ------------------------------------------------------------------ exposure
def test_mode_factor_ordering():
    assert segment_factor("metro", 0.3) < segment_factor("walk", 1.0) < segment_factor("run", 1.0)
    assert segment_factor("indoor", 0.0) == config.INDOOR_FACTOR


def test_scores_in_range_and_delhi_worse_than_bengaluru():
    for p in PERSONAS:
        blr = session(p, "bengaluru"); blr.observe()
        dl = session(p, "delhi"); dl.observe()
        assert 0 <= blr.baseline["score"] <= 100
        assert dl.baseline["score"] > blr.baseline["score"]


def test_more_pm_means_higher_score():
    env = synthetic_environment("bengaluru", START)
    week = build_week("office", START)
    base = weekly_report(env, week)["score"]
    env2 = synthetic_environment("bengaluru", START)
    env2.pm25 = [[v * 3 for v in row] for row in env2.pm25]
    assert weekly_report(env2, week)["score"] > base


# ------------------------------------------------------------------ gaps
def test_student_class_block_is_flagged():
    week = build_week("student", date(2026, 10, 26))  # a Monday
    gaps = detect_sedentary_gaps(week)
    monday = [g for g in gaps if g["day"] == 0]
    assert any(abs(g["hours"] - 4.5) < 0.01 for g in monday)          # the 4.5h lecture block
    assert any(g["has_free_slot"] for g in monday)                      # evening free time sits in a gap


# ------------------------------------------------------------------ swaps
def test_swaps_never_increase_commute_exposure_and_keep_days_whole():
    for p in PERSONAS:
        s = session(p); s.observe()
        swaps, new_week = propose_route_swaps(s.env, s.week, ["Park"])
        before = weekly_report(s.env, s.week)["commute_exposure"]
        after = weekly_report(s.env, new_week)["commute_exposure"]
        assert after <= before + 1e-9
        for d in range(7):  # every day still covers the same total time and no block is negative/zero
            assert abs(sum(x.hours for x in s.week if x.day == d) - sum(x.hours for x in new_week if x.day == d)) < 1e-6
        assert all(x.hours > 0.25 for x in new_week)


def test_fixed_commutes_only_get_path_swaps():
    s = session("student"); s.observe()
    swaps, _ = propose_route_swaps(s.env, s.week, ["Park"])
    assert swaps and all(sw["shift_hours"] == 0 and sw["type"] == "path" for sw in swaps)


# ------------------------------------------------------------------ workouts
def test_workouts_min_two_distinct_days_inside_free_time():
    s = session(); s.observe()
    slots = schedule_workouts(s.env, s.week, detect_sedentary_gaps(s.week), None, count=3)
    assert len(slots) >= 2 and len({w["day"] for w in slots}) == len(slots)
    for w in slots:
        assert any(x.kind == "free" and x.day == w["day"] and x.start <= w["start"] and w["end"] <= x.end + 1e-9 for x in s.week)
        assert w["end"] <= config.WORKOUT_LATEST_END + 1e-9


def test_workout_goes_indoor_when_air_is_very_bad():
    s = session(); s.observe()
    s.env.pm25 = [[300.0] * 24 for _ in range(7)]
    slots = schedule_workouts(s.env, s.week, [], None, count=2)
    assert slots and all(w["type"] == "indoor" for w in slots)


def test_asking_for_fewer_than_two_still_gives_two():
    s = session(); s.observe()
    assert len(schedule_workouts(s.env, s.week, [], None, count=1)) >= 2


# ------------------------------------------------------------------ learning
def test_learning_moves_slots_away_from_ignored_bucket():
    s = session()
    rep1 = s.run()
    early1 = sum(1 for w in rep1["workouts"] if w["bucket"] == "early")
    assert early1 >= 1
    for w in rep1["workouts"]:
        s.give_feedback(w["id"], accepted=(w["bucket"] != "early"))
    rep2 = s.run()
    early2 = sum(1 for w in rep2["workouts"] if w["bucket"] == "early")
    assert early2 < early1
    assert any(n["bucket"] == "early" for n in rep2["learned"])
    assert len(rep2["workouts"]) >= 2


def test_memory_cost_multiplier_and_persistence():
    with tempfile.TemporaryDirectory() as d:
        m = Memory("u1", Path(d))
        assert m.cost_multiplier(6) == 1.0
        m.record_plan("2026-10-24", 40.0, [{"id": "a", "bucket": "early", "kind": "workout"}])
        assert m.record_feedback("a", accepted=False) is True
        assert m.record_feedback("a", accepted=False) is False   # already answered
        assert m.cost_multiplier(6) > 1.0                          # ignored 'early' bucket got more expensive
        assert m.cost_multiplier(12) == 1.0                        # untouched bucket unchanged
        assert Memory("u1", Path(d)).stats()["ignored"] == 1      # survived a reload


# ------------------------------------------------------------------ meetups / calendar
def test_meetups_only_for_low_social_weeks():
    office = session("office"); office.observe()
    assert social_hours(office.week) < config.SOCIAL_HOURS_THRESHOLD
    assert office.tool_suggest_meetups()["triggered"] is True and office.meetups["items"]
    student = session("student"); student.observe()
    assert student.tool_suggest_meetups()["triggered"] is False


def test_ics_has_events_in_utc_and_escapes_text():
    slots = [{"date": "2026-10-26", "start": 6.0, "end": 7.0, "title": "Run, walk; fun", "type": "outdoor",
              "pm25": 30.0, "temp": 22.0, "uv": 0.0}]
    ics = build_ics(slots)
    assert ics.startswith("BEGIN:VCALENDAR") and ics.count("BEGIN:VEVENT") == 1
    assert "DTSTART:20261026T003000Z" in ics            # 06:00 IST = 00:30 UTC
    assert r"Run\, walk\; fun" in ics


# ------------------------------------------------------------------ safety / i18n
def test_safety_classification():
    assert safety.classify("I want to die") == "distress"
    assert safety.classify("मुझे आत्महत्या के विचार आ रहे हैं") == "distress"
    assert safety.classify("Do I have asthma? what medicine should I take") == "medical"
    assert safety.classify("when is my workout?") == "ok"
    assert "14416" in safety.reply_for("distress", "kn")


def test_all_languages_render():
    rep = session().run(lang="en")
    for lang in ("en", "hi", "kn"):
        text = i18n.build_summary(rep, lang)["text"]
        assert str(rep["baseline"]["score"]) in text
    assert i18n.build_summary(rep, "kn")["text"] != i18n.build_summary(rep, "en")["text"]


# ------------------------------------------------------------------ LLM tool-calling loop (fake client)
def _block(type_, **kw): return SimpleNamespace(type=type_, **kw)


def test_llm_agent_loop_runs_tools_in_order_with_fake_client():
    script = [
        [("get_week_overview", {}), ("get_exposure_report", {})],
        [("find_sedentary_gaps", {}), ("propose_route_swaps", {"apply": True})],
        [("schedule_workouts", {"count": 3})],
        [("suggest_meetups", {}), ("export_calendar", {}), ("get_learning_stats", {})],
    ]
    calls = []

    class FakeMessages:
        def create(self, **kw):
            calls.append(kw)
            i = len(calls) - 1
            if i < len(script):
                content = [_block("tool_use", id=f"t{i}-{j}", name=n, input=a) for j, (n, a) in enumerate(script[i])]
                return SimpleNamespace(content=content, stop_reason="tool_use")
            return SimpleNamespace(content=[_block("text", text="Your weekly report: ...")], stop_reason="end_turn")

    s = session()
    rep = run_llm_agent(s, "English", client=SimpleNamespace(messages=FakeMessages()))
    names = [t["tool"] for t in rep["llm"]["tool_calls"]]
    assert names == ["get_week_overview", "get_exposure_report", "find_sedentary_gaps", "propose_route_swaps",
                     "schedule_workouts", "suggest_meetups", "export_calendar", "get_learning_stats"]
    assert rep["llm"]["final_text"].startswith("Your weekly report")
    assert len(rep["workouts"]) >= 2 and Path(rep["calendar_file"]).exists()
    assert calls[0]["tools"] == TOOL_SCHEMAS and "system" in calls[0]
    # the tool results must have been sent back to the model as tool_result blocks
    last_user = [m for m in calls[-1]["messages"] if m["role"] == "user"][-1]
    assert last_user["content"][0]["type"] == "tool_result"
    json.loads(last_user["content"][0]["content"])      # valid JSON


def test_unknown_tool_and_bad_args_do_not_crash_the_agent():
    s = session(); s.observe()
    assert "error" in s.call_tool("does_not_exist")
    assert "error" in s.call_tool("schedule_workouts", {"count": "banana"})
    assert "error" in s.call_tool("export_calendar")    # nothing scheduled yet


# ------------------------------------------------------------------ service layer (what the web API calls)
def test_service_plan_feedback_chat_flow():
    service.SESSIONS.clear()
    rep = service.make_plan("metro", "bengaluru", "hi", use_live=False, user_id="t-user", persist_memory=False)
    assert rep["user_id"] == "t-user" and rep["summary"]["lang"] == "hi"
    wid = rep["workouts"][0]["id"]
    assert service.feedback("t-user", wid, True)["ok"] is True
    assert service.feedback("nobody", wid, True)["ok"] is False
    assert service.chat("when are my workouts?", "en", "t-user")["kind"] == "ok"
    d = service.chat("I feel hopeless", "en", "t-user")
    assert d["kind"] == "distress" and d["stop_advising"] and "14416" in d["reply"]
    assert service.chat("what medicine for asthma", "en", "t-user")["kind"] == "medical"
    assert service.ics_path("t-user") and Path(service.ics_path("t-user")).exists()


if __name__ == "__main__":
    import traceback
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn(); print("PASS", name)
        except Exception:
            failed += 1; print("FAIL", name); traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)
