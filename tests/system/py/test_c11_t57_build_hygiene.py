"""7b: exercise both actual shell build paths with recorded CMake argv.

Linux proves propagation and reconfiguration, not the macOS linker result.
The fleet verify-macos clean build remains the target-warning acceptance gate.
"""

import hashlib
import io
import json
import tarfile

import pytest
from test_e09_t58_float_build_protocol import (
    _BuildHarness,  # noqa: PLC2701 — shared deterministic build harness
)


def calls(harness):
    return [
        json.loads(line) for line in (harness.root / 'cmake-calls.jsonl').read_text().splitlines()
    ]


def definitions(argv):
    return dict(arg[2:].split('=', 1) for arg in argv if arg.startswith('-D') and '=' in arg)


def require_hygiene(rows, target):
    configured = [definitions(row) for row in rows if '-S' in row]
    assert len(configured) == 1, '/ core-build configures edi alone against its prebuilt SDK'
    assert all(row.get('CMAKE_OSX_DEPLOYMENT_TARGET') == target for row in configured), (
        ' every configure must explicitly refresh the compile/link deployment target'
    )


@pytest.mark.parametrize('consumer', [False, True])
def test_every_build_path_propagates_hygiene_and_refreshes_target(tmp_path, consumer):
    harness = _BuildHarness(tmp_path)
    cmake = tmp_path / 'bin/cmake'
    original = cmake.read_text()
    original = original.replace(
        "if name == 'cmake':",
        "if name == 'cmake':\n"
        "    with (root / 'cmake-calls.jsonl').open('a') as log:\n"
        "        log.write(json.dumps(args) + '\\n')",
    )
    cmake.write_text(original)
    if consumer:
        harness.env['CRYSTA_CONSUMER_SRC'] = str(harness.sibling)
    for target in ('13.4', '14.2'):
        # The independently packaged SDK must declare this same target: edi no
        # longer recompiles a different crysta deployment target on demand.
        for folder in ('ordinary-sdk', 'candidate-sdk'):
            sdk = tmp_path / folder / 'sdk'
            manifest = sdk / 'share/crysta-sdk/manifest.json'
            data = json.loads(manifest.read_text())
            data['fingerprint']['macos_deployment_target'] = target
            manifest.write_text(json.dumps(data))
        archive = io.BytesIO()
        sdk = tmp_path / 'ordinary-sdk/sdk'
        with tarfile.open(fileobj=archive, mode='w:gz') as tar:
            for file in sorted(sdk.rglob('*')):
                if file.is_file():
                    tar.add(file, arcname=str(file.relative_to(sdk)))
        (harness.release / 'published-sdk.tar.gz').write_bytes(archive.getvalue())
        digest = hashlib.sha256(archive.getvalue()).hexdigest()
        state_file = harness.release / 'download.json'
        state = json.loads(state_file.read_text())
        old_digest = state['metadata']['assets'][0]['digest'].removeprefix('sha256:')
        state['metadata']['assets'][0]['digest'] = 'sha256:' + digest
        state_file.write_text(json.dumps(state))
        pin = harness.edi / 'pixi.toml'
        pin.write_text(pin.read_text().replace(old_digest, digest))
        harness.env['MACOSX_DEPLOYMENT_TARGET'] = target
        (tmp_path / 'cmake-calls.jsonl').write_text('')
        result = harness.run('core-build.sh')
        assert result.returncode == 0, ' controlled core-build must finish: ' + result.stderr
        rows = calls(harness)
        require_hygiene(rows, target)
        # Exercise omitted-option escapes at the argv boundary, including stale cached target.
        for option in ('CMAKE_OSX_DEPLOYMENT_TARGET',):
            damaged = [[arg for arg in row if not arg.startswith(f'-D{option}=')] for row in rows]
            with pytest.raises(AssertionError, match='deployment target'):
                require_hygiene(damaged, target)


def test_build_option_omission_controls_are_exercised():
    rows = [['-S', 'edi', '-DCMAKE_OSX_DEPLOYMENT_TARGET=14.2']]
    require_hygiene(rows, '14.2')
    for option in ('CMAKE_OSX_DEPLOYMENT_TARGET',):
        damaged = [[arg for arg in row if not arg.startswith(f'-D{option}=')] for row in rows]
        with pytest.raises(AssertionError, match='deployment target'):
            require_hygiene(damaged, '14.2')
    with pytest.raises(AssertionError, match='deployment target'):
        require_hygiene(rows, '13.4')
