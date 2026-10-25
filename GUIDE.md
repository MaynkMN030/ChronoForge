# CityPulse - Team Guide (START HERE)

Follow the parts in order. Every step says exactly what to type, what you should see, and **what to do if it goes wrong**.
Time needed: Parts B-D about 60-90 minutes. Part G (demo day) is what wins - do not skip it.

---
## 0. Read this first: what you have, and what is and is not verified

**What is in the zip:** a complete working project (code + tests + web dashboard + Colab notebook + docs). Files: see `README.md`. Explanations of every file: `CODE_EXPLAINED.md`. Questions judges may ask, with answers: `VIVA_QA.md`.

**Verified before you got it (in my build environment):**
- 23 automated tests pass.
- The full simulation runs for 3 personas x 3 cities x 3 languages; calendar `.ics` files are generated correctly.
- The "agent chooses tools itself" loop works (tested with a stand-in model).
- The web layer's logic works (tested with a stand-in for FastAPI).
- The offline fallback works: when live data cannot be reached, the agent says so and uses synthetic data.

**NOT verified (my environment had no internet access to these). You must check them on your laptop in Part C - this is your first 15 minutes:**
1. Real **Open-Meteo** and **OpenStreetMap** calls (`python run_demo.py --live` should print `Data: open-meteo`).
2. The **FastAPI web server and dashboard in a real browser**.
3. **LLM mode** with a real API key (optional).
4. **Google Calendar API** (optional; the `.ics` file already does the job).

**Differences from your proposal - know them, say them confidently:**
| Proposal says | What the code actually does | What to say |
|---|---|---|
| OpenAQ / CPCB station PM2.5 | Uses Open-Meteo's air-quality API (modelled estimates) | "MVP uses modelled PM2.5; station data from OpenAQ/CPCB is the next integration. We state this limit openly." |
| LangGraph | Own Observe-Plan-Act-Learn loop + native LLM tool calling | "The loop is framework-independent and ports to LangGraph." |
| Google Calendar API | `.ics` export (works everywhere); optional real API module | "Slots go into any calendar through a standard file; direct Google insert is an optional module." |
| Web **or** Telegram | Web dashboard only | "We chose the web dashboard; Telegram is a thin wrapper over the same service layer." |
| Multilingual via LLM | Built-in Hindi/Kannada/English templates + optional LLM for any language | "Works offline; LLM mode extends it." |
| User week | Simulated personas (as the proposal said) | Same as proposal. |

Be honest in front of judges: **claiming things that are not built is the fastest way to lose points; showing limits openly is a strength** (your proposal already does this).

---
## Part A. Understand the problem and the AI (10 minutes - read, then explain it to each other)

