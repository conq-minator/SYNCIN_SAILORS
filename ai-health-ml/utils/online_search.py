from __future__ import annotations

import re

from utils.hf_client import call_huggingface_api, get_last_hf_error
from utils.disease_json_db import load_disease_db, calculate_match
from utils.nlp_engine import extract_raw_phrases as extract_symptom_phrases, normalize_phrase
from utils.symptom_db import add_symptom
import httpx
import time
import json
import html
from typing import Any

def _score_online_disease(name: str, symptoms: list[str]) -> float:
    # If we can find the disease in our local JSON DB, score by symptom overlap.
    entries = load_disease_db()
    name_l = name.strip().lower()
    for e in entries:
        if e.disease.strip().lower() == name_l:
            return calculate_match(symptoms, e.symptoms)
    # Otherwise, assign a conservative weak score (still "online" source).
    return 0.3


def search_diseases(symptoms: list[str], *, min_results: int = 4, top_k: int = 6) -> list[dict]:
    """
    Online search via Hugging Face inference (read-only).
    Returns [] if HF_API_KEY is missing or the API fails.
    """
    if not symptoms:
        return []

    print("Triggering ONLINE SEARCH...")
    print("Symptoms:", symptoms)

    # Normalize symptoms for external sources (avoid underscores) and for storage (underscore keys).
    norm_symptoms = [s.replace("_", " ").strip() for s in symptoms if s and str(s).strip()]
    store_symptoms = [s.strip().lower().replace(" ", "_") for s in norm_symptoms if s.strip()]

    prompt = (
        "List diseases/conditions related to these symptoms: "
        f"{', '.join(norm_symptoms)}.\n"
        "Return ONLY a Python list of strings.\n\n"
        "Answer:"
    )
    # Two-stage learning:
    # Stage 1: fetch candidate diseases for the symptom set
    # Stage 2: for each disease, fetch common symptoms (5-10), validate, then return.
    last_err = ""
    for attempt in range(1, 4):
        if attempt > 1:
            time.sleep(1.2)

        print("Fetching diseases...")
        disease_names = _stage1_fetch_diseases(norm_symptoms, limit=max(8, int(top_k)))
        if disease_names:
            learned: list[dict[str, Any]] = []
            for dname in disease_names:
                if len(learned) >= max(min_results, top_k):
                    break
                print(f"Fetching symptoms for disease: {dname}")
                dsx = _stage2_fetch_symptoms_for_disease(dname)
                validated = _validate_symptoms(dname, dsx)
                if not validated:
                    continue
                print("Validated symptoms:", validated)
                # Symptom learning: store each symptom phrase (spaces) into symptom_db.json
                try:
                    for s in validated:
                        add_symptom(str(s).replace("_", " "), source="learned")
                except Exception:
                    pass
                score = calculate_match(symptoms, validated)
                learned.append(
                    {"disease": dname, "symptoms": validated, "confidence": round(float(score), 4), "source": "online", "verified": False}
                )
                print("Stored disease successfully")

            if len(learned) >= min_results:
                return learned[: max(min_results, top_k)]

        last_err = get_last_hf_error() or last_err

        # 2) Web scrape fallback (PubMed titles)
        try:
            from utils.internet_checker import InternetDiseaseChecker

            print("HF returned empty, falling back to web search...")
            checker = InternetDiseaseChecker()
            names = checker.search_web_for_diseases(", ".join(symptoms)) or []
            names = _clean_names(names, top_k=top_k)
            if names:
                # We only have names; store using the user's symptom set (non-binary).
                return [
                    {
                        "disease": n,
                        "symptoms": store_symptoms,
                        "confidence": round(float(_score_online_disease(n, symptoms)), 4),
                        "source": "online",
                    }
                    for n in names[: max(min_results, min(top_k, len(names)))]
                ]
        except Exception as e:
            last_err = str(e)

        # 3) Public medical terminology fallback (NLM ClinicalTables)
        try:
            print("Web search returned no candidates, trying NLM ClinicalTables...")
            # NLM works better with plain keywords (spaces), not underscore tokens.
            q = ", ".join(norm_symptoms) if norm_symptoms else ", ".join(symptoms)
            with httpx.Client(timeout=12.0, headers={"User-Agent": "ai-health-ml/1.0"}) as client:
                r = client.get(
                    "https://clinicaltables.nlm.nih.gov/api/conditions/v3/search",
                    params={"terms": q, "maxList": str(top_k)},
                )
                if r.status_code < 400:
                    payload = r.json()
                    # Format: [count, [ids...], null, [[names...], ...]]
                    if (
                        isinstance(payload, list)
                        and len(payload) >= 4
                        and isinstance(payload[3], list)
                        and payload[3]
                        and isinstance(payload[3][0], list)
                    ):
                        names = _clean_names(payload[3][0], top_k=25)
                    else:
                        names = []

                    # If ClinicalTables is too sparse, expand with NLM Health Topics search (reliable, public).
                    if len(names) < min_results:
                        print("ClinicalTables sparse, expanding with NLM Health Topics...")
                        expanded: list[str] = []
                        for sx in (norm_symptoms or []):
                            expanded.extend(_nlm_health_topics(sx, limit=10))
                        # combine + dedup
                        combined: list[str] = []
                        for n in names + expanded:
                            if n and n.lower() not in {c.lower() for c in combined}:
                                combined.append(n)
                            if len(combined) >= max(min_results, top_k):
                                break
                        names = combined

                    if names:
                        # Store using observed symptom set (non-binary).
                        take = min(len(names), max(min_results, top_k))
                        return [
                            {
                                "disease": n,
                                "symptoms": store_symptoms,
                                "confidence": round(float(0.35), 4),
                                "source": "online",
                            }
                            for n in names[:take]
                        ]
                # If broad query returned nothing, try each symptom individually (more reliable).
                for sx in (norm_symptoms or []):
                    r2 = client.get(
                        "https://clinicaltables.nlm.nih.gov/api/conditions/v3/search",
                        params={"terms": sx, "maxList": str(top_k)},
                    )
                    if r2.status_code >= 400:
                        continue
                    payload2 = r2.json()
                    if (
                        isinstance(payload2, list)
                        and len(payload2) >= 4
                        and isinstance(payload2[3], list)
                        and payload2[3]
                        and isinstance(payload2[3][0], list)
                    ):
                        names2 = _clean_names(payload2[3][0], top_k=top_k)
                        if names2:
                            # NLM gives condition names only; store with the user's symptoms as the "observed set".
                            # This is still non-binary and enables DB growth + reuse.
                            return [
                                {"disease": n, "symptoms": store_symptoms, "confidence": round(float(0.35), 4), "source": "online"}
                                for n in names2[: max(min_results, min(top_k, len(names2)))]
                            ]
        except Exception as e:
            last_err = str(e)

    print("API failed:", last_err or get_last_hf_error() or "No online results")
    return []


