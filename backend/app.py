import os
import tempfile
import threading
import uuid
import time
from flask import Flask, jsonify, request, render_template
from werkzeug.utils import secure_filename
from constants import APP_ROOT, DEMOS_DIR
try:
    from demoparser2 import DemoParser  # type: ignore
    DEMOPARSER_AVAILABLE = True
except ImportError:
    DEMOPARSER_AVAILABLE = False


app = Flask(
    __name__,
    static_folder=os.path.join(APP_ROOT, "app"),
    static_url_path="/static",
    template_folder=os.path.join(APP_ROOT, "templates"),
)

# In-memory cache for parsed demos {filename: json_data}
PARSED_CACHE = {}
JOBS = {}
JOBS_LOCK = threading.Lock()

SAMPLE_ROUND_PATH = os.path.join(os.path.dirname(__file__), "../app/sample-round.json")


def parse_demo_to_rounds(demo_path: str, every_n_ticks: int = 1, alive_only: bool = True) -> dict:
    """Parse a CS2 demo file into the front-end JSON structure.

    Structure returned:
    {
      "rounds": [
        {"round": <int>, "players": [
           {"id": <str>, "name": <str>, "positions": [ {"tick": <int>, "x": <float>, "y": <float>}, ... ] }
        ]}
      ]
    }

    If demoparser2 is not installed, returns an empty structure.
    """
    if not DEMOPARSER_AVAILABLE:
        return {"rounds": []}

    parser = DemoParser(demo_path)
    # Request needed fields. We include X,Y and meta fields (some may be missing).
    requested = ["X", "Y", "player_name", "user_id", "entity_id", "player_steamid", "is_alive", "total_rounds_played"]
    ticks_df = parser.parse_ticks(requested)  # type: ignore

    # Ensure required coordinates exist
    for needed in ["X", "Y"]:
        if needed not in ticks_df.columns:
            raise ValueError("Ticks dataframe missing coordinates X/Y")

    # Choose an identifier column
    id_col = "user_id" if "user_id" in ticks_df.columns else ("entity_id" if "entity_id" in ticks_df.columns else None)
    if id_col is None:
        # As last resort, use player_steamid
        id_col = "player_steamid" if "player_steamid" in ticks_df.columns else None
    if id_col is None:
        raise ValueError("No suitable player id column found (user_id/entity_id/player_steamid)")

    # Choose a name column
    name_col = "player_name" if "player_name" in ticks_df.columns else ("player_steamid" if "player_steamid" in ticks_df.columns else id_col)

    # Add a monotonic tick index if not present. We use the dataframe index.
    ticks_df = ticks_df.reset_index(drop=True)
    ticks_df["tick"] = ticks_df.index

    # Optionally sample every N ticks
    if every_n_ticks > 1:
        ticks_df = ticks_df[ticks_df["tick"] % every_n_ticks == 0]

    # Filter out dead players if requested
    if alive_only and "is_alive" in ticks_df.columns:
        ticks_df = ticks_df[ticks_df["is_alive"] == True]

    rounds = []
    # If total_rounds_played missing, treat entire demo as one round
    round_group_col = "total_rounds_played" if "total_rounds_played" in ticks_df.columns else None
    if round_group_col is None:
        ticks_df["__round"] = 1
        round_group_col = "__round"

    for round_num, round_df in ticks_df.groupby(round_group_col):
        players = []
        for player_id, player_df in round_df.groupby(id_col):
            name = str(player_df[name_col].iloc[0]) if name_col in player_df.columns else str(player_id)
            positions = [
                {"tick": int(tick), "x": float(row["X"]), "y": float(row["Y"])}
                for tick, row in player_df.iterrows()
            ]
            players.append({"id": str(player_id), "name": name, "positions": positions})
        rounds.append({"round": int(round_num), "players": players})
    return {"rounds": rounds}


def _update_job(job_id: str, **kwargs):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        job.update(kwargs)


