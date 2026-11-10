# SPDX-License-Identifier: BSD-3-Clause
"""Author one-entry collections, archive members and outside canaries independently."""

import hashlib
import json
import os
import stat
import zipfile
from pathlib import Path

PROJECT = b'data_project\n_project.name boundary-reference\n'
DATA = b'1.25 17.125 0.5\n2.75 8.625 0.25\n'
CANARY = b'outside sentinel 31.625; keep unchanged\n'


def make(root, identity='safe-project', *, kind='project', member=None, outside=None):
    root.mkdir(parents=True, exist_ok=True)
    if kind == 'project':
        path = root / 'project.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('reference/project.edi', PROJECT)
            archive.writestr('reference/structures/readme.txt', b'independent archive member\n')
            if member == 'directory-conflict':
                archive.writestr('reference/blocked', b'ordinary file, not a directory\n')
                archive.writestr('reference/blocked/', b'')
            elif member == 'conflict':
                archive.writestr('reference/blocked', b'ordinary file, not a directory\n')
                archive.writestr('reference/blocked/child', b'cannot be published\n')
            elif member == 'symlink':
                link = zipfile.ZipInfo('escape-link')
                link.create_system = 3
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(link, os.fsencode(outside))
                archive.writestr('escape-link/written.edi', PROJECT)
            elif member:
                archive.writestr(member, PROJECT)
    else:
        path = root / 'payload.xye'
        path.write_bytes(DATA)
    content = path.read_bytes()
    file = {
        'path': path.name,
        'format': 'zip' if kind == 'project' else 'xye',
        'bytes': len(content),
        'sha256': hashlib.sha256(content).hexdigest(),
    }
    index = {
        'schema': 'edi-data-index/1',
        'entries': [
            {
                'id': identity,
                'kind': kind,
                'name': 'Independent boundary record',
                'description': 'Authored containment fixture',
                'files': [file],
            }
        ],
    }
    (root / 'index.json').write_text(json.dumps(index), encoding='utf-8')
    return file


def attack_id(form, outside):
    drive = outside.drive or 'C:'
    windows = str(outside / 'drive').replace('/', '\\')
    if not outside.drive:
        windows = drive + windows
    choices = {
        'parent': '../outside/parent',
        'absolute': str(outside / 'absolute'),
        'backslash-parent': '..\\outside\\backslash',
        'drive-absolute': windows,
        'drive-relative': drive + '..\\outside\\relative',
        'extended-drive': '\\\\?\\' + windows,
    }
    return choices[form]


def archive_member(form, outside):
    if form == 'parent':
        return '../../outside/archive.edi'
    if form == 'absolute':
        return str(outside / 'archive.edi')
    if form == 'drive':
        return attack_id('drive-absolute', outside) + '.edi'
    return 'symlink'


def snapshot(root, exclude=None):
    records = {}
    if not root.exists():
        return records
    for directory, children, files in os.walk(root, followlinks=False):
        base = Path(directory)
        children[:] = [
            name
            for name in children
            if exclude is None or not (base / name).is_relative_to(exclude)
        ]
        for name in [*children, *files]:
            path = base / name
            if exclude is not None and path.is_relative_to(exclude):
                continue
            if path.is_symlink():
                value = ('symlink', str(path.readlink()))
            elif path.is_file():
                value = ('file', path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
            else:
                value = ('directory',)
            records[path.relative_to(root).as_posix()] = value
    return records
