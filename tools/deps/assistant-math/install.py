# SPDX-License-Identifier: BSD-3-Clause
"""Build-only package of the FIRST minimal upstream MathText/Common/XITS closure."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat

def wanted(path: PurePosixPath) -> bool:
    name = path.as_posix()
    if name in ('LICENSE', 'VERSION', 'cmake/jkqtplotter_macros.cmake'):
        return True
    if any(part in ('tests', 'test', 'test-suite', 'examples', 'tools', 'doc') for part in path.parts):
        return False
    if name.startswith('lib/jkqtcommon/'):
        return True
    if not name.startswith('lib/jkqtmathtext/'):
        return False
    if '/resources/' not in name:
        return True
    return name == 'lib/jkqtmathtext/resources/xits.qrc' or (
        name.startswith('lib/jkqtmathtext/resources/xits/') and
        (path.suffix == '.otf' or path.name in ('OFL.txt', 'README.md')))


p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True)
a=p.parse_args();commit='9e9f0af8b140192e3de7ff866a0013e7da5e1e93'
root=a.prefix/'share/edi/assistant/mathtext'/commit;destination=root/'source';members={}
# Only this recipe's namespaced BUILD output is replaced on a reused prefix.
if root.exists() or root.is_symlink():
    if root.is_symlink() or not root.is_dir():raise RuntimeError('Math build output is not an owned regular tree')
    for existing in root.rglob('*'):
        mode=existing.lstat().st_mode
        if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):raise RuntimeError('Math build output contains a non-regular member')
    shutil.rmtree(root)
for path in sorted(a.source.rglob('*')):
    relative=path.relative_to(a.source);mode=path.lstat().st_mode
    if not wanted(PurePosixPath(relative.as_posix())) or stat.S_ISDIR(mode):continue
    if not stat.S_ISREG(mode):raise RuntimeError('Native math source contains a non-regular member')
    target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    with target.open('rb') as stream:members[relative.as_posix()]=hashlib.file_digest(stream,'sha256').hexdigest()
for required in ('lib/jkqtcommon/CMakeLists.txt','lib/jkqtmathtext/CMakeLists.txt','lib/jkqtmathtext/resources/xits/OFL.txt','LICENSE'):
    if required not in members:raise RuntimeError('Native math package is incomplete')
manifest=dict(schema='edi.assistant.math-package/1',commit=commit,archive_sha256='e70f491cee4203a74f76a86c197bd456c89371db35cf7b0068d4db1b21e44e00',source='source',files=members)
(root/'input.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
