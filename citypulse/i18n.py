"""MULTILINGUAL output (English, Hindi, Kannada) without needing any API key.

Template-based, so the demo works offline. If an LLM key is set, agent_llm.py can ALSO write a
free-form summary in any Indian language - this file is the guaranteed fallback.
Have a native speaker re-check the Hindi/Kannada strings before the final demo.
"""
from __future__ import annotations

LANGS = {"en": "English", "hi": "हिन्दी", "kn": "ಕನ್ನಡ"}

DAYS = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "hi": ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"],
    "kn": ["ಸೋಮವಾರ", "ಮಂಗಳವಾರ", "ಬುಧವಾರ", "ಗುರುವಾರ", "ಶುಕ್ರವಾರ", "ಶನಿವಾರ", "ಭಾನುವಾರ"],
}
LABELS = {
    "en": {"Low": "Low", "Moderate": "Moderate", "High": "High"},
    "hi": {"Low": "कम", "Moderate": "मध्यम", "High": "अधिक"},
    "kn": {"Low": "ಕಡಿಮೆ", "Moderate": "ಮಧ್ಯಮ", "High": "ಹೆಚ್ಚು"},
}
T = {
    "score": {
        "en": "Your weekly exposure score is {score}/100 ({label}).",
        "hi": "आपका साप्ताहिक एक्सपोज़र स्कोर {score}/100 है ({label})।",
        "kn": "ನಿಮ್ಮ ಸಾಪ್ತಾಹಿಕ ಎಕ್ಸ್‌ಪೋಸರ್ ಸ್ಕೋರ್ {score}/100 ({label}).",
    },
    "commute": {
        "en": "Applying the suggested timing/route changes can cut your commute PM2.5 exposure by about {pct}%.",
        "hi": "सुझाए गए समय/रास्ते के बदलाव अपनाने से आपके सफ़र में PM2.5 एक्सपोज़र लगभग {pct}% कम हो सकता है।",
        "kn": "ಸೂಚಿಸಲಾದ ಸಮಯ/ಮಾರ್ಗ ಬದಲಾವಣೆಗಳನ್ನು ಅನುಸರಿಸಿದರೆ ನಿಮ್ಮ ಪ್ರಯಾಣದ PM2.5 ಒಡ್ಡಿಕೆ ಸುಮಾರು {pct}% ಕಡಿಮೆಯಾಗಬಹುದು.",
    },
    "no_commute": {
        "en": "Your commute is already fairly low-exposure; no big timing or route change is needed.",
        "hi": "आपका सफ़र पहले से ही काफ़ी कम एक्सपोज़र वाला है; समय या रास्ते में बड़े बदलाव की ज़रूरत नहीं।",
        "kn": "ನಿಮ್ಮ ಪ್ರಯಾಣದ ಒಡ್ಡಿಕೆ ಈಗಾಗಲೇ ಕಡಿಮೆ ಇದೆ; ಸಮಯ ಅಥವಾ ಮಾರ್ಗದಲ್ಲಿ ದೊಡ್ಡ ಬದಲಾವಣೆ ಅಗತ್ಯವಿಲ್ಲ.",
    },
    "workouts": {
        "en": "{n} workout slots were added at the least-polluted, most comfortable times:",
        "hi": "{n} वर्कआउट स्लॉट सबसे कम प्रदूषित और आरामदायक समय पर जोड़े गए:",
        "kn": "{n} ವ್ಯಾಯಾಮ ಸ್ಲಾಟ್‌ಗಳನ್ನು ಅತಿ ಕಡಿಮೆ ಮಾಲಿನ್ಯ ಮತ್ತು ಆರಾಮದಾಯಕ ಸಮಯದಲ್ಲಿ ಸೇರಿಸಲಾಗಿದೆ:",
    },
    "indoor": {
        "en": "indoor, air is poor", "hi": "घर के अंदर, हवा ख़राब है", "kn": "ಒಳಾಂಗಣ, ಗಾಳಿ ಕೆಟ್ಟದಾಗಿದೆ",
    },
    "outdoor": {"en": "outdoor", "hi": "बाहर", "kn": "ಹೊರಾಂಗಣ"},
    "gaps": {
        "en": "{n} long sitting blocks (3h+) found; {m} now include a movement slot.",
        "hi": "{n} लंबे बैठे रहने के ब्लॉक (3 घंटे+) मिले; {m} में अब मूवमेंट स्लॉट है।",
        "kn": "{n} ದೀರ್ಘ ಕುಳಿತುಕೊಳ್ಳುವ ಅವಧಿಗಳು (3 ಗಂಟೆ+) ಕಂಡುಬಂದಿವೆ; {m} ರಲ್ಲಿ ಈಗ ಚಲನೆಯ ಸ್ಲಾಟ್ ಇದೆ.",
    },
    "meetup": {
        "en": "A quiet social week - consider: {names}.",
        "hi": "इस हफ़्ते सामाजिक मेलजोल कम रहा - ये आज़माएँ: {names}।",
        "kn": "ಈ ವಾರ ಸಾಮಾಜಿಕ ಸಂಪರ್ಕ ಕಡಿಮೆ - ಇವುಗಳನ್ನು ಪ್ರಯತ್ನಿಸಿ: {names}.",
    },
    "learned": {
        "en": "Learning: you often skipped {bucket} slots, so they are used less this week.",
        "hi": "सीख: आपने {bucket} वाले स्लॉट अक्सर छोड़े, इसलिए इस हफ़्ते उन्हें कम रखा गया है।",
        "kn": "ಕಲಿಕೆ: ನೀವು {bucket} ಸ್ಲಾಟ್‌ಗಳನ್ನು ಹೆಚ್ಚಾಗಿ ಬಿಟ್ಟಿದ್ದೀರಿ, ಆದ್ದರಿಂದ ಈ ವಾರ ಅವುಗಳನ್ನು ಕಡಿಮೆ ಬಳಸಲಾಗಿದೆ.",
    },
    "buckets": {
        "en": {"early": "early-morning", "morning": "morning", "afternoon": "afternoon", "evening": "evening", "night": "night"},
        "hi": {"early": "सुबह-सवेरे", "morning": "सुबह", "afternoon": "दोपहर", "evening": "शाम", "night": "रात"},
        "kn": {"early": "ಮುಂಜಾನೆ", "morning": "ಬೆಳಿಗ್ಗೆ", "afternoon": "ಮಧ್ಯಾಹ್ನ", "evening": "ಸಂಜೆ", "night": "ರಾತ್ರಿ"},
    },
    "disclaimer": {
        "en": "This is guidance on exposure and habits, not medical advice. Values come from modelled/open data.",
        "hi": "यह केवल एक्सपोज़र और आदतों पर मार्गदर्शन है, चिकित्सकीय सलाह नहीं। मान मॉडल/ओपन डेटा से आते हैं।",
        "kn": "ಇದು ಒಡ್ಡಿಕೆ ಮತ್ತು ಅಭ್ಯಾಸಗಳ ಮಾರ್ಗದರ್ಶನ ಮಾತ್ರ, ವೈದ್ಯಕೀಯ ಸಲಹೆ ಅಲ್ಲ. ಮೌಲ್ಯಗಳು ಮಾದರಿ/ಮುಕ್ತ ಡೇಟಾದಿಂದ ಬಂದಿವೆ.",
    },
}


