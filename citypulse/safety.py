"""SAFETY: CityPulse gives exposure and habit guidance only. No diagnosis, no treatment.

1. Distress detection  -> the agent STOPS advising and shows helpline details (Tele-MANAS 14416).
2. Medical questions   -> polite refusal + suggestion to see a doctor.
This is a simple keyword screen (good enough for a hackathon, not a clinical tool). Say so in the viva.
"""
from __future__ import annotations

import re

DISTRESS_PATTERNS = [
    r"suicid", r"kill myself", r"end my life", r"want to die", r"wanna die", r"self[- ]?harm",
    r"hurt myself", r"no reason to live", r"can'?t go on", r"hopeless", r"better off dead",
    "आत्महत्या", "मरना चाहता", "मरना चाहती", "जीना नहीं",
    "ಆತ್ಮಹತ್ಯೆ", "ಸಾಯಬೇಕು", "ಸಾಯಲು",
]
MEDICAL_PATTERNS = [
    r"diagnos", r"do i have (asthma|copd|cancer|a disease)", r"which (medicine|medication|tablet|drug)",
    r"prescri", r"\bdosage\b", r"treat(ment)? for", r"what medicine",
]

HELPLINE = {
    "en": "It sounds like you may be going through a very hard time. I am a wellness-planning tool and "
          "can't help with this, but you do not have to face it alone. Please talk to someone now. "
          "Tele-MANAS (India, free, 24x7): 14416. If you are in immediate danger, call 112.",
    "hi": "ऐसा लगता है कि आप बहुत मुश्किल समय से गुज़र रहे हैं। मैं केवल एक वेलनेस-प्लानिंग टूल हूँ और इसमें मदद नहीं कर सकता, "
          "लेकिन आप अकेले नहीं हैं। कृपया अभी किसी से बात करें। टेली-मानस (भारत, निःशुल्क, 24x7): 14416। "
          "तुरंत ख़तरा हो तो 112 पर कॉल करें।",
    "kn": "ನೀವು ತುಂಬಾ ಕಷ್ಟದ ಸಮಯದಲ್ಲಿದ್ದೀರಿ ಎಂದು ಅನಿಸುತ್ತದೆ. ನಾನು ಕೇವಲ ಆರೋಗ್ಯ-ಯೋಜನಾ ಸಾಧನ, ಇದರಲ್ಲಿ ಸಹಾಯ ಮಾಡಲು ಸಾಧ್ಯವಿಲ್ಲ, "
          "ಆದರೆ ನೀವು ಒಬ್ಬರೇ ಅಲ್ಲ. ದಯವಿಟ್ಟು ಈಗಲೇ ಯಾರೊಂದಿಗಾದರೂ ಮಾತನಾಡಿ. ಟೆಲಿ-ಮಾನಸ್ (ಭಾರತ, ಉಚಿತ, 24x7): 14416. "
          "ತಕ್ಷಣದ ಅಪಾಯವಿದ್ದರೆ 112 ಗೆ ಕರೆ ಮಾಡಿ.",
}
MEDICAL_REPLY = {
    "en": "I can only guide exposure and daily habits - I can't diagnose or advise on treatment. "
          "Please speak to a doctor for health concerns.",
    "hi": "मैं केवल एक्सपोज़र और दैनिक आदतों पर मार्गदर्शन दे सकता हूँ - निदान या इलाज की सलाह नहीं। "
          "स्वास्थ्य संबंधी चिंता के लिए कृपया डॉक्टर से मिलें।",
    "kn": "ನಾನು ಒಡ್ಡಿಕೆ ಮತ್ತು ದೈನಂದಿನ ಅಭ್ಯಾಸಗಳ ಬಗ್ಗೆ ಮಾತ್ರ ಮಾರ್ಗದರ್ಶನ ನೀಡಬಲ್ಲೆ - ರೋಗನಿರ್ಣಯ ಅಥವಾ ಚಿಕಿತ್ಸೆಯ ಸಲಹೆ ನೀಡಲಾರೆ. "
          "ಆರೋಗ್ಯ ಸಮಸ್ಯೆಗಳಿಗೆ ದಯವಿಟ್ಟು ವೈದ್ಯರನ್ನು ಭೇಟಿಯಾಗಿ.",
}


def classify(text: str) -> str:
    """Return 'distress', 'medical' or 'ok'. Distress always wins."""
    t = (text or "").lower()
    if any(re.search(p, t) for p in DISTRESS_PATTERNS):
        return "distress"
    if any(re.search(p, t) for p in MEDICAL_PATTERNS):
        return "medical"
    return "ok"


def reply_for(kind: str, lang: str = "en") -> str | None:
    lang = lang if lang in HELPLINE else "en"
    if kind == "distress":
        return HELPLINE[lang]
    if kind == "medical":
        return MEDICAL_REPLY[lang]
    return None
