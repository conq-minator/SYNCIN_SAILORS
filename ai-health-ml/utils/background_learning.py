from __future__ import annotations

from typing import Any

from utils.disease_store_v2 import match_raw, upsert_raw, upsert_verified
from utils.learning_jobs import finish_job, update_job
from utils.symptom_cleaner import clean_symptoms
from utils.pubtator_client import fetch_diseases_with_symptoms_from_pubtator
from utils.online_search import search_diseases, fetch_disease_symptoms


def run_learning_job(
    job_id: str,
    *,
    normalized_symptoms: list[str],
    user_phrases: list[str],
    candidate_diseases: list[str] | None = None,
    low_confidence: bool = False,
) -> None:
    """
    Background learning:
    - always call online search
    - clean symptoms
    - store into RAW DB
    - maybe promote into VERIFIED DB
    """
    try:
        update_job(job_id, status="running", message="Learning from external sources...", progress=0.05)

        # Reuse learned data first to avoid repeated API calls:
        # If we already have 5 learned RAW matches with non-zero overlap for this symptom set,
        # skip external calls and finish quickly.
        try:
            cached = match_raw(user_phrases)[:5] if user_phrases else []
        except Exception:
            cached = []
        cached_good = [c for c in cached if float(c.get("confidence", 0.0)) > 0.0]
        if len(cached_good) >= 5:
            finish_job(
                job_id,
                status="done",
                message="Reused learned diseases (skipped external call)",
                result={
                    "reused_cache": True,
                    "reused_names": [c.get("name") for c in cached_good[:5] if c.get("name")],
                    "stored_raw": 0,
                    "promoted_verified": 0,
                    "promoted_names": [],
                },
            )
            return

        fetched: list[dict[str, Any]] = []

        # PubTator is primary external source (quota-friendly, no API key).
        update_job(job_id, progress=0.15, message="Fetching from PubTator...")
        pubtator_results = fetch_diseases_with_symptoms_from_pubtator(
            user_phrases or normalized_symptoms, max_pmids=6, max_diseases=12
        ) or []
        fetched: list[dict[str, Any]] = []

        if pubtator_results:
            update_job(
                job_id,
                progress=0.25,
                message=f"Fetched from PubTator: {len(pubtator_results)} diseases",
            )
            print("Fetched from PubTator")
            print(
                "Extracted diseases:",
                [f.get("disease") for f in pubtator_results if f.get("disease")][:10],
            )

            # For each PubTator disease, require at least 2 PubTator symptoms,
            # then enrich with online symptoms. These mixed entries are marked as 'pubonline'.
            for r in pubtator_results:
                dname = str(r.get("disease") or "").strip()
                if not dname:
                    continue
                pub_sx_raw = [str(s) for s in (r.get("symptoms") or [])]
                pub_sx = clean_symptoms(pub_sx_raw)
                if len(pub_sx) < 2:
                    continue  # not enough PubTator signal, skip to fallback later

                # Enrich with online symptoms for the same disease
                try:
                    extra = fetch_disease_symptoms(dname) or []
                except Exception:
                    extra = []
                extra_clean = clean_symptoms([str(s) for s in extra])

                merged = clean_symptoms([*pub_sx, *extra_clean])[:10]
                if len(merged) < 4:
                    continue

                fetched.append(
                    {
                        "disease": dname,
                        "symptoms": merged,
                        "source": "pubonline",
                    }
                )

            if not fetched:
                # PubTator returned data but nothing passed quality gates; fall back.
                fallback = search_diseases(normalized_symptoms, min_results=12, top_k=12) or []
                fetched = fallback
                update_job(
                    job_id,
                    progress=0.3,
                    message=f"PubTator unusable. Fallback fetched: {len(fetched)} diseases",
                )
            else:
                update_job(
                    job_id,
                    progress=0.3,
                    message=f"Stored {len(fetched)} PubTator+online (pubonline) diseases",
                )
        else:
            # PubTator returned nothing at all; fallback to existing online_search pipeline.
            fetched = search_diseases(normalized_symptoms, min_results=12, top_k=12) or []
            update_job(
                job_id,
                progress=0.3,
                message=f"PubTator empty. Fallback fetched: {len(fetched)} diseases",
            )

        stored = 0
        stored_verified = 0
        promoted = 0
        promoted_names: list[str] = []

        processed = 0
        for r in fetched[:30]:
            if stored_verified >= 5:
                break
            processed += 1
            dname = str(r.get("disease") or r.get("name") or "").strip()
            rsx = r.get("symptoms", []) or []
            rsx_phrases = [str(s).replace("_", " ") for s in rsx]
            rsx_clean = clean_symptoms(rsx_phrases)
            # Store only if we have at least 4 clean symptom phrases (quality gate)
            if len(rsx_clean) < 4:
                continue
            src = str(r.get("source") or "online")
            if upsert_raw(dname, rsx_clean, source=src):
                stored += 1
            # Immediate promotion: store directly into VERIFIED once valid.
            if upsert_verified(dname, rsx_clean, source=src):
                stored_verified += 1
                promoted += 1
                promoted_names.append(dname)
                print("Stored in RAW:", dname)
                print("Promoted to VERIFIED:", dname)
            # progress 0.35 .. 0.95
            update_job(
                job_id,
                progress=min(0.95, 0.35 + 0.6 * (processed / max(1, min(10, len(fetched))))),
                message=f"Learning… ({processed})",
            )

        finish_job(
            job_id,
            status="done",
            message="Learning finished",
            result={
                "reused_cache": False,
                "stored_raw": stored,
                "stored_verified": stored_verified,
                "promoted_verified": promoted,
                "promoted_names": promoted_names[:10],
            },
        )
    except Exception as e:
        finish_job(job_id, status="error", message=str(e)[:200], result={})

