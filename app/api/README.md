# CS2 Round Winner Predictor API

FastAPI application that predicts the winner of CS2 (Counter-Strike 2) rounds based on team composition and equipment values.

## Features

- 🎯 **Round Winner Prediction**: Predicts whether CT or TERRORIST team will win
- 📊 **Probability Scores**: Returns confidence scores for each outcome
- 🔄 **Player Encoding**: Handles player identification with intelligent encoding
- 📈 **Equipment Analysis**: Considers team equipment values in predictions
- 🏥 **Health Check**: Endpoint to verify model status
- 📚 **Auto Documentation**: Swagger UI and ReDoc integration

## Setup

### Prerequisites

- Python 3.12+
- FastAPI
- Uvicorn
- Joblib
- Numpy
- Pandas

### Installation

1. Install dependencies:
```bash
pip install fastapi uvicorn joblib numpy pandas
```

2. Train the model first (must be done in the notebook):
   - Run all cells in `model/before_round.ipynb`
   - This will generate:
     - `model/rf_pipeline.pkl` (trained model)
     - `model/all_players.pkl` (player mapping)

### Running the API

Start the API server:

```bash
cd /Users/computador/development/demoparser-main
python -m uvicorn app.api.app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **Main API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### 1. Health Check

```
GET /health
```

Returns:
```json
{
  "status": "ok",
  "model_loaded": true,
  "total_known_players": 1250
}
```

### 2. Root Info

```
GET /
```

Returns API information and available endpoints.

### 3. Predict Round Winner

```
POST /predict
```

**Request Body:**
```json
{
  "team_a_players": [76561198123456789, 76561198987654321],
  "team_b_players": [76561198111111111, 76561198222222222],
  "team_a_equip_value": 5000,
  "team_b_equip_value": 3500
}
```

**Response:**
```json
{
  "predicted_winner": "CT",
  "winner_probability": 0.8234,
  "ct_probability": 0.8234,
  "terrorist_probability": 0.1766,
  "confidence": 0.8234,
  "team_a_players": [76561198123456789, 76561198987654321],
  "team_b_players": [76561198111111111, 76561198222222222],
  "team_a_equip_value": 5000,
  "team_b_equip_value": 3500
}
```

## Example Usage

### Using curl:

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "team_a_players": [76561198123456789, 76561198987654321],
    "team_b_players": [76561198111111111, 76561198222222222],
    "team_a_equip_value": 5000,
    "team_b_equip_value": 3500
  }'
```

### Using Python:

```python
import requests

response = requests.post(
    "http://localhost:8000/predict",
    json={
        "team_a_players": [76561198123456789, 76561198987654321],
        "team_b_players": [76561198111111111, 76561198222222222],
        "team_a_equip_value": 5000,
        "team_b_equip_value": 3500
    }
)

print(response.json())
```

### Testing:

```bash
python app/api/test_api.py
```

## Model Details

- **Algorithm**: Random Forest Classifier (100 estimators)
- **Features**: 
  - Team A equipment value
  - Team B equipment value
  - Player encoding (0=absent, 1=team A, 2=team B)
- **Training Data**: CS2 demo files with round outcomes
- **Accuracy**: ~97.2% on test set

## Error Handling

The API handles various error cases:

- **400**: Invalid input (missing players, negative equipment values)
- **422**: Validation error (incorrect data types)
- **500**: Server error during prediction

## Performance

- Prediction time: < 10ms per request
- Model size: ~2-5MB
- Memory usage: ~50-100MB

## Notes

- Player IDs should be valid Steam IDs (76561198xxxxxxxxxx format recommended)
- Equipment values should be realistic (0-16000 for CS2)
- At least 1 player per team is required
- Unknown players are safely handled (ignored in encoding)

## File Structure

```
app/
├── api/
│   ├── __init__.py
│   ├── app.py              # Main API application
│   ├── test_api.py         # Test script
│   └── README.md           # This file
└── ...

model/
├── before_round.ipynb      # Training notebook
├── rf_pipeline.pkl         # Trained model (generated after training)
└── all_players.pkl         # Player mapping (generated after training)
```

## Troubleshooting

**Error: "Model files not found"**
- Make sure you've run the training notebook (`model/before_round.ipynb`)
- Verify `rf_pipeline.pkl` and `all_players.pkl` exist in the `model/` directory

**Error: "Port 8000 already in use"**
- Use a different port: `uvicorn app.api.app:app --port 8001`

**ImportError: "No module named 'fastapi'"**
- Install dependencies: `pip install fastapi uvicorn`

## Future Improvements

- [ ] Add batch prediction endpoint
- [ ] Add model retraining endpoint
- [ ] Add prediction explanation (SHAP values)
- [ ] Add caching for repeated predictions
- [ ] Add rate limiting
- [ ] Add authentication/API keys
- [ ] Add logging and monitoring
