#!/usr/bin/env python3
"""Local Library → Mosaic workbench. Bound to loopback; one authoring run at a time."""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import secrets
import sys
import threading
import traceback
import zipfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from skills import SkillStore

ROOT = Path(__file__).resolve().parents[2]
APP = Path(__file__).resolve().parent
STATE = APP / 'state'
from settings import load_settings


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')
    temp.replace(path)


def public_error(exc):
    value = str(exc)
    value = re.sub(r'(?i)(bearer\s+|access_token["\s:=]+)[^\s"\x27]+', r'\1[redacted]', value)
    return value[:1200]


class Workbench:
    def __init__(self):
        STATE.mkdir(parents=True, exist_ok=True)
        self.skills = SkillStore(ROOT)
        self.csrf = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.active_id = None
        self.cancel = None
        self.catalog = None
        self.environment = None
        self.environment_lock = threading.Lock()
        self.index = STATE / 'jobs.json'
        self.jobs = json.loads(self.index.read_text()) if self.index.exists() else {}
        for job in self.jobs.values():
            if job['status'] in ['running', 'queued', 'cancelling']:
                # Retain saved IDs and completed items; stop stale queue states.
                for item in job.get('partialItems', []):
                    if item.get('status') in ('running', 'queued'):
                        item.update(status='interrupted' if item['status']=='running' else 'not_run',
                                    error='工作台进程中断；保留已保存成果，未自动重试。')
                job.update(status='interrupted', message='工作台上次运行中断；保留已生成内容，请查看任务文件后重试。', updatedAt=now())
                atomic_json(Path(job['directory']) / 'job.json', job)
        self.save_index()

    def save_index(self):
        atomic_json(self.index, self.jobs)

    def get_catalog(self):
        with self.lock:
            if self.catalog is None:
                from catalog import build_catalog
                self.catalog = build_catalog(ROOT)
            return self.catalog

    def get_environment(self, refresh=False):
        with self.environment_lock:
            if refresh or self.environment is None:
                from codex_engine import get_environment
                self.environment = get_environment(ROOT)
            return self.environment

    def start(self, request):
        selections = request.get('selectionIds')
        if not isinstance(selections, list) or not 1 <= len(selections) <= 50 or not all(isinstance(s, str) for s in selections):
            raise ValueError('请选择1到50个组件变体。')
        selections = list(dict.fromkeys(selections))
        lookup = {i['id']: i for i in self.get_catalog()['items']}
        if any(s not in lookup for s in selections):
            raise ValueError('所选组件已不在当前 library 中，请刷新后重选。')
        if not re.fullmatch(r'v\d+\.\d+', str(request.get('targetVersion', ''))):
            raise ValueError('请选择有效的 Mosaic 版本。')
        for key in ['workspaceId', 'folderId']:
            val = request.get(key, '')
            if not isinstance(val, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', val):
                raise ValueError('Workspace 与文件夹 ID 只能包含字母、数字、横线和下划线。')
        prefix = request.get('namePrefix', 'Library')
        notes = request.get('notes', '')
        codex_model = request.get('codexModel') or ''
        if not isinstance(codex_model, str) or (codex_model and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,100}', codex_model)):
            raise ValueError('请输入有效的 Codex 模型 ID。')
        effort = request.get('reasoningEffort','medium')
        timeout = request.get('itemTimeoutSeconds',300)
        repairs = request.get('maxRepairs',1)
        if effort not in ('low','medium','high'):
            raise ValueError('请选择有效的思考强度。')
        if not isinstance(timeout,int) or isinstance(timeout,bool) or not 60 <= timeout <= 900:
            raise ValueError('单卡时间预算应为60至900秒。')
        if not isinstance(repairs,int) or isinstance(repairs,bool) or not 0 <= repairs <= 2:
            raise ValueError('修复次数应为0至2。')
        if not isinstance(prefix, str) or len(prefix) > 80 or not isinstance(notes, str) or len(notes) > 4000:
            raise ValueError('名称前缀或补充说明过长。')
        output = Path(request.get('outputRoot') or ROOT / 'outputs/mosaic-workbench').expanduser()
        output = (ROOT / output).resolve() if not output.is_absolute() else output.resolve()
        if not output.is_relative_to(ROOT) or any(x in ('.git','.agents','.codex','.aws') for x in output.relative_to(ROOT).parts):
            raise ValueError('本地输出请选择当前项目下的普通目录。')
        _, skill_info = self.skills.resolve(request.get('skillId'))
        with self.lock:
            if self.active_id:
                raise ValueError('已有还原任务正在执行。完成或停止后再启动下一批。')
            job_id = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(3)
            directory = output / job_id
            directory.mkdir(parents=True, exist_ok=False)
            request = {'selectionIds': selections, 'targetVersion': request['targetVersion'],
                       'schemaVersion': request['targetVersion'], 'workspaceId': request['workspaceId'],
                       'folderId': request['folderId'], 'namePrefix': prefix.strip() or 'Library',
                       'notes': notes, 'skillId': skill_info['id'], 'outputRoot': str(output),
                       'codexModel': codex_model, 'reasoningEffort': effort,
                       'itemTimeoutSeconds': timeout, 'maxRepairs': repairs,
                       'libraryRoot': self.get_catalog()['libraryRoot'], 'origin': 'workbench'}
            job = {'id': job_id, 'status': 'queued', 'createdAt': now(), 'updatedAt': now(),
                   'directory': str(directory), 'request': request, 'skill': skill_info,
                   'selectionNames': [lookup[s]['name'] + (' · '+lookup[s].get('variant','') if lookup[s].get('variant') else '') for s in selections],
                   'events': [], 'message': '准备读取来源与 skill', 'report': None,
                   'executionMode':'codex-app-server',
                   'partialItems':[{'selectionId':s,'name':lookup[s].get('variant') or lookup[s]['name'],
                                    'status':'queued','elapsedSeconds':0} for s in selections]}
            self.skills.snapshot(skill_info['id'], directory / 'skill')
            atomic_json(directory / 'request.json', request)
            atomic_json(directory / 'job.json', job)
            self.jobs[job_id] = job
            self.active_id = job_id
            self.cancel = threading.Event()
            self.save_index()
            threading.Thread(target=self.execute, args=(job_id, self.cancel), daemon=True).start()
            return job

    def execute(self, job_id, cancel):
        job = self.jobs[job_id]
        directory = Path(job['directory'])
        def emit(event):
            with self.lock:
                event = {'at': now(), **(event if isinstance(event, dict) else {'message':str(event)})}
                if event.get('type') == 'batch' and isinstance(event.get('items'),list):
                    job['partialItems'] = event['items']
                elif event.get('type') == 'item' and isinstance(event.get('item'),dict):
                    item = event['item']
                    existing = job.setdefault('partialItems',[])
                    for i, row in enumerate(existing):
                        if row.get('selectionId') == item.get('selectionId'):
                            existing[i] = item
                            break
                    else:
                        existing.append(item)
                if event.get('type') == 'item' and 'message' not in event:
                    result = event.get('item', {})
                    event['message'] = '组件结果：' + str(result.get('selectionId','')) + ' · ' + str(result.get('status',''))
                if 'stage' not in event:
                    event['stage'] = 'source' if event.get('phase') == 'preflight' else 'references'
                if 'message' in event:
                    event['message'] = public_error(event['message'])
                # Full item evidence lives in partialItems/report, not in every
                # historical event. Repeating it makes large batches grow quadratically.
                event.pop('items', None)
                event.pop('item', None)
                job['events'].append(event)
                job['events'] = job['events'][-400:]
                job.update(updatedAt=now(), message=event.get('message', job.get('message', '')))
                atomic_json(directory / 'job.json', job)
                self.save_index()
        try:
            from catalog import extract_selection
            from codex_engine import run_job
            job['status'] = 'running'
            emit({'stage':'source','message':'读取所选组件，冻结本次来源和 skill。'})
            briefs = []
            for selection_id in job['request']['selectionIds']:
                try:
                    brief = extract_selection(ROOT, selection_id)
                except Exception as exc:
                    selected = next(i for i in self.get_catalog()['items'] if i['id']==selection_id)
                    brief = {'selection':selected,'extractionError':public_error(exc)}
                briefs.append(brief)
            atomic_json(directory / 'sources.json', briefs)
            report = run_job(ROOT, directory, job['request'], briefs, directory / 'skill', emit, cancel)
            job['report'] = report
            status = report.get('status', 'needs_review')
            if status in ('success', 'completed', 'complete'):
                status = 'needs_review'
            job['status'] = 'cancelled' if cancel.is_set() else status
            atomic_json(directory / 'report.json', report)
            summary = report.get('summary')
            if isinstance(summary, dict):
                summary = summary.get('message') or summary.get('error')
            emit({'stage':'report','message':summary or '结果已保存，请查看还原报告。'})
        except Exception as exc:
            job['status'] = 'cancelled' if cancel.is_set() else 'failed'
            message = public_error(exc)
            items = job.get('partialItems', [])
            for item in items:
                if item.get('status') in ('queued','running'):
                    item.update(status='cancelled' if cancel.is_set() else 'failed', error=message)
            job['report'] = {'status':job['status'], 'summary':message, 'items':items,
                             'limitations':['未取得完整交付证据；请查看日志及任务目录中保留的部分结果。']}
            atomic_json(directory / 'report.json', job['report'])
            emit({'stage':'error','message':message})
            print('Run failed:', message, flush=True)
        finally:
            with self.lock:
                job['updatedAt'] = now()
                atomic_json(directory / 'job.json', job)
                self.active_id = None
                self.cancel = None
                self.save_index()


class Handler(BaseHTTPRequestHandler):
    server_version = 'MosaicWorkbench/0.3'

    @property
    def app(self):
        return self.server.workbench

    def log_message(self, fmt, *args):
        if not self.path.startswith('/api/jobs/'):
            super().log_message(fmt, *args)

    def json(self, data, status=200):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        self.wfile.write(payload)

    def check_origin(self, mutate=False):
        host = self.headers.get('Host','')
        hostname = host.split(':')[0]
        if hostname not in ('127.0.0.1','localhost'):
            raise ValueError('只接受本机访问。')
        origin = self.headers.get('Origin')
        if origin and origin not in ('http://'+host,):
            raise ValueError('拒绝跨来源请求。')
        if mutate and self.headers.get('X-Workbench-Token') != self.app.csrf:
            raise ValueError('页面会话已过期，请刷新工作台。')

    def file(self, root, relative, download=False):
        target = (root / unquote(relative)).resolve()
        if not target.is_relative_to(root.resolve()) or not target.is_file() or target.is_symlink():
            self.send_error(404)
            return
        if any(x.startswith('.') for x in target.relative_to(root).parts):
            self.send_error(404)
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type',mimetypes.guess_type(str(target))[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(len(data)))
        self.send_header('X-Content-Type-Options','nosniff')
        if download:
            self.send_header('Content-Disposition','attachment')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        try:
            self.check_origin()
            parsed = urlsplit(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            if path == '/api/bootstrap':
                catalog = self.app.get_catalog()
                settings = load_settings(ROOT)
                return self.json({'version':'0.3.0','csrf':self.app.csrf,'projectRoot':str(ROOT),
                    'defaults':{'workspaceId':settings['workspaceId'],'folderId':settings['folderId'],'outputRoot':str(ROOT/'outputs/mosaic-workbench'),'targetVersion':'v1.5',
                                'codexModel':'','reasoningEffort':'medium','itemTimeoutSeconds':300,'maxRepairs':1},
                    'skill':self.app.skills.list(),'catalog':{k:v for k,v in catalog.items() if k != 'libraryRoot'},
                    'activeJobId':self.app.active_id})
            if path == '/api/environment':
                return self.json(self.app.get_environment(query.get('refresh') == ['1']))
            if path == '/api/folders':
                from engine import get_folders
                workspace_id = query.get('workspaceId',[''])[0]
                if not re.fullmatch(r'[A-Za-z0-9_-]{1,160}',workspace_id):
                    raise ValueError('无效的 workspace ID。')
                return self.json({'folders':get_folders(ROOT,workspace_id)})
            if path == '/api/skills':
                return self.json(self.app.skills.list())
            if path == '/api/jobs':
                jobs = sorted(self.app.jobs.values(), key=lambda j:j['createdAt'], reverse=True)
                return self.json({'jobs':[{k:v for k,v in j.items() if k not in ('events','report')} for j in jobs]})
            if path.startswith('/api/jobs/'):
                job = self.app.jobs.get(path.removeprefix('/api/jobs/'))
                return self.json(job,200) if job else self.json({'error':'任务不存在。'},404)
            if path.startswith('/library/'):
                return self.file(Path(self.app.get_catalog()['libraryRoot']),path[len('/library/'):])
            if path.startswith('/runs/'):
                bits = path.split('/',3)
                if len(bits)<4 or bits[2] not in self.app.jobs:
                    return self.send_error(404)
                rel=bits[3]
                if any(x in rel.lower() for x in ['token_cache','credential','profile','auth','cookie']):
                    return self.send_error(404)
                return self.file(Path(self.app.jobs[bits[2]]['directory']),rel,query.get('download')==['1'])
            return self.file(APP/'web','index.html' if path=='/' else path.lstrip('/'))
        except (ValueError, KeyError, FileNotFoundError) as exc:
            self.json({'error':public_error(exc)},400)
        except Exception as exc:
            self.json({'error':public_error(exc)},500)

    def do_POST(self):
        try:
            self.check_origin(mutate=True)
            size=int(self.headers.get('Content-Length','0'))
            if size<0 or size>24*1024*1024:
                raise ValueError('请求过大。')
            payload=self.rfile.read(size)
            path=urlsplit(self.path).path
            if path=='/api/skills/import':
                result=self.app.skills.import_zip(payload,unquote(self.headers.get('X-Filename','skill.zip')))
                return self.json(result)
            request=json.loads(payload or b'{}')
            if not isinstance(request,dict):
                raise ValueError('请求格式无效。')
            if path=='/api/skills/activate':
                return self.json(self.app.skills.activate(request.get('id','')))
            if path=='/api/jobs':
                return self.json(self.app.start(request),202)
            if path.endswith('/cancel') and path.startswith('/api/jobs/'):
                job_id=path.split('/')[3]
                with self.app.lock:
                    if self.app.active_id==job_id and self.app.cancel:
                        self.app.cancel.set()
                        self.app.jobs[job_id]['status']='cancelling'
                        self.app.save_index()
                    return self.json({'status':'cancelling' if self.app.active_id==job_id else 'inactive'})
            return self.json({'error':'未知操作。'},404)
        except (ValueError,KeyError,FileNotFoundError,zipfile.BadZipFile) as exc:
            self.json({'error':public_error(exc)},400)
        except Exception as exc:
            self.json({'error':public_error(exc)},500)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8770)
    args=parser.parse_args()
    app=Workbench()
    app.get_catalog()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.workbench=app
    print(f'Mosaic Workbench: http://127.0.0.1:{args.port}',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if app.cancel:
            app.cancel.set()
        server.server_close()


if __name__=='__main__':
    import zipfile
    main()
