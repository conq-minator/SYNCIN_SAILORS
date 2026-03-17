from __future__ import annotations

import re
from typing import Any

from utils.config import get_env
from utils.learning_store import retrieve_learned_patterns, store_new_patterns
from utils.hf_client import call_huggingface_api

def enhance_results(symptoms: list[str], predictions: list[dict[str, Any]], *, threshold: float = 0.5) -> dict[str, Any]:
    """
    Knowledge enhancement layer.

    - Never overrides ML predictions.
    - Never requires an API key.
    - Uses optional HF Inference only if HF_API_KEY exists.
    - Uses controlled learning store (`data/learned_data.json`) for unverified patterns.
    """
    result: dict[str, Any] = {"additional_insights": [], "suggested_diseases": []}
    if not predictions:
        return result

    max_conf = max(float(p.get("confidence", 0.0)) for p in predictions)
    symptoms_str = ", ".join(symptoms) if symptoms else ""

    # Always: add learned-pattern hints (unverified, suggestion-only)
    learned = retrieve_learned_patterns(symptoms, min_overlap=0.6)
    if learned:
        top = learned[:3]
        suggestions = [str(p.get("disease", "")).strip() for p in top if str(p.get("disease", "")).strip()]
        if suggestions:
            result["additional_insights"].append(
                "Unverified learned suggestions (from prior patterns): "
                + ", ".join(sorted(set(suggestions)))
                + "."
            )
            result["suggested_diseases"].extend(suggestions)

    # Low-confidence: optionally ask an external model for suggestions
    if max_conf < threshold and symptoms:
        suggested = _ai_suggest_diseases(symptoms_str, top_k=5)
        if suggested:
            # Store as unverified patterns (controlled learning)
            store_new_patterns(symptoms, suggested, source="ai_suggestion", tag="unverified")
            result["additional_insights"].append(
                "Additional possible conditions (AI-suggested, unverified): " + ", ".join(suggested) + "."
            )
            result["suggested_diseases"].extend(suggested)

        # Always add generic guidance
        advice = get_medical_info(symptoms_str)
        if advice:
            result["additional_insights"].append(advice)

    # Dedup
    result["suggested_diseases"] = sorted({d for d in result["suggested_diseases"] if d})
    return result

def get_medical_info(symptoms_query):
    """Try to get real medical information from APIs"""
    try:
        # This is a placeholder - in real implementation you'd use:
        # - PubMed API
        # - WHO API
        # - Medical databases
        # - OpenAI/Knowledge APIs

        # For demo, return generic advice
        if 'fever' in symptoms_query.lower():
            return "Fever is common with infections. Monitor temperature and consult healthcare provider if >103°F or persistent."
        elif 'cough' in symptoms_query.lower():
            return "Persistent cough may indicate respiratory issues. Stay hydrated and consider humidifier use."
        elif 'fatigue' in symptoms_query.lower():
            return "Chronic fatigue can have many causes. Consider sleep quality, nutrition, and stress levels."

        return "General advice: Monitor symptoms, stay hydrated, rest, and consult healthcare provider if symptoms worsen or persist."

    except Exception as e:
        print(f"Medical info error: {e}")
        return ""

def update_disease_confidence(disease_name, actual_outcome):
    """Update disease confidence based on user feedback or actual diagnosis"""
    try:
        db = DiseaseDatabase()
        # Simple confidence update - in real system this would be more sophisticated
        if actual_outcome == 'correct':
            db.update_disease_confidence(disease_name, 0.1)  # Small increase
        elif actual_outcome == 'incorrect':
            db.update_disease_confidence(disease_name, -0.05)  # Small decrease

    except Exception as e:
        print(f"Confidence update failed: {e}")

def get_disease_trends():
    """Get trending diseases and health insights"""
    try:
        # Kept for backwards compatibility: if the internet checker exists it can be used,
        # but trends must never crash the API.
        from utils.internet_checker import InternetDiseaseChecker  # local import

        checker = InternetDiseaseChecker()
        trends = checker.get_disease_trends() or []
        names = []
        for t in trends[:5]:
            name = t.get("name") if isinstance(t, dict) else None
            if name:
                names.append(str(name))
        return f"Recent health trends: {', '.join(names)}" if names else ""
    except Exception as e:
        return ""


def _ai_suggest_diseases(symptoms_str: str, *, top_k: int = 5) -> list[str]:
    """
    Optional external knowledge: Hugging Face Inference API.
    Returns a list of disease/condition names, or [] if not configured/failed.
    """
    prompt = (
        "Given these symptoms, suggest up to "
        f"{top_k} possible diseases/conditions. "
        "Return ONLY a comma-separated list of names.\n\n"
        f"Symptoms: {symptoms_str}\n\n"
        "Suggestions:"
    )
    try:
        generated = call_huggingface_api(prompt, model_env="HF_DISEASE_MODEL")
        if not generated:
            return []

        parts = [p.strip() for p in re.split(r"[,\n;]+", generated) if p.strip()]
        # Normalize and keep short list
        cleaned: list[str] = []
        for p in parts:
            p2 = re.sub(r"^[-•\\s]+", "", p).strip()
            p2 = re.sub(r"\\s+", " ", p2)
            if p2 and p2.lower() not in {c.lower() for c in cleaned}:
                cleaned.append(p2)
            if len(cleaned) >= top_k:
                break
        return cleaned
    except Exception:
        return []
