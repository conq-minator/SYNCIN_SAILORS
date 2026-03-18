from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import joblib
import os
import uvicorn
from utils.feature_mapper import create_feature_vector, get_feature_names
from utils.nlp_engine import extract_symptoms as extract_symptoms_full
from utils.knowledge_helper import get_disease_trends
from utils.dynamic_trainer import DynamicModelTrainer
from utils.config import MODEL_DIR, PROJECT_ROOT, load_env
from utils.config import DATA_DIR, get_env
import json
from utils.disease_json_db import clean_db_inplace
from utils.online_search import search_diseases
from utils.disease_store_v2 import (
    match_verified,
    match_raw,
    maybe_promote,
    seed_verified_from_legacy_if_empty,
    upsert_raw,
)
from utils.symptom_cleaner import clean_symptoms
from utils.symptom_db import add_symptom, expand_related_online, upsert_related
from utils.ml_trainer import train_and_save
from pathlib import Path
import socket

app = FastAPI(title="AI/ML Prediction Engine")

load_env()

# Clean invalid learned entries on startup (safe, idempotent)
try:
    clean_db_inplace()
except Exception:
    pass

# Seed verified DB from legacy trusted DB if empty (stabilizer)
try:
    seed_verified_from_legacy_if_empty()
except Exception:
    pass

# Allow the UI (served from / or opened locally) to call the API safely.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model and encoder globally
model_path = str(MODEL_DIR / "model.pkl")
encoder_path = str(MODEL_DIR / "label_encoder.pkl")

if os.path.exists(model_path) and os.path.exists(encoder_path):
    model = joblib.load(model_path)
    label_encoder = joblib.load(encoder_path)
else:
    model = None
    label_encoder = None

class VitalsModel(BaseModel):
    blood_sugar: Optional[float] = None
    bp: Optional[str] = None

class PredictionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Natural language description of symptoms")
    vitals: Optional[VitalsModel] = None
    history: List[str] = Field(default_factory=list)

class DiseasePrediction(BaseModel):
    name: str
    confidence: float
    source: str = "ml"

class StatusModel(BaseModel):
    used_database: bool = False
    searched_online: bool = False
    used_learned_data: bool = False  # now means: used stored "online" entries from disease_db.json
    confidence_level: str = "unknown"  # low|medium|high

class PredictionResponse(BaseModel):
    symptoms_detected: List[str]
    unknown_symptoms: List[str] = Field(default_factory=list)
    extracted_phrases: List[str] = Field(default_factory=list)
    diseases: List[DiseasePrediction]
    online_results: List[DiseasePrediction] = Field(default_factory=list)
    external_suggestions: List[str] = Field(default_factory=list)
    status: StatusModel = Field(default_factory=StatusModel)
    messages: List[str] = Field(default_factory=list)
    additional_insights: List[str] = Field(default_factory=list)
    note: str
    search_state: str = "done"
    learning_job_id: Optional[str] = None


class UserReportRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    symptoms: List[str] = Field(default_factory=list)
    description: str = Field(default="", max_length=2000)


class SimilarDiseasesRequest(BaseModel):
    symptoms: List[str] = Field(default_factory=list)

