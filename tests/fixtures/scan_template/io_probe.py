"""Observe input opens from project loading through the first committed result."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import edi

project_dir = Path(sys.argv[1]).resolve()
log = Path(os.environ['EDI_C08_NATIVE_OBSERVER_LOG'])
scan = project_dir / 'experiments/d20_scan'
observed = []
os.environ['EDI_C08_NATIVE_OBSERVER_ACTIVE'] = '1'
if sys.argv[2].startswith('eager-load'):
    directory = os.open(scan, os.O_RDONLY)
    previous = Path.cwd()
    try:
        os.chdir(scan)
        for file in sorted(scan.glob('*.dat')):
            if sys.argv[2] == 'eager-load-openat':
                descriptor = os.open(file.name, os.O_RDONLY, dir_fd=directory)
                os.read(descriptor, 1)
                os.close(descriptor)
            elif sys.argv[2] == 'eager-load-relative':
                Path(file.name).read_bytes()
            else:
                file.read_bytes()
    finally:
        os.chdir(previous)
        os.close(directory)
project = edi.Project.load(project_dir)


def on_file_complete(_row):
    files = set()
    unresolved = []
    for event in log.read_text(encoding='utf-8').splitlines():
        operation, _, path = event.partition('\t')
        if operation == 'unresolved':
            unresolved.append(path)
        file = Path(path)
        if file.parent == scan and file.suffix == '.dat':
            files.add(str(file))
    observed.append({'files': sorted(files), 'unresolved': unresolved})


project.analysis.fit(on_file_complete=on_file_complete, should_cancel=lambda: bool(observed))
os.environ['EDI_C08_NATIVE_OBSERVER_ACTIVE'] = '0'
print(json.dumps(observed[0] if observed else {'files': [], 'unresolved': []}))
