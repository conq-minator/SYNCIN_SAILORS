import pandas as pd
import numpy as np
import os
from utils.config import DATA_DIR

# Create data directory
os.makedirs(str(DATA_DIR), exist_ok=True)

# Define some base diseases and typical symptoms/features
diseases = ["Flu", "Diabetes", "Hypertension", "Depression", "COVID-19", "Asthma", "Migraine", "Gastroenteritis", "Common Cold", "Heart Disease"]

# List of symptoms (binary)
symptoms = [
    "fever", "cough", "fatigue", "difficulty_breathing",
    "headache", "nausea", "vomiting", "diarrhea",
    "chest_pain", "dizziness", "weight_loss", "increased_thirst",
    "frequent_urination", "blurred_vision", "feeling_sad", "loss_of_interest"
]

# Derived flags based on user specifications
derived_flags = ["high_blood_sugar", "high_blood_pressure"]

# History flags based on user specifications
history_flags = ["history_diabetes", "history_hypertension", "history_depression", "history_asthma", "history_heart_disease"]

columns = symptoms + derived_flags + history_flags

data = []
np.random.seed(42)

# Generate 2500 samples
for _ in range(2500):
    disease = np.random.choice(diseases)
    row = {col: 0 for col in columns}
    row["disease"] = disease
    
    # Add symptom probabilities based on disease
    if disease == "Flu" or disease == "Common Cold":
        for s in ["fever", "cough", "fatigue", "headache"]:
            if np.random.rand() > 0.2: row[s] = 1
    elif disease == "COVID-19":
        for s in ["fever", "cough", "fatigue", "difficulty_breathing"]:
            if np.random.rand() > 0.1: row[s] = 1
    elif disease == "Diabetes":
        for s in ["increased_thirst", "frequent_urination", "weight_loss", "fatigue", "blurred_vision"]:
            if np.random.rand() > 0.2: row[s] = 1
        if np.random.rand() > 0.1: row["high_blood_sugar"] = 1
        if np.random.rand() > 0.3: row["history_diabetes"] = 1
    elif disease == "Hypertension":
        for s in ["headache", "dizziness", "chest_pain"]:
            if np.random.rand() > 0.3: row[s] = 1
        if np.random.rand() > 0.05: row["high_blood_pressure"] = 1
        if np.random.rand() > 0.3: row["history_hypertension"] = 1
    elif disease == "Depression":
        for s in ["feeling_sad", "loss_of_interest", "fatigue"]:
            if np.random.rand() > 0.1: row[s] = 1
        if np.random.rand() > 0.3: row["history_depression"] = 1
    elif disease == "Asthma":
        for s in ["difficulty_breathing", "cough", "chest_pain"]:
            if np.random.rand() > 0.1: row[s] = 1
        if np.random.rand() > 0.4: row["history_asthma"] = 1
    elif disease == "Migraine":
        for s in ["headache", "nausea", "dizziness", "blurred_vision"]:
            if np.random.rand() > 0.1: row[s] = 1
    elif disease == "Gastroenteritis":
        for s in ["nausea", "vomiting", "diarrhea", "fever"]:
            if np.random.rand() > 0.1: row[s] = 1
    elif disease == "Heart Disease":
        for s in ["chest_pain", "difficulty_breathing", "fatigue", "dizziness"]:
            if np.random.rand() > 0.2: row[s] = 1
        if np.random.rand() > 0.4: row["high_blood_pressure"] = 1
        if np.random.rand() > 0.4: row["history_heart_disease"] = 1
            
    # Add random noise to simulate real-world varied symptoms
    for col in columns:
        if np.random.rand() > 0.92:
            row[col] = 1
            
    data.append(row)

df = pd.DataFrame(data)
# Shuffle rows
df = df.sample(frac=1).reset_index(drop=True)

df.to_csv(str(DATA_DIR / "dataset.csv"), index=False)
print("Successfully generated data/dataset.csv")
print("Features ordered:", columns)