def fetch_candidate_diseases(symptoms: list[str], *, limit: int = 5) -> list[str]:
    """
    Stage-1 only: return disease candidate names for the symptom set.
    Used for immediate UI suggestions while enrichment runs in background.
    """
    if not symptoms:
        return []
    norm_symptoms = [s.replace("_", " ").strip() for s in symptoms if s and str(s).strip()]
    names = _stage1_fetch_diseases(norm_symptoms, limit=max(1, int(limit)))
    # Dedup & trim
    out: list[str] = []
    for n in names:
        n2 = re.sub(r"\s+", " ", str(n or "")).strip()
        if n2 and n2.lower() not in {x.lower() for x in out}:
            out.append(n2)
        if len(out) >= limit:
            break
    return out


def _stage1_fetch_diseases(symptoms_human: list[str], *, limit: int = 8) -> list[str]:
    """
    Stage 1: get disease names related to the symptom set.
    Prefers HF; falls back to NLM Health Topics titles.
    """
    prompt = (
        f"List diseases related to: {', '.join(symptoms_human)}.\n"
        "Return ONLY a Python list of strings.\n"
    )
    text = call_huggingface_api(prompt, model_env="HF_DISEASE_MODEL")
    names = _parse_python_list_of_strings(text, limit=limit) if text else []
    if names:
        return names
    # fallback: NLM health topics
    expanded: list[str] = []
    for sx in symptoms_human:
        expanded.extend(_nlm_health_topics(sx, limit=10))
    # dedup
    out: list[str] = []
    for n in expanded:
        n2 = re.sub(r"\s+", " ", html.unescape(str(n))).strip()
        if n2 and n2.lower() not in {x.lower() for x in out}:
            out.append(n2)
        if len(out) >= limit:
            break
    return out


