"""Exercise actual request validation; preserve authored content languages."""
import copy
import importlib.util
import io
import json
import re
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH))
spec = importlib.util.spec_from_file_location("workbench_english_api", WORKBENCH / "server.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class EnglishApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        installed_skill = self.root / ".agents/skills/mosaic-gen-workflow"
        installed_skill.mkdir(parents=True)
        (installed_skill / "SKILL.md").write_text("---\nname: mosaic-gen-workflow\ndescription: Test package\n---\n# Mosaic Gen Workflow (v3.6)\n")
        self.source_text = "来源原文：单张图片，标题保持中文。"
        self.catalog = {"libraryRoot": str(self.root / "library"), "items": [
            {"id": "mm-image/test/default", "library": "mm-image", "componentId": "test", "name": "原始组件名",
             "variant": "默认样式", "description": self.source_text, "details": {"caption": "不要自动翻译。"}}]}
        self.root_patch = mock.patch.object(server, "ROOT", self.root)
        self.state_patch = mock.patch.object(server, "STATE", self.root / "state")
        self.root_patch.start()
        self.state_patch.start()
        self.app = server.Workbench()
        self.app.catalog = copy.deepcopy(self.catalog)
        self.environment_patch = mock.patch.object(self.app, "get_environment", side_effect=AssertionError("No live environment calls in API language tests"))
        self.environment_patch.start()

    def tearDown(self):
        self.environment_patch.stop()
        self.state_patch.stop()
        self.root_patch.stop()
        self.temporary.cleanup()

    def request(self, method, path, payload=b"", *, origin="http://127.0.0.1:8770", csrf=True, extra_headers=None):
        if isinstance(payload, dict):
            payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        handler = object.__new__(server.Handler)
        handler.server = SimpleNamespace(workbench=self.app)
        handler.path = path
        handler.headers = {"Host": "127.0.0.1:8770", "Content-Length": str(len(payload)), "Content-Type": "application/json"}
        if origin is not None:
            handler.headers["Origin"] = origin
        if csrf:
            handler.headers["X-Workbench-Token"] = self.app.csrf
        handler.headers.update(extra_headers or {})
        handler.rfile = io.BytesIO(payload)
        handler.wfile = io.BytesIO()
        status = []
        handler.send_response = lambda code: status.append(code)
        handler.send_header = lambda *args: None
        handler.end_headers = lambda: None
        getattr(handler, "do_" + method)()
        return status[-1], json.loads(handler.wfile.getvalue())

    def assert_english_error(self, status, response, *concepts):
        self.assertEqual(status, 400)
        message = response.get("error")
        self.assertIsInstance(message, str)
        self.assertRegex(message, r"[A-Za-z]")
        self.assertNotRegex(message, r"[\u3400-\u9fff]")
        for concept in concepts:
            self.assertIn(concept.lower(), message.lower())

    def test_empty_selection_error_is_english_and_does_not_queue(self):
        with mock.patch.object(self.app, "execute", side_effect=AssertionError("No execution allowed")), \
             mock.patch.object(server.threading, "Thread") as thread:
            status, response = self.request("POST", "/api/jobs", {"selectionIds": []})
        self.assert_english_error(status, response, "select", "variant")
        self.assertEqual(self.app.jobs, {})
        self.assertIsNone(self.app.active_id)
        thread.assert_not_called()

    def test_safe_invalid_skill_zip_returns_english_error_without_activation(self):
        before = self.app.skills.list()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("README.txt", "Deliberately missing SKILL.md; no paths or executable payloads.")
        status, response = self.request("POST", "/api/skills/import", buffer.getvalue(), extra_headers={"X-Filename": "invalid-skill.zip"})
        self.assert_english_error(status, response, "zip", "skill")
        self.assertEqual(self.app.skills.list(), before)
        self.assertEqual(self.app.jobs, {})

    def test_cross_origin_and_missing_csrf_fail_before_job_validation(self):
        with mock.patch.object(self.app, "start", side_effect=AssertionError("Origin guard must reject before start")) as start:
            cross = self.request("POST", "/api/jobs", {}, origin="https://other.invalid")
            no_csrf = self.request("POST", "/api/jobs", {}, csrf=False)
        self.assert_english_error(*cross, "cross-origin")
        self.assert_english_error(*no_csrf, "session", "refresh")
        start.assert_not_called()

    def test_bootstrap_declares_english_but_preserves_chinese_source_text(self):
        original = copy.deepcopy(self.app.catalog)
        status, response = self.request("GET", "/api/bootstrap")
        self.assertEqual(status, 200)
        self.assertEqual(response["uiLanguage"], "en")
        self.assertEqual(response["version"], "0.4.0")
        self.assertEqual(response["catalog"]["items"][0]["description"], self.source_text)
        self.assertEqual(response["catalog"]["items"][0]["details"]["caption"], "不要自动翻译。")
        self.assertEqual(self.app.catalog, original)

    def test_validated_chinese_notes_and_names_are_preserved_before_execution(self):
        notes = "保留用户中文说明。\n请不要把『全部图片』翻译成英文。"
        payload = {"selectionIds": ["mm-image/test/default"], "targetVersion": "v1.5", "workspaceId": "ws-test",
                   "folderId": "default", "notes": notes, "namePrefix": "中文前缀", "outputRoot": str(self.root / "outputs")}
        original_catalog = copy.deepcopy(self.app.catalog)
        # The real start validation/snapshot/persistence boundary runs, while
        # its asynchronous authoring thread is never started.
        with mock.patch.object(server.threading, "Thread") as thread:
            status, job = self.request("POST", "/api/jobs", payload)
        self.assertEqual(status, 202)
        self.assertEqual(job["request"]["notes"], notes)
        self.assertEqual(job["request"]["namePrefix"], "中文前缀")
        self.assertEqual(job["request"]["reportLanguage"], "en")
        self.assertIn("原始组件名", job["selectionNames"][0])
        saved = json.loads((Path(job["directory"]) / "request.json").read_text())
        self.assertEqual(saved["notes"], notes)
        self.assertEqual(self.app.catalog, original_catalog)
        thread.assert_called_once()
        self.assertEqual(self.app.jobs[job["id"]]["status"], "queued")


if __name__ == "__main__":
    unittest.main()
