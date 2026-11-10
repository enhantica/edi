# SPDX-License-Identifier: BSD-3-Clause
"""Listing and downloading from a collection, offline, through the one core implementation.

The collection is a local folder written here; sizes and digests come from hashlib, not from edi.
The first location is a folder that does not exist, so every read exercises the fallback to the
second location (ADR-0068, ADR-0075).
"""

import hashlib
import io
import json
import os
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
        assert sha256_hex(data) == hashlib.sha256(data).hexdigest(), (
            'The core SHA-256 must equal the independent standard-library digest.'
        )


@pytest.mark.usefixtures('source')
def test_download_by_id_and_by_listing_number_with_fallback(tmp_path, capsys):
    edi.list_data()
    listed = capsys.readouterr().out.splitlines()
    assert [line.split()[:3] for line in listed[1:]] == [
        ['1', 'lbco', 'structure'],
        ['2', 'lbco-hrpt', 'data'],
        ['3', 'lbco-project', 'project'],
    ], 'Ids and one-based listing numbers must return the same verified bytes through fallback.'
    by_id = Path(edi.download_data('lbco', tmp_path / 'out'))
    assert by_id == tmp_path / 'out/lbco.cif' and by_id.read_bytes() == CIF, (
        'Ids and one-based listing numbers must return the same verified bytes through fallback.'
    )
    by_row = Path(edi.download_data(2, tmp_path / 'out'))
    assert by_row.read_bytes() == XYE, (
        'Ids and one-based listing numbers must return the same verified bytes through fallback.'
    )
    with pytest.raises(ValueError, match='rows 1 to 3'):
        edi.download_data(4, tmp_path / 'out')
    with pytest.raises(ValueError, match="No entry 'missing'"):
        edi.download_data('missing', tmp_path / 'out')


@pytest.mark.usefixtures('source')
def test_a_kept_file_is_reused_and_a_damaged_one_replaced(tmp_path):
    first = Path(edi.download_data('lbco', tmp_path))
    first.write_bytes(b'damaged')
    assert Path(edi.download_data('lbco', tmp_path)).read_bytes() == CIF, (
        'A valid kept file must be reused and a damaged file replaced.'
    )


def test_a_wrong_digest_refuses_and_writes_nothing(tmp_path, monkeypatch):
    collection = tmp_path / 'collection'
    write_collection(collection, project_zip('one'), bad_digest=True)
    monkeypatch.setattr(edi._collection, 'DEFAULT_SOURCES', (str(collection),))
    with pytest.raises(ValueError, match='digest'):
        edi.download_data('lbco-hrpt', tmp_path / 'out')
    assert not (tmp_path / 'out/lbco-hrpt.xye').exists(), (
        'A wrong digest must refuse without writing a file.'
    )


def test_no_reachable_location_is_a_connection_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        edi._collection, 'DEFAULT_SOURCES', (str(tmp_path / 'a'), str(tmp_path / 'b'))
    )
    with pytest.raises(ConnectionError):
        edi.list_data()


def test_a_project_archive_is_unpacked_into_a_folder_named_by_its_digest(source, tmp_path):
    folder = Path(edi.download_data('lbco-project', tmp_path))
    assert (folder / 'project.edi').read_text().endswith('one\n'), (
        'A project archive must unpack into a folder named by its digest.'
    )
    digest = hashlib.sha256(project_zip('one')).hexdigest()
    assert folder.parent.name == f'lbco-project-{digest[:12]}', (
        'A project archive must unpack into a folder named by its digest.'
    )
    write_collection(source, project_zip('two'))
    replaced = Path(edi.download_data('lbco-project', tmp_path))
    assert replaced != folder and (replaced / 'project.edi').read_text().endswith('two\n'), (
        'A project archive must unpack into a folder named by its digest.'
    )


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
    assert capsys.readouterr().out.splitlines()[1].split() == ['1', 'fit-lbco', 'Fit', 'LBCO'], (
        'Tutorial downloads must return the selected notebook or Python format.'
    )
    notebook = Path(edi.download_tutorial(1, tmp_path / 'out', source=tutorials))
    script = Path(
        edi.download_tutorial('fit-lbco', tmp_path / 'out', file_format='py', source=tutorials)
    )
    assert notebook.name == 'fit-lbco.ipynb' and script.read_bytes() == b'# %%\nimport edi\n', (
        'Tutorial downloads must return the selected notebook or Python format.'
    )
    assert [
        Path(p).name for p in edi.download_all_tutorials(tmp_path / 'all', source=tutorials)
    ] == ['fit-lbco.ipynb'], (
        'Tutorial downloads must return the selected notebook or Python format.'
    )


