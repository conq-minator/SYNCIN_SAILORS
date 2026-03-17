from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from typing import Iterable

from utils.config import DATA_DIR
from utils.hf_client import call_huggingface_api

SYMPTOM_LIST_PATH = DATA_DIR / "symptom_list.json"


def load_symptoms() -> dict[str, list[str]]:
    if SYMPTOM_LIST_PATH.exists():
        return json.loads(SYMPTOM_LIST_PATH.read_text(encoding="utf-8"))
    return {}


symptom_map: dict[str, list[str]] = load_symptoms()

NORMALIZE_MAP: dict[str, str] = {
    # Example user-provided mappings / common phrasing
    "eye pain": "eye_pain",
    "pain in eye": "eye_pain",
    "painful eye": "eye_pain",
    "bloodiness in eye": "eye_redness",
    "bloodshot eye": "eye_redness",
    "red eye": "eye_redness",
    "eye redness": "eye_redness",
    "dizzy": "dizziness",
}

_STOP_PREFIXES = (
    "i have ",
    "i've ",
    "i feel ",
    "feeling ",
    "having ",
    "have ",
    "with ",
    "and ",
)


def extract_symptom_phrases(text: str) -> list[str]:
    """
    Phrase-level extraction:
    - split by commas / 'and' / semicolons
    - keep short noun-like chunks (e.g. 'eye pain', 'bloodiness in eye')
    """
    t = re.sub(r"[\r\n\t]+", " ", (text or "").strip().lower())
    t = re.sub(r"\s+", " ", t)
    if not t:
        return []

    # Normalize separators
    t = re.sub(r"\b(and|also)\b", ",", t)
    parts = [p.strip(" .") for p in re.split(r"[,\;]+", t) if p.strip(" .")]

    cleaned: list[str] = []
    for p in parts:
        for pref in _STOP_PREFIXES:
            if p.startswith(pref):
                p = p[len(pref) :].strip()
        p = p.strip(" .")
        if not p:
            continue
        # Keep reasonably sized phrases (avoid entire paragraphs)
        if len(p) > 80:
            p = p[:80].strip()
        if p and p not in cleaned:
            cleaned.append(p)
    return cleaned


def normalize_phrase(phrase: str) -> str:
    p = re.sub(r"\s+", " ", (phrase or "").strip().lower())
    if not p:
        return ""
    if p in NORMALIZE_MAP:
        return NORMALIZE_MAP[p]

    # If phrase contains a known synonym, map to the symptom key.
    for symptom_key, synonyms in symptom_map.items():
        for s in synonyms:
            s2 = str(s).lower()
            if s2 and (p == s2 or s2 in p):
                return symptom_key

    # Default normalization for unknowns: underscore it (but don't discard)
    return re.sub(r"[^a-z0-9]+", "_", p).strip("_")


def extract_symptoms_full(text: str) -> dict[str, list[str]]:
    """
    Full symptom understanding output:
    - extracted_phrases: phrase-level chunks from text
    - normalized_symptoms: normalized list (known + unknown)
    - known_symptoms: subset that exist in symptom_map keys
    - unknown_symptoms: everything else (kept, not discarded)
    """
    print("Raw input:", text)
    phrases = extract_symptom_phrases(text)
    print("Extracted phrases:", phrases)

    normalized: list[str] = []
    for ph in phrases:
        n = normalize_phrase(ph)
        if n and n not in normalized:
            normalized.append(n)

    # Also run existing rule/fuzzy extractors to catch embedded synonyms
    known_extra = extract_symptoms_rule(text) + extract_symptoms_fuzzy(text)
    for k in known_extra:
        if k and k not in normalized:
            normalized.append(k)

    known = [s for s in normalized if s in symptom_map]
    unknown = [s for s in normalized if s not in symptom_map]

    print("Normalized symptoms:", normalized)
    print("Unknown symptoms:", unknown)
    return {
        "extracted_phrases": phrases,
        "normalized_symptoms": normalized,
        "known_symptoms": sorted(set(known)),
        "unknown_symptoms": sorted(set(unknown)),
    }

