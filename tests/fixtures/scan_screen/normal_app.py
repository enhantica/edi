"""The desktop receipt for the normal app, which observes itself under --test-observer scan-screen.

Nothing is compiled here: the app is the one `pixi run -e app app-build` (or CI's app job) built at
build/app/app/edi_app. It must carry the canonical edi-build-commit marker from
cmake/build_commit.cmake (MARKER and MARK_DIRTY); checkout HEAD alone is not build evidence.
"""

import hashlib
import json
import subprocess
from pathlib import Path

from tests.fixtures.app_environment.closure import dependencies
from tests.fixtures.fast_chart_redraws.rendering import native_arguments
from tests.fixtures.scan_app.build_probe import (
    fingerprint,
    fingerprint_headers,
    sdk_inputs,
    validate_current_inputs,
)
from tools.ci.latency_bank import RefusedError, executable_build

APP = Path('build/app/app/edi_app')


def qualified_identity(root, executable):
    head = subprocess.check_output(
        ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True
    ).strip()
    try:
        built = executable_build(executable)
    except RefusedError as error:
        raise RuntimeError(
            'Desktop receipt refuses ambiguous or unreadable build identity'
        ) from error
    if built != head:
        raise RuntimeError(
            f'Desktop receipt requires embedded build identity {head}; '
            f'found {built or "no marker"}. The normal app needs the canonical '
            'CMake MARKER/MARK_DIRTY stamp and a rebuild from clean HEAD.'
        )
    dirty = subprocess.check_output(
        ['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=no'], text=True
    )
    untracked = subprocess.check_output(
        [
            'git',
            '-C',
            str(root),
            'ls-files',
            '--others',
            '--exclude-standard',
            '--',
            'app',
            'core',
            'cmake',
            'data',
            'shared',
            'docs/user/cli',
        ],
        text=True,
    )
    if dirty or untracked:
        raise RuntimeError('Desktop receipt refuses an uncommitted source tree')
    return {
        'kind': 'embedded-commit',
        'source_sha': built,
        'binary': hashlib.sha256(executable.read_bytes()).hexdigest(),
    }


def validate_identity(record, root):
    executable = Path(record['executable']).resolve()
    delivered = (root / APP).resolve()
    if Path(record.get('delivered_executable', executable)).resolve() != delivered:
        raise RuntimeError('Desktop receipt must identify the delivered normal app')
    if executable != delivered:
        snapshot = Path(native_arguments([delivered])[0]).resolve()
        if executable != snapshot:
            raise RuntimeError('Desktop receipt requires its checked native artifact snapshot')
        # Keep checking the delivered build identity, even when a stable copy is executed.
        qualified_identity(root, delivered)
    actual = qualified_identity(root, executable)
    if (
        record.get('build_identity') != actual
        or record['source_sha'] != actual['source_sha']
        or record['binary'] != actual['binary']
    ):
        raise RuntimeError('Desktop receipt refuses unsealed or relabelled binary build identity')


def receipt(root, output, sdk, engine_source):
    root, output, sdk = Path(root).resolve(), Path(output).resolve(), Path(sdk).resolve()
    executable = root / APP
    if not executable.is_file():
        raise RuntimeError(
            'The screen observer runs the normal app: build it with `pixi run -e app app-build`'
        )
    delivered = executable
    qualified_identity(root, delivered)
    executable = Path(native_arguments([delivered])[0])
    identity = qualified_identity(root, executable)
    fixture = Path(__file__).resolve().parent
    production = fingerprint(root)
    manifest = json.loads((sdk / 'share/crysta-sdk/manifest.json').read_text())
    record = {
        'dependencies': dependencies('screen', root),
        'backend': 'desktop',
        'production': production,
        'compiled_inputs': {'production': production, 'sdk': sdk_inputs(sdk, engine_source)},
        'source_sha': identity['source_sha'],
        'build_identity': identity,
        'engine_sha': (sdk / '.crysta-sha').read_text().strip(),
        'sdk_headers': fingerprint_headers(sdk / 'include'),
        'sdk_manifest': manifest,
        'binary': hashlib.sha256(executable.read_bytes()).hexdigest(),
        'executable': str(executable),
        'delivered_executable': str(delivered),
        'fixture': {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in fixture.iterdir()
            if p.is_file()
        },
    }
    validate_current_inputs(record, root, sdk, engine_source)
    validate_identity(record, root)
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'receipt.json'
    path.write_text(json.dumps(record, indent=2) + '\n')
    return path
