import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
from utils.config import DATA_DIR, MODEL_DIR

def main():
    print("Loading dataset...")
    data_path = DATA_DIR / "dataset.csv"
    if not data_path.exists():
        print(f"Error: {data_path} not found.")
        return

    df = pd.read_csv(str(data_path))
    
    print(f"Dataset loaded. Shape: {df.shape}")
    
    # Split features and target
    X = df.drop(columns=['disease'])
    y = df['disease']
    
    # Store feature names for reference later
    feature_names = X.columns.tolist()
    
    # Encode labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    
    print(f"Unique diseases: {len(label_encoder.classes_)}")
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)
    
    print("Training RandomForestClassifier...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    
    accuracy = clf.score(X_test, y_test)
    print(f"Model accuracy on test set: {accuracy:.4f}")
    
    # Save model, encoder, and feature names
    os.makedirs(str(MODEL_DIR), exist_ok=True)
    
    model_path = MODEL_DIR / "model.pkl"
    encoder_path = MODEL_DIR / "label_encoder.pkl"
    features_path = MODEL_DIR / "feature_names.pkl"
    
    joblib.dump(clf, str(model_path))
    joblib.dump(label_encoder, str(encoder_path))
    joblib.dump(feature_names, str(features_path))
    
    print("Saved model and encoders successfully.")
    
if __name__ == "__main__":
    main()