def _run_parse_job(job_id: str, demo_name: str, every_n: int):
    try:
        path = os.path.join(DEMOS_DIR, demo_name)
        if not os.path.isfile(path):
            _update_job(job_id, status="error", message="Demo não encontrada", percent=0)
            return
        if not DEMOPARSER_AVAILABLE:
            _update_job(job_id, status="error", message="demoparser2 não instalado", percent=0)
            return
        _update_job(job_id, status="running", message="A carregar ticks...", percent=0)
        # Attempt to discover map name from parser
        map_name = None
        try:
            map_name = getattr(parser, 'map_name', None) or getattr(parser, 'map', None) or getattr(parser, 'mapname', None)
        except Exception:
            map_name = None
        try:
            meta = getattr(parser, 'metadata', None) or getattr(parser, 'meta', None)
            if isinstance(meta, dict):
                map_name = map_name or meta.get('map') or meta.get('map_name')
        except Exception:
            pass
        # Parse ticks first (heaviest step, progress unknown)
        parser = DemoParser(path)
        requested = ["X", "Y", "player_name", "user_id", "entity_id", "player_steamid", "is_alive", "total_rounds_played"]
        ticks_df = parser.parse_ticks(requested)  # type: ignore
        # Build same normalization as parse_demo_to_rounds, but with per-round updates
        for needed in ["X", "Y"]:
            if needed not in ticks_df.columns:
                _update_job(job_id, status="error", message="Colunas X/Y em falta", percent=0)
                return
        id_col = "user_id" if "user_id" in ticks_df.columns else ("entity_id" if "entity_id" in ticks_df.columns else ("player_steamid" if "player_steamid" in ticks_df.columns else None))
        if id_col is None:
            _update_job(job_id, status="error", message="Sem coluna de id (user_id/entity_id/steamid)", percent=0)
            return
        name_col = "player_name" if "player_name" in ticks_df.columns else ("player_steamid" if "player_steamid" in ticks_df.columns else id_col)
        ticks_df = ticks_df.reset_index(drop=True)
        ticks_df["tick"] = ticks_df.index
        if every_n and every_n > 1:
            ticks_df = ticks_df[ticks_df["tick"] % every_n == 0]
        if "is_alive" in ticks_df.columns:
            ticks_df = ticks_df[ticks_df["is_alive"] == True]
        round_group_col = "total_rounds_played" if "total_rounds_played" in ticks_df.columns else None
        if round_group_col is None:
            ticks_df["__round"] = 1
            round_group_col = "__round"
        # Begin per-round aggregation
        unique_rounds = list(ticks_df[round_group_col].dropna().unique())
        total = len(unique_rounds)
        _update_job(job_id, status="running", message="A agregar rondas...", total_rounds=total, processed_rounds=0, percent=0)
        rounds = []
        processed = 0
        for round_num, round_df in ticks_df.groupby(round_group_col):
            players = []
            for player_id, player_df in round_df.groupby(id_col):
                name = str(player_df[name_col].iloc[0]) if name_col in player_df.columns else str(player_id)
                positions = [
                    {"tick": int(idx), "x": float(row["X"]), "y": float(row["Y"])}
                    for idx, row in player_df.iterrows()
                ]
                players.append({"id": str(player_id), "name": name, "positions": positions})
            rounds.append({"round": int(round_num), "players": players})
            processed += 1
            percent = int((processed / max(total, 1)) * 100)
            _update_job(job_id, processed_rounds=processed, percent=percent)
            # Yield to main thread for responsiveness
            time.sleep(0)
        result = {"rounds": rounds, "map": map_name}
        _update_job(job_id, status="done", message="Concluído", result=result, percent=100)
    except Exception as e:
        _update_job(job_id, status="error", message=str(e), percent=0)


@app.route("/")
def index():
    script_path = os.path.join(app.static_folder, "app.js")
    app_js = ""
    if os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as js_file:
            app_js = js_file.read()
    return render_template("index.html", app_js=app_js)


