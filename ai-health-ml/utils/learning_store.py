from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from utils.config import DATA_DIR


LEARNED_DATA_PATH = DATA_DIR / "learned_data.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_root() -> dict[str, Any]:
    if not LEARNED_DATA_PATH.exists():
        return {"version": 1, "patterns": []}
    try:
        return json.loads(LEARNED_DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        # If file is corrupted, do not crash prediction path.
        return {"version": 1, "patterns": []}


def _save_root(root: dict[str, Any]) -> None:
    LEARNED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEARNED_DATA_PATH.write_text(json.dumps(root, indent=2, sort_keys=False), encoding="utf-8")


def store_new_patterns(
    symptoms: Iterable[str],
    diseases: Iterable[str],
    *,
    source: str = "system",
    tag: str = "unverified",
) -> bool:
    """
    Controlled learning store.

    - Stores *suggestions* separately from the main training DB.
    - Marks them as 'unverified' by default.
    - Deduplicates by (sorted symptoms, disease).
    """
    symptoms_list = sorted({s for s in symptoms if s})
    diseases_list = sorted({d for d in diseases if d})
    if not symptoms_list or not diseases_list:
        return False

    root = _load_root()
    patterns: list[dict[str, Any]] = list(root.get("patterns", []))
    existing = {
        (tuple(p.get("symptoms", [])), str(p.get("disease", "")).strip().lower())
        for p in patterns
        if isinstance(p, dict)
    }

    created = 0
    for disease in diseases_list:
        key = (tuple(symptoms_list), disease.strip().lower())
        if key in existing:
            continue
        patterns.append(
            {
                "symptoms": symptoms_list,
                "disease": disease,
                "verified": False,
                "tag": tag,
                "source": source,
                "created_at": _utc_now_iso(),
            }
        )
        created += 1

    root["version"] = root.get("version", 1)
    root["patterns"] = patterns
    _save_root(root)
    return created > 0


def retrieve_learned_patterns(symptoms: Iterable[str], *, min_overlap: float = 0.6) -> list[dict[str, Any]]:
    """
    Retrieve unverified learned patterns matching the current symptom set.
    Returns entries sorted by overlap descending.
    """
    symptom_set = {s for s in symptoms if s}
    if not symptom_set:
        return []

    root = _load_root()
    patterns = root.get("patterns", [])
    if not isinstance(patterns, list):
        return []

    matches: list[dict[str, Any]] = []
    for p in patterns:
        if not isinstance(p, dict):
            continue
        ps = set(p.get("symptoms", []) or [])
        if not ps:
            continue
        # Overlap metric tuned for reuse:
        # allow subset/superset matching (e.g. previous search stored 3 symptoms but current extraction finds 1).
        denom = max(1, min(len(ps), len(symptom_set)))
        overlap = len(ps & symptom_set) / denom
        if overlap >= min_overlap:
            p2 = dict(p)
            p2["overlap"] = round(overlap, 3)
            matches.append(p2)

    matches.sort(key=lambda x: x.get("overlap", 0.0), reverse=True)
    return matches


def store_learned_data(symptoms: Iterable[str], diseases: Iterable[str]) -> bool:
    """
    Spec-friendly alias: stores learned patterns as unverified, source='online'.
    """
    return store_new_patterns(symptoms, diseases, source="online", tag="unverified")


def get_learned_matches(symptoms: Iterable[str], *, min_overlap: float = 0.6, top_k: int = 7) -> list[str]:
    """
    Returns learned disease suggestions for this symptom set (highest overlap first).
    """
    matches = retrieve_learned_patterns(symptoms, min_overlap=min_overlap)
    out: list[str] = []
    for m in matches:
        name = str(m.get("disease", "")).strip()
        if name and name.lower() not in {x.lower() for x in out}:
            out.append(name)
        if len(out) >= top_k:
            break
    return out

