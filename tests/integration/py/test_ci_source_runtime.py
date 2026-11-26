# SPDX-License-Identifier: BSD-3-Clause
"""Independent examples for the CI source checks and their publishing inputs."""

import hashlib
import io
import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SOURCE_LINE = b'int plantedPrivateValue = 23;'
SOURCE_BLOB = b'\x00\xffsynthetic source tree payload\x00\x0c'
DIAGNOSTIC = b'public warning at a known location'
SAFE_LINE = b'public job output stays visible'


@pytest.fixture
def runner(tmp_path):
    blobs = tmp_path / 'source-blobs'
    lines = tmp_path / 'source-lines'
    git_input = subprocess.run(
        ['git', 'hash-object', '--stdin'],
        input=SOURCE_BLOB,
        capture_output=True,
        check=True,
        timeout=5,
    )
    blobs.write_bytes(git_input.stdout)
    lines.write_text(hashlib.sha256(SOURCE_LINE).hexdigest() + '\n', encoding='ascii')
    return {
        **{key: val for key, val in os.environ.items() if not key.startswith('CRYSTA_')},
        'GITHUB_ACTIONS': 'true',
        'GITHUB_WORKSPACE': str(ROOT),
        'RUNNER_TEMP': str(tmp_path),
        'CRYSTA_SOURCE_BLOB_LIST': str(blobs),
        'CRYSTA_SOURCE_LINE_LIST': str(lines),
        'GITHUB_STEP_SUMMARY': str(tmp_path / 'summary.md'),
    }


def run_script(script, *args, env, cwd):
    entry = ROOT / 'tools/ci' / script
    assert entry.is_file(), f'{script} must enforce its boundary in the runner'
    return subprocess.run(
        [sys.executable, str(entry), *(str(arg) for arg in args)],
        env=env,
        cwd=cwd,
        capture_output=True,
        check=False,
        timeout=15,
    )


def make_archive(path, payload):
    if path.suffix in {'.zip', '.whl'}:
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as output:
            output.writestr('result/renamed.dat', payload)
    else:
        with tarfile.open(path, 'w:gz' if path.suffix == '.gz' else 'w') as output:
            item = tarfile.TarInfo('result/renamed.dat')
            item.size = len(payload)
            output.addfile(item, io.BytesIO(payload))


@pytest.mark.parametrize('suffix', ['.zip', '.whl', '.tar', '.tar.gz'])
def test_storage_check_reads_members_of_the_bytes_it_will_publish(tmp_path, runner, suffix):
    bundle = tmp_path / ('results' + suffix)
    make_archive(bundle, SAFE_LINE + b'\n')
    clean = run_script('stored_source.py', bundle, env=runner, cwd=tmp_path)
    assert clean.returncode == 0, 'A readable archive of public output is eligible for storage'
    for payload in (SOURCE_BLOB, b'warning:\n   9 | ' + SOURCE_LINE + b'\n'):
        make_archive(bundle, payload)
        refused = run_script('stored_source.py', bundle, env=runner, cwd=tmp_path)
        assert refused.returncode != 0, (
            'A renamed archive member with a source blob or quoted source line cannot be stored'
        )
        assert SOURCE_LINE not in refused.stdout + refused.stderr, (
            'The storage check must not print the line that caused it to refuse publication'
        )


def test_filtered_shell_preserves_public_output_and_child_exit(tmp_path, runner):
    step = tmp_path / 'run.sh'
    step.write_bytes(
        b"printf '%s\\n' '" + SAFE_LINE + b"' '  12 | " + SOURCE_LINE + b"'\n"
        b"printf '%s\\n' '" + DIAGNOSTIC + b"' '" + SOURCE_LINE + b"' >&2\n"
        b"printf '%s\\n' '"
        + SAFE_LINE
        + b"' '"
        + SOURCE_LINE
        + b'\' >> "$GITHUB_STEP_SUMMARY"\nexit 17\n'
    )
    result = run_script('public_log.py', step, env=runner, cwd=tmp_path)
    summary = Path(runner['GITHUB_STEP_SUMMARY']).read_bytes()
    assert result.returncode == 17, 'The filtered shell preserves the exact child failure status'
    assert SAFE_LINE in result.stdout and DIAGNOSTIC in result.stderr and SAFE_LINE in summary, (
        'The filtered shell preserves public stdout, stderr and summary text'
    )
    assert all(SOURCE_LINE not in data for data in (result.stdout, result.stderr, summary)), (
        'Source lines are withheld independently from stdout, stderr and the job summary'
    )
