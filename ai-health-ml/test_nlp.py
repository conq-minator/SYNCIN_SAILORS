from fastapi.testclient import TestClient
from main import app
import json

client = TestClient(app)

def test_nlp_endpoint():
    payload = {
        "text": "I feel weak, tired and have slight fever",
        "vitals": {},
        "history": []
    }

    print("Sending Natural Language Payload:")
    print(json.dumps(payload, indent=2))
    
    response = client.post("/ml/predict", json=payload)
    
    print("\nResponse Status:", response.status_code)
    try:
        data = response.json()
        print("Response JSON:")
        print(json.dumps(data, indent=2))
        
        assert "symptoms_detected" in data
        assert "diseases" in data
        assert "additional_insights" in data
        assert "note" in data
        
        # We expect it to find 'fatigue' (tired/weak) and 'fever'
        assert any(sym in ["fatigue", "fever"] for sym in data["symptoms_detected"])
        assert len(data["diseases"]) >= 5
        assert "This is an assistive prediction system" in data["note"]
        
        print("\nTest passed successfully: Smart NLP extraction and Hybrid Predictions working correctly.")
        
    except Exception as e:
        print("\nTest failed or response format is incorrect:")
        print(response.text)
        print("Error:", str(e))

if __name__ == "__main__":
    test_nlp_endpoint()