@app.post("/ml/predict", response_model=PredictionResponse)
def predict_disease(request: PredictionRequest, background_tasks: BackgroundTasks):
    if model is None or label_encoder is None:
        raise HTTPException(status_code=500, detail="Model or label encoder not found.")
        
    # 1. Get text input
    input_text = request.text
    
    # 2. Extract symptoms dynamically
    sx = extract_symptoms_full(input_text)
    # spaCy engine returns raw_phrases + normalized_symptoms + unknown_symptoms
    extracted_phrases = sx.get("raw_phrases", []) or []
    normalized_symptoms = sx.get("normalized_symptoms", []) or []
    unknown_symptoms = sx.get("unknown_symptoms", []) or []

    messages: list[str] = []

    # Symptom learning (ALWAYS store new phrases)
    for ph in extracted_phrases:
        try:
            if add_symptom(ph, source="user_input"):
                print("New symptom detected:", ph)
                print("Added to symptom_db:", ph)
                messages.append(f"Added new symptom to system: {ph}")
        except Exception:
            continue

    # Expand unknown symptoms with related symptoms (best-effort, read-only HF)
    # We use the *raw phrase* when possible for better prompts.
    for tok in unknown_symptoms[:6]:
        try:
            # Find the human phrase corresponding to this token (if present)
            phrase = None
            for ph in extracted_phrases:
                # normalize_phrase is in nlp_engine; compare underscore form
                from utils.symptom_db import phrase_to_token

                if phrase_to_token(ph) == tok:
                    phrase = ph
                    break
            phrase = phrase or tok.replace("_", " ")
            rel = expand_related_online(phrase, limit=8)
            if rel:
                if upsert_related(phrase, rel, source="learned"):
                    print("Expanded symptom relationships:", phrase, "->", rel)
                    messages.append(f"Expanded symptom relationships for '{phrase}'")
                    # also ensure related symptoms exist as entries
                    for r in rel:
                        try:
                            add_symptom(r, source="learned")
                        except Exception:
                            pass
        except Exception:
            continue

    # Known symptoms for ML feature vector are the ones present in our symptom dictionary.
    # (Everything else is still preserved and used to force online search.)
    try:
        from utils.nlp_engine import _known_symptom_keys  # type: ignore

        known_keys = _known_symptom_keys()
        extracted_symptoms = [s for s in normalized_symptoms if s in known_keys]
    except Exception:
        extracted_symptoms = []
    
    # Format vitals & history (kept for ML model feature vector)
    input_data = {
        "vitals": request.vitals.model_dump() if request.vitals else {},
        "history": request.history
    }
    
    # 3. Convert to feature vector mapped matching trained model footprint
    feature_vector = create_feature_vector(input_data, extracted_symptoms=extracted_symptoms)

    # 3b. Feature length stability: pad/truncate to model's expected size
    try:
        expected = int(getattr(model, "n_features_in_", len(feature_vector)))
    except Exception:
        expected = len(feature_vector)
    if len(feature_vector) != expected:
        if len(feature_vector) < expected:
            feature_vector = feature_vector + [0] * (expected - len(feature_vector))
        else:
            feature_vector = feature_vector[:expected]
    
    # 4. Predict probabilities Using Model (ML live predictions)
    try:
        feature_names = get_feature_names()
        if feature_names and len(feature_names) == len(feature_vector):
            import pandas as pd

            X = pd.DataFrame([feature_vector], columns=feature_names)
            probs = model.predict_proba(X)[0]
        else:
            probs = model.predict_proba([feature_vector])[0]
    except Exception:
        probs = model.predict_proba([feature_vector])[0]
    
    classes = label_encoder.classes_
    disease_probs = list(zip(classes, probs))
    
    # Sort descending based on probability
    disease_probs.sort(key=lambda x: x[1], reverse=True)
    
    # Goal constraint: Never return 1, always return 5-10
    top_n = min(len(disease_probs), 10)
    
    predictions = []
    for d_name, d_prob in disease_probs[:top_n]:
        predictions.append({"name": str(d_name), "confidence": round(float(d_prob), 4)})

    # Ensure minimum of 5 outputs even if the model has fewer classes
    while len(predictions) < 5:
        predictions.append({"name": "Other/Unknown", "confidence": 0.0})

    # ---- v2 Stable system ----
    # Use extracted symptom phrases (cleaned) for VERIFIED matching.
    user_symptoms_phrases = clean_symptoms(extracted_phrases)

    verified_matches_all = match_verified(user_symptoms_phrases)[:10]
    verified_matches = [m for m in verified_matches_all if float(m.get("confidence", 0.0)) >= 0.5]
    best_conf = float(verified_matches[0]["confidence"]) if verified_matches else 0.0
    confidence_level = "high" if best_conf >= 0.7 else ("medium" if best_conf >= 0.5 else "low")

    used_database = len(verified_matches) > 0
    searched_online = False
    used_learned_data = used_database
    search_state = "done"

    fetched: list[dict[str, Any]] = []
    promoted: list[str] = []

    if used_database:
        messages.append("Showing verified medical matches")

    # Compulsory learning on every request (background; does NOT block UI)
    # This continuously improves raw/verified DB without making the frontend wait.
    from utils.learning_jobs import create_job
    from utils.background_learning import run_learning_job

    job = create_job()
    candidates_for_job: list[str] | None = None
    low_conf = best_conf < 0.5
    searched_online = True
    search_state = "searching"
    messages.append("Learning from external sources... (running in background)")

    # Response lists
    # Primary: verified DB matches. If none, fall back to live ML predictions.
    predictions_objects: list[DiseasePrediction] = []
    if verified_matches:
        predictions_objects = [
            DiseasePrediction(
                name=str(m["name"]),
                confidence=float(m["confidence"]),
                source="verified",
            )
            for m in verified_matches
        ]
    else:
        # Use ML model probabilities as suggestions when DB has no strong match.
        predictions_objects = [
            DiseasePrediction(
                name=str(p["name"]),
                confidence=float(p["confidence"]),
                source="ml",
            )
            for p in predictions
        ]
    # If nothing verified matches, still show RAW suggestions so the UI isn't empty.
    online_objects: list[DiseasePrediction] = []
    external_suggestions: list[str] = []
    if not predictions_objects and user_symptoms_phrases:
        raw_suggestions = [r for r in match_raw(user_symptoms_phrases) if float(r.get("confidence", 0.0)) > 0.0][:5]
        online_objects = [
            DiseasePrediction(
                name=str(r.get("name")),
                confidence=float(r.get("confidence", 0.0)),
                source="unverified",
            )
            for r in raw_suggestions
            if r.get("name")
        ]
        external_suggestions = [o.name for o in online_objects]
        if online_objects:
            messages.append("No verified matches yet. Showing learned suggestions while learning continues.")
            # Ensure we still return 5 results by topping up with Gemini/Online candidates.
            if len(online_objects) < 5:
                try:
                    need = 5 - len(online_objects)
                    extra_online: list[str] = []
                    from utils.pubtator_client import search_pmids, fetch_biocjson
                    from utils.pubtator_client import _extract_diseases_from_bioc  # type: ignore
                    from utils.online_search import fetch_candidate_diseases

                    # PubTator candidate discovery first
                    pmids = search_pmids(", ".join(user_symptoms_phrases), limit=5)
                    docs = fetch_biocjson(pmids, full=False) if pmids else []
                    extra_pub = _extract_diseases_from_bioc(docs) if docs else []
                    extra_online = extra_pub or (fetch_candidate_diseases(normalized_symptoms, limit=12) or [])
                    existing = {o.name.lower() for o in online_objects if o.name}
                    picked_online: list[str] = []
                    for n in extra_online:
                        nn = str(n or "").strip()
                        if not nn:
                            continue
                        if nn.lower() in existing or nn.lower() in {p.lower() for p in picked_online}:
                            continue
                        picked_online.append(nn)
                        if len(picked_online) >= need:
                            break
                    for n in picked_online:
                        online_objects.append(
                            DiseasePrediction(
                                name=n,
                                confidence=0.0,
                                source="pubtator_candidate",
                            )
                        )
                    external_suggestions = [o.name for o in online_objects]
                except Exception:
                    pass
        else:
            # If RAW overlap is 0, show real online candidate diseases (stage-1) so results aren't "fixed".
            try:
                candidates: list[str] = []
                candidates_source = "online_candidate"
                # Prefer PubTator candidate discovery
                from utils.pubtator_client import search_pmids, fetch_biocjson
                from utils.pubtator_client import _extract_diseases_from_bioc  # type: ignore

                pmids = search_pmids(", ".join(user_symptoms_phrases), limit=6)
                docs = fetch_biocjson(pmids, full=False) if pmids else []
                candidates = _extract_diseases_from_bioc(docs) if docs else []
                if candidates:
                    messages.append("PubTator candidate discovery: ok")
                    candidates_source = "pubtator_candidate"
                else:
                    from utils.online_search import fetch_candidate_diseases

                    candidates = fetch_candidate_diseases(normalized_symptoms, limit=12)
                    candidates_source = "online_candidate"
            except Exception:
                candidates = []
            if candidates:
                # Ensure we return exactly 5 (fill with HF candidates if Gemini returned fewer).
                uniq: list[str] = []
                for n in candidates:
                    nn = str(n or "").strip()
                    if not nn:
                        continue
                    if nn.lower() not in {u.lower() for u in uniq}:
                        uniq.append(nn)
                    if len(uniq) >= 5:
                        break
                if len(uniq) < 5:
                    try:
                        from utils.online_search import fetch_candidate_diseases

                        extra = fetch_candidate_diseases(normalized_symptoms, limit=12) or []
                        for n in extra:
                            nn = str(n or "").strip()
                            if not nn:
                                continue
                            if nn.lower() not in {u.lower() for u in uniq}:
                                uniq.append(nn)
                            if len(uniq) >= 5:
                                break
                    except Exception:
                        pass

                online_objects = [DiseasePrediction(name=n, confidence=0.0, source=candidates_source) for n in uniq[:5]]
                external_suggestions = [o.name for o in online_objects]
                messages.append("Showing PubTator candidate diseases (symptom-related)." if candidates_source == "pubtator_candidate" else ("Low confidence. Enhancing results using online sources..." if low_conf else "Showing online candidate diseases (symptom-related)."))
                messages.append("Learning new diseases and storing symptoms in background.")
                candidates_for_job = [o.name for o in online_objects]

    # Start learning job once (prefer enriching displayed candidates)
    if online_objects and not candidates_for_job:
        # If we displayed any external results, enrich those exact names in background.
        candidates_for_job = [o.name for o in online_objects if o.name]
    background_tasks.add_task(
        run_learning_job,
        job.id,
        normalized_symptoms=normalized_symptoms,
        user_phrases=user_symptoms_phrases,
        candidate_diseases=candidates_for_job,
        low_confidence=low_conf,
    )
        
    return PredictionResponse(
        symptoms_detected=user_symptoms_phrases,
        unknown_symptoms=unknown_symptoms,
        extracted_phrases=extracted_phrases,
        diseases=predictions_objects,
        online_results=online_objects,
        external_suggestions=external_suggestions,
        status=StatusModel(
            used_database=used_database,
            searched_online=searched_online,
            used_learned_data=used_learned_data,
            confidence_level=confidence_level,
        ),
        messages=messages,
        additional_insights=[],
        note="This is an assistive prediction system, not a medical diagnosis.",
        search_state=search_state,
        learning_job_id=job.id,
    )


