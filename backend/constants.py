import os

STATUS_MAP = {0: "none", 1: "draw", 2: "t_win", 3: "ct_win"}
REASON_MAP = {0: "none", 1: "bomb_exploded", 7: "bomb_defused",
              8: "t_killed", 9: "ct_killed", 12: "time_ran_out"}

WEAPON_VALUES = {
    "primary_weapons": {
        "AK47": 2700,
        "M4A1-S": 2900,
        "M4A4": 2900,
        "AUG": 3300,
        "SG 553": 3000,
        "FAMAS": 2250,
        "GALIL AR": 2000,

        "AWP": 4750,
        "SSG 08": 1700,

        "MP9": 1250,
        "MAC-10": 1050,
        "MP7": 1500,
        "UMP-45": 1200,
        "P90": 2350,
        "PP-Bizon": 1400,
        "MP5-SD": 1500,

        "Nova": 1050,
        "XM1014": 2000,
        "Sawed-Off": 1100,
        "MAG-7": 1800,
    },

    "secondary_weapons": {
        "Desert Eagle": 700,
        "P250": 300,
        "Five-SeveN": 500,
        "CZ75-Auto": 500,
        "Tec-9": 500,
        "USP-S/P2000/Glock-18": 200
    },

    "equipment": {
        "Kevlar": 650,
        "Helmet": 350,
        "Defuse-kit": 400
    },

    "grenades": {
        "HE Grenade": 300,
        "Flashbang": 200,
        "Smoke Grenade": 300,
        "Molotov": 400,
        "Incendiary": 600,
        "Decoy": 50
    }
}

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEMOS_DIR = os.path.join(APP_ROOT, "demos")
ASSETS_DIR = os.path.join(APP_ROOT, "assets")
MAPS_BACKGROUND_DIR = os.path.join(ASSETS_DIR, "maps_background")
