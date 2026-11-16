import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH))
spec = importlib.util.spec_from_file_location("shareable_doctor", WORKBENCH / "doctor.py")
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        library = self.root / "library"
        library.mkdir()
        (library / "BUILD-MANIFEST.json").write_text("{}")
        self.binary = self.root / "mock-cli"
        self.binary.write_text("#!/bin/sh\nexit 99\n")
        self.binary.chmod(0o755)
        items = [{"id": f"image-{i}", "library": "mm-image", "componentId": "image-cards"} for i in range(49)]
        items += [{"id": f"component-{i}", "library": "video", "componentId": f"c-{i}"} for i in range(54)]
        items += [{"id": f"choice-{i}", "library": "video", "componentId": "c-0"} for i in range(464 - len(items))]
        self.catalog = {"items": items, "package": {"name": "release.zip", "path": str(self.root / "release.zip"), "sha256": "a" * 64}, "libraryRoot": str(library)}
        self.skill = {"version": "3.6", "fileCount": 16, "sha256": "b" * 64}
        self.patches = [mock.patch.object(doctor, "_read_catalog", return_value=self.catalog),
                        mock.patch.object(doctor, "_read_skill", return_value=self.skill),
                        mock.patch.object(doctor, "_resolve_codex", return_value=self.binary),
                        mock.patch.object(doctor, "_resolve_mosaic", return_value=self.binary)]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.temp.cleanup()

    def test_default_is_offline_and_never_starts_cli_or_reads_environment(self):
        with mock.patch.object(doctor, "_live_environment", side_effect=AssertionError("offline must not read accounts")) as live, \
             mock.patch("subprocess.Popen", side_effect=AssertionError("offline must not start a CLI")):
            report = doctor.run_checks(self.root)
        self.assertTrue(report["sourceReady"])
        self.assertEqual(report["exitCode"], 0)
        self.assertFalse(report["executionPrerequisites"]["liveChecked"])
        self.assertIsNone(report["executionPrerequisites"]["ready"])
        self.assertFalse(report["generationStarted"])
        live.assert_not_called()

    def test_missing_clis_warn_but_source_browsing_still_succeeds(self):
        with mock.patch.object(doctor, "_resolve_codex", side_effect=FileNotFoundError), \
             mock.patch.object(doctor, "_resolve_mosaic", side_effect=FileNotFoundError):
            report = doctor.run_checks(self.root)
        self.assertEqual(report["exitCode"], 0)
        self.assertTrue(report["sourceReady"])
        self.assertEqual(report["executionPrerequisites"]["codex"]["status"], "warning")
        self.assertFalse(report["executionPrerequisites"]["binariesAvailable"])

    def test_native_windows_advises_wsl_without_starting_live_execution(self):
        with mock.patch.object(doctor, "_is_posix", return_value=False), \
             mock.patch.object(doctor, "_live_environment", side_effect=AssertionError("must not start")) as live:
            offline = doctor.run_checks(self.root)
            live_report = doctor.run_checks(self.root, live=True)
        self.assertIn("WSL", offline["checks"]["platform"]["message"])
        self.assertEqual(offline["exitCode"], 0)
        self.assertEqual(live_report["exitCode"], 2)
        self.assertFalse(live_report["executionPrerequisites"]["liveChecked"])
        live.assert_not_called()

    def test_old_python_fails_before_loading_project_sources(self):
        with mock.patch.object(doctor.sys, "version_info", (3, 8, 0)), \
             mock.patch.object(doctor, "_read_catalog", side_effect=AssertionError("must not import")) as catalog:
            report = doctor.run_checks(self.root)
        self.assertEqual(report["exitCode"], 1)
        self.assertFalse(report["sourceReady"])
        catalog.assert_not_called()

    def test_source_inventory_mismatch_fails_offline_check(self):
        self.catalog["items"].pop()
        report = doctor.run_checks(self.root)
        self.assertFalse(report["sourceReady"])
        self.assertEqual(report["exitCode"], 1)
        self.assertEqual(report["checks"]["library"]["actual"]["selections"], 463)

    def test_invalid_skill_and_zip_are_reported_separately(self):
        with mock.patch.object(doctor, "_read_skill", side_effect=ValueError("missing reference")), \
             mock.patch.object(doctor, "_read_catalog", side_effect=ValueError("manifest mismatch")):
            report = doctor.run_checks(self.root)
        self.assertEqual(report["checks"]["skill"]["message"], "missing reference")
        self.assertEqual(report["checks"]["library"]["message"], "manifest mismatch")
        self.assertEqual(report["exitCode"], 1)

    def test_live_requires_codex_ready_and_mosaic_auth_and_api(self):
        environment = {"codex": {"available": True, "authenticated": True, "ready": True, "account": "private-account"},
                       "cli": {"available": True, "authenticated": True, "apiReachable": True, "access_token": "secret-marker"}}
        with mock.patch.object(doctor, "_live_environment", return_value=environment) as live:
            report = doctor.run_checks(self.root, live=True)
        live.assert_called_once_with(self.root)
        self.assertTrue(report["executionPrerequisites"]["ready"])
        self.assertEqual(report["exitCode"], 0)
        self.assertNotIn("secret-marker", json.dumps(report))
        self.assertNotIn("private-account", json.dumps(report))
        environment["cli"]["apiReachable"] = False
        with mock.patch.object(doctor, "_live_environment", return_value=environment):
            self.assertEqual(doctor.run_checks(self.root, live=True)["exitCode"], 2)

    def test_live_exception_does_not_dump_sensitive_diagnostic_payload(self):
        with mock.patch.object(doctor, "_live_environment", side_effect=RuntimeError("Authorization: secret-marker")):
            report = doctor.run_checks(self.root, live=True)
        self.assertEqual(report["exitCode"], 2)
        self.assertNotIn("secret-marker", json.dumps(report))

    def test_json_flag_outputs_machine_readable_report(self):
        report = doctor.run_checks(self.root)
        stream = io.StringIO()
        with mock.patch.object(doctor, "run_checks", return_value=report) as run, contextlib.redirect_stdout(stream):
            code = doctor.main(["--json"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(stream.getvalue())["sourceReady"])
        run.assert_called_once_with(live=False)


if __name__ == "__main__":
    unittest.main()