def test_python_m_edi_lists_and_downloads(source, tmp_path):
    run = [sys.executable, '-m', 'edi']
    listed = subprocess.run(
        [*run, 'list-data', '--source', str(source)], capture_output=True, text=True, check=True
    )
    assert 'lbco-hrpt' in listed.stdout, (
        'The module CLI must list and download the fixture data and tutorials.'
    )
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
    assert list((tmp_path / 'p').glob('lbco-project-*/lbco/project.edi')), (
        'The module CLI must list and download the fixture data and tutorials.'
    )


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
    ), 'An edited tutorial is kept unless overwriting.'
    edi.download_tutorial('fit-lbco', tmp_path / 'out', overwrite=True, source=tutorials)
    assert path.read_bytes() == b'{"cells": []}\n', (
        'An edited tutorial is kept unless overwriting.'
    )


@pytest.mark.parametrize(
    'entry_id',
    ['../outside', '..', '.', '/tmp/outside', 'a/b', '..\\outside', 'C:\\outside', 'C:x'],
)
def test_an_id_that_is_not_a_plain_name_refuses_and_writes_nothing(tmp_path, entry_id):
    collection = tmp_path / 'collection'
    archive = project_zip('one')
    entry = {
        'id': entry_id,
        'kind': 'project',
        'name': 'escape',
        'files': [file_record(collection, 'projects/escape.zip', archive, 'zip')],
    }
    (collection / 'index.json').write_text(
        json.dumps({'schema': 'edi-data-index/1', 'entries': [entry]})
    )
    before = sorted(tmp_path.rglob('*'))
    with pytest.raises(ValueError, match='not a plain name'):
        edi.download_data(entry_id, tmp_path / 'out' / 'inner', source=collection)
    with pytest.raises(ValueError, match='not a plain name'):
        edi.load_collection(collection).fetch(entry_id, tmp_path / 'out')
    assert sorted(tmp_path.rglob('*')) == before, (
        'An index id that is not one plain name must be refused before anything is written.'
    )


def test_fetch_copies_the_file_through_the_same_checks(source, tmp_path):
    collection = edi.load_collection(source)
    path = collection.fetch('lbco-project', tmp_path / 'raw')
    assert path == tmp_path / 'raw/lbco.zip' and path.read_bytes() == project_zip('one'), (
        'fetch must copy the first file unchanged, never unpacked.'
    )
    path.write_bytes(b'stale')
    assert collection.fetch('lbco-project', tmp_path / 'raw').read_bytes() == project_zip('one'), (
        'fetch must replace a file already there.'
    )
    write_collection(source, project_zip('one'), bad_digest=True)
    with pytest.raises(ValueError, match='digest'):
        edi.load_collection(source).fetch('lbco-hrpt', tmp_path / 'raw')
    assert not (tmp_path / 'raw/lbco-hrpt.xye').exists(), (
        'fetch must refuse a wrong digest without writing a file.'
    )


@pytest.mark.usefixtures('source')
def test_an_empty_listing_prints_its_header(capsys):
    edi.list_data(kind='experiment')
    assert capsys.readouterr().out.split() == ['#', 'id', 'kind', 'format', 'name'], (
        'A listing with no rows must print its header, not raise.'
    )


@pytest.mark.usefixtures('source')
def test_a_destination_spelled_with_a_trailing_separator_is_the_same_folder(tmp_path):
    folder = Path(edi.download_data('lbco-project', f'{tmp_path / "new"}/'))
    assert folder.parent.parent == tmp_path / 'new' and (folder / 'project.edi').is_file(), (
        "A destination such as 'data/' must place files in that folder, not refuse."
    )


