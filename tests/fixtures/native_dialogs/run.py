# SPDX-License-Identifier: BSD-3-Clause
"""Run the real chooser process checks and prevent in-process desktop picker regressions."""

import os
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
for path in (root / 'app/qml').rglob('*.qml'):
    if re.search(r'\b(?:FileDialog|FolderDialog)\s*\{', path.read_text(encoding='utf-8')):
        raise SystemExit(f'In-process desktop chooser in {path}')
client = (root / 'app/src/native_dialog.cpp').read_text(encoding='utf-8')
if re.search(r'\bwaitFor[A-Za-z]*\s*\(', client):
    raise SystemExit('The chooser client must never wait for its child process')
build = Path(sys.argv[1]).resolve()
name = 'native_dialog_probe' + ('.exe' if os.name == 'nt' else '')
executable = build / name
if not executable.is_file():
    executable = build / 'Release' / name
subprocess.run([str(executable)], env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'}, check=True)
