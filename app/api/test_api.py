"""
Test script for CS2 Round Winner Predictor API
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    return response.json()


def test_predict():
    """Test prediction endpoint"""
    print("Testing /predict endpoint...")
    
    # Example request with sample player IDs and equipment values
    payload = {
        "team_a_players": [76561198123456789, 76561198987654321],
        "team_b_players": [76561198111111111, 76561198222222222],
        "team_a_equip_value": 5000,
        "team_b_equip_value": 3500
    }
    
    response = requests.post(
        f"{BASE_URL}/predict",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    return response.json()


def test_root():
    """Test root endpoint"""
    print("Testing / endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    return response.json()


if __name__ == "__main__":
    print("=" * 60)
    print("CS2 Round Winner Predictor API - Test Suite")
    print("=" * 60 + "\n")
    
    try:
        test_root()
        test_health()
        test_predict()
        
        print("=" * 60)
        print("✓ All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        print("\nMake sure the API is running: python -m uvicorn app.api.app:app --reload")
