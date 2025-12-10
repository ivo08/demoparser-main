from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import joblib
import numpy as np
import pandas as pd
import os

app = FastAPI(
    title="CS2 Round Winner Predictor API",
    description="Predicts the winner of CS2 rounds based on team composition and equipment values",
    version="1.0.0"
)

# Load model and player mapping
MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../model/round_winner_model.pkl")
PLAYERS_PATH = os.path.join(os.path.dirname(__file__), "../../model/all_players.pkl")

try:
    rf_pipeline = joblib.load(MODEL_PATH)
    all_players = joblib.load(PLAYERS_PATH)
except FileNotFoundError as e:
    raise RuntimeError(f"Model files not found. Please train the model first. Error: {e}")


# Pydantic models for request/response
class RoundPredictionRequest(BaseModel):
    """Request model for round winner prediction"""
    team_ct_players: list[int]  # List of player IDs in team A (CT)
    team_t_players: list[int]  # List of player IDs in team B (TERRORIST)
    team_ct_equip_value: int    # Total equipment value for team A
    team_t_equip_value: int    # Total equipment value for team B

    class Config:
        json_schema_extra = {
            "example": {
                "team_ct_players": [76561198123456789, 76561198987654321],
                "team_t_players": [76561198111111111, 76561198222222222],
                "team_ct_equip_value": 5000,
                "team_t_equip_value": 3500
            }
        }


class RoundPredictionResponse(BaseModel):
    """Response model for round winner prediction"""
    predicted_winner: str       # "CT" or "TERRORIST"
    winner_probability: float   # Probability of predicted winner (0-1)
    ct_probability: float       # Probability of CT winning
    terrorist_probability: float # Probability of TERRORIST winning
    confidence: float          # Confidence score
    team_a_players: list[int]
    team_b_players: list[int]
    team_a_equip_value: int
    team_b_equip_value: int


class HealthCheckResponse(BaseModel):
    """Response model for health check"""
    status: str
    model_loaded: bool
    total_known_players: int


def create_feature_vector(team_a_players, team_b_players, team_a_equip, team_b_equip):
    """
    Create feature vector for the model based on player encoding and equipment values.
    
    Player encoding:
    - 0: player not present
    - 1: player in team A (CT)
    - 2: player in team B (TERRORIST)
    """
    # Initialize encoding for all known players
    encoding = np.zeros(len(all_players), dtype=int)
    player_to_idx = {p: i for i, p in enumerate(all_players)}
    
    # Encode team A players
    for player_id in team_a_players:
        if player_id in player_to_idx:
            encoding[player_to_idx[player_id]] = 1
    
    # Encode team B players
    for player_id in team_b_players:
        if player_id in player_to_idx:
            encoding[player_to_idx[player_id]] = 2
    
    # Combine encoding with equipment values
    features = np.concatenate([
        [team_a_equip, team_b_equip],
        encoding
    ])
    
    return features.reshape(1, -1)


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Check API health and model status"""
    return HealthCheckResponse(
        status="ok",
        model_loaded=rf_pipeline is not None,
        total_known_players=len(all_players)
    )


@app.post("/predict", response_model=RoundPredictionResponse)
async def predict_round_winner(request: RoundPredictionRequest):
    """
    Predict the winner of a CS2 round.
    
    Returns:
    - predicted_winner: "CT" or "TERRORIST"
    - winner_probability: Confidence in the prediction
    - ct_probability: Probability of CT winning
    - terrorist_probability: Probability of TERRORIST winning
    """
    try:
        # Validate input
        if not request.team_a_players or not request.team_b_players:
            raise HTTPException(
                status_code=400,
                detail="Both teams must have at least one player"
            )
        
        if request.team_a_equip_value < 0 or request.team_b_equip_value < 0:
            raise HTTPException(
                status_code=400,
                detail="Equipment values cannot be negative"
            )
        
        # Create feature vector
        X = create_feature_vector(
            request.team_a_players,
            request.team_b_players,
            request.team_a_equip_value,
            request.team_b_equip_value
        )
        
        # Make prediction
        prediction = rf_pipeline.predict(X)[0]
        probabilities = rf_pipeline.predict_proba(X)[0]
        
        # Map prediction to team name
        winner_map = {1: "CT", 2: "TERRORIST"}
        predicted_winner = winner_map.get(prediction, "UNKNOWN")
        
        # Get probabilities for each team
        ct_prob = probabilities[0] if prediction == 1 else probabilities[1]
        terrorist_prob = probabilities[1] if prediction == 1 else probabilities[0]
        winner_prob = max(probabilities)
        
        return RoundPredictionResponse(
            predicted_winner=predicted_winner,
            winner_probability=round(float(winner_prob), 4),
            ct_probability=round(float(ct_prob), 4),
            terrorist_probability=round(float(terrorist_prob), 4),
            confidence=round(float(winner_prob), 4),
            team_a_players=request.team_a_players,
            team_b_players=request.team_b_players,
            team_a_equip_value=request.team_a_equip_value,
            team_b_equip_value=request.team_b_equip_value
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during prediction: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "CS2 Round Winner Predictor API",
        "endpoints": {
            "health": "/health",
            "predict": "/predict",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "usage": {
            "POST /predict": "Predict round winner based on team composition and equipment"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
