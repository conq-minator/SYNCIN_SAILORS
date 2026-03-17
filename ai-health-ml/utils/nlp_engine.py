from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Iterable

import spacy

from utils.config import DATA_DIR
from utils.symptom_db import find_symptom, load_symptom_db


_MODEL_NAME = "en_core_web_sm"


# Normalization layer (extend as needed)
NORMALIZE_MAP: dict[str, str] = {
    "bloodiness in eye": "eye_redness",
    "bloodshot eye": "eye_redness",
    "red eye": "eye_redness",
    "eye redness": "eye_redness",
    "eye pain": "eye_pain",
    "pain in eye": "eye_pain",
    "painful eye": "eye_pain",
    "dizzy": "dizziness",
}


_PRONOUNS = {"i", "you", "he", "she", "it", "we", "they", "me", "my", "your", "our", "their"}
_BAD_START = {"i", "i'm", "im", "ive", "i've", "having", "have", "feel", "feeling", "with"}
_PREP_KEEP = {"in", "on", "behind", "around", "near", "under", "over", "inside", "outside"}


@lru_cache(maxsize=1)
def _known_symptom_keys() -> set[str]:
    """
    Keys from data/symptom_list.json (the project's symptom dictionary).
    Used to compute unknown_symptoms.
    """
    path = DATA_DIR / "symptom_list.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {str(k).strip() for k in raw.keys() if str(k).strip()}
    except Exception:
        pass
    return set()


@lru_cache(maxsize=1)
def _nlp():
    """
    spaCy pipeline loader.
    Falls back safely so the app doesn't crash if the model isn't present.
    """
    try:
        return spacy.load(_MODEL_NAME)
    except Exception:
        # Fallback: still tokenizes. No parser => no noun_chunks, so we'll rely on rule splitting.
        return spacy.blank("en")


def _dedup_keep_order(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    for x in items:
        x2 = (x or "").strip()
        if not x2:
            continue
        if x2 not in out:
            out.append(x2)
    return out


def _clean_phrase(s: str) -> str:
    t = re.sub(r"\s+", " ", (s or "").strip())
    t = t.strip(" ,.;:()[]{}\"'")
    return t


def _underscore(s: str) -> str:
    t = re.sub(r"\s+", " ", (s or "").strip().lower())
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    return t


def normalize_phrase(phrase: str) -> str:
    """
    Normalize a raw phrase into a symptom key.
    - Apply explicit mappings
    - Else underscore the phrase (do NOT discard)
    """
    p = _clean_phrase(phrase).lower()
    if not p:
        return ""
    if p in NORMALIZE_MAP:
        return NORMALIZE_MAP[p]

    # Use learned symptom aliases from symptom_db (continuous learning normalization)
    try:
        e = find_symptom(p, load_symptom_db())
        if e is not None and e.name:
            return _underscore(e.name)
    except Exception:
        pass
    return _underscore(p)


def extract_raw_phrases(text: str) -> list[str]:
    """
    "Real NLP" phrase extraction:
    - Prefer spaCy noun chunks
    - Add prepositional symptom phrases (e.g., "bloodiness in eye")
    - Fall back to comma/and splitting so unknown phrases are never lost
    """
    t = (text or "").strip()
    if not t:
        return []

    nlp = _nlp()
    doc = nlp(t)

    phrases: list[str] = []

    # 1) noun chunks when parser is available
    try:
        for chunk in doc.noun_chunks:
            s = _clean_phrase(chunk.text)
            s_l = s.lower()
            if not s or s_l in _PRONOUNS:
                continue
            # skip leading "I have ..." style prefixes if they sneak in
            w0 = s_l.split(" ", 1)[0]
            if w0 in _BAD_START:
                s = s.split(" ", 1)[1] if " " in s else ""
            s = _clean_phrase(s)
            if s and len(s) <= 60:
                phrases.append(s)
    except Exception:
        # blank("en") has no noun_chunks
        pass

    # 2) add prepositional phrases like "<noun> in <noun>"
    for tok in doc:
        try:
            if tok.dep_ != "pobj":
                continue
            if tok.head is None:
                continue
            if tok.head.lower_ not in _PREP_KEEP:
                continue
            head = tok.head
            if head.head is None:
                continue
            left = head.head
            if left.pos_ not in {"NOUN", "PROPN", "ADJ"}:
                continue
            span = doc[left.left_edge.i : tok.i + 1]
            s = _clean_phrase(span.text)
            if s and len(s) <= 60:
                phrases.append(s)
        except Exception:
            continue

    # 3) fallback split (never lose user input)
    # Treat common connectors as separators (including "with").
    parts = re.split(r"[,\n;]+|\band\b|\balso\b|\bwith\b", t, flags=re.IGNORECASE)
    for p in parts:
        s = _clean_phrase(p)
        if not s:
            continue
        # remove common leading filler
        s_l = s.lower()
        for pref in ("i have ", "i've ", "im ", "i'm ", "i feel ", "feeling ", "having ", "have ", "with "):
            if s_l.startswith(pref):
                s = _clean_phrase(s[len(pref) :])
                break
        if s and len(s) <= 60:
            phrases.append(s)

    phrases = _dedup_keep_order(phrases)

    # Split combined connector phrases like "X with Y" into ["X", "Y"].
    split_out: list[str] = []
    for p in phrases:
        if re.search(r"\bwith\b", p, flags=re.IGNORECASE):
            bits = [b.strip() for b in re.split(r"\bwith\b", p, flags=re.IGNORECASE) if b.strip()]
            split_out.extend(bits)
        else:
            split_out.append(p)
    phrases = _dedup_keep_order(split_out)

    # Prune: if a short phrase is fully contained in a longer phrase,
    # prefer the longer one (prevents "eye" + "bloodiness" duplicates).
    long_phrases = [p for p in phrases if " " in p]
    long_l = [p.lower() for p in long_phrases]
    pruned: list[str] = []
    for p in phrases:
        p_l = p.lower()
        if " " not in p and any(re.search(rf"\b{re.escape(p_l)}\b", lp) for lp in long_l):
            continue
        pruned.append(p)

    return pruned


def extract_symptoms(text: str) -> dict[str, list[str]]:
    """
    Required output format:
    {
      "raw_phrases": [...],
      "normalized_symptoms": [...],
      "unknown_symptoms": [...]
    }
    """
    print("Input text:", text)
    raw = extract_raw_phrases(text)
    print("Extracted phrases:", raw)

    normalized = _dedup_keep_order([normalize_phrase(p) for p in raw if normalize_phrase(p)])
    print("Normalized symptoms:", normalized)

    known = _known_symptom_keys()
    unknown = [s for s in normalized if s not in known]
    print("Unknown symptoms:", unknown)

    return {"raw_phrases": raw, "normalized_symptoms": normalized, "unknown_symptoms": unknown}

