"""The pinned source checkout and local export retain the former archive safety checks."""

import contextlib
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
import yaml

from tools.ci import crysta_source_export

ROOT = Path(__file__).resolve().parents[3]
PRIVATE = b'private engine source with meaningful text'
PAYLOAD = b'independent binary source payload\x00\r\n'


def git(root, *args):
    return subprocess.check_output(
        ['git', '-C', str(root), '-c', 'core.hooksPath=/dev/null', *args],
        timeout=8,
    ).strip()


@pytest.fixture
def engine(tmp_path):
    root = tmp_path / 'local remote' / 'enhantica' / 'crysta'
    root.mkdir(parents=True)
    git(root, 'init', '-q', '--object-format=sha1')
    (root / 'entry.bin').write_bytes(PAYLOAD)
    (root / 'private.txt').write_bytes(PRIVATE + b'\n')
    git(root, 'add', '--', 'entry.bin', 'private.txt')
    identity = ['-c', 'user.name=Source fixture', '-c', 'user.email=fixture@example.invalid']
    git(root, *identity, 'commit', '-qm', 'Pinned content', '--no-gpg-sign')
    sha = git(root, 'rev-parse', 'HEAD').decode()
    (root / 'private.txt').write_text('Later checkout content\n', encoding='utf-8')
    git(root, 'add', '--', 'private.txt')
    git(root, *identity, 'commit', '-qm', 'Advance checkout', '--no-gpg-sign')
    (root / 'untracked.txt').touch()
    return root, sha


def test_local_source_export_uses_pinned_git_bytes_and_excludes_untracked_files(tmp_path, engine):
    root, sha = engine
    destination = tmp_path / 'local source export Ω'
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'tools/ci/crysta_source_export.py'),
            str(root),
            sha,
            str(destination),
        ],
        check=False,
        capture_output=True,
        timeout=12,
    )
    assert result.returncode == 0, (
        'The local export must accept the pinned commit through native paths'
    )
    assert {p.name for p in destination.iterdir()} == {'entry.bin', 'private.txt'}, (
        'Only files selected by the source commit belong to the export'
    )
    assert (destination / 'entry.bin').read_bytes() == PAYLOAD and (
        destination / 'private.txt'
    ).read_bytes() == PRIVATE + b'\n', 'The local export retains exact Git blob bytes'


@pytest.mark.parametrize('kind', ['parent', 'absolute', 'symlink'])
def test_source_extraction_cannot_write_outside_its_destination(tmp_path, kind):
    archive = tmp_path / 'unsafe.tar'
    outside = tmp_path / 'outside.txt'
    outside.write_bytes(b'unrelated existing bytes')
    destination = tmp_path / 'destination'
    destination.mkdir()
    with tarfile.open(archive, 'w') as output:
        member = tarfile.TarInfo('../outside.txt' if kind == 'parent' else str(outside))
        if kind == 'symlink':
            member = tarfile.TarInfo('link')
            member.type = tarfile.SYMTYPE
            member.linkname = '../outside.txt'
            output.addfile(member)
        else:
            member.size = 7
            output.addfile(member, io.BytesIO(b'changed'))
    if kind == 'absolute':
        with contextlib.suppress(tarfile.FilterError):
            crysta_source_export.extract(archive, destination)
        written = [path for path in destination.rglob('*') if path.is_file()]
        assert all(
            path.name == outside.name and path.read_bytes() == b'changed' for path in written
        ), 'A normalized absolute member retains its name and payload inside the destination'
    else:
        with pytest.raises((tarfile.FilterError, ValueError)):
            crysta_source_export.extract(archive, destination)
    assert outside.read_bytes() == b'unrelated existing bytes', (
        'A refused export cannot overwrite a file outside its destination'
    )


def test_source_bootstrap_checks_out_the_pin_filters_output_and_refuses_missing_commit(
    tmp_path, engine
):
    root, pin = engine
    host = tmp_path / 'edi'
    scripts = host / 'tools/ci'
    scripts.mkdir(parents=True)
    for name in ('crysta_fetch.py', 'public_log.py', 'source_lists.py'):
        shutil.copyfile(ROOT / 'tools/ci' / name, scripts / name)
    git(host, 'init', '-q')
    git(host, 'add', '--', 'tools/ci')
    runner = tmp_path / 'runner'
    runner.mkdir()
    environment_file = runner / 'environment'
    placeholder = 'fake-local-source-token'
    env = {
        **os.environ,
        'GITHUB_SERVER_URL': root.parents[1].as_uri(),
        'RUNNER_TEMP': str(runner),
        'GITHUB_ENV': str(environment_file),
        'TOKEN': placeholder,
    }

    def fetch(sha):
        return subprocess.run(
            [sys.executable, str(scripts / 'crysta_fetch.py'), sha],
            cwd=host,
            env=env,
            capture_output=True,
            check=False,
            timeout=12,
        )

    result = fetch(pin)
    assert result.returncode == 0, (
        'A fresh runner can establish the declared Git source and filter'
    )
    fields = dict(
        line.split('=', 1) for line in environment_file.read_text(encoding='utf-8').splitlines()
    )
    source = Path(fields['CRYSTA_SRC'])
    assert git(source, 'rev-parse', 'HEAD').decode() == pin, (
        'The runner selects the requested commit even when its remote HEAD has moved'
    )
    assert (source / 'entry.bin').read_bytes() == PAYLOAD, 'The runner retains exact source bytes'
    assert (
        git(root, 'rev-parse', f'{pin}:entry.bin').decode()
        in Path(fields['CRYSTA_SOURCE_BLOB_LIST']).read_text(encoding='ascii').splitlines()
    ), 'The blob list contains the independent object id'
    assert (
        hashlib.sha256(PRIVATE).hexdigest()
        in Path(fields['CRYSTA_SOURCE_LINE_LIST']).read_text(encoding='ascii').splitlines()
    ), 'The independently hashed private line is covered by the public-log filter'
    assert PRIVATE not in result.stdout + result.stderr and placeholder not in (
        source / '.git/config'
    ).read_text(encoding='utf-8'), 'Source and credentials may not escape checkout setup'

    before = environment_file.read_bytes()
    result = fetch('f' * 40)
    assert result.returncode and not source.exists() and environment_file.read_bytes() == before, (
        'A refused pin cleans the checkout and never exports a new source environment'
    )
    assert b'git fetch exited' in result.stderr and b'not our ref' not in result.stderr, (
        'A failing Git child is identified without forwarding its raw diagnostic'
    )


def test_source_consumers_use_local_git_checkout_and_producer_stores_only_the_sdk():
    producer = yaml.safe_load((ROOT / '.github/workflows/crysta-sdk.yml').read_text())
    installer = yaml.safe_load((ROOT / '.github/workflows/installers.yml').read_text())
    for steps in (producer['jobs']['build']['steps'], installer['jobs']['installers']['steps']):
        assert any(step.get('uses') == './.github/actions/crysta-source' for step in steps), (
            'The producer and installer fetch the exact source themselves'
        )
        assert all('crysta_source_archive.py' not in step.get('run', '') for step in steps), (
            'No producer or consumer invokes the former source archive transport'
        )
    core = (ROOT / 'tools/ci/crysta-src.sh').read_text(encoding='utf-8')
    assert 'CRYSTA_SRC' in core and 'crysta_source_export.py' in core, (
        'The native source consumer exports its commit from the runner checkout'
    )
