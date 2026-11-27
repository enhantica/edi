# SPDX-License-Identifier: BSD-3-Clause
"""Packages the recipe's verified Copilot CLI binary, unmodified, with its licence files."""

import argparse
import hashlib
import json
import os
import shutil
import stat
from pathlib import Path

PLATFORMS = {'linux-x64', 'darwin-arm64', 'win32-x64'}
LICENCES = ['LICENSE.md', 'Unicode.LICENSE.txt']


def files(root) -> dict:
    result = {}
    for path in sorted(root.rglob('*')):
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise RuntimeError('Runtime package contains a non-regular member')
        with path.open('rb') as stream:
            result[path.relative_to(root).as_posix()] = hashlib.file_digest(
                stream, 'sha256'
            ).hexdigest()
    return result


p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--prefix', type=Path, required=True)
p.add_argument('--platform', required=True)
p.add_argument('--version', required=True)
p.add_argument('--archive-sha256', required=True)
a = p.parse_args()
if a.platform not in PLATFORMS:
    raise RuntimeError('Unqualified runtime platform')
entrypoint = 'copilot.exe' if a.platform == 'win32-x64' else 'copilot'
source = a.source
metadata = json.loads((source / 'package.json').read_text())
if metadata.get('name') != f'@github/copilot-{a.platform}' or metadata.get('version') != a.version:
    raise RuntimeError('Copilot CLI package identity changed')
original = files(source)
# Every licence file the package ships goes with the binary.
shipped = sorted(name for name in original if 'LICENSE' in name.upper() and '/' not in name)
if shipped != sorted(LICENCES) or entrypoint not in original:
    raise RuntimeError('Copilot CLI package layout changed')
if a.platform != 'win32-x64' and not os.access(source / entrypoint, os.X_OK):
    raise RuntimeError('Copilot CLI binary is not executable')

root = a.prefix / 'share/edi/assistant/copilot' / a.version
payload = root / 'payload'
# Rattler may reuse a build prefix; replace only this package's own output.
if root.exists() or root.is_symlink():
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError('Runtime build output is not an owned regular tree')
    files(root)
    shutil.rmtree(root)
payload.mkdir(parents=True)
for name in [entrypoint, *LICENCES]:
    shutil.copy2(source / name, payload / name)
identity = {
    'runtime': 'copilot',
    'version': a.version,
    'platform': a.platform,
    'entrypoint': entrypoint,
}
(payload / 'edi-runtime.json').write_text(json.dumps(identity, indent=2, sort_keys=True) + '\n')
members = files(payload)
if any(members[name] != original[name] for name in [entrypoint, *LICENCES]):
    raise RuntimeError('Runtime bytes changed while packaging')
manifest = {
    'schema': 'edi.assistant.vendor-runtime-package/1',
    'root': 'payload',
    'runtime': 'copilot',
    'version': a.version,
    'target': a.platform,
    'archive_sha256': a.archive_sha256,
    'files': members,
}
(root / 'input.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
