"""Exercise the install rules with authored collection payloads, without building Qt."""

import json
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.large_collection.inputs import generate

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def installed_collection(tmp_path_factory):
    folder = tmp_path_factory.mktemp('collection-install')
    online, _bundle = generate(folder / 'inputs')
    text = (ROOT / 'app/CMakeLists.txt').read_text()
    start = text.index('set(EDI_BUNDLED_COLLECTION ')
    end = text.index('set(EDI_LOCAL_COLLECTION ', start)
    source = folder / 'source'
    source.mkdir()
    (source / 'dummy.cpp').write_text('int main() {}\n')
    (source / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.24)\nproject(BundleRules NONE)\n'
        'include(GNUInstallDirs)\n'
        f'set(CMAKE_SOURCE_DIR "{ROOT.as_posix()}")\n'
        f'set(PROJECT_SOURCE_DIR "{ROOT.as_posix()}")\n'
        f'set(CMAKE_CURRENT_SOURCE_DIR "{(ROOT / "app").as_posix()}")\n'
        'add_custom_target(edi_app)\n' + text[start:end]
    )
    destination = folder / 'installed'
    for command in (
        [
            'cmake',
            '-S',
            str(source),
            '-B',
            str(folder / 'build'),
            f'-DEDI_BUNDLED_COLLECTION={online}',
            f'-DCMAKE_INSTALL_PREFIX={destination}',
            '-DCMAKE_INSTALL_DATADIR=share',
        ],
        ['cmake', '--install', str(folder / 'build'), '--component', 'desktop'],
    ):
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
        assert result.returncode == 0, (
            'ADR-0068: the actual collection install rules execute without a full app build: '
            + result.stdout
            + result.stderr
        )
    installed = list(destination.rglob('collection/index.json'))
    assert len(installed) == 1, 'ADR-0068: the desktop install supplies one collection index'
    return online, installed[0].parent


def test_bundle_omits_large_payload(installed_collection):
    _online, installed = installed_collection
    assert not (installed / 'projects/large.zip').exists(), (
        'ADR-0068: items above approximately five MB are excluded from the desktop bundle'
    )


def test_bundle_keeps_small_payload_byte_for_byte(installed_collection):
    online, installed = installed_collection
    assert (installed / 'projects/small.zip').read_bytes() == (
        online / 'projects/small.zip'
    ).read_bytes(), 'ADR-0068: small examples remain installed unchanged for fully offline opening'


def test_bundle_retains_large_example_discovery(installed_collection):
    online, installed = installed_collection
    expected = json.loads((online / 'index.json').read_text())['entries']
    actual = json.loads((installed / 'index.json').read_text())['entries']
    assert {row['id']: row['files'] for row in actual} == {
        row['id']: row['files'] for row in expected
    }, (
        'ADR-0068: omitted payloads keep ids, remote paths, sizes and digests for first open'
    )
