from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from utils.config import DATA_DIR
from utils.symptom_cleaner import clean_symptoms


RAW_PATH = DATA_DIR / "raw_disease_db.json"
VERIFIED_PATH = DATA_DIR / "verified_disease_db.json"


@dataclass
class RawDiseaseEntry:
    disease: str
    symptoms: list[str]
    seen: int = 1
    source: str = "online"


@dataclass
class VerifiedDiseaseEntry:
    disease: str
    symptoms: list[str]


def _ensure_files() -> None:
    if not RAW_PATH.exists():
        RAW_PATH.write_text("[]", encoding="utf-8")
    if not VERIFIED_PATH.exists():
        VERIFIED_PATH.write_text("[]", encoding="utf-8")


def _clean_disease_name(name: str) -> str:
    t = re.sub(r"\s+", " ", (name or "").strip())
    t = re.sub(r"<.*?>", "", t)
    return t.strip()

_BAD_DISEASE_TERMS = {
    "medicine",
    "medicines",
    "vaccine",
    "vaccines",
    "care",
    "problems",
    "exam",
    "tests",
    "testing",
}


def _is_valid_disease_name(name: str) -> bool:
    n = _clean_disease_name(name).lower()
    if not n:
        return False
    # Reject obvious non-disease topics
    if any(term in n for term in _BAD_DISEASE_TERMS):
        return False
    # Reject question-like/long fragments
    if len(n) > 60:
        return False
    return True


def load_raw() -> list[RawDiseaseEntry]:
    _ensure_files()
    try:
        raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        out: list[RawDiseaseEntry] = []
        for it in raw:
            if not isinstance(it, dict):
                continue
            name = _clean_disease_name(str(it.get("disease", "")))
            sx = it.get("symptoms", [])
            if not name or not isinstance(sx, list):
                continue
            sx_clean = clean_symptoms(sx)
            if len(sx_clean) < 3:
                continue
            out.append(
                RawDiseaseEntry(
                    disease=name,
                    symptoms=sx_clean,
                    seen=int(it.get("seen", 1) or 1),
                    source=str(it.get("source", "online") or "online"),
                )
            )
        return out
    except Exception:
        return []


