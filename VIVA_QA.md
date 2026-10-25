# Viva / Judge Q&A for CityPulse (answer in your own words - these are the facts)

## The idea
1. **What is CityPulse?** An agent that observes a person's week and the air/heat/UV they move through, plans changes, acts (calendar slots, route/time swaps, meetups) and learns from what they accept or ignore.
2. **Why is it "agentic" and not a dashboard?** It runs an Observe-Plan-Act-Learn loop, calls tools, produces actions, and changes its plan from feedback.
3. **Where is the AI?** Agentic planning with tools; online preference learning (`memory.py`); optional LLM tool-calling mode where Claude chooses the tools and writes the report. Numbers always come from tested tools, not the LLM.
4. **Who is it for?** College students and office commuters in Indian cities (first release); gig workers are the planned extension.
5. **How is it different from Google Fit / Apple Health / AQI apps?** They measure the body or show one number. CityPulse measures the environment you move through, combines it with your schedule, and acts on it.

## The model
6. **How is the score computed?** Per hour: hours x f x (0.5 PM2.5 + 0.3 heat + 0.2 UV), f = how much outdoor air reaches you (mode, outdoor share). Summed over the week, then 100x(1-exp(-raw/20)).
7. **Why those weights?** Modelling assumptions in `config.py`, chosen so PM2.5 dominates, then heat, then UV. They are not clinical; they are changeable and the score is a relative guide.
8. **Is it validated?** No clinical validation. Say so. Next step: calibrate against sensor data and expert input.
9. **Why 0.3 for indoor?** Outdoor pollution infiltrates indoors; 0.3 is a rough assumption. It is the reason whole-week reductions are smaller than commute reductions.
10. **What is "apparent temperature"?** Feels-like temperature from temperature + humidity (Steadman/BoM formula).

## Data
11. **Which data?** Open-Meteo forecast (temperature, humidity, UV) and Open-Meteo Air Quality (PM2.5, modelled); OpenStreetMap parks; a sample meetup dataset.
12. **Why not OpenAQ/CPCB?** Not integrated in the MVP; modelled PM2.5 covers any city. Station data is the next step.
13. **What if the internet fails?** Automatic fallback to deterministic synthetic data; the report states the data source.
14. **Is the user's week real?** Simulated personas for the demo (as in the proposal). Real product: calendar + saved places with consent.

## Results
15. **What did you measure?** In simulation: commute PM2.5 reduced ~10-14%; whole-week ~1.5-4% from swaps. Adding outdoor workouts adds a little PM2.5 intake in clean cities; the movement benefit is not in this metric.
16. **Why is the weekly number small?** Most hours are indoors, and the factor for indoors is fixed.
17. **Are the numbers real measurements?** No - synthetic/modelled inputs with stated assumptions.
18. **Is the 20% greener-path saving proven?** No, it is an assumption (one constant) to be calibrated.

## The agent
19. **What tools does the agent have?** get_week_overview, get_exposure_report, find_sedentary_gaps, propose_route_swaps, schedule_workouts, suggest_meetups, export_calendar, get_learning_stats.
20. **How does the LLM mode work?** Tools are described as JSON schemas; the model asks to call one; we run it and return the result; repeat until the final report.
21. **Why LLM + tools instead of just prompting?** The LLM can hallucinate numbers; tools guarantee them.
22. **Which framework?** Our own loop plus native tool calling; portable to LangGraph.
23. **How does it learn?** Per time-of-day bucket: rate=(ignored+1)/(accepted+ignored+2); cost multiplier=exp(2.5(rate-0.5)). Ignored times get costlier. Demo: `run_demo.py --learning`.
24. **Is that machine learning?** Simple online preference learning - honest and sufficient for a prototype.
25. **How are workout slots chosen?** Cheapest exposure hours inside free time, on different non-consecutive days, bonus inside long sitting blocks, indoor if PM2.5 > 90 or too hot, minimum 2, end by 21:00.
26. **How are routes improved?** Try shifting departure within the user's flexibility and/or a greener path; keep the best if it saves at least 5%.

## Safety and privacy
27. **Medical claims?** None. Guidance on exposure and habits only; medical questions get a refusal + "see a doctor".
28. **Distress?** The agent stops advising and shows Tele-MANAS 14416 (and 112 for emergencies). Keyword screen - a prototype, not a clinical tool.
29. **Privacy?** Stores only place names, times, scores, accepted/ignored flags. No GPS trail.

## Honest limitations and roadmap
30. **Limits?** Modelled PM2.5; approximate indoor exposure; simulated weeks; sample meetup data; keyword safety screen; template translations need native proofreading.
31. **Next steps?** OpenAQ/CPCB stations, gig-worker persona, Telegram bot over `service.py`, real calendar integration, ward-level dashboards for campuses/municipalities.
32. **Did AI write the code?** Drafted with Claude and then reviewed, run and tested by the team (see README); answer truthfully per the hackathon rules.
