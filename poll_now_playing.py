from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests


def write_atomic(path: Path, text: str) -> None:
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(text, encoding='utf-8')
    temp.replace(path)


def log(message: str) -> None:
    print(message, flush=True)


parser = argparse.ArgumentParser(description='Poll a text URL and write it to a local file for OBS.')
parser.add_argument('--url', default='https://sydney.emom.me/now-playing.txt')
parser.add_argument('--output', required=True, help='Path to the local text file OBS reads')
parser.add_argument('--interval', type=float, default=1.0, help='Polling interval in seconds')
parser.add_argument('--timeout', type=float, default=5.0, help='HTTP timeout in seconds')
parser.add_argument('--once', action='store_true', help='Fetch once, write the result, then exit')
parser.add_argument('--quiet', action='store_true', help='Only print errors')
args = parser.parse_args()

output_path = Path(args.output).expanduser().resolve()
output_path.parent.mkdir(parents=True, exist_ok=True)

last_text = None
session = requests.Session()
session.headers.update({'User-Agent': 'obs-now-playing-poller/1.0'})


def fetch_and_write() -> bool:
    global last_text

    response = session.get(args.url, timeout=args.timeout, headers={'Cache-Control': 'no-cache'})
    response.raise_for_status()
    text = response.text
    changed = text != last_text
    if changed:
        write_atomic(output_path, text)
        last_text = text
        if not args.quiet:
            log(f'Updated: {text!r}')
    elif not args.quiet and args.once:
        log('No change.')
    return changed


def main() -> int:
    while True:
        try:
            fetch_and_write()
            if args.once:
                return 0
        except KeyboardInterrupt:
            if not args.quiet:
                log('Stopped.')
            return 0
        except Exception as exc:
            log(f'Fetch failed: {exc}')
            if args.once:
                return 1
        time.sleep(max(args.interval, 0.1))


if __name__ == '__main__':
    sys.exit(main())
