from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from utils.config import DATA_DIR, MODEL_DIR, PROJECT_ROOT
from utils.symptom_cleaner import clean_symptoms


@dataclass
class TrainResult:
    model_path: str
    encoder_path: str
    feature_names_path: str
    report_path: str
    metrics: dict[str, Any]


def _load_dataset() -> pd.DataFrame:
    path = DATA_DIR / "dataset.csv"
    return pd.read_csv(path)


def _load_verified_as_rows(feature_names: list[str]) -> list[dict[str, Any]]:
    """
    Convert verified_disease_db.json into additional supervised rows.
    This makes the system a real continuous-learning ML system:
    verified DB becomes new training data.
    """
    vpath = DATA_DIR / "verified_disease_db.json"
    if not vpath.exists():
        return []
    try:
        raw = json.loads(vpath.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []

    rows: list[dict[str, Any]] = []
    for it in raw:
        if not isinstance(it, dict):
            continue
        disease = str(it.get("disease", "")).strip()
        sx = it.get("symptoms", [])
        if not disease or not isinstance(sx, list):
            continue
        sx_clean = clean_symptoms(sx)
        if len(sx_clean) < 3:
            continue
        row = {f: 0 for f in feature_names}
        # Mark any symptom that exists as a feature
        for s in sx_clean:
            token = str(s).strip().lower().replace(" ", "_")
            if token in row:
                row[token] = 1
        row["disease"] = disease
        rows.append(row)
    return rows


def train_and_save(*, test_size: float = 0.2, random_state: int = 42) -> TrainResult:
    """
    Train disease classifier using:
    - original dataset.csv
    - plus verified_disease_db.json as extra supervised rows
    Saves:
    - model/model.pkl
    - model/label_encoder.pkl
    - model/feature_names.pkl
    - reports/train_report.json
    """
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "reports").mkdir(parents=True, exist_ok=True)

    df = _load_dataset()
    if "disease" not in df.columns:
        raise ValueError("dataset.csv missing 'disease' column")

    feature_names = [c for c in df.columns if c != "disease"]
    # Extend with any missing features present in verified db (as underscore tokens)
    # but only if they already exist in dataset feature space, to keep compatibility.

    # Add verified DB rows (continuous learning)
    extra_rows = _load_verified_as_rows(feature_names)
    if extra_rows:
        df_extra = pd.DataFrame(extra_rows)
        df = pd.concat([df, df_extra], ignore_index=True)

    X = df[feature_names].astype(int)
    y_raw = df["disease"].astype(str)

    le = LabelEncoder()
    y = le.fit_transform(y_raw)

    # Stratified split only works when every class has >= 2 samples.
    stratify = None
    try:
        vc = pd.Series(y).value_counts()
        if len(vc) > 1 and int(vc.min()) >= 2:
            stratify = y
    except Exception:
        stratify = None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify
    )

    model = RandomForestClassifier(
        n_estimators=350,
        random_state=random_state,
        class_weight="balanced_subsample",
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = float(accuracy_score(y_test, y_pred))

    labels = list(range(len(le.classes_)))
    report = classification_report(
        y_test,
        y_pred,
        labels=labels,
        target_names=list(le.classes_),
        output_dict=True,
        zero_division=0,
    )
    metrics = {
        "accuracy": acc,
        "n_rows": int(len(df)),
        "n_features": int(len(feature_names)),
        "n_classes": int(len(le.classes_)),
        "trained_at": time.time(),
        "extra_verified_rows": int(len(extra_rows)),
    }

    # Save artifacts (overwrite current)
    model_path = str(MODEL_DIR / "model.pkl")
    enc_path = str(MODEL_DIR / "label_encoder.pkl")
    fn_path = str(MODEL_DIR / "feature_names.pkl")
    joblib.dump(model, model_path)
    joblib.dump(le, enc_path)
    joblib.dump(feature_names, fn_path)

    report_path = str((PROJECT_ROOT / "reports" / "train_report.json"))
    Path(report_path).write_text(json.dumps({"metrics": metrics, "report": report}, indent=2), encoding="utf-8")

    return TrainResult(
        model_path=model_path,
        encoder_path=enc_path,
        feature_names_path=fn_path,
        report_path=report_path,
        metrics=metrics,
    )

