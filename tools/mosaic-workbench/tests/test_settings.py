import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import settings
import engine


class SettingsTests(unittest.TestCase):
    def test_default_destination_belongs_to_no_author(self):
        with tempfile.TemporaryDirectory() as tmp:
            value = settings.load_settings(Path(tmp), {})
            self.assertEqual(value['workspaceId'], '')
            self.assertEqual(value['folderId'], 'default')
            self.assertTrue(Path(value['libraryZip']).is_relative_to(Path(tmp).resolve()))

    def test_environment_overrides_local_settings_and_relative_paths_follow_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'workbench.local.json').write_text(json.dumps({'workspaceId':'ws-local','codexBinary':'bin/codex'}))
            value = settings.load_settings(root, {'MOSAIC_WORKSPACE_ID':'ws-team'})
            self.assertEqual(value['workspaceId'], 'ws-team')
            self.assertEqual(value['codexBinary'], str(root.resolve()/'bin/codex'))

    def test_config_does_not_accept_credentials_or_unknown_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'workbench.local.json').write_text('{"apiKey":"not-a-real-secret"}')
            with self.assertRaisesRegex(ValueError,'Unknown workbench setting'):
                settings.load_settings(root,{})

    def test_asset_host_requires_uncredentialed_https(self):
        with tempfile.TemporaryDirectory() as tmp:
            for url in ['http://example.test/','https://user:password@example.test/','https://example.test/?key=x']:
                with self.subTest(url=url),self.assertRaises(ValueError):
                    settings.load_settings(Path(tmp),{'MOSAIC_ASSET_BASE_URL':url})
            self.assertEqual(settings.load_settings(Path(tmp),{'MOSAIC_ASSET_BASE_URL':'https://example.test/assets'})['assetBaseUrl'],'https://example.test/assets/')

    def test_invalid_explicit_mosaic_path_does_not_fall_back_to_another_account_tool(self):
        with patch.object(engine,'load_settings',return_value={'mosaicBinary':'/not/a/real/mosaic'}),patch.object(engine.shutil,'which') as which:
            with self.assertRaises(engine.EngineError) as caught:engine._cli_path()
            self.assertEqual(caught.exception.status,'needs_setup')
            which.assert_not_called()

    def test_valid_explicit_mosaic_executable_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary=Path(tmp)/'mosaic';binary.write_text('#!/bin/sh\nexit 0\n');binary.chmod(0o755)
            with patch.object(engine,'load_settings',return_value={'mosaicBinary':str(binary)}):
                self.assertEqual(engine._cli_path(),str(binary.resolve()))


if __name__=='__main__':unittest.main()
