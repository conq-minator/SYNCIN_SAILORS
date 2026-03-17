from fastapi.testclient import TestClient
from main import app
import json

client = TestClient(app)

def test_predict_endpoint():
    payload = {
        "text": "I have fever and cough",
        "vitals": {
            "blood_sugar": 150,
            "bp": "140/90"
        },
        "history": ["diabetes"],
    }

    print("Sending payload:")
    print(json.dumps(payload, indent=2))
    
    response = client.post("/ml/predict", json=payload)
    
    print("\nResponse status:", response.status_code)
    try:
        data = response.json()
        print("Response JSON:")
        print(json.dumps(data, indent=2))
        
        assert "diseases" in data
        assert len(data["diseases"]) >= 5
        assert "symptoms_detected" in data
        assert "additional_insights" in data
        print("\nTest passed successfully: Response contains 5-10 predictions.")
    except Exception as e:
        print("\nTest failed or response format is incorrect:")
        print(response.text)
        print("Error:", str(e))

if __name__ == "__main__":
    test_predict_endpoint()
