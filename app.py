from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
STATE_FILE = DATA_DIR / 'program_state.json'
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
MANAGER_USERNAME = os.environ.get('NOW_PLAYING_MANAGER_USERNAME', 'admin@emom.me')
MANAGER_PASSWORD = os.environ.get('NOW_PLAYING_MANAGER_PASSWORD', '123abc')


def default_state() -> dict[str, Any]:
    return {
        'locked': False,
        'acts': [],
        'selected_act_id': None,
    }


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return default_state()
    try:
        with STATE_FILE.open('r', encoding='utf-8') as f:
            data = json.load(f)
        return normalize_state(data)
    except Exception:
        return default_state()


def save_state(state: dict[str, Any]) -> None:
    tmp_file = STATE_FILE.with_suffix('.tmp')
    with tmp_file.open('w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, STATE_FILE)


def normalize_state(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return default_state()

    locked = bool(data.get('locked', False))
    acts_raw = data.get('acts', [])
    selected_act_id = data.get('selected_act_id', None)
    current_index = data.get('current_index', None)

    acts: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    if isinstance(acts_raw, list):
        for item in acts_raw:
            act = normalize_act(item)
            if act is not None:
                while act['id'] in seen_ids:
                    act['id'] = generate_act_id()
                seen_ids.add(act['id'])
                acts.append(act)

    if selected_act_id is None and isinstance(current_index, int) and 0 <= current_index < len(acts):
        selected_act_id = acts[current_index]['id']

    valid_ids = {act['id'] for act in acts}
    if not isinstance(selected_act_id, str) or selected_act_id not in valid_ids:
        selected_act_id = None

    return {
        'locked': locked,
        'acts': acts,
        'selected_act_id': selected_act_id,
    }


def normalize_act(item: Any) -> dict[str, str] | None:
    if isinstance(item, str):
        name = item.strip()
        if not name:
            return None
        return {'id': generate_act_id(), 'name': name[:200]}

    if not isinstance(item, dict):
        return None

    name = item.get('name')
    if not isinstance(name, str):
        return None
    name = name.strip()
    if not name:
        return None

    act_id = item.get('id')
    if not isinstance(act_id, str) or not act_id.strip():
        act_id = generate_act_id()

    return {
        'id': act_id.strip(),
        'name': name[:200],
    }


def generate_act_id() -> str:
    return secrets.token_hex(8)


def no_cache_headers() -> dict[str, str]:
    return {
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
    }


def build_now_playing_text(state: dict[str, Any]) -> str:
    selected_act = get_selected_act(state)
    if selected_act is not None:
        return selected_act['name']
    return ' '


def get_selected_act(state: dict[str, Any]) -> dict[str, str] | None:
    selected_act_id = state.get('selected_act_id')
    if not isinstance(selected_act_id, str):
        return None

    for act in state.get('acts', []):
        if isinstance(act, dict) and act.get('id') == selected_act_id:
            return act
    return None


def check_manager_auth() -> bool:
    auth = request.authorization
    if auth is None:
        return False
    return auth.username == MANAGER_USERNAME and auth.password == MANAGER_PASSWORD


def unauthorized_response() -> Response:
    return Response(
        'Authentication required.',
        401,
        {
            'WWW-Authenticate': 'Basic realm="Now Playing Manager"',
            **no_cache_headers(),
        },
    )


def require_manager_auth() -> Response | None:
    if check_manager_auth():
        return None
    return unauthorized_response()


@app.get('/program-manager')
def program_manager() -> Response | str:
    auth_response = require_manager_auth()
    if auth_response is not None:
        return auth_response
    return Response(render_template('program_manager.html'), headers=no_cache_headers())


@app.get('/api/program')
def get_program() -> Response:
    auth_response = require_manager_auth()
    if auth_response is not None:
        return auth_response
    response = jsonify(load_state())
    response.headers.update(no_cache_headers())
    return response


@app.post('/api/program')
def update_program() -> tuple[Response, int] | Response:
    auth_response = require_manager_auth()
    if auth_response is not None:
        return auth_response

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({'error': 'Expected JSON object'}), 400

    acts = payload.get('acts')
    if acts is not None and not isinstance(acts, list):
        return jsonify({'error': 'acts must be a list'}), 400

    selected_act_id = payload.get('selected_act_id')
    if selected_act_id is not None and not isinstance(selected_act_id, str):
        return jsonify({'error': 'selected_act_id must be a string or null'}), 400

    state = normalize_state(payload)
    save_state(state)
    response = jsonify(state)
    response.headers.update(no_cache_headers())
    return response


@app.get('/api/now-playing')
def get_now_playing() -> Response:
    state = load_state()
    selected_act = get_selected_act(state)
    response = jsonify({
        'text': build_now_playing_text(state),
        'has_selection': selected_act is not None,
        'selected_act_id': state.get('selected_act_id'),
        'selected_act': selected_act,
        'acts': state.get('acts', []),
        'locked': state.get('locked', False),
    })
    response.headers.update(no_cache_headers())
    return response


@app.get('/now-playing.txt')
def now_playing() -> Response:
    state = load_state()
    return Response(
        build_now_playing_text(state),
        mimetype='text/plain; charset=utf-8',
        headers=no_cache_headers(),
    )


@app.get('/now-playing.html')
def now_playing_html() -> Response:
    state = load_state()
    selected_act = get_selected_act(state)
    return Response(
        render_template(
            'now_playing.html',
            state=state,
            selected_act=selected_act,
            now_playing_text=build_now_playing_text(state),
        ),
        headers=no_cache_headers(),
    )


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000)
