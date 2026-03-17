from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable
import html
import re

from utils.config import DATA_DIR
from utils.symptom_db import expand_symptom_tokens


DISEASE_DB_PATH = DATA_DIR / "disease_db.json"


@dataclass(frozen=True)
class DiseaseEntry:
    disease: str
    symptoms: list[str]
    source: str = "database"
    verified: bool = True


def _clean_disease_name(name: str) -> str:
    raw = html.unescape(str(name or "")).strip()
    raw = re.sub(r"<.*?>", "", raw)
    return re.sub(r"\s+", " ", raw).strip()


def _normalize_symptoms(symptoms: list[str]) -> list[str]:
    out: list[str] = []
    for s in symptoms or []:
        t = str(s or "").strip().lower().replace(" ", "_")
        if not t:
            continue
        # Drop obviously-invalid "sentence fragments" learned from web summaries.
        if len(t) > 40:
            continue
        if t.count("_") > 6:
            continue
        if t not in out:
            out.append(t)
    return out


def load_disease_db() -> list[DiseaseEntry]:
    if not DISEASE_DB_PATH.exists():
        return []
    try:
        raw = json.loads(DISEASE_DB_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        out: list[DiseaseEntry] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = _clean_disease_name(item.get("disease", ""))
            symptoms = item.get("symptoms", [])
            if not name or not isinstance(symptoms, list):
                continue
            sx = _normalize_symptoms(symptoms)
            if not sx:
                continue
            src = str(item.get("source", "database") or "database").strip()
            verified = bool(item.get("verified", True if src.strip().lower() == "database" else False))
            out.append(DiseaseEntry(disease=name, symptoms=sx, source=src, verified=verified))
        return out
    except Exception:
        return []


def calculate_match(user_symptoms: list[str], disease_symptoms: list[str]) -> float:
    """
    Score = overlap / total disease symptoms (as requested).
    """
    # Expand user symptoms using learned "related" symptom links (symptom_db.json).
    try:
        u = expand_symptom_tokens([s for s in user_symptoms if s])
    except Exception:
        u = {s for s in user_symptoms if s}
    d = {s for s in disease_symptoms if s}
    if not u or not d:
        return 0.0
    overlap = len(u & d)
    return overlap / max(1, len(d))


def match_diseases(user_symptoms: list[str]) -> list[dict[str, Any]]:
    """
    Returns disease matches from JSON DB with simple overlap scoring.
    """
    entries = load_disease_db()
    scored: list[dict[str, Any]] = []
    for e in entries:
        score = calculate_match(user_symptoms, e.symptoms)
        if score > 0:
            scored.append(
                {
                    "name": e.disease,
                    "confidence": round(float(score), 4),
                    "source": "disease_db.json",
                    "db_source": e.source,
                }
            )
    scored.sort(key=lambda x: x["confidence"], reverse=True)
    return scored


def match_diseases_by_source(user_symptoms: list[str], *, sources: set[str]) -> list[dict[str, Any]]:
    """
    Match only diseases whose `source` field is in `sources` (e.g. {"online"}).
    Confidence is always overlap(user_symptoms, disease_symptoms) / total disease symptoms.
    """
    sources_l = {s.strip().lower() for s in sources if s}
    entries = load_disease_db()
    scored: list[dict[str, Any]] = []
    for e in entries:
        if e.source.strip().lower() not in sources_l:
            continue
        score = calculate_match(user_symptoms, e.symptoms)
        if score > 0:
            scored.append(
                {
                    "name": e.disease,
                    "confidence": round(float(score), 4),
                    "source": "disease_db.json",
                    "db_source": e.source,
                }
            )
    scored.sort(key=lambda x: x["confidence"], reverse=True)
    return scored


def upsert_diseases(diseases: Iterable[dict[str, Any]]) -> int:
    """
    Add/merge diseases into data/disease_db.json (non-binary format).
    Dedup by disease name (case-insensitive). Returns number of new entries added.
    """
    existing = load_disease_db()
    by_name = {e.disease.strip().lower(): e for e in existing}
    added = 0

    for d in diseases:
        if not isinstance(d, dict):
            continue
        name = _clean_disease_name(d.get("disease") or d.get("name") or "")
        sx = d.get("symptoms", [])
        if not name or not isinstance(sx, list):
            continue
        sx_clean = _normalize_symptoms(sx)
        if len(sx_clean) < 3:
            continue
        if len(sx_clean) > 10:
            sx_clean = sx_clean[:10]

        # Prevent invalid "disease == symptom" learning
        name_norm = name.strip().lower().replace(" ", "_")
        if name_norm in sx_clean:
            sx_clean = [s for s in sx_clean if s != name_norm]
        if len(sx_clean) < 3:
            continue

        key = name.lower()
        if key in by_name:
            # Merge symptoms, keep existing source unless new says "online"
            prev = by_name[key]
            merged_sx = sorted({*prev.symptoms, *sx_clean})
            src = prev.source
            new_src = str(d.get("source") or "").strip().lower()
            if new_src == "online":
                src = "online"
            verified = prev.verified and (src.strip().lower() != "online")
            by_name[key] = DiseaseEntry(disease=prev.disease, symptoms=merged_sx[:10], source=src, verified=verified)
        else:
            src = str(d.get("source", "online") or "online").strip()
            verified = bool(d.get("verified", False)) if src.strip().lower() == "online" else True
            by_name[key] = DiseaseEntry(disease=name, symptoms=sorted(set(sx_clean))[:10], source=src, verified=verified)
            added += 1

    # Save back
    data_out = [
        {"disease": e.disease, "symptoms": e.symptoms, "source": e.source, "verified": e.verified}
        for e in sorted(by_name.values(), key=lambda x: x.disease.lower())
    ]
    DISEASE_DB_PATH.write_text(json.dumps(data_out, indent=2), encoding="utf-8")
    return added


def clean_db_inplace() -> dict[str, int]:
    """
    Remove invalid learned entries from disease_db.json:
    - symptoms length < 3
    - disease name equals a symptom (normalized)
    Returns counts of removed items.
    """
    if not DISEASE_DB_PATH.exists():
        return {"removed_too_short": 0, "removed_same_as_symptom": 0, "removed_invalid_symptoms": 0}

    removed_too_short = 0
    removed_same = 0
    removed_invalid_symptoms = 0

    try:
        raw = json.loads(DISEASE_DB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"removed_too_short": 0, "removed_same_as_symptom": 0, "removed_invalid_symptoms": 0}

    if not isinstance(raw, list):
        return {"removed_too_short": 0, "removed_same_as_symptom": 0, "removed_invalid_symptoms": 0}

    kept: list[DiseaseEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = _clean_disease_name(item.get("disease", ""))
        symptoms = item.get("symptoms", [])
        if not name or not isinstance(symptoms, list):
            continue
        src = str(item.get("source", "database") or "database").strip()
        verified = bool(item.get("verified", True if src.strip().lower() == "database" else False))

        sx = _normalize_symptoms(symptoms)
        if len(sx) < 3 and src.strip().lower() == "online":
            removed_too_short += 1
            continue

        name_norm = name.strip().lower().replace(" ", "_")
        if name_norm in sx and src.strip().lower() == "online":
            removed_same += 1
            continue

        # If we filtered out a lot of symptom junk, don't keep online entries that
        # are now effectively empty/low quality.
        if src.strip().lower() == "online":
            original_nonempty = len([s for s in symptoms if str(s or "").strip()])
            if original_nonempty >= 3 and len(sx) < 3:
                removed_invalid_symptoms += 1
                continue

        kept.append(DiseaseEntry(disease=name, symptoms=sx[:10], source=src, verified=verified))

    data_out = [
        {"disease": e.disease, "symptoms": e.symptoms, "source": e.source, "verified": e.verified}
        for e in sorted(kept, key=lambda x: x.disease.lower())
    ]
    DISEASE_DB_PATH.write_text(json.dumps(data_out, indent=2), encoding="utf-8")
    return {
        "removed_too_short": removed_too_short,
        "removed_same_as_symptom": removed_same,
        "removed_invalid_symptoms": removed_invalid_symptoms,
    }