def _stage2_fetch_symptoms_for_disease(disease: str) -> list[str]:
    """
    Stage 2: fetch common symptoms for a disease (5-10).
    Prefers HF; falls back to NLM Health Topics summary -> symptom extraction.
    """
    prompt = (
        f"List the most common symptoms of {disease}. "
        "Return 5 to 10 symptoms as a Python list of strings.\n"
    )
    text = call_huggingface_api(prompt, model_env="HF_DISEASE_MODEL")
    items = _parse_python_list_of_strings(text, limit=12) if text else []
    if items:
        return items

    # fallback: use NLM topic summary and extract symptom-like short phrases
    summary = _nlm_health_topics_summary(disease)
    if not summary:
        return []

    out: list[str] = []

    # Phrase extraction (keeps unknowns) but aggressively filter to avoid
    # learning entire sentences as "symptoms".
    for ph in extract_symptom_phrases(summary):
        tok = normalize_phrase(ph)
        if not tok:
            continue
        # keep symptom-like tokens only
        if len(tok) > 32:
            continue
        if tok.count("_") > 3:
            continue
        if tok.startswith(("what_", "why_", "how_", "can_", "should_", "when_", "who_")):
            continue
        if tok not in out:
            out.append(tok)
        if len(out) >= 12:
            break

    return out


def _validate_symptoms(disease: str, symptoms_any: list[str]) -> list[str]:
    """
    Validation rules:
    - 3 to 10 symptoms
    - dedup
    - symptoms not just disease name
    """
    sx = [str(s).strip().lower().replace(" ", "_") for s in symptoms_any if str(s).strip()]
    # remove duplicates preserving order
    out: list[str] = []
    for s in sx:
        if s not in out:
            out.append(s)
    # remove disease-like token
    dn = str(disease).strip().lower().replace(" ", "_")
    out = [s for s in out if s != dn]
    # enforce size
    if len(out) < 3:
        return []
    return out[:10]


def fetch_disease_symptoms(disease: str) -> list[str]:
    """
    Public wrapper for Stage-2 enrichment.
    Returns cleaned symptom TOKENS (underscore format) or [].
    """
    dsx = _stage2_fetch_symptoms_for_disease(disease)
    return _validate_symptoms(disease, dsx)


def _parse_python_list_of_strings(text: str, *, limit: int = 10) -> list[str]:
    if not text:
        return []
    # extract quoted strings without eval
    items = re.findall(r"['\"]([^'\"]{2,80})['\"]", text)
    if not items:
        return []
    out: list[str] = []
    for it in items:
        name = re.sub(r"\s+", " ", html.unescape(it)).strip()
        if name and name.lower() not in {x.lower() for x in out}:
            out.append(name)
        if len(out) >= limit:
            break
    return out


