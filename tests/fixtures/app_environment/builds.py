"""Process-local reuse of source-qualified app hosts and their captured observations."""

import copy
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from tests.fixtures.app_environment.closure import dependencies
from tests.fixtures.scan_app.build_probe import fingerprint, sdk_inputs

BUILDS = {}
CAPTURES = {}


def environment():
    return {
        key: value
        for key, value in os.environ.items()
        if key not in {'PYTEST_CURRENT_TEST', 'EDI_APP_BUILD_EVENTS'}
        and not key.endswith('_RECEIPT')
    }


def inputs(owner, backend, root, sdk, source, fixture):
    return {
        'dependencies': dependencies(owner, root),
        'owner': owner,
        'backend': backend,
        'paths': [str(path.resolve()) for path in (root, sdk, source, fixture)],
        'source_sha': subprocess.check_output(
            ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True
        ).strip(),
        'production': fingerprint(root),
        'sdk': sdk_inputs(sdk, source),
        'sdk_files': {
            str(path.relative_to(sdk)): hashlib.sha256(path.read_bytes()).hexdigest()
            for base in (sdk / 'include', sdk / 'lib', sdk / 'share/crysta-sdk')
            for path in base.rglob('*')
            if path.is_file()
        },
        'fixture': {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in fixture.iterdir()
            if path.is_file()
        },
        'environment': environment(),
    }


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def build_receipt(owner, backend, root, sdk, source, fixture, build):
    before = inputs(owner, backend, root, sdk, source, fixture)
    key = digest(before)
    if key not in BUILDS:
        start = time.monotonic()
        receipt = build()
        if inputs(owner, backend, root, sdk, source, fixture) != before:
            raise RuntimeError('App build inputs changed while preparing the cached host')
        BUILDS[key] = receipt
        event = os.environ.get('EDI_APP_BUILD_EVENTS')
        if event:
            with Path(event).open('a', encoding='utf-8') as stream:
                stream.write(
                    json.dumps({
                        'owner': owner,
                        'backend': backend,
                        'key': key,
                        'seconds': time.monotonic() - start,
                        'receipt': str(receipt),
                    })
                    + '\n'
                )
    return BUILDS[key]


def capture_once(receipt, capture):
    key = digest({'receipt': receipt, 'environment': environment()})
    if key not in CAPTURES:
        CAPTURES[key] = copy.deepcopy(capture())
    return copy.deepcopy(CAPTURES[key])
