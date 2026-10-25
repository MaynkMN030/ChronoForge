"""Run the CityPulse simulation from the command line (no web server needed).

Examples
    python run_demo.py                       # 3 personas, Bengaluru, offline synthetic data
    python run_demo.py --live                # try real Open-Meteo data (falls back to synthetic if offline)
    python run_demo.py --city delhi --lang hi
    python run_demo.py --learning            # show the LEARN step: plan adapts when early slots are skipped
    python run_demo.py --llm                 # let Claude drive the tools (needs ANTHROPIC_API_KEY)
Outputs are also saved to output/results.json, output/results.md and output/*.ics
"""
import argparse
import json
import sys
from datetime import date

from citypulse import config
from citypulse.agent import AgentSession
from citypulse.agent_llm import llm_available, run_llm_agent
from citypulse.i18n import LANGS
from citypulse.personas import PERSONAS


def table(rows):
    head = ("Persona", "City", "Data", "Score", "Commute PM2.5", "Weekly PM2.5", "PM2.5 incl. workouts", "Gaps filled", "Workouts")
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        m = r["metrics"]
        lines.append("| {} | {} | {} | {} | -{}% | -{}% | {}% | {}/{} | {} |".format(
            r["persona"]["name"], r["city"], r["data_source"], m["score_before"],
            m["commute_pm_reduction_pct"], m["weekly_pm_reduction_pct_swaps_only"],
            f"{-m['weekly_pm_reduction_pct_incl_workouts']:+.1f}", m["gaps_filled"], m["gaps_total"], m["workouts"]))
    return "\n".join(lines)


def run_all(city, use_live, lang):
    rows = []
    for p in PERSONAS:
        s = AgentSession(p, city, use_live=use_live, persist_memory=False)
        rows.append(s.run(lang=lang))
    return rows


def learning_demo(city, use_live):
    print(f"\n=== LEARN demo: Meera keeps SKIPPING early-morning slots ({city}) ===")
    s = AgentSession("office", city, use_live=use_live, persist_memory=False)
    for week in range(1, 5):
        rep = s.run()
        slots = [(w["day"], w["start"], w["bucket"]) for w in rep["workouts"]]
        print(f"Week {week}: slots (day, hour, bucket) = {slots}")
        for w in rep["workouts"]:
            s.give_feedback(w["id"], accepted=(w["bucket"] != "early"))
        for sw in rep["swaps"]:
            s.give_feedback(sw["id"], accepted=True)
        print(f"        acceptance so far = {s.memory.stats()['acceptance_rate']}  adaptations = {s.memory.learned_notes()}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # so Hindi/Kannada print on Windows consoles
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--city", default=config.DEFAULT_CITY, choices=list(config.CITIES))
    ap.add_argument("--lang", default="en", choices=list(LANGS))
    ap.add_argument("--live", action="store_true", help="try live Open-Meteo data")
    ap.add_argument("--learning", action="store_true", help="show the learning loop over 4 weeks")
    ap.add_argument("--llm", action="store_true", help="LLM tool-calling mode (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--persona", default=None, choices=list(PERSONAS), help="only this persona")
    a = ap.parse_args()

    if a.llm:
        if not llm_available():
            sys.exit("LLM mode needs:  pip install anthropic   and   set ANTHROPIC_API_KEY.  (The normal mode needs neither.)")
        s = AgentSession(a.persona or "office", a.city, use_live=a.live, persist_memory=False)
        rep = run_llm_agent(s, LANGS[a.lang])
        print("Tools the model called, in order:", [t["tool"] for t in rep["llm"]["tool_calls"]])
        print("\n" + rep["llm"]["final_text"])
        return

    rows = run_all(a.city, a.live, a.lang)
    if a.persona:
        rows = [r for r in rows if r["persona"]["key"] == a.persona]
    for r in rows:
        print(f"\n===== {r['persona']['name']} - {r['persona']['title']} | {r['city']} | week of {r['start_date']} =====")
        print(f"Data: {r['data_source']} ({r['data_note']})")
        print(r["summary"]["text"])
        for s in r["swaps"][:3]:
            via = f" via {s['via']}" if s["via"] else ""
            print(f"   swap: day {s['day']} {s['place']}: {s['old_window']} -> {s['new_window']} [{s['type']}]{via}  saves {s['saving_pct']}%")
    print("\n" + table(rows))
    print("\nHow to read the PM2.5 columns: 'Commute' = PM2.5 breathed during commutes; 'Weekly' = whole week after commute swaps;\n"
          "'incl. workouts' = whole week after ALSO adding workouts (positive = a small increase: exercising outdoors\n"
          "means breathing more air; the planner puts it at the cleanest hours, and moves indoors when air is poor).")
    out = config.OUTPUT_DIR
    out.mkdir(exist_ok=True)
    (out / "results.json").write_text(json.dumps([{k: r[k] for k in ("persona", "city", "data_source", "metrics")} for r in rows], indent=2), encoding="utf-8")
    (out / "results.md").write_text(table(rows) + "\n", encoding="utf-8")
    print(f"\nSaved: {out/'results.json'}, {out/'results.md'}, calendar .ics files in {out}/")
    if a.learning:
        learning_demo(a.city, a.live)


if __name__ == "__main__":
    main()
