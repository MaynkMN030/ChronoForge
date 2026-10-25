# CityPulse - every file explained (so you can answer any question)

Read this in order. Each section: **what it does**, **how it works**, **what to say if a judge asks**.

---
## 0. The big picture in 60 seconds
- CityPulse is an **agent**: it does not just show data, it runs a loop **Observe -> Plan -> Act -> Learn** and ends with actions (calendar slots, route/time swaps, meetup picks).
- **Observe**: get hourly weather, UV and PM2.5 for the city + the user's week (simulated persona).
- **Plan**: compute an exposure score, find long sitting blocks, search for better times/paths/workout slots.
- **Act**: write a calendar file, apply swaps, pick meetups, write the report (in English/Hindi/Kannada).
- **Learn**: remember which suggestions the user accepted or ignored and change next week's plan.
- Everything the agent can do is a **tool** (a method on `AgentSession`). The same tools are used by (a) a fixed pipeline and (b) an LLM that picks tools itself.

Data flow: `environment.py` + `personas.py` -> `exposure.py` -> `gaps.py` -> `routes.py` -> `workouts.py` -> `meetups.py` -> `calendar_tools.py` -> report (`agent.py`, `i18n.py`) -> web/CLI. `memory.py` feeds back into `routes.py` and `workouts.py`.

---
## 1. `citypulse/config.py` - the assumptions file
- One place for every number. If a judge asks "why 0.5 for PM2.5?", point here: these are **modelling assumptions**, not clinical facts.
- Cities: Bengaluru, Delhi, Mumbai with coordinates (used for the API) and fallback climate numbers (used only for offline synthetic data).
- `MODE_FACTOR`: how much outdoor air reaches you by travel mode (walk 1.0, run 1.5, bike 1.2, two-wheeler 0.95, auto 0.9, bus 0.6, metro 0.35, car 0.3, indoor 0.3).
- `INDOOR_FACTOR = 0.3`: indoor air is not clean - outdoor pollution leaks in.
- `WEIGHTS`: PM2.5 0.5, heat 0.3, UV 0.2 in the hourly exposure number.
- Normalisation: PM2.5 / 120 (capped at 2), heat from 30 C to 42 C apparent temperature -> 0..1, UV / 11.
- `SCORE_SCALE = 20`: converts raw weekly exposure to 0-100 with `100*(1-exp(-raw/20))`. Bands: Low <=33, Moderate <=66, High above.
- Planner settings: sedentary gap = 3 hours; workouts: at least 2 (default 3), 1 hour each, never ending after 21:00; greener path assumed to cut PM2.5 dose 20%; a swap is suggested only if it saves >=5%; indoor workout if forecast PM2.5 > 90 or very hot; social threshold 4 hours/week.
- `hour_bucket()`: early (<7), morning (<11), afternoon (<16), evening (<21), night. Used by the learning memory.

## 2. `citypulse/environment.py` - OBSERVE part 1 (the air and weather)
- `Environment` stores 7 days x 24 hours of temperature, humidity, UV, PM2.5 and `.at(day, hour)` returns one hour's values plus the **apparent temperature** (feels-like, from temperature + humidity).
- `fetch_open_meteo()` calls two free APIs: the Open-Meteo forecast API (temperature, humidity, UV) and the Open-Meteo Air Quality API (PM2.5). No API key.
- `synthetic_environment()` makes a **deterministic fake day/night pattern** (PM2.5 higher at night/rush hours, lowest in the afternoon; temperature peaks at ~15:00; UV peaks at noon). Same inputs -> same output.
- `get_environment()` tries live data and on **any** failure falls back to synthetic and writes why in `.note`. That is why the demo never breaks on bad wifi. The report always says `data_source: open-meteo | mixed | synthetic`.
- If asked: "PM2.5 from the open API is a modelled estimate (atmospheric model), not a sensor reading. We state that openly; station data (OpenAQ/CPCB) is the next step."

## 3. `citypulse/personas.py` - OBSERVE part 2 (the user's week)
- A `Segment` = one block of time: day, start/end hour, kind (home/commute/class/work/break/free/social/workout), place, travel mode, how outdoors (0-1), `flex` (hours it could be shifted), `active` (counts as movement), `path_alt` (greener route exists), `social`.
- Three personas: **Aarav** (student, walks, fixed class times), **Meera** (IT office, two-wheeler, long commute, flexible hours, almost no social time), **Rohan** (metro, hybrid job).
- Each persona has a weekday template and a weekend template; `build_week()` expands them into 7 days starting from the forecast start date.
- If asked: "The week is **simulated for the demo** (as stated in our proposal). In a real product it would come from calendar + a few saved places."
- To add your own week: copy one template function (e.g. `_office_weekday`), edit the times, add it to `TEMPLATES` and `PERSONAS`.

