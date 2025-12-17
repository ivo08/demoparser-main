import os
import json
import time
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

import joblib
import numpy as np

import backend.constants as constants
import pandas as pd

# Locate model and players file relative to repo root
BASE_REPO = Path(__file__).resolve().parents[2]
MODEL_PATH = BASE_REPO / 'model' / 'round_winner_model.pkl'
MODEL_PLAYERS_PATH = BASE_REPO / 'model' / 'all_players.pkl'
PLAYERS_PATH = BASE_REPO / 'dash_project' / 'predictor' / 'data' / 'players.json'
MAPS_NAMES_PATH = BASE_REPO / 'model' / 'maps_names.pkl'
HISTORY_FILE = BASE_REPO / 'data' / 'predictions_history.json'

# Load model and players lazily
_MODEL = None
_MODEL_PLAYERS = None
_ALL_PLAYERS = None
_MAPS_NAMES = None


def _load_model():
    global _MODEL
    if not _MODEL:
        if MODEL_PATH.exists():
            _MODEL = joblib.load(MODEL_PATH)
        else:
            _MODEL = None

def _load_model_players():
    global _MODEL_PLAYERS
    if not _MODEL_PLAYERS and MODEL_PLAYERS_PATH.exists():
        with open(MODEL_PLAYERS_PATH, 'r') as f:
            _MODEL_PLAYERS = joblib.load(MODEL_PLAYERS_PATH)

def _load_players():
    global _ALL_PLAYERS
    if not _ALL_PLAYERS and PLAYERS_PATH.exists():
        with open(PLAYERS_PATH, 'r') as f:
            _ALL_PLAYERS = json.load(f)

def _load_maps_names():
    global _MAPS_NAMES
    if not _MAPS_NAMES and MAPS_NAMES_PATH.exists():
        with open(MAPS_NAMES_PATH, 'r') as f:
            _MAPS_NAMES = joblib.load(MAPS_NAMES_PATH)
            

def dashboard(request):
    # Provide weapon list and players list for initial rendering
    _load_model()
    _load_players()
    weapons = sorted(list(constants.WEAPON_VALUES.keys()))
    import json as _json
    weapon_map_json = _json.dumps(constants.WEAPON_VALUES)
    all_players_json = _json.dumps(_ALL_PLAYERS)
    # provide categorized options per player: primaries, secondaries, grenades
    primary_options = constants.WEAPON_VALUES['primary_weapons'].keys()
    secondary_options = constants.WEAPON_VALUES['secondary_weapons'].keys()
    grenade_options = constants.WEAPON_VALUES['grenades'].keys()
    equipment_options = constants.WEAPON_VALUES['equipment'].keys()
    return render(request, 'predictor/dashboard.html', context={
        'weapons': weapons,
        'all_players_json': _ALL_PLAYERS,
        'weapon_map_json': weapon_map_json,
        'player_slots': range(5),
        'primary_options': primary_options,
        'secondary_options': secondary_options,
        'grenade_options': grenade_options,
        'equipment_options': equipment_options,
    })


def _ensure_history_dir():
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'w') as f:
            json.dump([], f)


def history_view(request):
    _ensure_history_dir()
    with open(HISTORY_FILE, 'r') as f:
        data = json.load(f)
    return render(request, 'predictor/history.html', context={'history': data})

def _calculate_players_columns(ct_players, t_players):
    # Create player columns from all_players list
    all_players = list(_MODEL_PLAYERS) if _MODEL_PLAYERS is not None else []
    player_cols = [f'player_{p}' for p in all_players]

    # Initialize row with zeros
    row = {c: 0 for c in player_cols}

    # Mark CT players as 1, T players as 2
    for p in ct_players:
        col = f'player_{p}'
        if col in row:
            row[col] = 2
    for p in t_players:
        col = f'player_{p}'
        if col in row:
            row[col] = 3
    return row, player_cols

def _calculate_maps_columns(default_maps_names: list, map: str):
    # Create one hot encoded map columns
    maps_cols = [m for m in default_maps_names]
    row = {c: False for c in maps_cols}
    for m in default_maps_names:
        if m in map:
            row[m] = True
            break
    return row, maps_cols

@csrf_exempt
def api_predict(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('Only POST supported')
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    # Get current equip value for both teams
    team_ct_current_equip_value = payload.get('team_ct_current_equip_value', 0)
    team_t_current_equip_value = payload.get('team_t_current_equip_value', 0)
    map = payload.get('map', 'de_nuke')

    if '\xa0' in team_ct_current_equip_value or '\xa0' in team_t_current_equip_value:
        team_ct_current_equip_value = team_ct_current_equip_value.replace('\xa0', '')
        team_t_current_equip_value = team_t_current_equip_value.replace('\xa0', '')

    # Get team players for both teams
    team_ct_players = payload.get('ct_team_players', [])
    team_t_players = payload.get('t_team_players', [])

    # Basic validation
    if len(team_ct_players) != 5 or len(team_t_players) != 5:
        return HttpResponseBadRequest('Expected 5 players per team')

    _load_model()
    _load_model_players()
    _load_maps_names()
    if _MODEL is None:
        return JsonResponse({'error': 'Model not found on server'}, status=500)

    # Build feature vector compatible with training encoding
    # Create player columns from all_players list
    players_row, player_cols = _calculate_players_columns(team_ct_players, team_t_players)
    maps_row, maps_cols = _calculate_maps_columns(_MAPS_NAMES, map)
    row = maps_row | players_row

    # Prepare X in proper column order expected by model
    # Many models expect the same columns as training; we'll order player cols then the two equip cols
    X_cols = maps_cols + ['team_ct_current_equip_value', 'team_t_current_equip_value', 'round'] + player_cols
    X = np.array([[row.get(c, 0) for c in X_cols]])

   # Create pandas dataframe from X
    df = pd.DataFrame(X, columns=X_cols)
    df['team_ct_current_equip_value'] = team_ct_current_equip_value
    df['team_t_current_equip_value'] = team_t_current_equip_value
    df['round'] = 1
    
    # Get predictions
    preds = _MODEL.predict(df)
    probs = _MODEL.predict_proba(df)
    print(f"Predictions: {preds}")
    print(f"Probabilities: {probs}")

    # Serialize to JSON for frontend
    return JsonResponse({
        'prediction': preds.tolist(),
        'probabilities': probs.tolist(), # 2 T; 3 CT
    })