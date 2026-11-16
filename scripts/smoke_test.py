#!/usr/bin/env python3
"""Offline HTTP smoke test on an owned random loopback port.

Checks only local bootstrap/catalog/skill/assets and origin rejection. It does
not request /api/environment, invoke a CLI, authenticate, or generate templates.
Only this script's child process and temporary job/skill state are cleaned up.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
CHILD = r'''
import sys
from pathlib import Path
import server
from http.server import ThreadingHTTPServer
scratch = Path(sys.argv[1])
server.STATE = scratch / "job-state"
RealSkillStore = server.SkillStore
server.SkillStore = lambda _: RealSkillStore(scratch)
def forbidden_environment(*args, **kwargs):
    raise AssertionError("Smoke test must not inspect live environment")
server.Workbench.get_environment = forbidden_environment
server.Workbench.execute = forbidden_environment
app = server.Workbench()
app.get_catalog()
httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
httpd.workbench = app
print("SMOKE_PORT:" + str(httpd.server_address[1]), flush=True)
try:
    httpd.serve_forever()
finally:
    httpd.server_close()
'''


def _request(base, path, headers=None, *, method="GET", data=None):
    request = urllib.request.Request(base + path, headers=headers or {}, method=method, data=data)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read(), response.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers


def _english_error(body, *concepts):
    try:
        value = json.loads(body).get("error", "")
    except (ValueError, AttributeError):
        return False
    return (isinstance(value, str) and bool(re.search(r"[A-Za-z]", value))
            and not re.search(r"[\u3400-\u9fff]", value)
            and all(concept.lower() in value.lower() for concept in concepts))


def _stop_owned(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
    except ProcessLookupError:
        pass


def run_smoke(project_root=None):
    root = Path(project_root or ROOT).resolve()
    report = {"mode": "offline-local-http", "projectRoot": str(root), "checks": [], "liveEnvironmentRequested": False,
              "generationStarted": False, "remoteWrites": False, "processCleanup": "not-started"}
    if os.name != "posix":
        return {**report, "ok": False, "error": "Run this smoke test inside WSL on Windows.", "exitCode": 1}
    process = None
    try:
        with tempfile.TemporaryDirectory(prefix="mosaic-local-smoke-") as temporary:
            scratch = Path(temporary)
            source_skill = root / ".agents/skills/mosaic-gen-workflow"
            shutil.copytree(source_skill, scratch / ".agents/skills/mosaic-gen-workflow", symlinks=True)
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            process = subprocess.Popen([sys.executable, "-u", "-c", CHILD, str(scratch)], cwd=root / "tools/mosaic-workbench",
                                       env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       start_new_session=True)
            port = None
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            deadline = time.monotonic() + 40
            try:
                while time.monotonic() < deadline and process.poll() is None:
                    for key, _ in selector.select(0.25):
                        line = key.fileobj.readline().decode("utf-8", "replace").strip()
                        if line.startswith("SMOKE_PORT:"):
                            port = int(line.partition(":")[2])
                            break
                    if port:
                        break
            finally:
                selector.close()
            if not port:
                _stop_owned(process)
                detail = process.stderr.read(6000).decode("utf-8", "replace").strip()
                raise RuntimeError("Local smoke server did not start. " + detail[-2000:])
            base = f"http://127.0.0.1:{port}"
            report["baseUrl"] = base
            def check(name, passed, **details):
                report["checks"].append({"name": name, "status": "pass" if passed else "fail", **details})
                if not passed:
                    raise AssertionError(name)
            status, body, _ = _request(base, "/")
            check("index", status == 200 and b"<html" in body.lower(), httpStatus=status)
            check("english-document-language", bool(re.search(rb"<html\b[^>]*\blang\s*=\s*['\"]en['\"]", body, re.I)))
            status, body, _ = _request(base, "/api/bootstrap")
            check("bootstrap", status == 200, httpStatus=status)
            bootstrap = json.loads(body)
            check("english-bootstrap-language", bootstrap.get("uiLanguage") == "en" and bootstrap.get("version") == "0.4.0",
                  uiLanguage=bootstrap.get("uiLanguage"), version=bootstrap.get("version"))
            items = bootstrap["catalog"]["items"]
            components = len({(i["library"], i["componentId"]) for i in items})
            image_cards = sum(i["library"] == "mm-image" and i["componentId"] == "image-cards" for i in items)
            check("catalog", (components, len(items), image_cards) == (55, 464, 49), components=components, selections=len(items), imageCards=image_cards)
            status, body, _ = _request(base, "/api/skills")
            skills = json.loads(body)
            check("skill", status == 200 and bool(skills.get("activeId")) and bool(skills.get("versions")), httpStatus=status)
            mutation_headers = {"Content-Type": "application/json", "Origin": base, "X-Workbench-Token": bootstrap["csrf"]}
            status, body, _ = _request(base, "/api/jobs", mutation_headers, method="POST", data=b'{"selectionIds":[]}')
            check("empty-selection-rejected-in-english", status == 400 and _english_error(body, "select", "variant"), httpStatus=status)
            invalid_zip = io.BytesIO()
            with zipfile.ZipFile(invalid_zip, "w") as archive:
                archive.writestr("README.txt", "Safe test archive: deliberately contains no skill.")
            status, body, _ = _request(base, "/api/skills/import", {**mutation_headers, "Content-Type": "application/zip", "X-Filename": "invalid-skill.zip"},
                                       method="POST", data=invalid_zip.getvalue())
            check("invalid-skill-rejected-in-english", status == 400 and _english_error(body, "zip", "skill"), httpStatus=status)
            status, body, _ = _request(base, "/api/skills")
            after_skills = json.loads(body)
            check("skill-import-did-not-activate", status == 200 and after_skills.get("activeId") == skills.get("activeId")
                  and {s["id"] for s in after_skills["versions"]} == {s["id"] for s in skills["versions"]})
            first = next(i for i in items if i["id"] == "mm-image/image-cards/2x2/single-image")
            status, body, _ = _request(base, "/library/" + first["previewPath"].split("#", 1)[0])
            check("library-page", status == 200 and b"<html" in body.lower(), httpStatus=status)
            status, body, _ = _request(base, "/library/BUILD-MANIFEST.json")
            check("library-manifest", status == 200, httpStatus=status)
            manifest = json.loads(body)
            asset = first["thumbnail"]
            status, body, headers = _request(base, "/library/" + quote(asset, safe="/"))
            check("source-asset", status == 200 and hashlib.sha256(body).hexdigest() == manifest["files"][asset],
                  httpStatus=status, contentType=headers.get("Content-Type"), bytes=len(body))
            status, body, _ = _request(base, "/api/bootstrap", {"Origin": "https://different-origin.invalid"})
            check("cross-origin-rejected", 400 <= status < 500 and _english_error(body, "cross-origin"), httpStatus=status)
            status, body, _ = _request(base, "/api/bootstrap", {"Host": "different-host.invalid"})
            check("non-loopback-host-rejected", 400 <= status < 500 and _english_error(body, "localhost"), httpStatus=status)
            status, body, _ = _request(base, "/api/jobs", {"Content-Type": "application/json", "Origin": base}, method="POST", data=b"{}")
            check("missing-csrf-rejected-in-english", status == 400 and _english_error(body, "session", "refresh"), httpStatus=status)
            status, body, _ = _request(base, "/api/jobs")
            check("no-jobs-created", status == 200 and json.loads(body).get("jobs") == [], httpStatus=status)
            report.update(ok=True, exitCode=0)
            _stop_owned(process)
            report["processCleanup"] = "owned-child-stopped"
    except Exception as error:
        report.update(ok=False, exitCode=1, error=str(error))
    finally:
        if process is not None:
            _stop_owned(process)
            report["processCleanup"] = "owned-child-stopped"
            process.stdout.close()
            process.stderr.close()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = run_smoke()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for check in report["checks"]:
            print(f"[{check['status'].upper()}] {check['name']}")
        print("Offline HTTP checks passed; the owned process has been stopped." if report["ok"] else "Check failed: " + report.get("error", "unknown"))
    return report["exitCode"]


if __name__ == "__main__":
    raise SystemExit(main())
