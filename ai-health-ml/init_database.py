import pandas as pd
import json
from utils.disease_database import DiseaseDatabase

def initialize_database_from_csv():
    """Initialize the database with data from the original CSV"""
    print("Initializing database from CSV...")

    # Load CSV
    df = pd.read_csv('data/dataset.csv')

    # Load symptom list
    with open('data/symptom_list.json', 'r') as f:
        symptom_map = json.load(f)

    db = DiseaseDatabase()

    # Process each disease in the CSV
    diseases_added = 0

    for _, row in df.iterrows():
        disease_name = row['disease']

        # Extract symptoms (columns that are 1)
        symptoms = []
        for col in df.columns:
            if col != 'disease' and row[col] == 1:
                symptoms.append(col)

        # Add to database
        try:
            db.add_disease(
                name=disease_name,
                symptoms=symptoms,
                description=f"Imported from original dataset",
                source='original',
                confidence=0.8  # High confidence for original data
            )
            diseases_added += 1
        except Exception as e:
            print(f"Failed to add {disease_name}: {e}")

    print(f"Added {diseases_added} diseases from CSV")

    # Verify
    all_diseases = db.get_all_diseases()
    print(f"Total diseases in database: {len(all_diseases)}")

    return diseases_added

if __name__ == "__main__":
    initialize_database_from_csv()
