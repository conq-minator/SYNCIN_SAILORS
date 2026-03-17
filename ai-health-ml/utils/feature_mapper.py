from __future__ import annotations

import json
from pathlib import Path

import joblib

from utils.config import DATA_DIR, MODEL_DIR


def load_feature_names(filepath: Path | None = None) -> list[str]:
    path = filepath or (MODEL_DIR / "feature_names.pkl")
    if path.exists():
        return joblib.load(path)
    return []


FEATURE_NAMES: list[str] = load_feature_names()

SYMPTOM_LIST_PATH = DATA_DIR / "symptom_list.json"


def load_symptoms() -> dict[str, list[str]]:
    if SYMPTOM_LIST_PATH.exists():
        return json.loads(SYMPTOM_LIST_PATH.read_text(encoding="utf-8"))
    return {}


symptom_map = load_symptoms()

def parse_bp(bp_str):
    if not bp_str:
        return 0, 0
    try:
        sys, dia = bp_str.split('/')
        return int(sys), int(dia)
    except Exception:
        return 0, 0

def create_feature_vector(input_data: dict, extracted_symptoms: list = None) -> list:
    """
    Convert structured/extracted input into ML feature vector based on EXACT trained feature names.
    This must match the feature_names.pkl exactly.
    """
    # Use the exact feature names the model was trained on
    vector_dict = {f: 0 for f in FEATURE_NAMES}
    
    # 1. Map extracted symptoms
    symptoms = extracted_symptoms if extracted_symptoms is not None else input_data.get("symptoms", [])
    
    for s in symptoms:
        # Direct mapping to feature names
        if s in vector_dict:
            vector_dict[s] = 1
            
    # 2. Map Derived Features (Vitals) - these create the duplicate entries
    vitals = input_data.get("vitals") or {}
    if vitals:
        # High sugar -> > 140
        bs = vitals.get("blood_sugar")
        if bs is not None and bs > 140:
            # Set ALL instances of high_blood_sugar
            for key in vector_dict:
                if key == "high_blood_sugar":
                    vector_dict[key] = 1
                
        # High BP -> sys > 130 or dia > 80
        bp_str = vitals.get("bp")
        if bp_str:
            sys, dia = parse_bp(bp_str)
            if sys > 130 or dia > 80:
                # Set ALL instances of high_blood_pressure
                for key in vector_dict:
                    if key == "high_blood_pressure":
                        vector_dict[key] = 1
                    
    # 3. Map History flags - these create the duplicate entries
    history = input_data.get("history", [])
    history_mappings = {
        "asthma": "history_asthma",
        "depression": "history_depression", 
        "diabetes": "history_diabetes",
        "heart disease": "history_heart_disease",
        "hypertension": "history_hypertension"
    }
    
    for h in history:
        h_lower = h.lower()
        for key, feature in history_mappings.items():
            if key in h_lower:
                # Set ALL instances of this history feature
                for dict_key in vector_dict:
                    if dict_key == feature:
                        vector_dict[dict_key] = 1
            
    # Return vector in exact order of FEATURE_NAMES
    feature_vector = [vector_dict[f] for f in FEATURE_NAMES]
    return feature_vector

def get_feature_names():
    return FEATURE_NAMES
