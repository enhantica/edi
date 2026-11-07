# SPDX-License-Identifier: BSD-3-Clause
"""Listing and downloading from a collection, offline, through the one core implementation.

The collection is a local folder written here; sizes and digests come from hashlib, not from edi.
The first location is a folder that does not exist, so every read exercises the fallback to the
second location (ADR-0068, ADR-0075).
"""

import hashlib
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

edi = pytest.importorskip('edi')

CIF = b'data_lbco\n_cell_length_a 3.89\n'
XYE = b'10.0 120.0 11.0\n10.1 121.0 11.0\n'


def project_zip(marker: str) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr('lbco/project.edi', f'data_project\n_project.id {marker}\n')
    return stream.getvalue()


def file_record(
    folder: Path, path: str, data: bytes, fmt: str, *, digest: str | None = None
) -> dict:
    target = folder / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {
        'path': path,
        'format': fmt,
        'sha256': digest or hashlib.sha256(data).hexdigest(),
        'bytes': len(data),
    }


def write_collection(folder: Path, archive: bytes, *, bad_digest: bool = False) -> None:
    entries = [
        {
            'id': 'lbco',
            'kind': 'structure',
            'name': 'LBCO',
            'files': [file_record(folder, 'structures/lbco.cif', CIF, 'cif')],
        },
        {
            'id': 'lbco-hrpt',
            'kind': 'data',
            'name': 'LBCO at HRPT',
            'files': [
                file_record(
                    folder,
                    'data/lbco-hrpt.xye',
                    XYE,
                    'xye',
                    digest='0' * 64 if bad_digest else None,
                )
            ],
        },
        {
            'id': 'lbco-project',
            'kind': 'project',
            'name': 'LBCO project',
            'files': [file_record(folder, 'projects/lbco.zip', archive, 'zip')],
        },
    ]
    (folder / 'index.json').write_text(
        json.dumps({'schema': 'edi-data-index/1', 'entries': entries})
    )


@pytest.fixture
def source(tmp_path, monkeypatch):
    collection = tmp_path / 'collection'
    write_collection(collection, project_zip('one'))
    # The first location cannot be reached, the second serves: the core's fallback order.
    monkeypatch.setattr(
        edi._collection, 'DEFAULT_SOURCES', (str(tmp_path / 'offline'), str(collection))
    )
    monkeypatch.delenv('EDI_COLLECTION', raising=False)
    return collection


def test_core_sha256_matches_hashlib():
    sha256_hex = edi._edi._sha256_hex  # the core's digest, as every interface uses it
    for data in (b'', b'abc', b'a' * 63, b'a' * 64, b'a' * 65, bytes(range(256)) * 4097):
        assert sha256_hex(data) == hashlib.sha256(data).hexdigest()


@pytest.mark.usefixtures('source')
def test_download_by_id_and_by_listing_number_with_fallback(tmp_path, capsys):
    edi.list_data()
    listed = capsys.readouterr().out.splitlines()
    assert [line.split()[:3] for line in listed[1:]] == [
        ['1', 'lbco', 'structure'],
        ['2', 'lbco-hrpt', 'data'],
        ['3', 'lbco-project', 'project'],
    ]
    by_id = Path(edi.download_data('lbco', tmp_path / 'out'))
    assert by_id == tmp_path / 'out/lbco.cif' and by_id.read_bytes() == CIF
    by_row = Path(edi.download_data(2, tmp_path / 'out'))
    assert by_row.read_bytes() == XYE
    with pytest.raises(ValueError, match='rows 1 to 3'):
        edi.download_data(4, tmp_path / 'out')
    with pytest.raises(ValueError, match="No entry 'missing'"):
        edi.download_data('missing', tmp_path / 'out')


@pytest.mark.usefixtures('source')
def test_a_kept_file_is_reused_and_a_damaged_one_replaced(tmp_path):
    first = Path(edi.download_data('lbco', tmp_path))
    first.write_bytes(b'damaged')
    assert Path(edi.download_data('lbco', tmp_path)).read_bytes() == CIF


