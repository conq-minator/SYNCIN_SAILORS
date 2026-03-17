import sqlite3
import os
from datetime import datetime
import json

class DiseaseDatabase:
    def __init__(self, db_path='data/diseases.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Diseases table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS diseases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    symptoms TEXT,  -- JSON array of symptoms
                    source TEXT,    -- 'original', 'internet', 'user_input'
                    confidence REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Symptoms table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS symptoms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    synonyms TEXT,  -- JSON array of synonyms
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Disease-Symptom relationships
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS disease_symptoms (
                    disease_id INTEGER,
                    symptom_id INTEGER,
                    weight REAL DEFAULT 1.0,  -- Importance weight
                    FOREIGN KEY (disease_id) REFERENCES diseases (id),
                    FOREIGN KEY (symptom_id) REFERENCES symptoms (id),
                    PRIMARY KEY (disease_id, symptom_id)
                )
            ''')

            # Model versions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    accuracy REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    dataset_size INTEGER
                )
            ''')

            conn.commit()

    def add_disease(self, name, symptoms, description='', source='internet', confidence=0.0):
        """Add a new disease to the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Insert or replace disease
            cursor.execute('''
                INSERT OR REPLACE INTO diseases (name, description, symptoms, source, confidence, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, description, json.dumps(symptoms), source, confidence, datetime.now()))

            disease_id = cursor.lastrowid

            # Add symptoms if they don't exist
            for symptom in symptoms:
                cursor.execute('INSERT OR IGNORE INTO symptoms (name) VALUES (?)', (symptom,))

                # Get symptom id
                cursor.execute('SELECT id FROM symptoms WHERE name = ?', (symptom,))
                symptom_id = cursor.fetchone()[0]

                # Link disease to symptom
                cursor.execute('''
                    INSERT OR REPLACE INTO disease_symptoms (disease_id, symptom_id)
                    VALUES (?, ?)
                ''', (disease_id, symptom_id))

            conn.commit()
            return disease_id

    def get_all_diseases(self):
        """Get all diseases with their symptoms"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT d.id, d.name, d.description, d.symptoms, d.source, d.confidence,
                       GROUP_CONCAT(s.name) as symptom_list
                FROM diseases d
                LEFT JOIN disease_symptoms ds ON d.id = ds.disease_id
                LEFT JOIN symptoms s ON ds.symptom_id = s.id
                GROUP BY d.id
            ''')

            diseases = []
            for row in cursor.fetchall():
                diseases.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'symptoms': json.loads(row[3]) if row[3] else [],
                    'source': row[4],
                    'confidence': row[5],
                    'symptom_list': row[6].split(',') if row[6] else []
                })

            return diseases

    def search_similar_diseases(self, symptoms, threshold=0.3):
        """Find diseases with similar symptoms"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            diseases = self.get_all_diseases()
            matches = []

            for disease in diseases:
                disease_symptoms = set(disease['symptoms'])
                input_symptoms = set(symptoms)

                if not disease_symptoms:
                    continue

                # Calculate Jaccard similarity
                intersection = len(disease_symptoms & input_symptoms)
                union = len(disease_symptoms | input_symptoms)

                if union > 0:
                    similarity = intersection / union
                    if similarity >= threshold:
                        matches.append({
                            'disease': disease,
                            'similarity': similarity,
                            'matching_symptoms': list(disease_symptoms & input_symptoms)
                        })

            return sorted(matches, key=lambda x: x['similarity'], reverse=True)

    def update_disease_confidence(self, disease_name, new_confidence):
        """Update disease confidence score"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE diseases
                SET confidence = ?, updated_at = ?
                WHERE name = ?
            ''', (new_confidence, datetime.now(), disease_name))
            conn.commit()

    def get_recent_diseases(self, days=7):
        """Get diseases added in the last N days"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM diseases
                WHERE created_at >= datetime('now', '-{} days')
                ORDER BY created_at DESC
            '''.format(days))
            return cursor.fetchall()

# Initialize database
if __name__ == "__main__":
    db = DiseaseDatabase()
    print("Disease database initialized successfully!")
