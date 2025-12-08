import os

STATUS_MAP = {0: "none", 1: "draw", 2: "t_win", 3: "ct_win"}
REASON_MAP = {0: "none", 1: "bomb_exploded", 7: "bomb_defused",
                8: "t_killed", 9: "ct_killed", 12: "time_ran_out"}

WEAPON_VALUES = {
    
}

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEMOS_DIR = os.path.join(APP_ROOT, "demos")
ASSETS_DIR = os.path.join(APP_ROOT, "assets")
MAPS_BACKGROUND_DIR = os.path.join(ASSETS_DIR, "maps_background")