def project_folder_name(archive: bytes) -> str:
    return f'lbco-project-{hashlib.sha256(archive).hexdigest()[:12]}'


@pytest.mark.parametrize('link', ['symlink', 'hardlink'])
@pytest.mark.usefixtures('source')
def test_a_link_at_a_staging_or_final_name_is_never_written_through(tmp_path, link):
    outside = tmp_path / 'outside.cif'
    outside.write_bytes(b'keep me')
    destination = tmp_path / 'out'
    destination.mkdir()
    if link == 'symlink':
        (destination / 'lbco.cif.partial').symlink_to(outside)  # the old fixed staging name
    else:
        os.link(outside, destination / 'lbco.cif.partial')
        os.link(outside, destination / 'lbco.cif')  # the final name itself, holding other bytes
    path = Path(edi.download_data('lbco', destination))
    assert path.read_bytes() == CIF and outside.read_bytes() == b'keep me', (
        'A download must never write through a link at its staging or final name.'
    )
    assert not [p.name for p in destination.iterdir() if p.name.startswith('.')], (
        'A finished download must leave no staging file behind.'
    )


@pytest.mark.parametrize('planted', ['child-link', 'marker-link', 'empty-folder', 'loose-file'])
@pytest.mark.usefixtures('source')
def test_a_cached_project_folder_is_reused_only_when_it_holds_a_plain_project(tmp_path, planted):
    outside = tmp_path / 'outside-project'
    outside.mkdir()
    (outside / 'project.edi').write_text('data_project\n_project.id outside\n')
    destination = tmp_path / 'out'
    folder = destination / project_folder_name(project_zip('one'))
    folder.mkdir(parents=True)
    if planted == 'child-link':
        (folder / 'lbco').symlink_to(outside)
    elif planted == 'marker-link':
        (folder / 'lbco').mkdir()
        (folder / 'lbco/project.edi').symlink_to(outside / 'project.edi')
    elif planted == 'loose-file':
        (folder / 'notes.txt').write_text('not a project')
    project = Path(edi.download_data('lbco-project', destination))
    assert project == folder / 'lbco' and not project.is_symlink(), (
        'A cache entry reached through a link or without a project must be unpacked again.'
    )
    assert (project / 'project.edi').read_text().endswith('one\n'), (
        'The re-unpacked project must come from the downloaded archive.'
    )
    assert (outside / 'project.edi').read_text().endswith('outside\n'), (
        'Replacing a cache entry must not touch what a link in it pointed to.'
    )


def test_a_failed_unpack_leaves_nothing_a_retry_could_reuse(tmp_path):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr('project.edi', 'data_project\n')
        archive.writestr('blocked', 'a file')
        archive.writestr('blocked/child', 'cannot be written under a file')
    data = stream.getvalue()
    collection = tmp_path / 'collection'
    entry = {
        'id': 'lbco-project',
        'kind': 'project',
        'name': 'broken',
        'files': [file_record(collection, 'projects/broken.zip', data, 'zip')],
    }
    (collection / 'index.json').write_text(
        json.dumps({'schema': 'edi-data-index/1', 'entries': [entry]})
    )
    destination = tmp_path / 'out'
    for attempt in range(2):
        with pytest.raises(ValueError, match='cannot unpack'):
            edi.download_data('lbco-project', destination, source=collection)
        assert not destination.exists() or not list(destination.iterdir()), (
            f'Attempt {attempt + 1}: a failed unpack must leave no folder, partial or staged.'
        )


@pytest.mark.usefixtures('source')
def test_a_link_named_x_in_the_destination_does_not_move_it(tmp_path):
    destination = tmp_path / 'out'
    (tmp_path / 'elsewhere/inner').mkdir(parents=True)
    destination.mkdir()
    (destination / 'x').symlink_to(tmp_path / 'elsewhere/inner')
    assert Path(edi.download_data('lbco', destination)) == destination / 'lbco.cif', (
        'An unrelated link in the destination must not change where the destination is.'
    )