@app.get("/learning/status/{job_id}")
def learning_status(job_id: str):
    from utils.learning_jobs import get_job

    j = get_job(job_id)
    if not j:
        return {"status": "missing"}
    return {
        "id": j.id,
        "status": j.status,
        "message": j.message,
        "progress": j.progress,
        "result": j.result,
        "created_at": j.created_at,
    }


@app.get("/meta")
async def meta():
    """
    Self-verification endpoint to ensure the running server is the updated build.
    Safe to expose locally; contains no secrets.
    """
    try:
        main_path = Path(__file__).resolve()
        fields = []
        try:
            fields = list(PredictionResponse.model_fields.keys())  # pydantic v2
        except Exception:
            fields = list(getattr(PredictionResponse, "__fields__", {}).keys())  # pydantic v1 fallback

        return {
            "module": str(main_path),
            "mtime": main_path.stat().st_mtime,
            "hostname": socket.gethostname(),
            "prediction_response_fields": fields,
        }
    except Exception:
        return {"module": "unknown", "prediction_response_fields": []}

# Health check endpoint
@app.get("/health")
async def health_check():
    # Stable health endpoint (must never crash)
    hf_configured = bool(get_env("HF_API_KEY"))

    # Model status
    model_loaded = bool(model is not None and label_encoder is not None)
    if label_encoder is not None and hasattr(label_encoder, "classes_"):
        try:
            model_classes = int(len(getattr(label_encoder, "classes_")))
        except Exception:
            model_classes = 0
    else:
        model_classes = 0
    try:
        model_features = int(getattr(model, "n_features_in_", 0)) if model is not None else 0
    except Exception:
        model_features = 0

    # DB counts
    verified_count = 0
    raw_count = 0
    symptom_db_count = 0
    try:
        from utils.disease_store_v2 import load_raw, load_verified

        verified_count = len(load_verified())
        raw_count = len(load_raw())
    except Exception:
        verified_count = 0
        raw_count = 0

    try:
        from utils.symptom_db import load_symptom_db

        symptom_db_count = len(load_symptom_db())
    except Exception:
        symptom_db_count = 0

    return {
        "status": "healthy",
        "model_loaded": model_loaded,
        "model_classes": model_classes,
        "model_features": model_features,
        "verified_diseases": verified_count,
        "raw_diseases": raw_count,
        "symptom_db_count": symptom_db_count,
        "optional_ai_configured": hf_configured,
    }

