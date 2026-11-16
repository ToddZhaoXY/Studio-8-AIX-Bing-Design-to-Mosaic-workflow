"""Versioned workbench skill packages. Never execute package scripts on import."""
from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import stat
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

OFFICIAL_URL = 'https://vibehub.microsoft.com/app/anthonyleung-fp-t-a/'
SKILL_NAME = 'mosaic-gen-workflow'


def metadata(folder: Path) -> dict:
    raw = (folder / 'SKILL.md').read_bytes()
    text = raw.decode('utf-8')
    front = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.S)
    if not front or not re.search(r'^name:\s*[\"\x27]?mosaic-gen-workflow[\"\x27]?\s*$', front[1], re.M):
        raise ValueError('The skill package must contain a SKILL.md with name: mosaic-gen-workflow.')
    if not re.search(r'^description:\s*\S', front[1], re.M):
        raise ValueError('SKILL.md is missing its description.')
    version = re.search(r'(?im)^#\s+Mosaic Gen Workflow\s*\(v([0-9]+(?:\.[0-9]+){1,3})\b', text)
    if not version:
        raise ValueError('No version was found in SKILL.md. Import a complete, versioned skill package.')
    files = sorted(p for p in folder.rglob('*') if p.is_file())
    digest = hashlib.sha256()
    for file in files:
        if file.is_symlink():
            raise ValueError('Skill packages cannot contain symbolic links.')
        digest.update(file.relative_to(folder).as_posix().encode())
        digest.update(file.read_bytes())
    for file in files:
        if file.suffix != '.md':
            continue
        for link in re.findall(r'\]\(([^)]+)\)', file.read_text('utf-8')):
            link = link.strip().split()[0].strip('<>')
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', link) or link.startswith('#'):
                continue
            target = (file.parent / link.split('#')[0]).resolve()
            if not target.is_relative_to(folder.resolve()) or not target.is_file():
                raise ValueError(f'A skill reference is missing or outside the package: {link}')
    return {'name': SKILL_NAME, 'version': version[1], 'sha256': digest.hexdigest(),
            'fileCount': len(files), 'title': f'Mosaic Gen Workflow v{version[1]}'}


class SkillStore:
    def __init__(self, project_root: Path):
        self.root = project_root / 'tools/mosaic-workbench/state/skills'
        self.root.mkdir(parents=True, exist_ok=True)
        self.active_file = self.root / 'active.json'
        if not self.active_file.exists():
            source = project_root / '.agents/skills' / SKILL_NAME
            info = metadata(source)
            self._store(source, info, 'project-installed')
            self.activate(info['id'])

    def _store(self, folder, info, source):
        info['id'] = 'v' + info['version'] + '-' + info['sha256'][:12]
        target = self.root / info['id']
        if not target.exists():
            temp = Path(tempfile.mkdtemp(prefix='.import-', dir=self.root))
            try:
                shutil.copytree(folder, temp / 'package')
                info.update(source=source, importedAt=datetime.now(timezone.utc).isoformat())
                (temp / 'metadata.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), 'utf-8')
                temp.rename(target)
            finally:
                if temp.exists():
                    shutil.rmtree(temp)
        return info

    def list(self):
        active = json.loads(self.active_file.read_text())['id']
        versions = []
        for path in self.root.glob('v*/metadata.json'):
            info = json.loads(path.read_text())
            info['active'] = info['id'] == active
            versions.append(info)
        versions.sort(key=lambda i: tuple(int(n) for n in i['version'].split('.')), reverse=True)
        return {'activeId': active, 'versions': versions, 'officialUrl': OFFICIAL_URL,
                'scope': 'workbench', 'note': 'Skill versions are stored separately. Running tasks keep their original snapshot.'}

    def resolve(self, skill_id=None):
        skill_id = skill_id or json.loads(self.active_file.read_text())['id']
        if not re.fullmatch(r'v\d+(?:\.\d+){1,3}-[0-9a-f]{12}', skill_id):
            raise ValueError('Invalid skill version.')
        folder = self.root / skill_id / 'package'
        info = json.loads((folder.parent / 'metadata.json').read_text())
        if metadata(folder)['sha256'] != info['sha256']:
            raise ValueError('The skill files have changed. Import the complete package again.')
        return folder, info

    def activate(self, skill_id):
        _, info = self.resolve(skill_id)
        tmp = self.active_file.with_suffix('.tmp')
        tmp.write_text(json.dumps({'id': info['id']}))
        tmp.replace(self.active_file)
        return info

    def import_zip(self, payload: bytes, filename='skill.zip'):
        if len(payload) > 24 * 1024 * 1024:
            raise ValueError('The skill package exceeds 24 MB.')
        with tempfile.TemporaryDirectory(prefix='.check-', dir=self.root) as tmp:
            folder = Path(tmp)
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                infos = archive.infolist()
                if len(infos) > 2000 or sum(i.file_size for i in infos) > 64 * 1024 * 1024:
                    raise ValueError('The extracted skill package is too large.')
                seen = set()
                for item in infos:
                    name = item.orig_filename
                    path = PurePosixPath(name)
                    if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or '\x00' in name:
                        raise ValueError('The skill package contains an unsafe path.')
                    key = name.rstrip('/').casefold()
                    if key in seen:
                        raise ValueError('The skill package contains duplicate paths.')
                    seen.add(key)
                    kind = stat.S_IFMT(item.external_attr >> 16)
                    if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                        raise ValueError('The skill package contains links or special files.')
                    if item.flag_bits & 1:
                        raise ValueError('Encrypted skill packages are not supported.')
                    if item.is_dir() or name.startswith('__MACOSX/'):
                        continue
                    target = folder.joinpath(*path.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(item))
                entries = [p for p in folder.rglob('SKILL.md') if not any(n.startswith('.') for n in p.relative_to(folder).parts)]
                if len(entries) != 1:
                    raise ValueError('Import a complete ZIP containing exactly one Mosaic skill.')
                package = entries[0].parent
                info = metadata(package)
                self._store(package, info, Path(filename).name)
                is_active = self.list()['activeId'] == info['id']
                return {**info, 'activated': False, 'alreadyActive': is_active,
                        'message': 'This version is already active.' if is_active else 'Package verified. Select Activate to use it for new runs.'}

    def snapshot(self, skill_id, output):
        source, info = self.resolve(skill_id)
        shutil.copytree(source, output)
        return info