def project_collection(tmp_path: Path, members: list[tuple[str, str | None]]) -> Path:
    """A one-project collection whose archive holds `members`; a None body is a directory."""
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for name, body in members:
            if body is None:
                archive.writestr(zipfile.ZipInfo(name), '')
            else:
                archive.writestr(name, body)
    collection = tmp_path / 'collection'
    entry = {
        'id': 'lbco-project',
        'kind': 'project',
        'name': 'project',
        'files': [file_record(collection, 'projects/p.zip', stream.getvalue(), 'zip')],
    }
    (collection / 'index.json').write_text(
        json.dumps({'schema': 'edi-data-index/1', 'entries': [entry]})
    )
    return collection


def test_a_directory_member_over_a_file_refuses_every_time(tmp_path):
    collection = project_collection(
        tmp_path, [('project.edi', 'data_project\n'), ('blocked', 'a file'), ('blocked/', None)]
    )
    destination = tmp_path / 'out'
    for attempt in range(2):
        with pytest.raises(ValueError, match='cannot unpack'):
            edi.download_data('lbco-project', destination, source=collection)
        assert not destination.exists() or not list(destination.iterdir()), (
            f'Attempt {attempt + 1}: a failed directory must leave no folder, marker or stage.'
        )


@pytest.mark.parametrize(
    'member',
    ['NUL.txt', 'con', 'Aux.EDI', 'lpt1.log', 'sub/com3', 'my data.xye', '.hidden', 'trailing.'],
)
def test_an_archive_member_outside_the_name_grammar_refuses(tmp_path, member):
    collection = project_collection(tmp_path, [('project.edi', 'data_project\n'), (member, 'x')])
    destination = tmp_path / 'out'
    with pytest.raises(ValueError, match='not a plain name'):
        edi.download_data('lbco-project', destination, source=collection)
    assert not destination.exists() or not list(destination.iterdir()), (
        'An archive with a member outside the grammar must refuse before writing anything.'
    )


@pytest.mark.parametrize('field', ['id', 'path'])
def test_a_device_name_in_the_index_refuses(tmp_path, field):
    collection = tmp_path / 'collection'
    record = file_record(collection, 'structures/lbco.cif', CIF, 'cif')
    entry = {'id': 'lbco', 'kind': 'structure', 'name': 'LBCO', 'files': [record]}
    if field == 'id':
        entry['id'] = 'nul'
    else:
        (collection / 'structures/con.cif').write_bytes(CIF)
        record['path'] = 'structures/con.cif'
    (collection / 'index.json').write_text(
        json.dumps({'schema': 'edi-data-index/1', 'entries': [entry]})
    )
    with pytest.raises(ValueError, match='not a plain'):
        edi.download_data(1, tmp_path / 'out', source=collection)


@pytest.mark.usefixtures('source')
def test_a_project_is_reused_only_with_its_completion_marker(tmp_path):
    destination = tmp_path / 'out'
    project = Path(edi.download_data('lbco-project', destination))
    folder = project.parent
    marker = destination / f'.{folder.name}.complete'
    digest = hashlib.sha256(project_zip('one')).hexdigest()
    assert marker.read_text() == digest, 'A finished project download must write its marker last.'
    (project / 'project.edi').write_text('truncated')
    assert (Path(edi.download_data('lbco-project', destination)) / 'project.edi').read_text() == (
        'truncated'
    ), 'A project with its marker is the cached download and is reused as it is.'
    for broken in ('missing', 'wrong'):
        if broken == 'missing':
            marker.unlink()
        else:
            marker.write_text('0' * 64)
        again = Path(edi.download_data('lbco-project', destination))
        assert (again / 'project.edi').read_text().endswith('one\n'), (
            f'A project whose marker is {broken} must be downloaded again.'
        )
        assert marker.read_text() == digest, 'The fresh download must write its marker again.'


FILE_LIMIT_RUN = r"""
import resource, signal, sys
import edi
# A write past the limit then fails instead of killing the process.
signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
resource.setrlimit(resource.RLIMIT_FSIZE, (int(sys.argv[3]), int(sys.argv[3])))
try:
    edi.download_data('lbco-project', sys.argv[2], source=sys.argv[1])
except ValueError as error:
    print('refused:', error)
else:
    print('downloaded')
"""


