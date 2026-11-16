"""Offline CLI discovery/config isolation checks; never call a real model."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import codex_runtime as runtime


@unittest.skipUnless(os.name == "posix", "Runtime targets macOS/Linux/WSL")
class CodexPortabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "colleague-home"
        self.home.mkdir()
        self.bin_dir = self.root / "npm-global-bin"
        self.bin_dir.mkdir()
        self.binary = self.make_binary(self.bin_dir / "codex")
        self.settings = patch.object(runtime, "_load_settings", return_value={"codexBinary": ""})
        self.settings_mock = self.settings.start()
        self.home_patch = patch.object(runtime.Path, "home", return_value=self.home)
        self.home_patch.start()
        self.environment = patch.dict(os.environ, {"CODEX_HOME": "", "PATH": str(self.bin_dir)})
        self.environment.start()
        self.mac = patch.object(runtime, "MACOS_CODEX_CANDIDATES", ())
        self.mac.start()

    def tearDown(self):
        self.mac.stop()
        self.environment.stop()
        self.home_patch.stop()
        self.settings.stop()
        self.temp.cleanup()

    def make_binary(self, path):
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o755)
        return path.resolve()

    def test_path_npm_codex_is_resolved_without_launching(self):
        with patch.object(runtime.subprocess, "Popen") as launch:
            resolved = runtime.resolve_codex_binary()
        self.assertEqual(resolved, self.binary)
        launch.assert_not_called()

    def test_explicit_setting_wins_over_path_and_bundle(self):
        explicit = self.make_binary(self.root / "team-codex")
        self.settings_mock.return_value = {"codexBinary": str(explicit)}
        with patch.object(runtime.shutil, "which") as search:
            self.assertEqual(runtime.resolve_codex_binary(), explicit)
        search.assert_not_called()

    def test_invalid_explicit_path_never_falls_back_to_path(self):
        self.settings_mock.return_value = {"codexBinary": str(self.root / "missing")}
        with patch.object(runtime.shutil, "which") as search:
            with self.assertRaises(runtime.CodexRuntimeError) as caught:
                runtime.resolve_codex_binary()
        self.assertEqual(caught.exception.status, "needs_setup")
        self.assertIn("未改用其他CLI", str(caught.exception))
        search.assert_not_called()

    def test_explicit_non_executable_is_an_error(self):
        path = self.root / "not-executable"
        path.write_text("not a CLI")
        path.chmod(0o644)
        self.settings_mock.return_value = {"codexBinary": str(path)}
        with self.assertRaises(runtime.CodexRuntimeError) as caught:
            runtime.resolve_codex_binary()
        self.assertEqual(caught.exception.status, "needs_setup")

    def test_explicit_command_name_is_resolved_only_by_that_name(self):
        command = self.make_binary(self.bin_dir / "team-codex")
        self.settings_mock.return_value = {"codexBinary": "team-codex"}
        self.assertEqual(runtime.resolve_codex_binary(), command)
        self.settings_mock.return_value = {"codexBinary": "missing-team-codex"}
        with self.assertRaises(runtime.CodexRuntimeError):
            runtime.resolve_codex_binary()

    def test_path_precedes_existing_macos_bundle(self):
        bundle = self.make_binary(self.root / "desktop-codex")
        with patch.object(runtime.sys, "platform", "darwin"), patch.object(runtime, "MACOS_CODEX_CANDIDATES", (bundle,)):
            self.assertEqual(runtime.resolve_codex_binary(), self.binary)

    def test_macos_bundle_is_only_a_present_executable_fallback(self):
        bundle = self.make_binary(self.root / "desktop-codex")
        with patch.dict(os.environ, {"PATH": ""}), patch.object(runtime.sys, "platform", "darwin"), patch.object(runtime, "MACOS_CODEX_CANDIDATES", (self.root / "missing", bundle)):
            self.assertEqual(runtime.resolve_codex_binary(), bundle)
        with patch.dict(os.environ, {"PATH": ""}), patch.object(runtime.sys, "platform", "linux"), patch.object(runtime, "MACOS_CODEX_CANDIDATES", (bundle,)):
            with self.assertRaises(runtime.CodexRuntimeError):
                runtime.resolve_codex_binary()

    def test_missing_cli_returns_useful_environment_error_without_spawning(self):
        with patch.dict(os.environ, {"PATH": ""}), patch.object(runtime.subprocess, "run") as version, patch.object(runtime, "_AppServer") as server:
            result = runtime.get_codex_environment()
        self.assertFalse(result["available"])
        self.assertEqual(result["status"], "needs_setup")
        self.assertIn("@openai/codex", result["error"])
        self.assertIn("codexBinary", result["error"])
        version.assert_not_called()
        server.assert_not_called()

    def test_default_config_is_relative_to_current_user_home(self):
        config = self.home / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text('[mcp_servers.colleague]\ncommand="example"\n[plugins."test@local"]\nenabled=true\n')
        original = config.read_bytes()
        self.assertEqual(runtime._configured_names(), (["colleague"], ["test@local"]))
        args, isolation = runtime._server_argv()
        self.assertEqual(args[0], str(self.binary))
        self.assertIn("mcp_servers.colleague.enabled=false", args)
        self.assertEqual(isolation["codexHome"], str(config.parent))
        self.assertEqual(config.read_bytes(), original)

    def test_codex_home_overrides_home_for_config_sections(self):
        default = self.home / ".codex"
        default.mkdir()
        (default / "config.toml").write_text('[mcp_servers.wrong_home]\ncommand="example"\n')
        custom = self.root / "custom-codex-home"
        custom.mkdir()
        config = custom / "config.toml"
        config.write_text('[mcp_servers.correct_home]\ncommand="example"\n')
        original = config.read_bytes()
        with patch.dict(os.environ, {"CODEX_HOME": str(custom)}):
            args, isolation = runtime._server_argv()
            self.assertIn("mcp_servers.correct_home.enabled=false", args)
            self.assertNotIn("mcp_servers.wrong_home.enabled=false", args)
            self.assertEqual(isolation["codexHome"], str(custom))
        self.assertEqual(config.read_bytes(), original)

    def test_probe_cache_separates_binary_and_codex_home(self):
        home1, home2 = self.root / "codex-one", self.root / "codex-two"
        home1.mkdir(); home2.mkdir()
        for home in (home1, home2):
            path = home / "config.toml"
            path.write_text('model="same"\n')
            os.utime(path, ns=(1000000000, 1000000000))
        with patch.dict(os.environ, {"CODEX_HOME": str(home1)}):
            first = runtime._readiness_cache_key(self.binary, "same-version", "same-model")
        with patch.dict(os.environ, {"CODEX_HOME": str(home2)}):
            second = runtime._readiness_cache_key(self.binary, "same-version", "same-model")
            other_binary = self.make_binary(self.root / "other-codex")
            third = runtime._readiness_cache_key(other_binary, "same-version", "same-model")
        self.assertNotEqual(first, second)
        self.assertNotEqual(second, third)

    def test_probe_cache_separates_default_home_without_codex_home(self):
        first = runtime._readiness_cache_key(self.binary, "same-version", "same-model")
        with patch.object(runtime.Path, "home", return_value=self.root / "different-user"):
            second = runtime._readiness_cache_key(self.binary, "same-version", "same-model")
        self.assertNotEqual(first, second)

    def test_environment_reports_pinned_binary_and_compatibility_failure(self):
        fake = Mock()
        fake.initialize.side_effect = runtime.CodexRuntimeError("Unknown method initialize: older CLI")
        fake.events_path = self.root / "fake-events.jsonl"
        with patch.object(runtime.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "codex-cli old\n", "")) as version, patch.object(runtime, "_AppServer", return_value=fake) as server:
            result = runtime.get_codex_environment()
        self.assertEqual(result["binary"], str(self.binary))
        self.assertTrue(result["available"])
        self.assertFalse(result["ready"])
        self.assertEqual(result["compatibility"], "not-established")
        self.assertIn("dynamicTools", result["compatibilityHint"])
        self.assertEqual(version.call_args.args[0], [str(self.binary), "--version"])
        self.assertEqual(server.call_args.kwargs["binary"], self.binary)
        fake.close.assert_called_once()

    def test_relative_codex_home_is_rejected_without_rewriting_environment(self):
        with patch.dict(os.environ, {"CODEX_HOME": "relative-home"}):
            with self.assertRaises(runtime.CodexRuntimeError) as caught:
                runtime._codex_home()
            self.assertEqual(os.environ["CODEX_HOME"], "relative-home")
        self.assertEqual(caught.exception.status, "needs_setup")


if __name__ == "__main__":
    unittest.main()
