from __future__ import annotations

from typing import Any

from utils.disease_store_v2 import maybe_promote, upsert_raw
from utils.learning_jobs import finish_job, update_job
from utils.online_search import search_diseases
from utils.symptom_cleaner import clean_symptoms


def run_learning_job(job_id: str, *, normalized_symptoms: list[str], user_phrases: list[str]) -> None:
    """
    Background learning:
    - always call online search
    - clean symptoms
    - store into RAW DB
    - maybe promote into VERIFIED DB
    """
    try:
        update_job(job_id, status="running", message="Learning from external sources...", progress=0.05)

        fetched = search_diseases(normalized_symptoms, min_results=6, top_k=8) or []
        update_job(job_id, progress=0.35, message=f"Fetched {len(fetched)} candidates")

        stored = 0
        promoted = 0
        promoted_names: list[str] = []

        for idx, r in enumerate(fetched[:10], start=1):
            dname = str(r.get("disease") or r.get("name") or "").strip()
            rsx = r.get("symptoms", []) or []
            rsx_phrases = [str(s).replace("_", " ") for s in rsx]
            rsx_clean = clean_symptoms(rsx_phrases)
            if len(rsx_clean) < 3:
                continue
            if upsert_raw(dname, rsx_clean, source=str(r.get("source") or "online")):
                stored += 1
                if maybe_promote(dname, user_symptoms=user_phrases):
                    promoted += 1
                    promoted_names.append(dname)
            # progress 0.35 .. 0.95
            update_job(job_id, progress=min(0.95, 0.35 + 0.6 * (idx / max(1, min(10, len(fetched))))), message=f"Learning… ({idx})")

        finish_job(
            job_id,
            status="done",
            message="Learning finished",
            result={"stored_raw": stored, "promoted_verified": promoted, "promoted_names": promoted_names[:10]},
        )
    except Exception as e:
        finish_job(job_id, status="error", message=str(e)[:200], result={})

