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

# Locate model and players file relative to repo root
BASE_REPO = Path(__file__).resolve().parents[2]
MODEL_PATH = BASE_REPO / 'model' / 'round_winner_model.pkl'
PLAYERS_PATH = BASE_REPO / 'model' / 'all_players.pkl'
HISTORY_FILE = BASE_REPO / 'data' / 'predictions_history.json'

# Load model and players lazily
_MODEL = None
_ALL_PLAYERS = None

def _load_model():
    global _MODEL, _ALL_PLAYERS
    if _MODEL is None:
        if MODEL_PATH.exists():
            _MODEL = joblib.load(MODEL_PATH)
        else:
            _MODEL = None
    if _ALL_PLAYERS is None:
        if PLAYERS_PATH.exists():
            _ALL_PLAYERS = joblib.load(PLAYERS_PATH)
        else:
            _ALL_PLAYERS = []

def dashboard(request):
    # Provide weapon list and players list for initial rendering
    _load_model()
    weapons = sorted(list(constants.WEAPON_VALUES.keys()))
    import json as _json
    weapon_map_json = _json.dumps(constants.WEAPON_VALUES)
    # provide categorized options per player: primaries, secondaries, grenades
    primary_options = constants.WEAPON_VALUES['primary_weapons'].keys()
    secondary_options = constants.WEAPON_VALUES['secondary_weapons'].keys()
    grenade_options = constants.WEAPON_VALUES['grenades'].keys()
    equipment_options = constants.WEAPON_VALUES['equipment'].keys()
    return render(request, 'predictor/dashboard.html', context={
        'weapons': weapons,
        'all_players': _ALL_PLAYERS,
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

@csrf_exempt
def api_predict(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('Only POST supported')
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    # Expected payload keys
    team_ct_players = payload.get('team_ct_players', [])
    team_t_players = payload.get('team_t_players', [])

    # New structured per-player fields: primaries, secondaries, grenades (list per player)
    team_ct_primaries = payload.get('team_ct_player_primaries', [])
    team_ct_secondaries = payload.get('team_ct_player_secondaries', [])
    team_ct_grenades = payload.get('team_ct_player_grenades', [])

    team_t_primaries = payload.get('team_t_player_primaries', [])
    team_t_secondaries = payload.get('team_t_player_secondaries', [])
    team_t_grenades = payload.get('team_t_player_grenades', [])

    # Backwards compatibility: single list per player (legacy key)
    team_ct_player_weapons = payload.get('team_ct_player_weapons', None)
    team_t_player_weapons = payload.get('team_t_player_weapons', None)

    # Basic validation
    if len(team_ct_players) != 5 or len(team_t_players) != 5:
        return HttpResponseBadRequest('Expected 5 players per team')

    _load_model()
    if _MODEL is None:
        return JsonResponse({'error': 'Model not found on server'}, status=500)

    # Build feature vector compatible with training encoding
    # Create player columns from all_players list
    all_players = list(_ALL_PLAYERS) if _ALL_PLAYERS is not None else []
    player_cols = [f'player_{p}' for p in all_players]

    # Initialize row with zeros
    row = {c: 0 for c in player_cols}

    # Mark CT players as 1, T players as 2
    for p in team_ct_players:
        col = f'player_{p}'
        if col in row:
            row[col] = 1
    for p in team_t_players:
        col = f'player_{p}'
        if col in row:
            row[col] = 2

    # Compute equipment value per team using selected weapons
    def compute_equip_from_lists(primaries, secondaries, grenades, legacy_list=None):
        total = 0
        # legacy list (flat list of weapons per player)
        if legacy_list:
            for w in legacy_list:
                if not w:
                    continue
                total += int(constants.WEAPON_VALUES.get(w, 0))
            return total

        for w in (primaries or []):
            if w:
                total += int(constants.WEAPON_VALUES.get(w, 0))
        for w in (secondaries or []):
            if w:
                total += int(constants.WEAPON_VALUES.get(w, 0))
        for grp in (grenades or []):
            if isinstance(grp, (list, tuple)):
                for g in grp:
                    if g:
                        total += int(constants.WEAPON_VALUES.get(g, 0))
        return total

    ct_equip = compute_equip_from_lists(team_ct_primaries, team_ct_secondaries, team_ct_grenades, team_ct_player_weapons)
    tt_equip = compute_equip_from_lists(team_t_primaries, team_t_secondaries, team_t_grenades, team_t_player_weapons)

    row['team_ct_current_equip_value'] = ct_equip
    row['team_t_current_equip_value'] = tt_equip

    # Prepare X in proper column order expected by model
    # Many models expect the same columns as training; we'll order player cols then the two equip cols
    X_cols = player_cols + ['team_ct_current_equip_value', 'team_t_current_equip_value']
    X = np.array([[row.get(c, 0) for c in X_cols]])

    # Predict
    try:
        probs = _MODEL.predict_proba(X)[0]
        classes = list(_MODEL.classes_)
        # map classes to labels
        class_map = {c: constants.STATUS_MAP.get(c, str(c)) for c in classes}
        result = {class_map[c]: float(probs[i]) for i, c in enumerate(classes)}
        pred_idx = int(_MODEL.predict(X)[0])
        pred_label = constants.STATUS_MAP.get(pred_idx, str(pred_idx))
    except Exception as e:
        return JsonResponse({'error': f'Prediction error: {str(e)}'}, status=500)

    # Save history record
    record = {
        'timestamp': int(time.time()),
        'input': {
            'team_ct_players': team_ct_players,
            'team_t_players': team_t_players,
            'team_ct_player_weapons': team_ct_player_weapons,
            'team_t_player_weapons': team_t_player_weapons,
            'team_ct_equip': ct_equip,
            'team_t_equip': tt_equip,
        },
        'output': {
            'probabilities': result,
            'prediction': pred_label,
        }
    }
    try:
        _ensure_history_dir()
        with open(HISTORY_FILE, 'r+') as f:
            try:
                data = json.load(f)
            except Exception:
                data = []
            data.append(record)
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
    except Exception:
        # non-fatal
        pass

    return JsonResponse({'prediction': pred_label, 'probabilities': result, 'team_ct_equip': ct_equip, 'team_t_equip': tt_equip})