@app.route("/api/sample-round")
def sample_round():
    if not os.path.exists(SAMPLE_ROUND_PATH):
        return jsonify({"error": "sample-round.json not found"}), 404
    import json
    with open(SAMPLE_ROUND_PATH, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/api/upload-demo", methods=["POST"])
def upload_demo():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    filename = secure_filename(f.filename)
    with tempfile.TemporaryDirectory() as tmpd:
        path = os.path.join(tmpd, filename)
        f.save(path)
        try:
            data = parse_demo_to_rounds(path, every_n_ticks=int(request.form.get("every_n", 1)))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    PARSED_CACHE[filename] = data
    return jsonify({"demo": filename, "rounds": data["rounds"]})


@app.route("/api/rounds")
def get_rounds():
    demo = request.args.get("demo")
    if not demo:
        return jsonify({"error": "Missing demo query param"}), 400
    if demo not in PARSED_CACHE:
        return jsonify({"error": "Demo not parsed yet"}), 404
    return jsonify(PARSED_CACHE[demo])


@app.route("/api/demos")
def list_demos():
    if not os.path.isdir(DEMOS_DIR):
        return jsonify({"demos": [], "error": "demos dir not found"}), 200
    demos = [f for f in os.listdir(DEMOS_DIR) if f.lower().endswith('.dem')]
    return jsonify({"demos": demos})


@app.route("/api/parse-demo")
def parse_existing_demo():
    name = request.args.get("name")
    if not name:
        return jsonify({"error": "Missing 'name' query param"}), 400
    path = os.path.join(DEMOS_DIR, name)
    if not os.path.isfile(path):
        return jsonify({"error": "Demo not found"}), 404
    if name in PARSED_CACHE:
        return jsonify(PARSED_CACHE[name])
    every_n = int(request.args.get("every_n", 1))
    try:
        data = parse_demo_to_rounds(path, every_n_ticks=every_n)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    PARSED_CACHE[name] = data
    return jsonify(data)


@app.route("/api/start-parse", methods=["POST"])
def start_parse():
    payload = request.get_json(silent=True) or request.form or {}
    name = payload.get("name")
    every_n = int(payload.get("every_n", 1))
    if not name:
        return jsonify({"error": "Missing 'name'"}), 400
    job_id = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "status": "pending",
            "message": "",
            "total_rounds": None,
            "processed_rounds": 0,
            "percent": 0,
            "result": None,
        }
    t = threading.Thread(target=_run_parse_job, args=(job_id, name, every_n), daemon=True)
    t.start()
    return jsonify({"job": job_id})


@app.route("/api/progress")
def progress():
    job_id = request.args.get("job")
    if not job_id:
        return jsonify({"error": "Missing job"}), 400
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        # Do not include heavy result here
        resp = {k: v for k, v in job.items() if k != "result"}
    return jsonify(resp)


@app.route("/api/result")
def result():
    job_id = request.args.get("job")
    if not job_id:
        return jsonify({"error": "Missing job"}), 400
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        if job.get("status") != "done":
            return jsonify({"error": "Job not finished"}), 400
        return jsonify(job.get("result") or {"rounds": []})


    @app.route('/api/map')
    def api_map():
        """Return a static URL for a map image if one exists in the `assets/maps` folder.

        Query param: `name` - map name as returned by the parser. The endpoint will try a
        few normalized variants (spaces -> underscore, lowercase) and common extensions.
        """
        name = request.args.get('name')
        if not name:
            return jsonify({'error': 'Missing name'}), 400

        maps_dir = os.path.join(app.static_folder, 'assets','maps')
        exts = ['.jpg', '.png', '.webp']
        tried = []

        # Variants to try
        variants = [name, name.replace(' ', '_'), name.lower(), name.lower().replace(' ', '_')]
        for v in variants:
            safe = v.strip()
            if not safe:
                continue
            for e in exts:
                fname = safe + e
                path = os.path.join(maps_dir, fname)
                tried.append(path)
                if os.path.isfile(path):
                    # Return the static URL for the frontend to use
                    url = f"/static/assets/maps/{fname}"
                    return jsonify({'url': url})

        return jsonify({'error': 'Map image not found'}), 404


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "demoparser": DEMOPARSER_AVAILABLE, "demos_dir": os.path.isdir(DEMOS_DIR)})


if __name__ == "__main__":
    # Run Flask development server
    app.run(host="0.0.0.0", port=5000, debug=True)
