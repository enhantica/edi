"""Observe native scan-file opens at the first committed result."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import edi

project_dir = Path(sys.argv[1])
log = Path(os.environ['EDI_C08_NATIVE_OBSERVER_LOG'])
project = edi.Project.load(project_dir)
scan = project_dir / 'experiments/d20_scan'
observed = []
os.environ['EDI_C08_NATIVE_OBSERVER_ACTIVE'] = '1'
if sys.argv[2] == 'eager':
    for file in scan.glob('*.dat'):
        file.read_bytes()


def on_file_complete(_row):
    files = set()
    for event in log.read_text(encoding='utf-8').splitlines():
        _, _, path = event.partition('\t')
        file = Path(path)
        if file.parent == scan and file.suffix == '.dat':
            files.add(file.name)
    observed.append(sorted(files))


project.analysis.fit(on_file_complete=on_file_complete, should_cancel=lambda: bool(observed))
os.environ['EDI_C08_NATIVE_OBSERVER_ACTIVE'] = '0'
print(json.dumps({'opened_at_first_row': observed[0] if observed else []}))
