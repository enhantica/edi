"""The update repository must fit its publishing service's file limit."""

import hashlib
import importlib.util
import sys
from pathlib import Path
from unittest import mock

import pytest

from tools.release import plan

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    'archive_size_promotion', ROOT / 'tools/release/promote.py'
)
PROMOTE = importlib.util.module_from_spec(SPEC)
with mock.patch.dict(sys.modules, {'plan': plan}):
    SPEC.loader.exec_module(PROMOTE)
VERSION = '2026.11.24'
APP = 'org.easydiffraction.app'
ASSISTANT = APP + '.assistant'
MAINTENANCE = APP + '.maintenancetool'


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha1').hexdigest()


def repository(folder, sizes):
    folder.mkdir()
    records = []
    for component in (APP, ASSISTANT, MAINTENANCE):
        target = folder / component
        target.mkdir()
        hashes = {}
        for name in ('content.7z', 'meta.7z'):
            path = target / (VERSION + name)
            with path.open('wb') as stream:
                stream.truncate(sizes.get((component, name), 32))
            hashes[name] = checksum(path)
            if name == 'content.7z':
                path.with_suffix('.7z.sha1').write_text(hashes[name])
        records.append(
            f'<PackageUpdate><Name>{component}</Name><Version>{VERSION}</Version>'
            '<DownloadableArchives>content.7z</DownloadableArchives>'
            f'<SHA1>{hashes["meta.7z"]}</SHA1></PackageUpdate>'
        )
    (folder / 'Updates.xml').write_text('<Updates>' + ''.join(records) + '</Updates>')
    return folder


@pytest.mark.parametrize('size', [61_000_000, 71_000_000, 95_000_000])
def test_admit_current_and_boundary_archive_sizes(tmp_path, size):
    folder = repository(tmp_path / 'repository', {(APP, 'content.7z'): size})
    PROMOTE.validate_repository(folder, VERSION, expected=PROMOTE.component_names('macos-arm64'))


@pytest.mark.parametrize('component', [APP, ASSISTANT, MAINTENANCE])
@pytest.mark.parametrize('member', ['content.7z', 'meta.7z'])
def test_refuse_any_component_archive_over_publishing_limit(tmp_path, component, member):
    folder = repository(tmp_path / 'repository', {(component, member): 95_000_001})
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)95|size|large|limit'):
        PROMOTE.validate_repository(
            folder, VERSION, expected=PROMOTE.component_names('macos-arm64')
        )