def test_a_wrong_digest_refuses_and_writes_nothing(tmp_path, monkeypatch):
    collection = tmp_path / 'collection'
    write_collection(collection, project_zip('one'), bad_digest=True)
    monkeypatch.setattr(edi._collection, 'DEFAULT_SOURCES', (str(collection),))
    with pytest.raises(ValueError, match='digest'):
        edi.download_data('lbco-hrpt', tmp_path / 'out')
    assert not (tmp_path / 'out/lbco-hrpt.xye').exists()


def test_no_reachable_location_is_a_connection_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        edi._collection, 'DEFAULT_SOURCES', (str(tmp_path / 'a'), str(tmp_path / 'b'))
    )
    with pytest.raises(ConnectionError):
        edi.list_data()


def test_a_project_archive_is_unpacked_into_a_folder_named_by_its_digest(source, tmp_path):
    folder = Path(edi.download_data('lbco-project', tmp_path))
    assert (folder / 'project.edi').read_text().endswith('one\n')
    digest = hashlib.sha256(project_zip('one')).hexdigest()
    assert folder.parent.name == f'lbco-project-{digest[:12]}'
    write_collection(source, project_zip('two'))
    replaced = Path(edi.download_data('lbco-project', tmp_path))
    assert replaced != folder and (replaced / 'project.edi').read_text().endswith('two\n')


def test_tutorials_download_as_notebook_or_python(tmp_path, capsys):
    tutorials = tmp_path / 'tutorials'
    files = [
        file_record(tutorials, 'fit-lbco.ipynb', b'{"cells": []}\n', 'ipynb'),
        file_record(tutorials, 'fit-lbco.py', b'# %%\nimport edi\n', 'py'),
    ]
    entry = {'id': 'fit-lbco', 'kind': 'tutorial', 'name': 'Fit LBCO', 'files': files}
    (tutorials / 'index.json').write_text(
        json.dumps({'schema': 'edi-data-index/1', 'entries': [entry]})
    )
    edi.list_tutorials(source=tutorials)
    assert capsys.readouterr().out.splitlines()[1].split() == ['1', 'fit-lbco', 'Fit', 'LBCO']
    notebook = Path(edi.download_tutorial(1, tmp_path / 'out', source=tutorials))
    script = Path(
        edi.download_tutorial('fit-lbco', tmp_path / 'out', file_format='py', source=tutorials)
    )
    assert notebook.name == 'fit-lbco.ipynb' and script.read_bytes() == b'# %%\nimport edi\n'
    assert [
        Path(p).name for p in edi.download_all_tutorials(tmp_path / 'all', source=tutorials)
    ] == ['fit-lbco.ipynb']


def test_python_m_edi_lists_and_downloads(source, tmp_path):
    run = [sys.executable, '-m', 'edi']
    listed = subprocess.run(
        [*run, 'list-data', '--source', str(source)], capture_output=True, text=True, check=True
    )
    assert 'lbco-hrpt' in listed.stdout
    subprocess.run(
        [
            *run,
            'download-data',
            '3',
            '--destination',
            str(tmp_path / 'p'),
            '--source',
            str(source),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert list((tmp_path / 'p').glob('lbco-project-*/lbco/project.edi'))


def test_an_edited_tutorial_is_kept_unless_overwriting(tmp_path):
    tutorials = tmp_path / 'tutorials'
    files = [file_record(tutorials, 'fit-lbco.ipynb', b'{"cells": []}\n', 'ipynb')]
    entry = {'id': 'fit-lbco', 'kind': 'tutorial', 'name': 'Fit LBCO', 'files': files}
    (tutorials / 'index.json').write_text(
        json.dumps({'schema': 'edi-data-index/1', 'entries': [entry]})
    )
    path = Path(edi.download_tutorial('fit-lbco', tmp_path / 'out', source=tutorials))
    path.write_bytes(b'my notes')
    assert (
        Path(edi.download_tutorial('fit-lbco', tmp_path / 'out', source=tutorials)).read_bytes()
        == b'my notes'
    )
    edi.download_tutorial('fit-lbco', tmp_path / 'out', overwrite=True, source=tutorials)
    assert path.read_bytes() == b'{"cells": []}\n'
