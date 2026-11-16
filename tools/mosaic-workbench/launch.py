#!/usr/bin/env python3
"""Start/reuse this checkout's loopback workbench, then open its browser UI."""
import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

APP = Path(__file__).resolve().parent
ROOT = APP.parents[1]


def inspect(url):
    try:
        with urllib.request.urlopen(url + '/api/bootstrap', timeout=2) as response:
            data = json.load(response)
        return data.get('projectRoot')
    except (OSError, ValueError):
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8770)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args(argv)
    if sys.version_info < (3, 9):
        parser.error('Python 3.9 or newer is required.')
    if not 1024 <= args.port <= 65535:
        parser.error('Choose a local port between 1024 and 65535.')
    if sys.platform == 'win32':
        parser.error('Run this POSIX runtime inside WSL2; native Windows is not supported.')
    url = f'http://127.0.0.1:{args.port}'
    owner = inspect(url)
    if owner and Path(owner).resolve() != ROOT.resolve():
        print(f'Port {args.port} belongs to another checkout: {owner}\nUse --port {args.port + 1}.', file=sys.stderr)
        return 1
    if not owner:
        (APP / 'state').mkdir(exist_ok=True)
        with (APP / 'state/server.log').open('ab') as log:
            process = subprocess.Popen([sys.executable, str(APP / 'server.py'), '--port', str(args.port)],
                                       cwd=ROOT, stdout=log, stderr=log,
                                       stdin=subprocess.DEVNULL, start_new_session=True)
        for _ in range(60):
            if inspect(url) == str(ROOT):
                break
            if process.poll() is not None:
                print('Startup failed. See: ' + str(APP / 'state/server.log'), file=sys.stderr)
                return 1
            time.sleep(.5)
        else:
            print('Startup is not complete. See: ' + str(APP / 'state/server.log'), file=sys.stderr)
            return 1
        (APP / 'state/server-process.json').write_text(json.dumps({'pid': process.pid, 'port': args.port, 'projectRoot': str(ROOT)}))
    print('Mosaic Workbench: ' + url)
    if not args.no_browser:
        webbrowser.open(url)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