def tr(key: str, lang: str, **kw) -> str:
    lang = lang if lang in LANGS else "en"
    s = T[key][lang]
    return s.format(**kw) if kw else s


def fmt_hour(h: float) -> str:
    hh, mm = int(h), int(round((h - int(h)) * 60))
    if mm == 60:
        hh, mm = hh + 1, 0
    return f"{hh:02d}:{mm:02d}"


def build_summary(report: dict, lang: str = "en") -> dict:
    """Make the plain-language weekly report from the numbers (no LLM needed)."""
    lang = lang if lang in LANGS else "en"
    m = report["metrics"]
    lines = [tr("score", lang, score=report["baseline"]["score"], label=LABELS[lang][report["baseline"]["label"]])]
    if report["swaps"]:
        lines.append(tr("commute", lang, pct=m["commute_pm_reduction_pct"]))
    else:
        lines.append(tr("no_commute", lang))
    lines.append(tr("gaps", lang, n=m["gaps_total"], m=m["gaps_filled"]))
    lines.append(tr("workouts", lang, n=len(report["workouts"])))
    for w in report["workouts"]:
        kind = tr("indoor" if w["type"] == "indoor" else "outdoor", lang)
        lines.append(f"  - {DAYS[lang][_weekday(report, w['day'])]} {fmt_hour(w['start'])}-{fmt_hour(w['end'])} ({kind})")
    if report["meetups"]["triggered"] and report["meetups"]["items"]:
        lines.append(tr("meetup", lang, names=", ".join(i["name"] for i in report["meetups"]["items"])))
    for n in report.get("learned", []):
        lines.append(tr("learned", lang, bucket=T["buckets"][lang][n["bucket"]]))
    lines.append(tr("disclaimer", lang))
    return {"lang": lang, "lines": lines, "text": "\n".join(lines)}


def _weekday(report: dict, day: int) -> int:
    from datetime import date
    return (date.fromisoformat(report["start_date"]).weekday() + day) % 7
