# OBS Now Playing

Small Flask app for an OBS "now playing" workflow:
- `/program-manager`: build, reorder, lock, and select acts
- `/now-playing.txt`: plain text output for OBS polling
- `/now-playing.html`: public read-only status page with one-minute refresh
- `/api/program`: JSON state for the manager UI
- `/api/now-playing`: JSON status for debugging or future automation

State is persisted to `data/program_state.json`.

## Current workflow

1. Open `/program-manager`.
2. Add acts and drag to reorder them.
3. Click `Done` to lock the list.
4. In play mode, click the current act to mark it as live.
5. Click the selected act again, or `Clear current act`, to clear it.

When no act is selected, `/now-playing.txt` returns a single space character so OBS and intermediate polling tools still receive non-empty content.
The manager and `/api/program` are protected with HTTP Basic Auth. Defaults:
- username `admin@emom.me`
- password `123abc`

You can override them with `NOW_PLAYING_MANAGER_USERNAME` and `NOW_PLAYING_MANAGER_PASSWORD`.

## Run server

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The app listens on `127.0.0.1:8000`.

## nginx shape

The included [`nginx.conf.example`](/Users/stewart/Library/CloudStorage/Dropbox/Documents/EMOM/GitHub/now-playing/nginx.conf.example) assumes:
- public host `https://sydney.emom.me`
- nginx in front of Flask
- Flask bound only to localhost
- cache disabled on text and API responses

If you add more operator tooling later, route it through nginx and keep `/now-playing.txt` and `/now-playing.html` explicitly uncacheable.

## Run the OBS-side polling script

```bash
python poll_now_playing.py --output /path/to/now-playing-local.txt
```

Useful options:

```bash
python poll_now_playing.py --output /path/to/now-playing-local.txt --interval 0.5
python poll_now_playing.py --output C:\path\to\now-playing.txt --quiet
python poll_now_playing.py --output /tmp/now-playing.txt --once
```

Point the OBS Text source with `Read from file` enabled at that local text file.

## Notes and next extensions

- The manager UI shows the exact text currently being served to `/now-playing.txt`.
- Acts now use stable IDs instead of positional selection, which is a better fit for a future database-backed source.
- The list cannot be locked while empty.
- Responses include no-cache headers so polling clients get fresh state.
- The current state model is intentionally simple: ordered acts plus a selected act ID.

Low-risk future additions:
- a second public-facing layout optimized for projector-only use if you want something even larger and simpler than `/now-playing.html`
- optional schedule metadata per act, while keeping `/now-playing.txt` plain text
