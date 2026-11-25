# SPDX-License-Identifier: BSD-3-Clause
"""Independent examples for the CI source checks and their publishing inputs."""

import hashlib
import io
import os
import re
import shutil
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


def compile_warning(scratch, cache, runner, name, *, reveal):
    compiler = shutil.which('cc')
    ccache = shutil.which('ccache')
    assert compiler and ccache, 'The cache test requires cc and ccache on the runner'
    source = scratch / f'{name}.c'
    source.write_bytes(
        b'int f(void) {\n'
        + (SOURCE_LINE if reveal else b'int publicValue = 31;')
        + b'\nreturn 0;\n}\n'
    )
    disable_caret = (
        '-fno-caret-diagnostics' if sys.platform == 'darwin' else '-fno-diagnostics-show-caret'
    )
    flags = [] if reveal else [disable_caret]
    before = set(cache.rglob('*'))
    result = subprocess.run(
        [
            ccache,
            compiler,
            '-Wall',
            '-fdiagnostics-color=never',
            *flags,
            '-c',
            str(source),
            '-o',
            str(source.with_suffix('.o')),
        ],
        env={
            **runner,
            'CCACHE_DIR': str(cache),
            'CCACHE_CONFIGPATH': os.devnull,
            'CCACHE_NODIRECT': 'true',
            'LC_ALL': 'C',
        },
        cwd=scratch,
        capture_output=True,
        timeout=10,
        check=True,
    )
    assert b'unused variable' in result.stderr, 'An actual compiler warning is stored by ccache'
    assert (SOURCE_LINE in result.stderr) is reveal, (
        'Real compiler stderr contains the planted source line only in the unsafe control'
    )
    results = []
    for path in set(cache.rglob('*')) - before:
        if not path.is_file():
            continue
        inspect = subprocess.run(
            [ccache, '--inspect', str(path)],
            capture_output=True,
            timeout=5,
            check=False,
        )
        if inspect.returncode == 0 and b'(result)' in inspect.stdout:
            results.append(path)
    assert len(results) == 1, 'A successful compile wrote one actual ccache result'
    return results[0]


@pytest.mark.skipif(os.name != 'posix', reason='The ccache fixture uses a POSIX C compiler')
@pytest.mark.parametrize(
    'family',
    [
        'new',
        'crysta-sdk',
        'core',
        'app',
        'app-windows',
        'installer',
        'wasm',
    ],
)
def test_full_cache_save_omits_source_diagnostics_in_new_and_untouched_restored_entries(
    tmp_path, runner, family
):
    original = tmp_path / 'producer-cache'
    restored = tmp_path / f'ccache2-{family}'
    planted = compile_warning(tmp_path, original, runner, 'private', reveal=True)
    if family == 'new':
        save_dir = original
    else:
        shutil.copytree(original, restored)
        save_dir = restored
    restored_entry = save_dir / planted.relative_to(original)
    extracted = tmp_path / 'cache-result'
    extracted.mkdir()
    subprocess.run(
        [shutil.which('ccache'), '--extract-result', str(restored_entry)],
        cwd=extracted,
        capture_output=True,
        timeout=5,
        check=True,
    )
    assert any(
        SOURCE_LINE in re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', entry.read_bytes())
        for entry in extracted.glob('*.stderr')
    ), 'The actual cache entry contains the source line in saved stderr'
    old_bytes = restored_entry.read_bytes()
    old_time = restored_entry.stat().st_mtime_ns
    allowed = compile_warning(tmp_path, save_dir, runner, 'public', reveal=False)
    assert (
        restored_entry.read_bytes() == old_bytes and restored_entry.stat().st_mtime_ns == old_time
    ), 'The restored unsafe result remained untouched during the new compile'
    checked = run_script('ccache_entries.py', save_dir, env=runner, cwd=tmp_path)
    assert checked.returncode == 0, (
        'The cache directory can be saved after removing unsafe results'
    )
    assert not restored_entry.exists() and allowed.is_file(), (
        'The exact saved cache drops the unsafe result and keeps the new harmless result'
    )
    assert SOURCE_LINE not in checked.stdout + checked.stderr, (
        'Removing a cache diagnostic must not quote the source line in the job log'
    )