def save_raw(entries: list[RawDiseaseEntry]) -> None:
    _ensure_files()
    data = [
        {"disease": e.disease, "symptoms": clean_symptoms(e.symptoms)[:10], "seen": int(e.seen), "source": e.source}
        for e in sorted(entries, key=lambda x: x.disease.lower())
    ]
    RAW_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_verified() -> list[VerifiedDiseaseEntry]:
    _ensure_files()
    try:
        raw = json.loads(VERIFIED_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        out: list[VerifiedDiseaseEntry] = []
        for it in raw:
            if not isinstance(it, dict):
                continue
            name = _clean_disease_name(str(it.get("disease", "")))
            sx = it.get("symptoms", [])
            if not name or not isinstance(sx, list):
                continue
            sx_clean = clean_symptoms(sx)
            if len(sx_clean) < 4:
                continue
            out.append(VerifiedDiseaseEntry(disease=name, symptoms=sx_clean[:10]))
        return out
    except Exception:
        return []


def save_verified(entries: list[VerifiedDiseaseEntry]) -> None:
    _ensure_files()
    data = [{"disease": e.disease, "symptoms": clean_symptoms(e.symptoms)[:10]} for e in sorted(entries, key=lambda x: x.disease.lower())]
    VERIFIED_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def upsert_raw(disease: str, symptoms: list[str], *, source: str = "online") -> bool:
    """
    Store into RAW learning DB (cleaned). Increments seen count if already present.
    Strict rules:
    - NEVER store disease with < 3 symptoms
    """
    name = _clean_disease_name(disease)
    sx = clean_symptoms(symptoms)
    if not _is_valid_disease_name(name) or len(sx) < 3:
        return False

    entries = load_raw()
    key = name.lower()
    for e in entries:
        if e.disease.lower() == key:
            # merge symptoms
            merged = clean_symptoms([*e.symptoms, *sx])[:10]
            e.symptoms = merged
            e.seen = int(e.seen) + 1
            e.source = e.source or source
            save_raw(entries)
            return True

    entries.append(RawDiseaseEntry(disease=name, symptoms=sx[:10], seen=1, source=source))
    save_raw(entries)
    return True


def _confidence(user: set[str], disease_symptoms: list[str]) -> float:
    d = set(clean_symptoms(disease_symptoms))
    if not user or not d:
        return 0.0
    return len(user & d) / max(1, len(d))


def match_verified(user_symptoms: list[str]) -> list[dict[str, Any]]:
    """
    Match only VERIFIED diseases.
    confidence = overlap / total symptoms
    """
    u = set(clean_symptoms(user_symptoms))
    scored: list[dict[str, Any]] = []
    for e in load_verified():
        c = _confidence(u, e.symptoms)
        scored.append({"name": e.disease, "confidence": round(float(c), 4), "source": "verified"})
    scored.sort(key=lambda x: x["confidence"], reverse=True)
    return scored


def match_raw(user_symptoms: list[str]) -> list[dict[str, Any]]:
    """
    Match RAW (unverified) diseases to provide suggestions even when nothing is verified yet.
    confidence = overlap / total symptoms (same formula), but caller must label as unverified.
    """
    u = set(clean_symptoms(user_symptoms))
    scored: list[dict[str, Any]] = []
    for e in load_raw():
        c = _confidence(u, e.symptoms)
        scored.append({"name": e.disease, "confidence": round(float(c), 4), "source": "raw", "seen": int(e.seen)})
    scored.sort(key=lambda x: x["confidence"], reverse=True)
    return scored


def maybe_promote(
    disease: str,
    *,
    user_symptoms: Optional[list[str]] = None,
    strong_match_threshold: float = 0.6,
    min_seen: int = 2,
) -> bool:
    """
    Promotion RAW -> VERIFIED only if:
    - symptoms count >= 4 (after cleaning)
    - valid symptoms (clean_symptoms)
    - appears multiple times OR strong match with current user symptoms
    """
    name = _clean_disease_name(disease)
    if not _is_valid_disease_name(name):
        return False

    raw_entries = load_raw()
    target = None
    for e in raw_entries:
        if e.disease.lower() == name.lower():
            target = e
            break
    if target is None:
        return False

    sx = clean_symptoms(target.symptoms)
    if len(sx) < 4:
        return False

    strong = False
    if user_symptoms:
        u = set(clean_symptoms(user_symptoms))
        strong = _confidence(u, sx) >= strong_match_threshold

    if not (int(target.seen) >= min_seen or strong):
        return False

    verified = load_verified()
    for v in verified:
        if v.disease.lower() == name.lower():
            # merge (keep clean)
            v.symptoms = clean_symptoms([*v.symptoms, *sx])[:10]
            save_verified(verified)
            return True

    verified.append(VerifiedDiseaseEntry(disease=name, symptoms=sx[:10]))
    save_verified(verified)
    return True


def seed_verified_from_legacy_if_empty() -> int:
    """
    Optional stabilizer:
    If verified DB is empty, seed it from legacy data/disease_db.json entries
    marked as source 'database' (trusted).
    """
    if load_verified():
        return 0
    legacy = DATA_DIR / "disease_db.json"
    if not legacy.exists():
        return 0
    try:
        raw = json.loads(legacy.read_text(encoding="utf-8"))
    except Exception:
        return 0
    if not isinstance(raw, list):
        return 0

    added = 0
    verified: list[VerifiedDiseaseEntry] = []
    for it in raw:
        if not isinstance(it, dict):
            continue
        if str(it.get("source", "")).strip().lower() != "database":
            continue
        name = _clean_disease_name(str(it.get("disease", "")))
        sx = it.get("symptoms", [])
        if not name or not isinstance(sx, list):
            continue
        sx_phrases = [str(s).replace("_", " ") for s in sx]
        sx_clean = clean_symptoms(sx_phrases)
        if len(sx_clean) < 4:
            continue
        verified.append(VerifiedDiseaseEntry(disease=name, symptoms=sx_clean[:10]))
        added += 1

    if added:
        save_verified(verified)
    return added