**A1. The problem in plain words.** People in Indian cities spend a week moving through heat, strong sun and polluted air, but they only ever see one number at a time (today's AQI, a step count). Nobody adds it up, and nobody tells them *what to change next week*.

**A2. What "agentic AI" means.** A chatbot answers questions. A dashboard shows data. An **agent** is given a goal and then works in a loop: it looks at the situation, makes a plan, **uses tools to take actions**, and learns from the result. CityPulse's goal: *lower this person's exposure and raise their movement next week*.

**A3. What the agent does (the 4 stages):**
| Stage | What happens | Where in code |
|---|---|---|
| **Observe** | Get hourly weather, UV, PM2.5 for the city + the user's week | `environment.py`, `personas.py` |
| **Plan** | Score the week, find long sitting blocks, rank better times/paths/workout slots | `exposure.py`, `gaps.py`, `routes.py`, `workouts.py` |
| **Act** | Create calendar slots, apply route/time swaps, pick meetups, write the report | `calendar_tools.py`, `meetups.py`, `i18n.py` |
| **Learn** | Remember accepted vs ignored suggestions; adapt next week | `memory.py` |

**A4. "Where is the AI?" (you WILL be asked).** Three honest answers:
1. **Agentic planning with tools** - the agent decides and acts, it does not just report.
2. **Online learning from feedback** - the plan changes based on what the user followed (run `python run_demo.py --learning`).
3. **LLM tool-calling mode** - an LLM decides which tools to call and writes the report in the user's language (optional, needs an API key). The numbers always come from tested tools, never from the LLM's imagination.

**A5. Picture to keep in your head**
```
 Open data (weather, UV, PM2.5, parks) + user's week
                 |
        [ OBSERVE ] -> [ PLAN ] -> [ ACT ] -> [ LEARN ] --(feedback)--+
             ^                                                         |
             +---------------- next week's plan is adjusted -----------+
 Outputs: exposure report | calendar workout slots | route/time swaps | meetup picks
```

---
## Part B. One-time setup on a laptop (do this on EVERY teammate's laptop that will run the project)

**Step B1 - Install Python 3.10 or newer.** Download from python.org. **Windows: tick "Add python.exe to PATH" on the first installer screen.**
Check: open a terminal (Windows: PowerShell; Mac: Terminal) and type `python --version` (Mac/Linux may need `python3 --version`).
> If it says "not recognized": reinstall Python and tick "Add to PATH", or use `py --version` on Windows. If the version is below 3.10, install a newer one - the web server needs 3.10+.

**Step B2 - Install Git** from git-scm.com (accept defaults). Check: `git --version`.

**Step B3 - Install VS Code** (code.visualstudio.com) - optional but makes life easier.

**Step B4 - Create a GitHub account** at github.com (one per person; the team repo is shared later).

**Step B5 - Tell Git who you are (once per laptop):**
```
git config --global user.name "Your Name"
git config --global user.email "the-email-you-used-on-github@example.com"
```
> Use the same email as your GitHub account, otherwise your commits will not show under your profile.

**Step B6 - Unzip `citypulse-hackathon.zip`** somewhere simple (e.g. `Documents`), then open that folder in VS Code (File > Open Folder) and open a terminal inside it (Terminal > New Terminal). All commands below are typed **inside that folder**.

---
## Part C. Run and test it on your laptop (first 30 minutes - do this BEFORE GitHub)

**Step C1 - Create a virtual environment (an isolated Python for this project):**
- Windows PowerShell: `python -m venv .venv` then `.venv\Scripts\activate`
- Mac/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`

You should now see `(.venv)` at the start of the terminal line.
> **Windows error "running scripts is disabled on this system":** run `Set-ExecutionPolicy -Scope Process Bypass` and then the activate command again.

**Step C2 - Install the libraries:** `pip install -r requirements.txt`
> If `anthropic` fails to install, delete that one line from `requirements.txt` and run again - it is only for optional LLM mode.
> If `pip` is not found: use `python -m pip install -r requirements.txt`.

**Step C3 - Run the tests:** `python -m pytest -q`
Expected last line: `23 passed`. (If pytest is missing: `python -m tests.test_core` prints `23/23 passed`.)
> A failing test = tell the team; do not continue until you understand it. Copy the error text into Claude and ask.

**Step C4 - Run the simulation:** `python run_demo.py`
Expected: three reports (Aarav, Meera, Rohan) and a table like:
```
| Persona | City | Data | Score | Commute PM2.5 | Weekly PM2.5 | PM2.5 incl. workouts | Gaps filled | Workouts |
| Aarav | Bengaluru | synthetic | 33.1 | -12.9% | -1.7% | +6.9% | 2/17 | 3 |
| Meera | Bengaluru | synthetic | 36.8 | -9.7%  | -3.7% | +3.7% | 3/7  | 3 |
| Rohan | Bengaluru | synthetic | 31.4 | -12.4% | -1.5% | +7.7% | 3/7  | 3 |
```
(Dates differ; numbers come from synthetic data, so they should match these closely.) Files appear in the `output` folder (`results.md`, `.ics` calendars).
> **Hindi/Kannada shows as boxes or errors on Windows?** Run `$env:PYTHONUTF8=1` first, and use Windows Terminal or VS Code's terminal.

**Step C5 - Try live data:** `python run_demo.py --live`
Look at the line starting `Data:`.
- `Data: open-meteo (...)` = real forecast is working. 
- `Data: synthetic (Live data unavailable (...))` = the internet/API was not reachable; the agent fell back safely. Check wifi/VPN/firewall and try again. The text in brackets names the cause (e.g. `ConnectionError`, `Timeout`, `HTTPError`).
> If you see `open-meteo` but with `mixed`, some hours were missing and filled synthetically - fine.
> If `HTTPError 400`: the API changed a parameter name - copy the full error to Claude. Demo still works on fallback.

**Step C6 - See the learning loop:** `python run_demo.py --learning`
Expected: week 1 has three early-morning (06:00) slots; after Meera skips them, week 2 moves them to the evening.

**Step C7 - Start the web dashboard:** `python -m uvicorn main:app --reload`
Open **http://127.0.0.1:8000** in Chrome. You should see the CityPulse page.
1. Choose a persona, city, language; leave "Try live Open-Meteo data" ticked (it falls back automatically).
2. Press **Generate plan**. Tiles, a summary, a heatmap, workout slots, swaps, sitting blocks and meetups appear.
3. Press **Accept / Skip** on workout rows, then press Generate plan again - watch the plan adapt.
4. Click **Download calendar file (.ics)** and open it (it adds the workouts to a calendar).
5. In "Ask the agent" type `when are my workouts?`, then type `I feel hopeless` - the agent must stop advising and show **Tele-MANAS 14416**.
Auto-generated API page: **http://127.0.0.1:8000/docs**. Stop the server with `Ctrl + C`.
> **"No module named fastapi"**: the virtual environment is not active or Step C2 failed - repeat C1 and C2.
> **"Address already in use"**: add `--port 8001` and open `http://127.0.0.1:8001`.
> **Page loads but buttons do nothing / "Could not load options"**: press F12 > Console tab and copy the red error to Claude. Make sure you started the server from the project folder.
> **"ModuleNotFoundError: citypulse"**: you are in the wrong folder; `cd` into the folder that contains `main.py`.

---
## Part D. Put it on GitHub (step by step, with a commit history that tells the story)

Judges look at your repo AND your commit history. Make several meaningful commits over the day - **do not do one giant commit, and never fake or backdate timestamps**. Use the commits below as you actually read and understand each part (that reading is also your viva preparation).

**Step D1 - Create the repository** (one teammate, the "owner"):
1. github.com > click **+** (top right) > **New repository**.
2. Repository name: `citypulse`. Description: *CityPulse - agentic AI for urban exposure (Array of Hope, ChronoForge)*.
3. Choose **Public** (judges must be able to open it).
4. **Do NOT tick** "Add a README", ".gitignore" or "license" (we already have them - ticking causes a push error).
5. Click **Create repository**. Copy the URL, like `https://github.com/YOUR-USERNAME/citypulse.git`.

**Step D2 - Connect your folder to it** (inside the project folder):
```
git init
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/citypulse.git
git status
```
`git status` should list files in red as "untracked". `.venv`, `output`, `__pycache__` must **not** appear (they are ignored on purpose).
> If `git init` says "already a repository", skip it. If `remote origin already exists`: `git remote set-url origin https://github.com/YOUR-USERNAME/citypulse.git`.

**Step D3 - Make the commits, one group at a time.** Run each block, then move on. Space them out while you read the code.

Commit 1 - project skeleton and configuration
```
git add .gitignore .env.example requirements.txt README.md citypulse/__init__.py citypulse/config.py
git commit -m "Project skeleton: config with all exposure-model assumptions"
```
Commit 2 - data layer (Observe)
```
git add citypulse/environment.py citypulse/personas.py citypulse/osm.py
git commit -m "Observe: Open-Meteo connector with offline fallback, simulated personas, OSM parks"
```
Commit 3 - exposure engine and gap detection (Plan)
```
git add citypulse/exposure.py citypulse/gaps.py
git commit -m "Plan: weekly exposure score engine and sedentary gap detection"
```
Commit 4 - planners and actions (Plan + Act)
```
git add citypulse/routes.py citypulse/workouts.py citypulse/meetups.py data/meetups.json citypulse/calendar_tools.py citypulse/google_calendar.py
git commit -m "Act: low-exposure route/timing swaps, workout scheduler, meetup recommender, calendar export"
```
Commit 5 - learning, safety, languages
```
git add citypulse/memory.py citypulse/safety.py citypulse/i18n.py
git commit -m "Learn + safety: accepted/ignored memory, distress guard (Tele-MANAS), en/hi/kn reports"
```
Commit 6 - the agent core
```
git add citypulse/agent.py citypulse/agent_llm.py citypulse/service.py run_demo.py
git commit -m "Agent core: observe-plan-act-learn loop, tool interface, LLM tool-calling mode, demo runner"
```
Commit 7 - web interface
```
git add main.py static/
git commit -m "FastAPI backend and dashboard (heatmap, accept/skip feedback, calendar download, safe chat)"
```
Commit 8 - tests and docs
```
git add tests/ CODE_EXPLAINED.md GUIDE.md VIVA_QA.md CityPulse_Colab.ipynb docs/
git commit -m "Tests (23), Colab notebook, documentation"
```
> `error: pathspec '...' did not match any files`: a file name was mistyped or a file is missing - run `git status` and add whatever is still untracked.
> `Author identity unknown`: redo Step B5.

**Step D4 - Push to GitHub:** `git push -u origin main`
A browser window or login box appears - sign in to GitHub (Git Credential Manager does this on Windows/Mac).
> If asked for a **password** in the terminal: GitHub no longer accepts account passwords. Create a token: GitHub > profile picture > Settings > Developer settings > Personal access tokens > Tokens (classic) > Generate new token > tick `repo` > copy it > paste it as the password.
> `remote: Repository not found`: wrong URL or you are signed in to a different account. Check `git remote -v`.
> `failed to push some refs ... fetch first`: the remote has something you do not (usually a README created on GitHub). Run `git pull origin main --rebase` then `git push -u origin main`.
> `src refspec main does not match any`: you have not committed yet or the branch is named differently - run `git branch -M main` after at least one commit.

Refresh the GitHub page: you should see all folders, and README.md renders below the file list.

**Step D5 - Add teammates and make everyone commit.**
- Repo > **Settings > Collaborators > Add people** > enter each teammate's GitHub username (they accept by email).
- Each teammate: `git clone https://github.com/YOUR-USERNAME/citypulse.git`, set up Part B5 and Part C, make changes, then:
  ```
  git pull
  git add <files>
  git commit -m "what you changed and why"
  git push
  ```
- **Always `git pull` before `git push`.** If you get a merge conflict, open the file, keep the right lines, remove the `<<<<<<<`/`>>>>>>>` markers, then `git add` and `git commit`.
- Real contributions each person can make (also great for the viva): replace sample meetups with real verified groups (`data/meetups.json`); proof-read Hindi/Kannada (`i18n.py`); add a 4th persona (e.g. gig worker - the planned extension); add a city; improve the dashboard; write 2 more tests.

**Suggested split (change freely):**
| Person | Owns | Should be able to explain |
|---|---|---|
| Mayank | agent core, `agent.py`, `agent_llm.py`, demo | the Observe-Plan-Act-Learn loop and tools |
| Samarth | data layer: `environment.py`, `osm.py`, `personas.py` | data sources, fallback, assumptions |
| Pruthviraj | planners: `exposure.py`, `gaps.py`, `routes.py`, `workouts.py` | the score formula and swaps |
| Aniket | `main.py`, `static/`, `i18n.py`, `safety.py`, slides | web app, languages, safety, demo flow |
Everyone must still read `CODE_EXPLAINED.md` fully.

**Step D6 - Safety checks before every push**
- `git status` must never show `.env`, `credentials.json`, `token.json` or any API key. If a secret was ever committed, **revoke the key immediately** (deleting the file is not enough).
- Be transparent about AI assistance: the README has an "AI assistance" line. **Check the hackathon rules** on AI-generated code and edit that line to match what is true for your team.

---
## Part E. Run it in Google Colab (optional; good as a backup demo)

Colab runs the **command-line/Python demo** (not the web dashboard).
1. Go to colab.research.google.com > **File > Upload notebook** > choose `CityPulse_Colab.ipynb` (or open it from your GitHub repo via the GitHub tab).
2. In the first code cell replace `YOUR-USERNAME` with your GitHub username. The repo must be **public**.
3. **Runtime > Run all.** You should see: clone, tests (23/23), the persona reports and table, a heatmap picture, and the learning demo.
> `fatal: repository ... not found`: the username is wrong or the repo is private.
> `No module named citypulse`: the `%cd citypulse` cell did not run - run cells in order from the top.
> Colab's session resets when idle; just run all again.

---
## Part F. Optional upgrades (only after Part C passes)

**F1. LLM mode - Claude chooses the tools** (this is the most "agentic" demo moment)
1. Create an account at console.anthropic.com and an API key (billing/credits may be required - check current pricing yourself).
2. Set the key in the terminal (Windows PowerShell: `$env:ANTHROPIC_API_KEY="paste-key"`; Mac/Linux: `export ANTHROPIC_API_KEY="paste-key"`).
3. Run `python run_demo.py --llm --persona office` - it prints the list of tools the model called, in order, then its weekly report. In the web app the "LLM agent mode" box becomes usable after you restart the server.
> `LLM mode needs ... ANTHROPIC_API_KEY`: the variable is not set in **this** terminal window (it is per-window).
> `401` / authentication error: wrong or revoked key. `404 model not found`: set `CITYPULSE_MODEL` to a model available to your account. `429`/credit errors: out of quota - use the normal mode; it needs no key.
> This path was tested only with a stand-in model, not the real API, so test it before the demo and keep the normal mode as your default.

**F2. Real Google Calendar insertion** (skip unless you have spare hours)
`pip install google-api-python-client google-auth-oauthlib`; Google Cloud Console > new project > enable "Google Calendar API" > OAuth consent screen (External; add your own email as a test user) > Credentials > OAuth client ID > Desktop app > download JSON > save as `credentials.json` in the project folder. Then in Python: `from citypulse.google_calendar import add_events; add_events(slots)`. A browser login opens the first time. Never commit `credentials.json` or `token.json`. This path is untested - the `.ics` download already satisfies "adds to the calendar".

**F3. Make the data real:** replace sample entries in `data/meetups.json` with real verified clubs; proof-read translations.

**F4. Use CityPulse for your own week:** copy a template in `citypulse/personas.py` (e.g. `_office_weekday`), change the hours/places/modes to match your real routine, register it in `TEMPLATES` and `PERSONAS`, restart. Example of one block: `(1.25, dict(kind="commute", place="Hostel -> Lab", mode="walk", outdoor=1.0, active=True, path_alt=True))` = a 75-minute walking commute that has a greener path alternative. Blocks are laid back-to-back starting at 06:00, so durations must add up to a full day.

---
## Part G. Demo day playbook

**G1. Night-before checklist**
- [ ] `python -m pytest -q` shows 23 passed on the demo laptop.
- [ ] `python -m uvicorn main:app` starts; dashboard works for all 3 personas and all 3 languages.
- [ ] Generated plans for Bengaluru **and** Delhi once (the contrast is a great story: indoor workouts appear when air is poor).
- [ ] Screen-record a 2-minute backup video of the full demo.
- [ ] Repo is public, README renders, commit history has multiple commits from different people.
- [ ] You decided what to say about live data: if venue wifi is bad, the app falls back to synthetic data **and says so** - say that deliberately: "built to degrade gracefully".
- [ ] Laptop charged, charger packed, browser zoom 100-125%.

**G2. 4-minute demo script**
1. (30 s) *Problem.* "Urban Indians' weekly exposure to heat, UV and PM2.5 is invisible and nobody plans around it."
2. (30 s) *Idea.* Show the loop diagram: Observe-Plan-Act-Learn; "it acts, not just reports".
3. (60 s) *Live demo.* Pick **Meera**, Bengaluru, press Generate plan. Point at: score tile; heatmap (dark commute blocks); swap row "18:30 -> 20:00 via a park, saves ~30%"; workout slots; meetup suggestion for a lonely week.
4. (30 s) *Act.* Download the `.ics` and open it: "the slots are in her calendar."
5. (45 s) *Learn.* Press **Skip** on the early slots, Generate plan again: "she keeps skipping 6 am, so the agent moves workouts to the evening."
6. (20 s) *Language + safety.* Switch to Kannada/Hindi and regenerate. Type "I feel hopeless" in chat: the agent stops advising and shows Tele-MANAS 14416.
7. (25 s) *Impact + honesty.* Show the metric: "commute PM2.5 down ~10-14% in simulation; whole-week change is smaller because most hours are indoors; we report both." Close with the roadmap: gig workers, station data, ward dashboards.

**G3. Slide outline (7 slides)**: (1) Title + team; (2) Problem + why it matters for future cities; (3) Solution: the 4-stage agent + features; (4) Architecture diagram + data sources; (5) Live demo / screenshots; (6) Results table + honest limits; (7) Impact, scalability, roadmap, team roles. Take the table straight from `output/results.md`.

**G4. How to talk about the numbers (important)**
- Say "in simulation on synthetic/modelled data". Never say "measured" or "proven to improve health".
- Both columns matter: commute PM2.5 reduction (~10-14%) and whole-week reduction (~1.5-4%). Adding outdoor workouts increases PM2.5 intake slightly in cleaner cities; the benefit of movement is real but not in this metric. A judge who spots this will respect you more if you said it first.

**G5. Likely judge questions** - see `VIVA_QA.md` (30+ questions with answers).

---
## Part H. Troubleshooting table

| Symptom | Likely cause | Fix |
|---|---|---|
| `python` not recognized | Python not on PATH | Reinstall, tick "Add to PATH"; or use `py` (Windows) / `python3` (Mac) |
| `No module named fastapi` / `uvicorn` | venv not active or install failed | Activate venv (C1), `pip install -r requirements.txt` |
| `ModuleNotFoundError: citypulse` | Wrong folder | `cd` to the folder containing `main.py` |
| `TypeError: unsupported operand type(s) for |` | Python older than 3.10 | Install Python 3.10+ and recreate the venv |
| `Address already in use` | Port 8000 busy | `--port 8001` |
| Dashboard blank / buttons dead | Server not started from project folder, or JS error | Restart from project folder; F12 > Console |
| `Data: synthetic (Live data unavailable (...))` | No internet / API blocked | Normal fallback. Check wifi/VPN; demo still valid; say so |
| Everything shows "no workouts" | Edited a persona so no `free` blocks exist | Workouts need `kind="free"` blocks |
| Hindi/Kannada garbled on Windows | Console encoding | `$env:PYTHONUTF8=1`; use Windows Terminal/VS Code |
| `git push` rejected / not found / fetch first | See Step D4 notes | `git pull origin main --rebase`, check `git remote -v` |
| Secret committed by mistake | - | Revoke the key at once, then remove from history |
| LLM mode errors | Key not set in this terminal, wrong model, no credit | See F1; use normal mode as default |
| A test fails after you change a number in `config.py` | Tests assert behaviours that depend on assumptions | Read the failing assertion; update the test only if your new assumption is intended |
| Anything else | - | Copy the **full** error text and ask Claude: "this error came when I ran <command>" |

---
## After the hackathon
CityPulse is a prototype you can keep extending: real station data (OpenAQ/CPCB), a gig-worker persona, a Telegram bot over `service.py`, and real calendar/location inputs with consent. Everything in the code is built so each of those is one new module, not a rewrite.
