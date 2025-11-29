# Flask Backend for Movement Viewer

This backend provides endpoints to supply round movement data to the existing front-end (`app/`).

## Endpoints
- `GET /` Serves the front-end `index.html`.
- `GET /api/sample-round` Returns the static sample JSON shipped with the front-end.
- `POST /api/upload-demo` Accepts a CS2 `.dem` file (form field name `file`). Optional form field `every_n` to sample ticks. Returns parsed JSON in the format the front-end expects.
- `GET /api/rounds?demo=<filename>` Returns cached parsed rounds for a previously uploaded demo.
- `GET /api/health` Simple health check.

## Parsing Logic
If `demoparser2` is installed (`pip install demoparser2`), `parse_demo_to_rounds` uses `parse_ticks(["X","Y","player_name","user_id","is_alive","total_rounds_played"])` to construct per-round player position arrays. If not installed the upload endpoint returns an empty structure.

## Install
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
pip install demoparser2  # for real demo parsing
```

## Run
```cmd
.venv\Scripts\activate
python backend\app.py
```
Visit: http://localhost:5000/

## Upload Demo Example (PowerShell / cmd)
```cmd
curl -F "file=@demos\furia-vs-vitality-m1-nuke.dem" -F "every_n=10" http://localhost:5000/api/upload-demo > movement.json
```

Then drag `movement.json` into the front-end file picker or extend the front-end to fetch `/api/rounds?demo=furia-vs-vitality-m1-nuke.dem`.

## Front-End Integration
A new button "Load Sample (API)" fetches `/api/sample-round` and populates the viewer without manually uploading a JSON file.

## Next Ideas
- Add direct demo fetch button invoking `/api/upload-demo` via `<input type=file>`.
- Add server-side caching with size limits.
- Add optional Z coordinate & map scaling logic.
