# SPDX-License-Identifier: BSD-3-Clause
"""Packages the recipe's verified Claude Code binary, unmodified, with its licence."""

import argparse
import hashlib
import json
import shutil
import stat
from pathlib import Path

PLATFORMS = {'linux-x64', 'darwin-arm64', 'win32-x64'}


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
p.add_argument('--binary', type=Path, required=True)
p.add_argument('--licenses', type=Path, required=True)
p.add_argument('--prefix', type=Path, required=True)
p.add_argument('--platform', required=True)
p.add_argument('--version', required=True)
p.add_argument('--sha256', required=True)
a = p.parse_args()
if a.platform not in PLATFORMS:
    raise RuntimeError('Unqualified runtime platform')
entrypoint = 'claude.exe' if a.platform == 'win32-x64' else 'claude'
if a.binary.name != entrypoint or not stat.S_ISREG(a.binary.lstat().st_mode):
    raise RuntimeError('Claude Code binary missing')
with a.binary.open('rb') as stream:
    if hashlib.file_digest(stream, 'sha256').hexdigest() != a.sha256:
        raise RuntimeError('Claude Code binary does not match its pin')
npm = a.licenses
if json.loads((npm / 'package.json').read_text()).get('version') != a.version:
    raise RuntimeError('Claude Code licence package is another release')
licence = npm / 'LICENSE.md'
if not stat.S_ISREG(licence.lstat().st_mode):
    raise RuntimeError('Claude Code licence missing')

root = a.prefix / 'share/edi/assistant/claude' / a.version
payload = root / 'payload'
# Rattler may reuse a build prefix; replace only this package's own output.
if root.exists() or root.is_symlink():
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError('Runtime build output is not an owned regular tree')
    files(root)
    shutil.rmtree(root)
payload.mkdir(parents=True)
shutil.copyfile(a.binary, payload / entrypoint)
if a.platform != 'win32-x64':
    # Downloads arrive without the executable bit; only the mode changes, never the bytes.
    (payload / entrypoint).chmod(0o755)
shutil.copyfile(licence, payload / 'LICENSE.md')
identity = {
    'runtime': 'claude',
    'version': a.version,
    'platform': a.platform,
    'entrypoint': entrypoint,
}
(payload / 'edi-runtime.json').write_text(json.dumps(identity, indent=2, sort_keys=True) + '\n')
members = files(payload)
if members[entrypoint] != a.sha256:
    raise RuntimeError('Runtime bytes changed while packaging')
manifest = {
    'schema': 'edi.assistant.vendor-runtime-package/1',
    'root': 'payload',
    'runtime': 'claude',
    'version': a.version,
    'target': a.platform,
    'archive_sha256': a.sha256,
    'files': members,
}
(root / 'input.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
