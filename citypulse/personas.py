"""OBSERVE (part 2): the user's week.

The proposal says the week is *simulated for the demo* - three personas. Each persona is a
weekday template + a weekend template, expanded into explicit time Segments for 7 days.

A Segment is one block of time: where, doing what, how (mode), how outdoors, how flexible.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta


@dataclass
class Segment:
    day: int                 # 0..6 (offset from start_date)
    start: float             # hour of day, e.g. 8.5 = 08:30
    end: float
    kind: str                # home | commute | class | work | break | free | social | workout
    place: str
    mode: str = "indoor"     # key of config.MODE_FACTOR
    outdoor: float = 0.0     # 0..1 share of the block spent outdoors
    flex: float = 0.0        # +/- hours this block could be shifted (flexible work hours)
    active: bool = False     # counts as movement (walking/cycling/exercise)
    path_alt: bool = False   # a greener / side-street alternative exists for this trip
    social: bool = False     # counts as social contact
    pm_scale: float = 1.0    # <1 after a cleaner path is applied
    note: str = ""

    @property
    def hours(self) -> float:
        return self.end - self.start

    def copy(self, **kw) -> "Segment":
        return replace(self, **kw)


PERSONAS = {
    "student": {
        "name": "Aarav", "title": "College student (hostel + walking commute)",
        "interests": ["running", "football", "music", "board_games"],
    },
    "office": {
        "name": "Meera", "title": "IT office commuter (two-wheeler, long commute)",
        "interests": ["yoga", "walking", "books", "cycling"],
    },
    "metro": {
        "name": "Rohan", "title": "Metro commuter (hybrid desk job)",
        "interests": ["cycling", "photography", "board_games", "walking"],
    },
}


def _seq(day: int, start: float, items: list) -> list:
    """Lay blocks back-to-back from `start`. items = [(duration_hours, {Segment kwargs}), ...]"""
    out, t = [], start
    for dur, kw in items:
        out.append(Segment(day=day, start=t, end=round(t + dur, 4), **kw))
        t = round(t + dur, 4)
    return out


# ---------------------------- templates (weekday / weekend) -----------------------------
def _student_weekday(d):
    return _seq(d, 6.0, [
        (1.0, dict(kind="free", place="Hostel")),
        (1.25, dict(kind="home", place="Hostel")),
        (0.5, dict(kind="commute", place="Hostel -> Campus", mode="walk", outdoor=1.0, active=True, path_alt=True)),
        (4.5, dict(kind="class", place="Lecture hall")),
        (0.75, dict(kind="break", place="Mess (walk)", mode="walk", outdoor=0.3, active=True)),
        (3.0, dict(kind="class", place="Lecture hall / lab")),
        (0.5, dict(kind="commute", place="Campus -> Hostel", mode="walk", outdoor=1.0, active=True, path_alt=True)),
        (2.5, dict(kind="free", place="Hostel")),
        (1.0, dict(kind="social", place="Mess dinner with friends", social=True)),
        (2.0, dict(kind="home", place="Hostel")),
    ])


def _student_weekend(d):
    return _seq(d, 6.0, [
        (2.0, dict(kind="free", place="Hostel")),
        (3.0, dict(kind="home", place="Hostel")),
        (3.0, dict(kind="free", place="Hostel")),
        (2.0, dict(kind="social", place="Hangout with friends", social=True)),
        (3.0, dict(kind="free", place="Hostel")),
        (4.0, dict(kind="home", place="Hostel")),
    ])


def _office_weekday(d):
    return _seq(d, 6.0, [
        (1.0, dict(kind="free", place="Home")),
        (1.5, dict(kind="home", place="Home")),
        (1.25, dict(kind="commute", place="Home -> Office", mode="two_wheeler", outdoor=1.0, flex=1.0, path_alt=True)),
        (3.75, dict(kind="work", place="Office desk")),
        (0.75, dict(kind="break", place="Office lunch")),
        (4.25, dict(kind="work", place="Office desk")),
        (1.5, dict(kind="commute", place="Office -> Home", mode="two_wheeler", outdoor=1.0, flex=1.5, path_alt=True)),
        (2.0, dict(kind="free", place="Home")),
        (1.0, dict(kind="home", place="Home")),
    ])


def _office_weekend(d):
    return _seq(d, 6.0, [
        (1.5, dict(kind="free", place="Home")),
        (2.5, dict(kind="home", place="Home")),
        (1.0, dict(kind="commute", place="Errands (market)", mode="two_wheeler", outdoor=1.0, flex=2.0, path_alt=True)),
        (2.0, dict(kind="free", place="Home")),
        (7.0, dict(kind="home", place="Home (TV / phone)")),
        (3.0, dict(kind="free", place="Home")),
    ])


def _metro_weekday(d):
    return _seq(d, 6.0, [
        (1.5, dict(kind="free", place="Home")),
        (1.5, dict(kind="home", place="Home")),
        (1.25, dict(kind="commute", place="Home -> Office (walk+metro)", mode="metro", outdoor=0.3, flex=0.5, path_alt=True)),
        (4.0, dict(kind="work", place="Office desk")),
        (0.75, dict(kind="break", place="Lunch")),
        (3.5, dict(kind="work", place="Office desk")),
        (1.25, dict(kind="commute", place="Office -> Home (metro+walk)", mode="metro", outdoor=0.3, flex=1.0, path_alt=True)),
        (2.5, dict(kind="free", place="Home")),
        (0.5, dict(kind="social", place="Call with family", social=True)),
        (0.75, dict(kind="home", place="Home")),
    ])


def _metro_weekend(d):
    return _seq(d, 6.0, [
        (2.0, dict(kind="free", place="Home")),
        (2.0, dict(kind="home", place="Home")),
        (3.0, dict(kind="social", place="Lunch with friends", mode="auto", outdoor=0.4, social=True)),
        (3.0, dict(kind="free", place="Home")),
        (7.0, dict(kind="home", place="Home")),
    ])


TEMPLATES = {
    "student": (_student_weekday, _student_weekend),
    "office": (_office_weekday, _office_weekend),
    "metro": (_metro_weekday, _metro_weekend),
}


def build_week(persona_key: str, start_date: date) -> list:
    """Expand the persona's templates into 7 days of Segments starting at start_date."""
    if persona_key not in TEMPLATES:
        raise KeyError(f"Unknown persona '{persona_key}'. Choose from {list(TEMPLATES)}")
    weekday_fn, weekend_fn = TEMPLATES[persona_key]
    week = []
    for d in range(7):
        wd = (start_date + timedelta(days=d)).weekday()   # 0=Mon .. 6=Sun
        week.extend(weekend_fn(d) if wd >= 5 else weekday_fn(d))
    return week


def social_hours(week: list) -> float:
    return sum(s.hours for s in week if s.social)
