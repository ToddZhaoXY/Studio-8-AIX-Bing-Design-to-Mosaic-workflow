"""Per-checkout, non-secret settings; environment overrides local JSON."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = {
    'codexBinary': '',
    'mosaicBinary': '',
    'workspaceId': '',
    'folderId': 'default',
    'libraryZip': 'MM_design_library/MM-Design-Libraries-compat-00f36936859b.zip',
    'assetBaseUrl': 'https://toddzhaoxy.github.io/Bing-MM-design-library/',
}
ENV_KEYS = {
    'codexBinary': 'MOSAIC_WORKBENCH_CODEX_BIN',
    'mosaicBinary': 'MOSAIC_WORKBENCH_MOSAIC_BIN',
    'workspaceId': 'MOSAIC_WORKSPACE_ID',
    'folderId': 'MOSAIC_FOLDER_ID',
    'libraryZip': 'MOSAIC_LIBRARY_ZIP',
    'assetBaseUrl': 'MOSAIC_ASSET_BASE_URL',
}


def load_settings(root=None, environ=None):
    root = Path(root or ROOT).resolve()
    env = os.environ if environ is None else environ
    result = dict(DEFAULTS)
    config = root / 'workbench.local.json'
    if config.exists():
        data = json.loads(config.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('workbench.local.json must be a JSON object.')
        if set(data) - set(DEFAULTS):
            raise ValueError('Unknown workbench setting. Use workbench.example.json; do not put credentials in this file.')
        result.update(data)
    for key, name in ENV_KEYS.items():
        if name in env:
            result[key] = env[name]
    if any(not isinstance(value, str) for value in result.values()):
        raise ValueError('Workbench settings must be strings.')
    for key in ('workspaceId', 'folderId'):
        if result[key] and not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', result[key]):
            raise ValueError('Invalid ' + key + ' in workbench settings.')
    url = urlsplit(result['assetBaseUrl'])
    if url.scheme != 'https' or not url.netloc or url.username or url.password or url.query or url.fragment:
        raise ValueError('assetBaseUrl must be an HTTPS directory URL without credentials, query, or fragment.')
    result['assetBaseUrl'] = result['assetBaseUrl'].rstrip('/') + '/'
    for key in ('codexBinary', 'mosaicBinary', 'libraryZip'):
        if result[key]:
            path = Path(result[key]).expanduser()
            result[key] = str(path if path.is_absolute() else root / path)
    return result
