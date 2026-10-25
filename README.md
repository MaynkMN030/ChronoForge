# CityPulse

**An agentic AI that turns a person's weekly urban exposure (heat, UV, PM2.5) into healthier next-week actions.**

Team **Array of Hope** - ChronoForge (IET Cipher x Engineer NITK) - Theme: Cities of the Future - Track: Agentic AI

> CityPulse gives guidance on exposure and daily habits only. It makes **no medical diagnosis or treatment claims**.

## The problem
Urban Indians move through heat, strong UV and polluted air all week without ever seeing the total. Existing tools show one number at a time (today's AQI, a step count) and none of them plans what to do about it.

## What CityPulse does
| Feature | What the agent does |
|---|---|
| Weekly Exposure Score | One 0-100 score from time in heat, UV and PM2.5, weighted by how outdoors you are and how you travel |
| Sedentary gap detection | Finds 3h+ inactive blocks and the free slots where movement fits |
| Low-exposure route and timing | Suggests a different departure window and/or a greener path for the same trip |
| Auto-scheduled workouts | Picks 2+ sessions at low-pollution, comfortable-heat times (switches to indoor when air is poor) and exports a calendar file |
| Club and meetup suggestions | After a low-social week, recommends activities matching interests and the weekend forecast |
| Multilingual | English, Hindi, Kannada out of the box; any language in optional LLM mode |
| Learning | Records accepted/ignored suggestions and adapts next week's plan |

## The agent loop
```
 OBSERVE  ->  PLAN  ->  ACT  ->  LEARN
 fetch weather/UV/PM2.5      score exposure, find gaps,      calendar (.ics), route and      accepted/ignored ->
 + the user's week           rank routes/times/activities    timing swaps, meetups, report   adjust next week
```
Two ways to drive the same tools:
1. **Deterministic pipeline** (`AgentSession.run()`): no API key, same result every time. This is the default demo.
2. **LLM tool-calling mode** (`citypulse/agent_llm.py`): Claude decides which tools to call and writes the report. Optional; needs an API key.

## Quick start
Requires Python 3.10+.
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python -m pytest -q                      # 23 tests
python run_demo.py                       # 3 simulated personas, prints the report + metrics table
python run_demo.py --live                # try real Open-Meteo data (falls back to synthetic if offline)
python run_demo.py --learning            # shows the plan adapting when early slots are skipped
python -m uvicorn main:app --reload      # web dashboard at http://127.0.0.1:8000  (API docs at /docs)
```

## Simulation results (synthetic offline data, 3 personas, one simulated week)
| Persona | City | Score (0-100) | Commute PM2.5 | Whole-week PM2.5 (commute swaps) | Whole-week PM2.5 incl. workouts | Long sitting blocks with a workout |
|---|---|---|---|---|---|---|
| Aarav (student) | Bengaluru | 33.1 | -12.9% | -1.7% | +6.9% | 2/17 |
| Meera (office, two-wheeler) | Bengaluru | 36.8 | -9.7% | -3.7% | +3.7% | 3/7 |
| Rohan (metro) | Bengaluru | 31.4 | -12.4% | -1.5% | +7.7% | 3/7 |
| Aarav (student) | Delhi | 70.2 | -13.7% | -1.8% | -1.8% | 3/17 |
| Meera (office, two-wheeler) | Delhi | 75.3 | -10.7% | -3.8% | -3.8% | 3/7 |
| Rohan (metro) | Delhi | 68.3 | -9.8% | -1.4% | -1.4% | 3/7 |

How to read it honestly: commute swaps cut PM2.5 breathed **during commutes** by roughly 10-14%. Over the **whole week** the effect is smaller (about 1.5-4%) because most hours are spent indoors. Adding outdoor workouts raises PM2.5 intake slightly in clean-air cities (you breathe more air while exercising) - the planner therefore places workouts at the cleanest hours and moves them indoors when air is poor (as in the Delhi runs). The benefit of the extra movement is not part of this metric. These numbers come from a **simulation on synthetic data** with the assumptions listed in `citypulse/config.py`; they are not measurements.

## Project layout
```
citypulse/
  config.py          every tunable number and assumption in one place
  environment.py     OBSERVE: Open-Meteo weather/UV/air quality + offline fallback
  personas.py        OBSERVE: the simulated user weeks (3 personas)
  exposure.py        PLAN: the Weekly Exposure Score engine
  gaps.py            PLAN: sedentary-gap detection
  routes.py          PLAN/ACT: low-exposure timing and path swaps
  workouts.py        PLAN/ACT: workout slot scheduler
  meetups.py         ACT: club/meetup recommender (data/meetups.json = SAMPLE data)
  calendar_tools.py  ACT: .ics calendar export        google_calendar.py: optional real Google Calendar
  osm.py             OpenStreetMap park lookup (with fallback)
  memory.py          LEARN: accepted/ignored history -> adapts the plan
  agent.py           the agent core: session + tools + pipeline
  agent_llm.py       LLM tool-calling loop (optional)
  safety.py          distress detection (Tele-MANAS 14416) and no-diagnosis guard
  i18n.py            English / Hindi / Kannada report text
  service.py         plain-Python layer used by the web API
main.py              FastAPI server           static/   dashboard (HTML + JS)
run_demo.py          command-line simulation  tests/    23 automated tests
```

## Privacy and safety by design
- Stores only place names, times, scores and accepted/ignored flags - no GPS trail, no raw location history.
- No medical diagnosis or treatment claims. If a user message shows distress, the agent stops advising and shows helpline details (Tele-MANAS 14416, India).

## Known limits (stated openly)
- Air-quality values from open APIs are modelled estimates, and indoor exposure is approximated by a fixed factor; the score is a **relative guide**.
- The user's week is **simulated** (three personas) for the demo; there is no real location tracking.
- Meetup data in `data/meetups.json` is a **sample** dataset; replace it with verified local groups.
- Not yet built: OpenAQ/CPCB station data, Telegram bot, gig-worker persona, ward-level dashboards (planned extensions).

## Data sources and credits
- [Open-Meteo](https://open-meteo.com) weather and air-quality APIs (free for non-commercial use; attribution required, CC BY 4.0).
- (c) [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL) via the Overpass API.

## AI assistance
The proposal and the first version of this code were drafted with Claude (Anthropic) and then reviewed, run and tested by the team.
