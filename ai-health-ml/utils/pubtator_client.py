from __future__ import annotations

from typing import Any

import httpx

from utils.nlp_engine import extract_raw_phrases
from utils.symptom_cleaner import clean_symptoms
from utils.disease_store_v2 import _is_valid_disease_name  # type: ignore


PUBTATOR3_BASE = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"

_SYMPTOM_HINTS = {
    "pain",
    "ache",
    "nausea",
    "vomit",
    "diarr",
    "fever",
    "cough",
    "snee",
    "itch",
    "rash",
    "red",
    "swelling",
    "edema",
    "dizz",
    "headache",
    "fatigue",
    "weak",
    "numb",
    "tingl",
    "burn",
    "sore",
    "shortness",
    "breath",
    "chest",
    "palpitat",
    "blur",
    "vision",
    "bleed",
    "cramp",
}

_BAD_DISEASE_NAMES = {
    # common symptoms (avoid learning them as diseases)
    "pain",
    "headache",
    "nausea",
    "vomiting",
    "diarrhea",
    "cough",
    "fever",
    "fatigue",
    "dizziness",
    "edema",
    "rash",
    "redness",
    "swelling",
}

_DISEASE_HINTS = {
    "disease",
    "syndrome",
    "infection",
    "cancer",
    "tumor",
    "infarction",
    "arthritis",
    "deficiency",
    "fracture",
    "stroke",
    "diabetes",
    "pneumonia",
    "asthma",
    "angina",
    "myocardial",
    "hepatitis",
    "influenza",
    "conjunctivitis",
    "dermatitis",
    "cellulitis",
    "shingles",
}


def _is_plausible_disease_name(name: str) -> bool:
    t = " ".join(str(name or "").strip().split())
    if not t:
        return False
    tl = t.lower()
    if tl in _BAD_DISEASE_NAMES:
        return False
    # avoid extremely short fragments
    if len(tl) < 4:
        return False
    # avoid category-like plurals
    if tl.endswith("s") and " " not in tl:
        return False
    # Avoid symptom-like phrases unless they look like a real diagnosis
    if not any(h in tl for h in _DISEASE_HINTS):
        # allow longer medical names, but reject short symptom phrases
        if len(tl.split()) <= 3:
            return False
    try:
        if not _is_valid_disease_name(t):
            return False
    except Exception:
        pass
    return True


