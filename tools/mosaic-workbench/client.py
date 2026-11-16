#!/usr/bin/env python3
"""Scriptable entry to the same local workbench used by the UI."""
import argparse
import json
import urllib.error
import urllib.parse
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8770')
    sub = parser.add_subparsers(dest='command', required=True)
    catalog = sub.add_parser('catalog', help='List selectable library entries')
    catalog.add_argument('--search', default='')
    sub.add_parser('environment')
    sub.add_parser('skills')
    sub.add_parser('jobs')
    job = sub.add_parser('job')
    job.add_argument('id')
    cancel = sub.add_parser('cancel')
    cancel.add_argument('id')
    run = sub.add_parser('run', help='Create new templates and retain a report')
    run.add_argument('--select', action='append', required=True, help='Selection id; repeat for a batch')
    run.add_argument('--version', default='v1.5')
    run.add_argument('--workspace')
    run.add_argument('--folder', default='default')
    run.add_argument('--prefix', default='Library')
    run.add_argument('--model', default='', help='Codex model; empty uses the configured default')
    run.add_argument('--effort', choices=['low','medium','high'], default='medium')
    run.add_argument('--timeout', type=int, default=300, help='Per-card time budget in seconds')
    run.add_argument('--repairs', type=int, choices=[0,1,2], default=1)
    run.add_argument('--notes', default='')
    args = parser.parse_args()
    try:
        endpoint = urllib.parse.urlsplit(args.url)
        valid = endpoint.scheme == 'http' and endpoint.hostname in ('127.0.0.1', 'localhost') and endpoint.port is not None and 1024 <= endpoint.port <= 65535 and endpoint.path in ('', '/') and not endpoint.query and not endpoint.fragment and not endpoint.username and not endpoint.password
    except ValueError:
        valid = False
    if not valid:
        parser.error('This client accepts only an explicit localhost HTTP port, for example http://127.0.0.1:8770.')
    args.url = args.url.rstrip('/')

    def request(path, data=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['X-Workbench-Token'] = token
        req = urllib.request.Request(args.url + path,
            data=json.dumps(data).encode() if data is not None else None, headers=headers)
        with urllib.request.urlopen(req, timeout=180) as response:
            return json.load(response)

    try:
        if args.command in ('environment', 'skills', 'jobs'):
            result = request('/api/' + args.command)
        elif args.command == 'job':
            result = request('/api/jobs/' + urllib.parse.quote(args.id, safe=''))
        else:
            bootstrap = request('/api/bootstrap')
            if args.command == 'catalog':
                result = [{k: item.get(k) for k in ('id','libraryName','name','variant','size')}
                          for item in bootstrap['catalog']['items']
                          if args.search.lower() in json.dumps(item, ensure_ascii=False).lower()]
            elif args.command == 'cancel':
                result = request('/api/jobs/' + urllib.parse.quote(args.id, safe='') + '/cancel', {}, bootstrap['csrf'])
            else:
                if not (args.workspace or bootstrap['defaults']['workspaceId']):
                    parser.error('Choose your Mosaic workspace with --workspace, or configure workspaceId in workbench.local.json.')
                result = request('/api/jobs', {'selectionIds': args.select,
                    'targetVersion': args.version, 'workspaceId': args.workspace or bootstrap['defaults']['workspaceId'],
                    'folderId': args.folder, 'namePrefix': args.prefix, 'notes': args.notes, 'codexModel': args.model,
                    'reasoningEffort':args.effort,'itemTimeoutSeconds':args.timeout,'maxRepairs':args.repairs,
                    'skillId': bootstrap['skill']['activeId']}, bootstrap['csrf'])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except urllib.error.HTTPError as error:
        print(error.read().decode(), file=__import__('sys').stderr)
    except (OSError, ValueError) as error:
        print('工作台请求失败：' + str(error), file=__import__('sys').stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
