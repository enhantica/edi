"""The desktop receipt for the normal app, which observes itself under --test-observer scan-screen.

Nothing is compiled here: the app is the one `pixi run -e app app-build` (or CI's app job) built at
build/app/app/edi_app. The receipt binds it to the current sources and SDK as build.py's does.
"""

import hashlib
import json
import subprocess
from pathlib import Path

from tests.fixtures.app_environment.closure import dependencies
from tests.fixtures.scan_app.build_probe import (
    fingerprint,
    fingerprint_headers,
    sdk_inputs,
    validate_current_inputs,
)

APP = Path('build/app/app/edi_app')


def receipt(root, output, sdk, engine_source):
    root, output, sdk = Path(root).resolve(), Path(output).resolve(), Path(sdk).resolve()
    executable = root / APP
    if not executable.is_file():
        raise RuntimeError(
            'The screen observer runs the normal app: build it with `pixi run -e app app-build`'
        )
    fixture = Path(__file__).resolve().parent
    production = fingerprint(root)
    manifest = json.loads((sdk / 'share/crysta-sdk/manifest.json').read_text())
    record = {
        'dependencies': dependencies('screen', root),
        'backend': 'desktop',
        'production': production,
        'compiled_inputs': {'production': production, 'sdk': sdk_inputs(sdk, engine_source)},
        'source_sha': subprocess.check_output(
            ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True
        ).strip(),
        'engine_sha': (sdk / '.crysta-sha').read_text().strip(),
        'sdk_headers': fingerprint_headers(sdk / 'include'),
        'sdk_manifest': manifest,
        'binary': hashlib.sha256(executable.read_bytes()).hexdigest(),
        'executable': str(executable),
        'fixture': {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in fixture.iterdir()
            if p.is_file()
        },
    }
    validate_current_inputs(record, root, sdk, engine_source)
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'receipt.json'
    path.write_text(json.dumps(record, indent=2) + '\n')
    return path