def _nlm_health_topics_summary(term: str) -> str:
    """
    Fetch one healthTopics document and return a textual summary.
    """
    url = "https://wsearch.nlm.nih.gov/ws/query"
    params = {"db": "healthTopics", "term": term, "retmax": "1"}
    try:
        with httpx.Client(timeout=12.0, headers={"User-Agent": "ai-health-ml/1.0"}) as client:
            r = client.get(url, params=params)
            if r.status_code >= 400:
                return ""
            xml = r.text
        # Prefer FullSummary; else use snippet
        m = re.search(r'<content\s+name="FullSummary">(.*?)</content>', xml, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            m = re.search(r'<content\s+name="snippet">(.*?)</content>', xml, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            return ""
        raw = html.unescape(m.group(1))
        return re.sub(r"\s+", " ", re.sub(r"<.*?>", "", raw)).strip()
    except Exception:
        return ""


def _parse_json_diseases(text: str) -> list[dict[str, Any]]:
    """
    Strict JSON parser for HF output. Retries expect the model to return JSON only.
    """
    try:
        # Strip common leading/trailing noise
        t = text.strip()
        # If model wrapped JSON in text, try to locate the first '[' and last ']'
        if "[" in t and "]" in t:
            t = t[t.find("[") : t.rfind("]") + 1]
        data = json.loads(t)
        if not isinstance(data, list):
            return []
        out: list[dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("disease", "")).strip()
            sx = item.get("symptoms", [])
            if not name or not isinstance(sx, list):
                continue
            sx_clean = [str(s).strip().lower().replace(" ", "_") for s in sx if str(s).strip()]
            if not sx_clean:
                continue
            out.append({"disease": name, "symptoms": sorted(set(sx_clean))})
        # Dedup by disease name
        dedup = []
        seen = set()
        for it in out:
            key = it["disease"].lower()
            if key in seen:
                continue
            seen.add(key)
            dedup.append(it)
        return dedup
    except Exception:
        return []


def _nlm_health_topics(term: str, *, limit: int = 10) -> list[str]:
    """
    NLM Health Topics search (public). Returns topic titles that often correspond
    to conditions/diseases relevant to the term.
    Endpoint: https://wsearch.nlm.nih.gov/ws/query
    """
    term = (term or "").strip()
    if not term:
        return []
    url = "https://wsearch.nlm.nih.gov/ws/query"
    params = {
        "db": "healthTopics",
        "term": term,
        "retmax": str(limit),
    }
    try:
        with httpx.Client(timeout=12.0, headers={"User-Agent": "ai-health-ml/1.0"}) as client:
            r = client.get(url, params=params)
            if r.status_code >= 400:
                return []
            xml = r.text
        # Very small XML extraction (avoid adding XML deps)
        titles = re.findall(r'<content\s+name="title">(.*?)</content>', xml, flags=re.IGNORECASE)
        cleaned: list[str] = []
        for t in titles:
            # Titles sometimes include HTML entities/markup; clean and unescape.
            raw = html.unescape(str(t))
            name = re.sub(r"\s+", " ", re.sub(r"<.*?>", "", raw)).strip()
            if name and name.lower() not in {c.lower() for c in cleaned}:
                cleaned.append(name)
            if len(cleaned) >= limit:
                break
        return cleaned
    except Exception:
        return []

def _clean_names(items: list, *, top_k: int) -> list[str]:
    cleaned: list[str] = []
    for it in items:
        name = re.sub(r"\s+", " ", str(it)).strip()
        if not name:
            continue
        if name.lower() not in {c.lower() for c in cleaned}:
            cleaned.append(name)
        if len(cleaned) >= top_k:
            break
    return cleaned


def _parse_names_from_text(text: str, *, top_k: int) -> list[str]:
    # Try to parse list-ish output safely (without eval): extract quoted strings first.
    items = re.findall(r"['\"]([^'\"]{2,120})['\"]", text)
    if items:
        return _clean_names(items, top_k=top_k)

    # If model didn't quote items, fallback to comma splitting
    parts = [p.strip() for p in re.split(r"[,\n;]+", text) if p.strip()]
    cleaned: list[str] = []
    for p in parts:
        p2 = re.sub(r"^[\[\]\-\•\s]+", "", p).strip()
        p2 = re.sub(r"[\[\]]+$", "", p2).strip()
        if p2 and p2.lower() not in {c.lower() for c in cleaned}:
            cleaned.append(p2)
        if len(cleaned) >= top_k:
            break
    return cleaned