## 4. `citypulse/exposure.py` - PLAN part 1 (the Weekly Exposure Score)
- For each hour in each block: `exposure = hours x f x (0.5*PM + 0.3*Heat + 0.2*UV)`, where `f = outdoor*MODE_FACTOR + (1-outdoor)*INDOOR_FACTOR`.
- Sum over the week = `raw`. Score = `100*(1-exp(-raw/20))` -> 0-100 (the curve saturates so it can never exceed 100).
- Also tracks a **PM2.5 dose** (ug/m3 x hours, weighted by f) - this is what the "% reduction" metric uses.
- `weekly_report()` returns score, label, per-day totals, a 7x24 grid (the heatmap), commute-only totals and the top 5 exposure blocks.
- If asked "is this validated?": "No. It is a relative, transparent index built from published-style ingredients; weights are assumptions you can change in config.py. It guides behaviour, it is not a health measurement."

## 5. `citypulse/gaps.py` - PLAN part 2 (sedentary gaps)
- Walks each day, merges back-to-back blocks where the person is **not active**, and flags runs of >=3 hours.
- Inside a flagged gap, blocks of kind `free` are the **slots where movement fits**; a gap with no free slot gets "take 5-minute breaks".
- `gaps_filled()` counts gaps that now contain a scheduled workout (metric: "sedentary gaps filled").

