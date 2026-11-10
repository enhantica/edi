"""Python's ZIP reader and Unix owner access judge the actual Qt web archive writers."""

import os
import stat
import subprocess
import zipfile
from pathlib import Path

import pytest

from tests.fixtures.web_archive_permissions.generate import FILES

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def archives(tmp_path_factory):
    root = tmp_path_factory.mktemp('web-archive-permissions')
    probe = os.environ.get('EDI_WEB_ARCHIVE_PROBE')
    if probe:
        command = [
            probe,
            str(ROOT / 'tests/fixtures/web_archive_permissions/project'),
            str(root / 'archives'),
        ]
    else:
        runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
        assert runner.is_file(), 'The archive permission gate uses the production Qt test host'
        command = [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_web_archive_permissions.qml'),
            '-o',
            '-,txt',
            'WebArchiveExport::test_write_archives',
        ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        env={
            **os.environ,
            'EDI_ACCEPTANCE_REFERENCE': str(root),
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, (
        'The actual Qt archive writers run successfully before independent inspection: '
        + result.stdout
        + result.stderr
    )
    for name in ['pack', 'packFiles']:
        assert (root / 'archives' / (name + '.zip')).is_file(), (
            'Both real web archive entry points produce an inspectable ZIP'
        )
    return root / 'archives'


def expected(method):
    # Folder archives use the shared root-relative format and omit hidden/cache files.
    # Explicit packFiles members remain opaque, including the hidden binary witness.
    return {
        name: data
        for name, data in FILES.items()
        if method != 'pack' or not any(part.startswith('.') for part in Path(name).parts)
    }


@pytest.mark.parametrize('method', ['pack', 'packFiles'])
def test_every_stored_zip_member_has_the_owner_read_bit(archives, method):
    with zipfile.ZipFile(archives / (method + '.zip')) as archive:
        entries = archive.infolist()
        assert entries, 'The owner permission check reaches real archive members'
        assert {info.filename for info in entries if not info.is_dir()} == set(expected(method)), (
            'The permission witness contains every independent input file'
        )
        for info in entries:
            assert (info.external_attr >> 16) & stat.S_IRUSR, (
                'Every stored ZIP member carries the Unix owner read bit'
            )


@pytest.mark.parametrize('method', ['pack', 'packFiles'])
def test_every_stored_zip_directory_has_the_owner_execute_bit(archives, method):
    with zipfile.ZipFile(archives / (method + '.zip')) as archive:
        assert archive.infolist(), 'The directory permission check reaches a real archive'
        for info in archive.infolist():
            mode = info.external_attr >> 16
            if info.is_dir() or stat.S_ISDIR(mode):
                assert mode & stat.S_IXUSR, (
                    'Every stored ZIP directory carries the Unix owner execute bit'
                )


@pytest.mark.parametrize('method', ['pack', 'packFiles'])
def test_owner_can_list_and_read_the_extracted_archive_with_stored_modes(
    archives, tmp_path, method
):
    target = tmp_path / 'extracted'
    problems = []
    with zipfile.ZipFile(archives / (method + '.zip')) as archive:
        archive.extractall(target)
        directories = [target, *(p for p in target.rglob('*') if p.is_dir())]
        files = [target / name for name in expected(method)]
        try:
            # Apply files first, then deepest directories, before testing any access.
            entries = sorted(
                archive.infolist(), key=lambda info: info.filename.count('/'), reverse=True
            )
            for info in [i for i in entries if not i.is_dir()]:
                (target / info.filename).chmod(stat.S_IMODE(info.external_attr >> 16))
            for info in [i for i in entries if i.is_dir()]:
                (target / info.filename).chmod(stat.S_IMODE(info.external_attr >> 16))
            for path in directories:
                try:
                    list(path.iterdir())
                    mode = path.stat().st_mode
                    if mode & (stat.S_IRUSR | stat.S_IXUSR) != (stat.S_IRUSR | stat.S_IXUSR):
                        problems.append(str(path.relative_to(target)))
                except OSError:
                    problems.append(str(path.relative_to(target)))
            for name, data in expected(method).items():
                try:
                    if (target / name).read_bytes() != data:
                        problems.append(name)
                    if not (target / name).stat().st_mode & stat.S_IRUSR:
                        problems.append(name)
                except OSError:
                    problems.append(name)
        finally:
            # Restore access from known paths so a deliberately bad ZIP cannot strand basetemps.
            for path in sorted(directories, key=lambda item: len(item.parts)):
                path.chmod(0o700)
            for path in files:
                path.chmod(0o600)
    assert not problems, (
        'Stored modes let the owner list every extracted folder and read each input file'
    )
