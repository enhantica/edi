# SPDX-License-Identifier: BSD-3-Clause
"""Public download expectations from the reference CLI and Python documentation."""

import importlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    'download_reference_fixture', ROOT / 'tests/fixtures/download_reference/build.py'
)
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)
FUNCTIONS = [
    'list_data',
    'download_data',
    'list_tutorials',
    'download_tutorial',
    'download_all_tutorials',
]


@pytest.fixture
def collection(tmp_path, monkeypatch):
    root = tmp_path / 'collection'
    index = FIXTURE.build(root)
    monkeypatch.setenv('EDI_COLLECTION', str(root))
    return root, index


@pytest.mark.parametrize('name', FUNCTIONS)
def test_reference_python_download_surface_exists(name):
    edi = importlib.import_module('edi')

    assert callable(getattr(edi, name, None)), (
        'The public Python download surface must carry the reference function: ' + name
    )


@pytest.mark.parametrize('name', [name.replace('_', '-') for name in FUNCTIONS])
def test_reference_cli_download_commands_exist(name):
    result = subprocess.run(
        [sys.executable, '-m', 'edi', '--help'],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0 and name in result.stdout, (
        'The Python module CLI must expose the documented download command: ' + name
    )


def test_data_id_and_app_index_reader_select_the_same_entry(collection, tmp_path):
    edi = importlib.import_module('edi')
    native = importlib.import_module('edi._edi')

    root, _ = collection
    expected = native._collection_find((root / 'index.json').read_text(), 'alpha-data')
    assert expected['files'][0]['path'] == 'data/alpha.xye', (
        'The app index reader must resolve the independently authored alpha entry'
    )
    path = Path(edi.download_data('alpha-data', destination=str(tmp_path / 'download')))
    assert path.read_bytes() == FIXTURE.MEASUREMENT, (
        'A public download by id must fetch the same entry selected by the app index reader'
    )


@pytest.mark.usefixtures('collection')
def test_data_rows_are_sorted_and_one_based(tmp_path, capsys):
    edi = importlib.import_module('edi')

    edi.list_data()
    output = capsys.readouterr().out
    assert (
        output.index('alpha-data') < output.index('proj-reference') < output.index('zeta-data')
    ), 'Data listing rows must sort by canonical id as the reference documents'
    assert re.search(r'\b1\b[^\n]*alpha-data', output), (
        'The first data-listing row must have the reference one-based number'
    )
    for number in [1, '1']:
        downloaded = Path(edi.download_data(number, destination=str(tmp_path / str(type(number)))))
        assert downloaded.read_bytes() == FIXTURE.MEASUREMENT, (
            'Integer and numeric-string row handles must resolve the listing first row'
        )


def test_wrong_digest_refuses_without_output(collection, tmp_path):
    edi = importlib.import_module('edi')

    root, index = collection
    index['entries'][1]['files'][0]['sha256'] = '0' * 64
    (root / 'index.json').write_text(json.dumps(index))
    destination = tmp_path / 'refused'
    with pytest.raises(ValueError, match=r'sha256|digest|hash'):
        edi.download_data('alpha-data', destination=str(destination))
    assert not destination.exists() or not list(destination.rglob('*')), (
        'A bad download digest must leave no destination file or partial artifact'
    )


def test_dead_primary_falls_back_to_local_mirror(collection, tmp_path, monkeypatch):
    edi = importlib.import_module('edi')
    implementation = importlib.import_module('edi._collection')

    root, _ = collection
    monkeypatch.delenv('EDI_COLLECTION')
    monkeypatch.setattr(implementation, 'DEFAULT_SOURCES', (str(tmp_path / 'dead'), str(root)))
    downloaded = Path(edi.download_data('alpha-data', destination=str(tmp_path / 'fallback')))
    assert downloaded.read_bytes() == FIXTURE.MEASUREMENT, (
        'An unavailable primary must fall back to the collection mirror for index and file'
    )


@pytest.mark.usefixtures('collection')
def test_project_archive_returns_extracted_project_and_removes_zip(tmp_path):
    edi = importlib.import_module('edi')

    destination = tmp_path / 'projects'
    downloaded = Path(edi.download_data('proj-reference', destination=str(destination)))
    assert downloaded.is_dir() and (downloaded / 'project.edi').read_bytes() == FIXTURE.PROJECT, (
        'Downloading a saved-project archive must return its extracted project directory'
    )
    assert not list(destination.rglob('*.zip')), (
        'The reference project-download route removes its archive after successful extraction'
    )


def native_cli():
    suffix = '.exe' if sys.platform == 'win32' else ''
    return ROOT / f'build/app/cli/easydiffraction{suffix}'


@pytest.mark.parametrize('name', [name.replace('_', '-') for name in FUNCTIONS])
def test_standalone_cli_offers_reference_download_commands(name):
    answer = subprocess.run(
        [str(native_cli()), '--help'], capture_output=True, text=True, timeout=5, check=False
    )
    assert answer.returncode == 0 and name in answer.stdout, (
        'The standalone CLI must offer the same documented download command: ' + name
    )


@pytest.mark.parametrize('interface', ['python-cli', 'standalone'])
@pytest.mark.usefixtures('collection')
def test_cli_id_download_uses_the_authored_collection(tmp_path, interface):
    prefix = [sys.executable, '-m', 'edi'] if interface == 'python-cli' else [str(native_cli())]
    destination = tmp_path / 'download'
    answer = subprocess.run(
        [*prefix, 'download-data', 'alpha-data', '-d', str(destination)],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert answer.returncode == 0, (
        'Each CLI must download the fixture id through its ordinary command: ' + answer.stderr
    )
    files = [p for p in destination.rglob('*') if p.is_file()]
    assert len(files) == 1 and files[0].read_bytes() == FIXTURE.MEASUREMENT, (
        'Each CLI must return exactly the bytes of the entry selected by the app index reader'
    )


@pytest.mark.parametrize('interface', ['python', 'python-cli', 'standalone'])
def test_refused_archive_cannot_leave_extracted_files(collection, tmp_path, interface):
    root, index = collection
    FIXTURE.refuse_archive(root, index)
    destination = tmp_path / 'download'
    if interface == 'python':
        edi = importlib.import_module('edi')
        assert callable(getattr(edi, 'download_data', None)), (
            'The public download command must exist before its extraction refusal is exercised'
        )
        with pytest.raises((ValueError, RuntimeError), match=r'archive|path|escape|ZIP'):
            edi.download_data('proj-reference', destination=str(destination))
    else:
        prefix = (
            [sys.executable, '-m', 'edi'] if interface == 'python-cli' else [str(native_cli())]
        )
        help_result = subprocess.run(
            [*prefix, '--help'], capture_output=True, text=True, timeout=5, check=False
        )
        assert 'download-data' in help_result.stdout, (
            'Each CLI must expose the actual download command before the extraction witness'
        )
        refused = subprocess.run(
            [*prefix, 'download-data', 'proj-reference', '-d', str(destination)],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        assert refused.returncode != 0, 'Every CLI must refuse the verified unsafe archive'
    assert not (tmp_path / 'outside.edi').exists(), (
        'A refused archive must not publish a member outside its extraction destination'
    )
    assert not destination.exists() or not [
        p for p in destination.rglob('*') if p.is_file() and p.suffix != '.zip'
    ], 'A refused archive must leave no extracted member'


@pytest.mark.parametrize('interface', ['python-cli', 'standalone'])
def test_cli_bad_digest_refuses_without_a_destination_file(collection, tmp_path, interface):
    root, index = collection
    index['entries'][1]['files'][0]['sha256'] = '0' * 64
    (root / 'index.json').write_text(json.dumps(index))
    prefix = [sys.executable, '-m', 'edi'] if interface == 'python-cli' else [str(native_cli())]
    help_result = subprocess.run(
        [*prefix, '--help'], capture_output=True, text=True, timeout=5, check=False
    )
    assert 'download-data' in help_result.stdout, (
        'The CLI download command must exist before the bad-digest channel is exercised'
    )
    destination = tmp_path / 'download'
    result = subprocess.run(
        [*prefix, 'download-data', 'alpha-data', '-d', str(destination)],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0, 'Each CLI must refuse a digest mismatch in the collection'
    assert not destination.exists() or not list(destination.rglob('*')), (
        'Each CLI must refuse a bad digest without publishing any destination file'
    )