## 6. `citypulse/routes.py` - PLAN part 3 + ACT (low-exposure route and timing)
- For every commute block it tries: **timing** (shift departure in 30-minute steps within the user's flexibility), **path** (greener/side-street, assumed -20% PM2.5), and **both**; keeps the best.
- Neighbouring blocks stretch/shrink so the day still adds up; a shift is rejected if it would squeeze a neighbour below 30 minutes (`shift_feasible`).
- Only suggested if it saves >=5%; the top 6 are kept. Fixed commutes (Aarav's classes) can only get a **path** swap.
- Park names come from OpenStreetMap (`osm.py`) when online, else from the curated list in config.
- The learning memory also nudges which time is picked (`memory.cost_multiplier`).
- If asked: "The 20% path benefit is an **assumption** from the idea that tree-lined/low-traffic roads have less roadside pollution; we expose it as one constant so it can be calibrated with real data."

## 7. `citypulse/workouts.py` - PLAN part 4 + ACT (workout slots)
- Candidates = every whole hour inside a `free` block (06:00-21:00).
- Cost of a candidate = exposure of a 1-hour run at that hour (clean air + comfortable heat + low UV = cheap), then discounted 3% per hour of that day's longest sitting block, max 8 hours (prefer long-gap days), x0.75 if the slot sits inside a flagged gap, x learning multiplier.
- If forecast PM2.5 > 90 or it is very hot, the slot becomes an **indoor** workout instead.
- Picks the cheapest slots on **different days, preferably not consecutive** (2 passes). Minimum 2 sessions always.
- `insert_workouts()` puts the chosen slots into the week so the "after" score includes their exposure (honest accounting).

## 8. `citypulse/meetups.py` + `data/meetups.json` - ACT (clubs and meetups)
- Triggered when weekly social hours < 4.
- Ranks events by interest match; subtracts points if the event is outdoors and the forecast air/heat is bad at that time; returns the top 2 with date and time.
- **The dataset is SAMPLE data** ("(sample)" in each name). Before the final demo replace it with real, verified local groups. Say this openly.

## 9. `citypulse/memory.py` - LEARN
- Saves, per user, each suggestion with its time-of-day bucket and status (pending / accepted / ignored) in `data/memory/<user>.json`. Stores **no location history**.
- Per bucket: `rate = (ignored+1)/(accepted+ignored+2)` (Laplace smoothing; 0.5 with no data). `cost_multiplier = exp(2.5*(rate-0.5))` (1.0 with no data; ~2.1 after 3 ignores in a row).
- Higher multiplier = that time looks more expensive to the planner, so next week it picks other times. Run `python run_demo.py --learning` to see Meera's early-morning slots disappear after she skips them.
- This is simple **online preference learning**, not deep learning. Say that - it is honest and defensible.

## 10. `citypulse/calendar_tools.py` and `google_calendar.py` - ACT (calendar)
- `build_ics()` writes a standard iCalendar file (times converted from IST to UTC, text escaped, 30-minute reminder). Works with Google, Apple, Outlook, phones. No login needed.
- `google_calendar.py` is an **optional** direct insert using the Google Calendar API (OAuth). Not needed for the demo; untested in our build environment.

## 11. `citypulse/osm.py` - OpenStreetMap
- One Overpass API query for named parks within 4 km of the city centre. On any failure returns `[]` and the curated list is used.

## 12. `citypulse/safety.py` - guardrails
- `classify()`: keyword screen -> `distress`, `medical` or `ok`. Distress wins.
- Distress -> the agent **stops advising** and shows helpline info (Tele-MANAS 14416, emergency 112) in English/Hindi/Kannada. Medical -> "I can only guide exposure and habits; please see a doctor."
- If asked: "It is a simple keyword screen suitable for a prototype, not a clinical tool; a production version would use a proper classifier and human escalation."

## 13. `citypulse/i18n.py` - multilingual
- Template strings for English, Hindi, Kannada (day names, labels, every sentence of the report). Works offline.
- In LLM mode the model can also write the report in any language. Have a native speaker proof-read the Hindi/Kannada strings before presenting.

## 14. `citypulse/agent.py` - the agent core
- `AgentSession` holds one user's state: environment, week, baseline report, swaps, workouts, meetups, calendar file, memory.
- **Tools** (methods): `get_week_overview`, `get_exposure_report`, `find_sedentary_gaps`, `propose_route_swaps`, `schedule_workouts`, `suggest_meetups`, `export_calendar`, `get_learning_stats`. `call_tool(name, args)` is the single entry point and never crashes (errors go back to the caller).
- `run()` = fixed pipeline: observe -> exposure -> gaps -> swaps -> workouts -> meetups -> calendar -> report, and records the plan in memory.
- `report()` builds the final dictionary with the metrics: commute PM2.5 reduction, whole-week reduction (swaps only and including workouts), gaps filled, acceptance rate.

## 15. `citypulse/agent_llm.py` - LLM tool-calling mode (optional)
- We describe the tools to the model as JSON schemas. The model replies with either text or "call tool X with these arguments". **We** execute the tool, send the result back, and repeat until the model writes its final report.
- The LLM never computes the numbers - tools do. The LLM chooses the order and writes the explanation. That keeps numbers trustworthy.
- Needs `ANTHROPIC_API_KEY` and `pip install anthropic`. Tested here with a **fake model** (the loop, the tool order, result passing); not with the real API.
- If asked "which agent framework?": "We implemented the loop directly with native tool calling; it can be ported to LangGraph (nodes = observe/plan/act/learn) - the tools are framework-independent."

## 16. `citypulse/service.py`, `main.py`, `static/` - the web app
- `service.py`: plain functions (`make_plan`, `feedback`, `chat`, `ics_path`). No web code, so they are easy to test.
- `main.py`: FastAPI routes - `GET /` dashboard, `GET /api/options`, `POST /api/plan`, `POST /api/feedback`, `POST /api/chat`, `GET /api/calendar/{user}.ics`. Auto-docs at `/docs`.
- `static/index.html` + `static/app.js`: dashboard with score tiles, summary, 7x24 exposure heatmap (green outline = workout), Accept/Skip buttons (that is the **learning input**), swaps, gaps, meetups, calendar download, and a safety-aware chat box. No libraries, so it works offline.

## 17. `run_demo.py` - command line
- `python run_demo.py [--city X] [--lang hi] [--live] [--persona office] [--learning] [--llm]`. Prints each persona's report and the metrics table and saves `output/results.md`, `results.json` and `.ics` files. Use it to produce numbers for your slides.

## 18. `tests/test_core.py` - 23 tests
- Scores in range; Delhi worse than Bengaluru; more PM2.5 -> higher score; swaps never increase commute exposure and keep each day's total time; fixed commutes only get path swaps; >=2 workouts on distinct days inside free time; indoor when air is terrible; learning moves slots away from ignored times; memory persists; calendar file correct (UTC conversion, escaping); safety classification; all three languages; Open-Meteo parsing (fake API); fallback when the network fails; the LLM loop with a fake model; the whole service flow.
- Run: `python -m pytest -q` (or `python -m tests.test_core` without pytest).

---
## Numbers cheat sheet
| Thing | Value |
|---|---|
| Hourly exposure | hours x f x (0.5 PM + 0.3 heat + 0.2 UV) |
| PM2.5 normaliser | /120, capped at 2 |
| Heat range | 30-42 C apparent temperature |
| Score | 100 x (1 - exp(-raw/20)); Low <=33, Moderate <=66, High above |
| Sedentary gap | >= 3 h inactive |
| Workouts | >= 2 (default 3), 1 h, end by 21:00, indoor if PM2.5 > 90 |
| Greener path | assumed -20% PM2.5; swap needs >= 5% saving |
| Social trigger | < 4 h per week |
| Learning | rate=(ign+1)/(acc+ign+2); multiplier=exp(2.5(rate-0.5)) |