def test_a_write_that_fails_only_when_the_file_closes_is_never_published(tmp_path):
    # 2000 bytes stay in the C library's buffer until the close, so only a checked close or
    # flush sees the failure.
    body = 'x' * 2000
    collection = project_collection(tmp_path, [('lbco/project.edi', body)])
    destination = tmp_path / 'out'
    run = subprocess.run(
        [sys.executable, '-c', FILE_LIMIT_RUN, str(collection), str(destination), '1000'],
        capture_output=True,
        text=True,
        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
        check=False,
    )
    assert 'refused: cannot unpack' in run.stdout, (
        f'A failed close must refuse the download, not report it done: {run.stdout}{run.stderr}'
    )
    assert not destination.exists() or not list(destination.iterdir()), (
        'A failed close must leave no folder, marker or stage.'
    )
    project = Path(edi.download_data('lbco-project', destination, source=collection))
    assert (project / 'project.edi').read_text() == body, (
        'The retry without the limit must download the whole project, not reuse a partial one.'
    )


EXAMPLE = Path(__file__).resolve().parents[3] / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project'


def user_archive(tmp_path: Path, extra: str) -> Path:
    """A zip of an example project, as a user would make it, with one extra file."""
    path = tmp_path / 'mine.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        for file in sorted(EXAMPLE.rglob('*')):
            if file.is_file():
                archive.write(file, 'lbco/' + file.relative_to(EXAMPLE).as_posix())
        archive.writestr('lbco/' + extra, 'notes')
    return path


@pytest.mark.parametrize('extra', ['notes/résumé.txt', '.hidden', 'notes/two words.txt'])
def test_a_users_own_archive_keeps_their_file_names(tmp_path, extra):
    project = edi.Project.load(str(user_archive(tmp_path, extra)))
    assert project is not None, 'A user-made project archive must open with their file names.'


@pytest.mark.parametrize('extra', ['NUL.txt', 'notes/con', 'Aux.log', 'notes/a:b.txt'])
def test_a_users_archive_with_a_device_or_reserved_name_refuses(tmp_path, extra):
    with pytest.raises(ValueError, match='not a plain name'):
        edi.Project.load(str(user_archive(tmp_path, extra)))


def patched_user_archive(tmp_path: Path, placeholder: str, raw: bytes) -> Path:
    """A user archive whose extra file name has `placeholder` swapped for raw bytes."""
    assert len(placeholder.encode()) == len(raw), (
        "The raw name has the placeholder's byte length, so archive offsets stay valid."
    )
    path = user_archive(tmp_path, f'notes/{placeholder}.txt')
    name = f'lbco/notes/{placeholder}.txt'.encode()  # local header and central directory
    path.write_bytes(path.read_bytes().replace(name, b'lbco/notes/' + raw + b'.txt'))
    return path


@pytest.mark.parametrize(
    'extra', ['COM¹.txt', 'notes/lpt²', 'Com³.log', 'CON .txt', 'nul .tar.gz']
)
def test_a_users_archive_with_a_superscript_or_spaced_device_name_refuses(tmp_path, extra):
    with pytest.raises(ValueError, match='not a plain name'):
        edi.Project.load(str(user_archive(tmp_path, extra)))


@pytest.mark.parametrize(
    'raw',
    [b'\xe0\x80\xaf', b'\xed\xa0\x80', b'\xf4\x90\x80\x80', b'\xf5\x80\x80', b'\xc0\xaf', b'\x80'],
    ids=['overlong', 'surrogate', 'above-range', 'f5', 'c0-overlong', 'lone-continuation'],
)
def test_a_users_archive_with_a_name_that_is_not_unicode_refuses(tmp_path, raw):
    path = patched_user_archive(tmp_path, 'X' * len(raw), raw)
    with pytest.raises(ValueError, match='not a plain name'):
        edi.Project.load(str(path))


@pytest.mark.parametrize('extra', ['notes/日本.txt', 'notes/🙂.txt'])
def test_a_users_archive_keeps_any_unicode_file_name(tmp_path, extra):
    assert edi.Project.load(str(user_archive(tmp_path, extra))) is not None, (
        'Three- and four-byte UTF-8 names in a user archive must open.'
    )