def extract_symptoms_rule(text: str) -> list:
    """Mode 1: Rule-based primary parser"""
    text = text.lower()
    extracted = []
    
    for symptom_key, synonyms in symptom_map.items():
        for synonym in synonyms:
            # Word boundary matching
            if re.search(r'\b' + re.escape(synonym) + r'\b', text):
                extracted.append(symptom_key)
                break 
                
    return extracted

def extract_symptoms_ai(text: str) -> list:
    """
    Mode 2: Optional AI fallback.

    Uses Hugging Face Inference API *only if* HF_API_KEY is present.
    Never raises; returns [] on any error.
    """
    try:
        # Ask the model to extract symptom phrases; we then map them back to known symptoms.
        # Kept lightweight: no extra deps, and safe on failures/timeouts.
        prompt = (
            "Extract symptoms from this sentence. Return as a Python list of strings.\n\n"
            f"Sentence: {text}\n\n"
            "Answer:"
        )
        generated = call_huggingface_api(prompt, model_env="HF_SYMPTOM_MODEL")
        if not generated:
            return []

        # Parse list-ish output without eval: pull quoted items, else split commas.
        items = re.findall(r"['\"]([^'\"]{2,80})['\"]", generated)
        if not items:
            items = [c.strip() for c in re.split(r"[,\n;]+", generated) if c.strip()]
        candidates = [c.strip().lower() for c in items if c.strip()]
        return _map_candidate_phrases_to_symptoms(candidates)
    except Exception as e:
        return []

def extract_symptoms(text: str) -> list:
    """Combined strategy: First Rule-based, then AI Fallback if needed."""
    symptoms = extract_symptoms_rule(text)
    if symptoms:
        return sorted(set(symptoms))

    # Soft fallback (no network): fuzzy match against synonyms
    fuzzy = extract_symptoms_fuzzy(text)
    if fuzzy:
        return sorted(set(fuzzy))

    # Optional AI fallback (requires key)
    ai = extract_symptoms_ai(text)
    return sorted(set(ai))


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _iter_all_synonyms() -> Iterable[tuple[str, str]]:
    for symptom_key, synonyms in symptom_map.items():
        for s in synonyms:
            yield symptom_key, s.lower()


def extract_symptoms_fuzzy(text: str, *, cutoff: float = 0.86) -> list[str]:
    """
    Optional improvement: fuzzy synonym matching for slightly misspelled / paraphrased inputs.
    Kept conservative to avoid false positives.
    """
    t = re.sub(r"\s+", " ", text.lower()).strip()
    if not t:
        return []

    extracted: set[str] = set()
    words = re.findall(r"[a-z][a-z']+", t)
    phrases = set(words)
    # Add short 2-grams for things like "sore throat"
    for i in range(len(words) - 1):
        phrases.add(f"{words[i]} {words[i+1]}")

    for symptom_key, synonym in _iter_all_synonyms():
        if synonym in t:
            extracted.add(symptom_key)
            continue
        # Fuzzy against phrases, not whole text
        best = 0.0
        for p in phrases:
            if abs(len(p) - len(synonym)) > 6:
                continue
            best = max(best, _ratio(p, synonym))
            if best >= cutoff:
                extracted.add(symptom_key)
                break

    return sorted(extracted)


def _map_candidate_phrases_to_symptoms(candidates: list[str]) -> list[str]:
    """
    Map free-form symptom phrases to known symptom keys (using exact + fuzzy synonym match).
    """
    if not candidates:
        return []

    extracted: set[str] = set()
    for cand in candidates:
        cand = re.sub(r"\s+", " ", cand).strip()
        if not cand:
            continue

        # Exact key match
        key_like = cand.replace(" ", "_")
        if key_like in symptom_map:
            extracted.add(key_like)
            continue

        # Exact synonym substring match
        for symptom_key, synonyms in symptom_map.items():
            if any(s.lower() == cand for s in synonyms):
                extracted.add(symptom_key)
                break

    if extracted:
        return sorted(extracted)

    # If exact mapping fails, do a conservative fuzzy pass
    # (use the same helper as fuzzy mode by treating candidate text as the input)
    fused = " ".join(candidates)
    return extract_symptoms_fuzzy(fused, cutoff=0.88)