# Get disease trends
@app.get("/trends")
async def get_trends():
    trends_note = get_disease_trends()
    return {"trends": trends_note}

# Manual internet check
@app.post("/admin/check-internet")
async def manual_internet_check():
    try:
        checker = InternetDiseaseChecker()
        new_diseases = checker.perform_internet_check()

        if new_diseases:
            # Retrain model
            trainer = DynamicModelTrainer()
            trainer.train_model()

        return {
            "new_diseases_found": len(new_diseases),
            "diseases": new_diseases,
            "model_retrained": len(new_diseases) > 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internet check failed: {str(e)}")


@app.post("/admin/train")
async def admin_train(background_tasks: BackgroundTasks):
    """
    Train a real ML model from:
    - data/dataset.csv (supervised dataset)
    - data/verified_disease_db.json (continuously learned verified labels)

    Runs in background and writes artifacts to model/ and reports/.
    """
    from utils.learning_jobs import create_job, finish_job, update_job

    job = create_job()

    def _run() -> None:
        try:
            update_job(job.id, status="running", message="Training model...", progress=0.1)
            res = train_and_save()
            update_job(job.id, progress=0.9, message="Saving artifacts...")
            finish_job(
                job.id,
                status="done",
                message="Training complete",
                result={"metrics": res.metrics, "report_path": res.report_path},
            )
        except Exception as e:
            finish_job(job.id, status="error", message=str(e)[:200], result={})

    background_tasks.add_task(_run)
    return {"training_job_id": job.id}

# Get all diseases in database
@app.get("/diseases")
async def get_all_diseases():
    try:
        db = DiseaseDatabase()
        diseases = db.get_all_diseases()
        return {"diseases": diseases, "count": len(diseases)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@app.get("/learned")
async def get_learned():
    """
    Inspect controlled learned patterns (unverified) for verification/debugging.
    """
    try:
        # Return a lightweight view; never errors hard.
        from utils.learning_store import _load_root  # type: ignore

        root = _load_root()
        patterns = root.get("patterns", []) or []
        return {"count": len(patterns), "patterns": patterns[-50:]}  # last 50
    except Exception:
        return {"count": 0, "patterns": []}

# Add user-reported disease
@app.post("/user-report")
async def add_user_disease(request: UserReportRequest):
    try:
        db = DiseaseDatabase()
        disease_id = db.add_disease(
            name=request.name,
            symptoms=request.symptoms,
            description=request.description,
            source='user_input',
            confidence=0.0  # User reports start with zero confidence
        )

        # Retrain model with new data
        trainer = DynamicModelTrainer()
        trainer.train_model()

        return {
            "message": f"Disease '{request.name}' added successfully",
            "id": disease_id,
            "model_updated": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add disease: {str(e)}")

# Get similar diseases
@app.post("/similar-diseases")
async def find_similar_diseases(request: SimilarDiseasesRequest):
    try:
        db = DiseaseDatabase()
        similar = db.search_similar_diseases(request.symptoms, threshold=0.1)
        return {"similar_diseases": similar}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similarity search failed: {str(e)}")

# Serve the HTML UI
@app.get("/")
async def serve_ui():
    html_path = str(PROJECT_ROOT / "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    return {"error": "UI not found"}

# Serve admin panel
@app.get("/admin")
async def serve_admin():
    html_path = str(PROJECT_ROOT / "admin.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    return {"error": "Admin panel not found"}

if __name__ == "__main__":
    print("Run using: uvicorn main:app --reload")