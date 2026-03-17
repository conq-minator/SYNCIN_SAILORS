from __future__ import annotations

import re
from typing import Iterable


_GENERIC = {
    "condition",
    "issue",
    "problem",
    "disease",
    "disorder",
    "illness",
    "symptom",
    "symptoms",
}

_NON_SYMPTOM = {
    "hormone",
    "permanent",
    "permanent loss",
    "loss",
    "treatment",
    "diagnosis",
    "exam",
    "provider",
    "medicine",
    "surgery",
}

_BAD_START = ("what ", "why ", "how ", "when ", "who ", "can ", "should ")

# Online sources often return explanatory fragments; reject common ones.
_STOPWORDS = {
    "your",
    "your body",
    "your throat",
    "itself",
    "the kind",
    "a reflex",
    "a cold",
    "flu",
    "weeks",
    "week",
    "days",
    "day",
}


def _clean_text(s: str) -> str:
    t = re.sub(r"\s+", " ", (s or "").strip().lower())
    t = t.strip(" ,.;:()[]{}\"'")
    return t


def _is_bad(t: str) -> bool:
    if not t:
        return True
    if any(t.startswith(p) for p in _BAD_START):
        return True
    if t in _GENERIC or t in _NON_SYMPTOM:
        return True
    if t in _STOPWORDS:
        return True
    # reject time spans / numeric fragments
    if re.search(r"\d", t):
        return True
    # reject very long fragments (usually not symptoms)
    if len(t) > 40:
        return True
    # reject many-word sentences (keep 1-3 word symptoms)
    words = t.split()
    if len(words) > 4:
        return True
    # reject if it has too many non-letters
    if re.search(r"[<>/\\{}\\[\\]]", t):
        return True
    return False


def clean_symptoms(symptoms: Iterable[str]) -> list[str]:
    """
    Strict symptom filter:
    - remove generic/non-symptom phrases
    - keep short physical/measurable phrases
    - dedup preserving order
    """
    out: list[str] = []
    seen = set()
    for s in symptoms or []:
        t = _clean_text(str(s))
        if _is_bad(t):
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out