def _dedup_ci(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for it in items:
        t = " ".join(str(it or "").strip().split())
        if not t:
            continue
        k = t.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(t)
    return out


def search_pmids(query_text: str, *, limit: int = 6) -> list[str]:
    """
    PubTator3 search → PMIDs.
    Endpoint: /search/?text=...
    """
    q = " ".join(str(query_text or "").strip().split())
    if not q:
        return []
    try:
        with httpx.Client(
            timeout=12.0,
            headers={"User-Agent": "ai-health-ml/1.0 (pubtator)"},
        ) as client:
            r = client.get(f"{PUBTATOR3_BASE}/search/", params={"text": q})
        if r.status_code >= 400:
            return []
        data = r.json()
    except Exception:
        return []

    # Response shape varies; we try best-effort extraction
    pmids: list[str] = []
    if isinstance(data, dict):
        # common: {"results":[{"pmid":"..."}, ...]}
        results = data.get("results")
        if isinstance(results, list):
            for it in results:
                if not isinstance(it, dict):
                    continue
                pmid = it.get("pmid") or it.get("PMID")
                if pmid:
                    pmids.append(str(pmid))
    elif isinstance(data, list):
        for it in data:
            if isinstance(it, dict):
                pmid = it.get("pmid") or it.get("PMID")
                if pmid:
                    pmids.append(str(pmid))

    return _dedup_ci(pmids)[: max(1, int(limit))]


def fetch_biocjson(pmids: list[str], *, full: bool = False) -> list[dict[str, Any]]:
    """
    PubTator3 export endpoint.
    Endpoint: /publications/export/biocjson?pmids=...&full=true|false
    """
    ids = [str(p).strip() for p in (pmids or []) if str(p).strip()]
    if not ids:
        return []
    try:
        with httpx.Client(
            timeout=20.0,
            headers={"User-Agent": "ai-health-ml/1.0 (pubtator)"},
        ) as client:
            r = client.get(
                f"{PUBTATOR3_BASE}/publications/export/biocjson",
                params={"pmids": ",".join(ids), "full": "true" if full else "false"},
            )
        if r.status_code >= 400:
            return []
        data = r.json()
    except Exception:
        return []

    # PubTator3 commonly wraps results as:
    # { "PubTator3": [ { ...BioC doc... }, ... ] }
    if isinstance(data, dict):
        wrapped = data.get("PubTator3")
        if isinstance(wrapped, list):
            return [d for d in wrapped if isinstance(d, dict)]
        return [data]
    if isinstance(data, list):
        # sometimes it's already a list of docs
        out: list[dict[str, Any]] = []
        for it in data:
            if isinstance(it, dict) and "PubTator3" in it and isinstance(it.get("PubTator3"), list):
                out.extend([d for d in (it.get("PubTator3") or []) if isinstance(d, dict)])
            elif isinstance(it, dict):
                out.append(it)
        return out
    return []


def _extract_diseases_from_bioc(docs: list[dict[str, Any]]) -> list[str]:
    diseases: list[str] = []
    for doc in docs:
        for p in (doc.get("passages") or []):
            if not isinstance(p, dict):
                continue
            for ann in (p.get("annotations") or []):
                if not isinstance(ann, dict):
                    continue
                inf = ann.get("infons") or {}
                if not isinstance(inf, dict):
                    inf = {}
                t = str(inf.get("type") or inf.get("Type") or "").lower()
                if "disease" not in t:
                    continue
                txt = str(ann.get("text") or "").strip()
                if txt and _is_plausible_disease_name(txt):
                    diseases.append(txt)
    return _dedup_ci(diseases)


def _extract_symptom_phrases_from_text(docs: list[dict[str, Any]]) -> list[str]:
    phrases: list[str] = []
    for doc in docs:
        for p in (doc.get("passages") or []):
            if not isinstance(p, dict):
                continue
            txt = str(p.get("text") or "").strip()
            if not txt:
                continue
            phrases.extend(extract_raw_phrases(txt))
    # Clean and dedup (keeps only symptom-like short phrases)
    cleaned = clean_symptoms(_dedup_ci(phrases))
    # Extra guard: PubMed text includes lots of non-symptom noun chunks.
    # Keep phrases that look symptom-like by keyword hints.
    out: list[str] = []
    for p in cleaned:
        pl = p.lower()
        if any(h in pl for h in _SYMPTOM_HINTS):
            out.append(p)
    return _dedup_ci(out)


def fetch_diseases_with_symptoms_from_pubtator(
    user_symptoms: list[str],
    *,
    max_pmids: int = 6,
    max_diseases: int = 12,
) -> list[dict[str, Any]]:
    """
    End-to-end PubTator learning:
    - Search PMIDs using symptom query
    - Export BioC JSON for those PMIDs
    - Extract DISEASE entities
    - Extract symptom-like phrases from the same BioC text
    - For each disease, attach a 5-10 symptom list (includes user symptoms)

    Returns entries shaped like:
      {"disease": "...", "symptoms": [...], "source": "pubtator"}
    """
    q = ", ".join([s.replace("_", " ").strip() for s in (user_symptoms or []) if str(s).strip()])
    q = " ".join(q.split())
    if not q:
        return []

    pmids = search_pmids(q, limit=max_pmids)
    if not pmids:
        return []

    docs = fetch_biocjson(pmids, full=False)
    if not docs:
        return []

    diseases = _extract_diseases_from_bioc(docs)[: max_diseases]
    if not diseases:
        return []

    extracted_symptoms = _extract_symptom_phrases_from_text(docs)
    # Always include the user's own symptoms as anchors
    anchor = clean_symptoms([s.replace("_", " ") for s in (user_symptoms or [])])
    combined_pool = _dedup_ci([*anchor, *extracted_symptoms])
    combined_pool = clean_symptoms(combined_pool)

    # If PubTator text is sparse, still return anchored symptoms
    if len(combined_pool) < 4:
        combined_pool = anchor

    out: list[dict[str, Any]] = []
    for d in diseases:
        sx = combined_pool[:10]
        if len(sx) < 5:
            # still return, storage layer will enforce >=4
            pass
        out.append({"disease": d, "symptoms": sx, "source": "pubtator"})
    return out

