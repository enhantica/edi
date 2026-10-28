# SPDX-License-Identifier: BSD-3-Clause
"""Build-only packaging of the recipe's verified original native closure."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

def files(root):
    result={}
    for path in sorted(root.rglob('*')):
        mode=path.lstat().st_mode
        if stat.S_ISDIR(mode):continue
        if not stat.S_ISREG(mode):raise RuntimeError('Native runtime contains a non-regular member')
        with path.open('rb') as stream:result[path.relative_to(root).as_posix()]=hashlib.file_digest(stream,'sha256').hexdigest()
    return result

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--licenses',type=Path,required=True)
p.add_argument('--prefix',type=Path,required=True);p.add_argument('--target',required=True);p.add_argument('--archive-sha256',required=True)
a=p.parse_args()
if a.target not in ('x86_64-unknown-linux-musl','aarch64-apple-darwin','x86_64-pc-windows-msvc'):raise RuntimeError('Unqualified runtime target')
windows=a.target=='x86_64-pc-windows-msvc'
suffix='.exe' if windows else ''
metadata=json.loads((a.source/'codex-package.json').read_text())
expected=dict(layoutVersion=1,version='0.162.1',target=a.target,variant='codex-app-server',entrypoint='bin/codex-app-server'+suffix,resourcesDir='codex-resources',pathDir='codex-path')
if any(metadata.get(k)!=v for k,v in expected.items()):raise RuntimeError('Official runtime layout changed')
original=files(a.source);files(a.licenses)
required=['bin/codex-app-server'+suffix,'bin/codex-code-mode-host'+suffix,'codex-path/rg'+suffix]
if windows:
    required.extend(['codex-resources/codex-command-runner.exe','codex-resources/codex-windows-sandbox-setup.exe'])
else:
    required.append('codex-resources/zsh/bin/zsh')
    if a.target=='x86_64-unknown-linux-musl':required.append('codex-resources/bwrap')
# FIRST upstream layout.py requires POSIX executable mode only on non-Windows.
if any(item not in original or (not windows and not os.access(a.source/item,os.X_OK)) for item in required):raise RuntimeError('Native runtime executable missing')
root=a.prefix/'share/edi/assistant/runtime/0.162.1';payload=root/'payload'
# Rattler may reuse this recipe's BUILD prefix across metadata workspaces.
# Replace only our complete namespaced build output, never another package,
# installed app environment, source tree or shared artifact cache.
if root.exists() or root.is_symlink():
    if root.is_symlink() or not root.is_dir():raise RuntimeError('Runtime build output is not an owned regular tree')
    files(root)  # Reject links/special members before replacing our own output.
    shutil.rmtree(root)
shutil.copytree(a.source,payload,copy_function=shutil.copy2)
shutil.copytree(a.licenses,payload/'edi-licenses',copy_function=shutil.copy2)
if any(files(payload).get(k)!=v for k,v in original.items()):raise RuntimeError('Runtime bytes changed while packaging')
manifest=dict(schema='edi.assistant.runtime-package/1',root='payload',version='0.162.1',target=a.target,archive_sha256=a.archive_sha256,dedicated=False,files=files(payload))
(root/'input.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
