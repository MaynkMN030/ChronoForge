"""All tunable numbers live here, so you can explain (and change) every assumption in one place.

IMPORTANT for the viva: these weights are *modelling assumptions* for a relative score.
They are NOT clinical measurements. The score is a guide, not a diagnosis.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MEMORY_DIR = DATA_DIR / "memory"
OUTPUT_DIR = ROOT / "output"

# ----------------------------------------------------------------------------
# Cities (first release supports a few; add yours by copying one block)
# pm_base / t_mean / t_amp / rh / uv_peak are used ONLY for the offline synthetic
# fallback when the live Open-Meteo API cannot be reached.
# ----------------------------------------------------------------------------
CITIES = {
    "bengaluru": {
        "name": "Bengaluru", "lat": 12.9716, "lon": 77.5946,
        "pm_base": 32, "t_mean": 24, "t_amp": 4.5, "rh": 65, "uv_peak": 9,
        "parks": ["Cubbon Park", "Lalbagh Botanical Garden"],
    },
    "delhi": {
        "name": "Delhi", "lat": 28.6139, "lon": 77.2090,
        "pm_base": 95, "t_mean": 29, "t_amp": 8, "rh": 50, "uv_peak": 8,
        "parks": ["Lodhi Garden", "Nehru Park"],
    },
    "mumbai": {
        "name": "Mumbai", "lat": 19.0760, "lon": 72.8777,
        "pm_base": 48, "t_mean": 29, "t_amp": 4, "rh": 75, "uv_peak": 10,
        "parks": ["Joggers Park Bandra", "Shivaji Park"],
    },
}
DEFAULT_CITY = "bengaluru"
TIMEZONE = "Asia/Kolkata"
UTC_OFFSET_MINUTES = 330  # IST = UTC+05:30

# ----------------------------------------------------------------------------
# Exposure model
# ----------------------------------------------------------------------------
# Relative "how much of the outdoor air/heat does this mode let you breathe/feel".
# walk = 1.0 is the reference. Running/cycling breathe more air per minute.
MODE_FACTOR = {
    "walk": 1.0,
    "run": 1.5,
    "bike": 1.2,
    "two_wheeler": 0.95,
    "auto": 0.9,       # open auto-rickshaw
    "bus": 0.6,
    "metro": 0.35,
    "car": 0.3,        # closed AC car
    "indoor": 0.3,
}
INDOOR_FACTOR = 0.3  # indoor air is not clean: outdoor PM leaks in (rough infiltration ratio)

# How the three components are combined into one hourly number
WEIGHTS = {"pm": 0.5, "heat": 0.3, "uv": 0.2}

PM_REF = 120.0          # PM2.5 (ug/m3) that counts as "1.0" (very bad) in the normalised scale
PM_CAP = 2.0            # cap so one extreme hour cannot dominate
HEAT_LOW, HEAT_HIGH = 30.0, 42.0   # apparent temperature (C): below LOW = 0, above HIGH = 1
UV_MAX = 11.0

# raw -> 0..100 : score = 100 * (1 - exp(-raw / SCORE_SCALE))
SCORE_SCALE = 20.0
SCORE_LABELS = [(33, "Low"), (66, "Moderate"), (100, "High")]

# ----------------------------------------------------------------------------
# Planner settings
# ----------------------------------------------------------------------------
WAKE_HOUR, SLEEP_HOUR = 6.0, 23.0
SEDENTARY_GAP_HOURS = 3.0       # a sedentary block this long is flagged
MIN_WORKOUTS = 2
DEFAULT_WORKOUTS = 3
WORKOUT_HOURS = 1.0
WORKOUT_LATEST_END = 21.0       # no workouts that finish after 21:00
GAP_SLOT_BONUS = 0.75           # a slot inside a long sitting block costs 25% less (it breaks up the sitting)
ROUTE_PM_REDUCTION = 0.20       # assumption: greener / side-street path lowers PM2.5 dose ~20%
MIN_SWAP_SAVING = 0.05          # only suggest a timing/path change if it saves >= 5%
INDOOR_WORKOUT_PM = 90.0        # if forecast PM2.5 is above this at a slot -> suggest an indoor workout
                                # (~ top of CPCB 'moderate' band; verify the exact band before quoting it)
INDOOR_WORKOUT_HEAT = 0.85      # or normalised heat above this

# Isolation: fewer than this many social hours in a week -> suggest clubs / meetups
SOCIAL_HOURS_THRESHOLD = 4.0

# Learning: how strongly a bucket's accept/ignore history changes the cost of a slot
LEARN_STRENGTH = 2.5

# Hours bucket names used by the learning memory
def hour_bucket(hour: float) -> str:
    h = int(hour)
    if h < 7:
        return "early"
    if h < 11:
        return "morning"
    if h < 16:
        return "afternoon"
    if h < 21:
        return "evening"
    return "night"
