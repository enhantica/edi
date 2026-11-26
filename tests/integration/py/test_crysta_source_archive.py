"""The pinned source checkout and local export retain the former archive safety checks."""

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

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


def export_source(root, sha, destination):
    return subprocess.run(
        [sys.executable, str(ROOT / 'tools/ci/crysta_source_export.py'), root, sha, destination],
        check=False,
        capture_output=True,
        timeout=12,
    )


def test_local_source_export_uses_pinned_git_bytes_and_excludes_untracked_files(tmp_path, engine):
    root, sha = engine
    destination = tmp_path / 'local source export Ω'
    result = export_source(root, sha, destination)
    assert result.returncode == 0, (
        'The local export must accept the pinned commit through native paths'
    )
    assert {p.name for p in destination.iterdir()} == {'entry.bin', 'private.txt'}, (
        'Only files selected by the source commit belong to the export'
    )
    assert (destination / 'entry.bin').read_bytes() == PAYLOAD and (
        destination / 'private.txt'
    ).read_bytes() == PRIVATE + b'\n', 'The local export retains exact Git blob bytes'


def git_object(root, command, data, *options):
    return subprocess.check_output(
        ['git', '-C', str(root), command, *options], input=data, timeout=8
    ).strip()


def export_commit(root, entries):
    # Build this commit directly so fixtures can name links and Windows-invalid paths on any host.
    tree = b'100644 blob ' + git_object(root, 'hash-object', PAYLOAD, '-w', '--stdin')
    tree += b'\tentry.bin\0'
    for mode, name, data in entries:
        command, label, args = (
            ('mktree', b'tree', ('-z',))
            if mode == b'040000'
            else ('hash-object', b'blob', ('-w', '--stdin'))
        )
        oid = git_object(root, command, data, *args)
        tree += b' '.join((mode, label, oid)) + b'\t' + name + b'\0'
    tree_id = git_object(root, 'mktree', tree, '-z')
    return git(
        root,
        '-c',
        'user.name=Source fixture',
        '-c',
        'user.email=fixture@example.invalid',
        'commit-tree',
        tree_id.decode(),
        '-m',
        'Export controls',
    ).decode()


@pytest.mark.parametrize(
    'target_kind',
    [
        'absolute',
        'outside-file',
        'parent-relative',
        'untracked-directory',
        'windows-drive',
        'windows-unc',
    ],
)
def test_local_source_export_refuses_links_outside_the_committed_tree(
    tmp_path, engine, target_kind
):
    root, _ = engine
    destination = tmp_path / 'destination'
    destination.mkdir()
    outside = tmp_path / 'outside.txt'
    outside.write_bytes(b'unrelated existing bytes')
    targets = {
        'absolute': os.fsencode(outside.as_posix()),
        'outside-file': b'untracked.txt',
        'parent-relative': b'../outside.txt',
        'untracked-directory': b'missing/../entry.bin',
        'windows-drive': rb'C:\outside.txt',
        'windows-unc': rb'\\server\share\outside.txt',
    }
    sha = export_commit(root, [(b'120000', b'link', targets[target_kind])])
    result = export_source(root, sha, destination)
    assert result.returncode == 1 and b'source-export: REFUSED:' in result.stderr, (
        'The exporter CLI must refuse the link through its normal error boundary'
    )
    assert (
        not list(destination.iterdir()) and outside.read_bytes() == b'unrelated existing bytes'
    ), 'A refused link must leave no partial export and preserve existing outside bytes'


@pytest.mark.parametrize(
    'names',
    [
        (b'aux.edi',),
        (b'C:drive.txt',),
        (b'file.txt:stream',),
        (rb'back\slash',),
        (b'trailing.',),
        (b'Twin.txt', b'twin.txt'),
    ],
    ids=['device', 'drive-relative', 'stream', 'backslash', 'trailing-dot', 'case-alias'],
)
def test_local_source_export_refuses_windows_native_path_conflicts(tmp_path, engine, names):
    root, _ = engine
    sha = export_commit(root, [(b'100644', name, PRIVATE) for name in names])
    destination = tmp_path / 'destination'
    result = export_source(root, sha, destination)
    assert result.returncode == 1 and b'source-export: REFUSED:' in result.stderr, (
        'Git entries that become a Windows device, stream, alternate path or alias must refuse'
    )
    assert not destination.exists() and PRIVATE not in result.stdout + result.stderr, (
        'The exporter judges the whole tree before writing and never quotes the refused blob'
    )


def test_parent_relative_link_to_committed_file_preserves_blob_bytes(tmp_path, engine):
    root, _ = engine
    link = git_object(root, 'hash-object', b'../entry.bin', '-w', '--stdin')
    sha = export_commit(root, [(b'040000', b'folder', b'120000 blob ' + link + b'\tlink\0')])
    destination = tmp_path / 'destination'
    result = export_source(root, sha, destination)
    exported_link = destination / 'folder/link'
    assert result.returncode == 0 and exported_link.read_bytes() == PAYLOAD, (
        'A parent-relative link through committed directories retains the selected blob bytes'
    )
    assert exported_link.is_symlink() == (os.name != 'nt'), (
        'The native export uses a POSIX symlink or copies the committed blob on Windows'
    )


def test_source_bootstrap_checks_out_the_pin_filters_output_and_refuses_missing_commit(
    tmp_path, engine
):
    root, pin = engine
    host = tmp_path / 'edi'
    scripts = host / 'tools/ci'
    scripts.mkdir(parents=True)
    helpers = ['crysta_fetch.py', 'public_log.py', 'source_lists.py', 'portable_paths.py']
    for name in helpers:
        if name == 'portable_paths.py' and not (ROOT / 'tools/ci' / name).exists():
            continue  # The pre-#158 source transport had no portable-path helper.
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