@pytest.mark.parametrize('length', [115, 116, 128])
def test_the_longest_admitted_id_downloads_its_project_and_raw_file(tmp_path, length):
    entry_id = 'p' * length
    collection = tmp_path / 'collection'
    archive = project_zip('one')
    entry = {
        'id': entry_id,
        'kind': 'project',
        'name': 'long',
        'files': [file_record(collection, 'projects/long.zip', archive, 'zip')],
    }
    (collection / 'index.json').write_text(
        json.dumps({'schema': 'edi-data-index/1', 'entries': [entry]})
    )
    if length > 115:
        with pytest.raises(ValueError, match='not a plain name'):
            edi.download_data(1, tmp_path / 'out', source=collection)
        return
    project = Path(edi.download_data(1, tmp_path / 'out', source=collection))
    assert project.parent.name == f'{entry_id}-{hashlib.sha256(archive).hexdigest()[:12]}', (
        'An id of the longest admitted length must still name its project folder.'
    )
    raw = edi.load_collection(collection).fetch(entry_id, tmp_path / 'raw')
    assert raw.read_bytes() == archive, 'The longest admitted id must also fetch its raw file.'


def empty_member_archive(*, damaged: bool) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('lbco/project.edi', 'data_project\n')
        archive.writestr('lbco/empty.dat', b'')
    data = bytearray(stream.getvalue())
    if damaged:
        with zipfile.ZipFile(io.BytesIO(bytes(data))) as archive:
            offset = archive.getinfo('lbco/empty.dat').header_offset
        assert data[offset : offset + 4] == b'PK\x03\x04', (
            "The central directory points at the empty member's local header."
        )
        data[offset : offset + 4] = b'XXXX'  # the local header the central directory points at
    return bytes(data)


@pytest.mark.parametrize('damaged', [False, True], ids=['intact', 'damaged-local-header'])
def test_an_empty_member_unpacks_only_when_the_reader_succeeds(tmp_path, damaged):
    data = empty_member_archive(damaged=damaged)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.getinfo('lbco/empty.dat').compress_size > 0, 'a deflated empty member'
    collection = tmp_path / 'collection'
    entry = {
        'id': 'lbco-project',
        'kind': 'project',
        'name': 'empty member',
        'files': [file_record(collection, 'projects/p.zip', data, 'zip')],
    }
    (collection / 'index.json').write_text(
        json.dumps({'schema': 'edi-data-index/1', 'entries': [entry]})
    )
    destination = tmp_path / 'out'
    if not damaged:
        project = Path(edi.download_data('lbco-project', destination, source=collection))
        assert (project / 'empty.dat').stat().st_size == 0, 'An intact empty member unpacks empty.'
        return
    for attempt in range(2):
        with pytest.raises(ValueError, match='cannot unpack'):
            edi.download_data('lbco-project', destination, source=collection)
        assert not destination.exists() or not list(destination.iterdir()), (
            f'Attempt {attempt + 1}: a member the reader fails on must leave nothing behind.'
        )


@pytest.mark.parametrize('mode', [0o300, 0o750, 0o775], ids=['owner-wx-only', '750', '775'])
@pytest.mark.usefixtures('source')
def test_a_published_project_keeps_owner_access_and_the_destinations_sharing(tmp_path, mode):
    destination = tmp_path / 'out'
    destination.mkdir()
    destination.chmod(mode)
    try:
        project = Path(edi.download_data('lbco-project', destination))
        again = Path(edi.download_data('lbco-project', destination))
        expected = 0o700 | (mode & 0o077)
        for folder in (project.parent, project):
            assert folder.stat().st_mode & 0o777 == expected, (
                f'{folder.name}: the owner keeps full access and group and others get the '
                f"destination's bits ({oct(expected)})."
            )
        assert again == project and (project / 'project.edi').read_text().endswith('one\n'), (
            'The published project must be readable and reused on the next download.'
        )
    finally:
        destination.chmod(0o700)
    assert not [p.name for p in destination.iterdir() if p.name.endswith('.unpacking')], (
        'No staging folder may be left behind.'
    )
