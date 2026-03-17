import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
from datetime import datetime
import json
from utils.disease_database import DiseaseDatabase
from utils.config import MODEL_DIR
import sqlite3

class DynamicModelTrainer:
    def __init__(self):
        self.db = DiseaseDatabase()
        self.model_path = str(MODEL_DIR / "model.pkl")
        self.encoder_path = str(MODEL_DIR / "label_encoder.pkl")
        self.features_path = str(MODEL_DIR / "feature_names.pkl")

    def generate_training_data_from_db(self):
        """Generate training data from database"""
        diseases = self.db.get_all_diseases()

        if not diseases:
            print("No diseases in database")
            return None

        # Use the exact same features as the original model
        all_features = [
            'fever', 'cough', 'fatigue', 'difficulty_breathing', 'headache', 'nausea', 'vomiting',
            'diarrhea', 'chest_pain', 'dizziness', 'weight_loss', 'increased_thirst', 'frequent_urination',
            'blurred_vision', 'feeling_sad', 'loss_of_interest', 'high_blood_sugar', 'high_blood_pressure',
            'history_diabetes', 'history_hypertension', 'history_depression', 'history_asthma', 'history_heart_disease'
        ]

        # Generate training samples - one per disease for now
        training_data = []

        for disease in diseases:
            # Create positive sample
            sample = {feature: 0 for feature in all_features}
            for symptom in disease['symptoms']:
                if symptom in sample:
                    sample[symptom] = 1

            training_data.append({
                'features': sample,
                'disease': disease['name'],
                'source': disease['source']
            })

        return training_data, all_features

    def train_model(self, force_retrain=False):
        """Train or retrain the model with current database data"""
        try:
            # Check if we need to retrain
            if not force_retrain and os.path.exists(self.model_path):
                # Check if database has been updated recently
                recent_diseases = self.db.get_recent_diseases(days=1)
                if not recent_diseases:
                    print("No recent database changes, skipping retrain")
                    return False

            print("Generating training data from database...")
            training_result = self.generate_training_data_from_db()

            if not training_result:
                print("No training data available")
                return False

            training_data, feature_names = training_result

            if len(training_data) < 10:
                print(f"Insufficient training data: {len(training_data)} samples")
                return False

            print(f"Training with {len(training_data)} samples and {len(feature_names)} features")

            # Convert to DataFrame
            df_data = []
            for item in training_data:
                row = item['features'].copy()
                row['disease'] = item['disease']
                df_data.append(row)

            df = pd.DataFrame(df_data)

            # Split features and target
            X = df.drop(columns=['disease'])
            y = df['disease']

            # Ensure we have enough samples per class
            class_counts = y.value_counts()
            min_samples = class_counts.min()

            if min_samples < 2:
                print("Warning: Some classes have very few samples, model may not generalize well")

            # Encode labels
            label_encoder = LabelEncoder()
            y_encoded = label_encoder.fit_transform(y)

            # Split data - handle small datasets
            if len(X) < 10:
                print("Very small dataset, using all data for training")
                X_train, X_test = X, X
                y_train, y_test = y_encoded, y_encoded
            else:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y_encoded, test_size=0.2, random_state=42
                )

            # Train model
            print("Training RandomForestClassifier...")
            clf = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                class_weight='balanced'  # Handle imbalanced classes
            )
            clf.fit(X_train, y_train)

            # Evaluate
            train_accuracy = clf.score(X_train, y_train)
            test_accuracy = clf.score(X_test, y_test)

            print(f"Train accuracy: {train_accuracy:.4f}")
            print(f"Test accuracy:  {test_accuracy:.4f}")

            # Save model and metadata
            os.makedirs(str(MODEL_DIR), exist_ok=True)

            joblib.dump(clf, self.model_path)
            joblib.dump(label_encoder, self.encoder_path)
            joblib.dump(feature_names, self.features_path)

            # Save model version info
            self.save_model_version(test_accuracy, len(training_data))

            print("Model retrained and saved successfully!")
            return True

        except Exception as e:
            print(f"Model training failed: {e}")
            return False

    def save_model_version(self, accuracy, dataset_size):
        """Save model version information"""
        try:
            version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO model_versions (version, accuracy, dataset_size)
                    VALUES (?, ?, ?)
                    """,
                    (version, float(accuracy), int(dataset_size)),
                )
                conn.commit()
        except Exception as e:
            print(f"Failed to save model version: {e}")

    def get_model_stats(self):
        """Get current model statistics"""
        try:
            if not os.path.exists(self.model_path):
                return None

            model = joblib.load(self.model_path)
            encoder = joblib.load(self.encoder_path)
            features = joblib.load(self.features_path)

            return {
                'n_features': len(features),
                'n_classes': len(encoder.classes_),
                'classes': list(encoder.classes_),
                'feature_names': features
            }
        except Exception as e:
            print(f"Failed to load model stats: {e}")
            return None

    def predict_with_confidence(self, feature_vector):
        """Make prediction with confidence scores"""
        try:
            model = joblib.load(self.model_path)
            encoder = joblib.load(self.encoder_path)

            # Ensure feature vector matches expected features
            features = joblib.load(self.features_path)
            vector_dict = {f: 0 for f in features}

            # Update with provided features
            for feature, value in feature_vector.items():
                if feature in vector_dict:
                    vector_dict[feature] = value

            # Convert to array
            X = np.array([list(vector_dict.values())])

            # Get predictions
            probs = model.predict_proba(X)[0]
            classes = encoder.classes_

            # Return top predictions
            predictions = []
            for i, prob in enumerate(probs):
                predictions.append({
                    'disease': classes[i],
                    'confidence': float(prob)
                })

            # Sort by confidence
            predictions.sort(key=lambda x: x['confidence'], reverse=True)

            return predictions[:10]  # Return top 10

        except Exception as e:
            print(f"Prediction failed: {e}")
            return []

# Initialize trainer
if __name__ == "__main__":
    trainer = DynamicModelTrainer()
    success = trainer.train_model(force_retrain=True)
    if success:
        stats = trainer.get_model_stats()
        print(f"Model stats: {stats}")
    else:
        print("Model training failed")
