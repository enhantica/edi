# SPDX-License-Identifier: BSD-3-Clause
"""Download behavior from upstream docs, over one authored collection and recorded replies."""

import importlib
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CARRIER = ROOT / 'tests/fixtures/download_reference'


def reference(name):
    spec = importlib.util.spec_from_file_location(
        'download_reference_' + name, CARRIER / (name + '.py')
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def collection(tmp_path, monkeypatch):
    root = tmp_path / 'collection'
    data = reference('build')
    index = data.build(root)
    reference('tutorials').build(root)
    trace = tmp_path / 'transport.jsonl'
    carrier = reference('recorded_transport')
    transport = carrier.Transport(root, trace)
    monkeypatch.setattr(socket.socket, 'connect', carrier.refuse_socket)
    monkeypatch.setattr(socket.socket, 'connect_ex', carrier.refuse_socket)
    monkeypatch.setattr(urllib.request, 'urlopen', transport)
    monkeypatch.delenv('EDI_COLLECTION', raising=False)
    monkeypatch.delenv('EDI_TUTORIALS', raising=False)
    return root, index, trace, transport


def function(name):
    target = getattr(importlib.import_module('edi'), name, None)
    assert callable(target), (
        'The documented download entrance must exist before its fault is exercised: ' + name
    )
    return target


def cli(collection, command, *arguments):
    root, _, trace, transport = collection
    env = {
        **os.environ,
        'PYTHONPATH': str(CARRIER) + os.pathsep + os.environ.get('PYTHONPATH', ''),
        'EDI_REFERENCE_TRANSPORT_ROOT': str(root),
        'EDI_REFERENCE_TRANSPORT_TRACE': str(trace),
        'EDI_REFERENCE_PRIMARY_OUTAGE': '1' if transport.dead_primary else '0',
    }
    supported = subprocess.run(
        [sys.executable, '-m', 'edi', '--help'],
        env=env,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert supported.returncode == 0 and command in supported.stdout, (
        'The module CLI must expose the documented command before its transport is exercised: '
        + command
    )
    return subprocess.run(
        [sys.executable, '-m', 'edi', command, *map(str, arguments)],
        env=env,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def trace_rows(collection):
    path = collection[2]
    assert path.is_file(), 'A behavior witness must actually reach the injected transport'
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


@pytest.mark.parametrize('interface', ['python', 'python-cli'])
def test_dead_primary_reaches_the_recorded_mirror(collection, tmp_path, interface):
    collection[3].dead_primary = True
    destination = tmp_path / 'download'
    if interface == 'python':
        path = Path(function('download_data')('alpha-data', destination=str(destination)))
    else:
        result = cli(collection, 'download-data', 'alpha-data', '-d', destination)
        assert result.returncode == 0, (
            'The CLI must complete a download after a primary outage: ' + result.stderr
        )
        path = destination / 'alpha.xye'
    assert path.read_bytes() == reference('build').MEASUREMENT, (
        'Mirror fallback must return the same independently authored bytes as the app'
    )
    rows = trace_rows(collection)
    assert any(row['location'] == 'primary' for row in rows), (
        'Fallback must first attempt the primary'
    )
    assert any(row['location'] == 'mirror' and row['path'] == 'data/alpha.xye' for row in rows), (
        'Fallback must fetch the verified file from the injected mirror'
    )


@pytest.mark.parametrize('interface', ['python', 'python-cli'])
def test_bad_digest_stops_before_any_destination_file(collection, tmp_path, interface):
    root, index, _, _ = collection
    index['entries'][1]['files'][0]['sha256'] = '0' * 64
    (root / 'index.json').write_text(json.dumps(index), encoding='utf-8')
    destination = tmp_path / 'refused'
    if interface == 'python':
        download = function('download_data')
        with pytest.raises((ValueError, RuntimeError), match=r'sha|digest|hash'):
            download('alpha-data', destination=str(destination))
    else:
        result = cli(collection, 'download-data', 'alpha-data', '-d', destination)
        assert result.returncode != 0, 'The CLI must refuse the independently wrong digest'
    rows = trace_rows(collection)
    assert any(row['path'] == 'data/alpha.xye' for row in rows), (
        'Digest refusal must inspect the actual received file'
    )
    assert not any(row['location'] == 'mirror' for row in rows), (
        'An integrity mismatch must not become a mirror outage'
    )
    assert not destination.exists() or not list(destination.rglob('*')), (
        'Digest refusal must leave no destination artifact'
    )


@pytest.mark.parametrize('interface', ['python', 'python-cli'])
def test_verified_unsafe_archive_publishes_no_extracted_member(collection, tmp_path, interface):
    root, index, _, _ = collection
    reference('build').refuse_archive(root, index)
    destination = tmp_path / 'refused'
    if interface == 'python':
        download = function('download_data')
        with pytest.raises((ValueError, RuntimeError), match=r'archive|path|escape|ZIP'):
            download('proj-reference', destination=str(destination))
    else:
        result = cli(collection, 'download-data', 'proj-reference', '-d', destination)
        assert result.returncode != 0, (
            'The CLI must refuse extraction of the digest-verified unsafe archive'
        )
    assert any(row['path'] == 'data/project.zip' for row in trace_rows(collection)), (
        'Extraction refusal must reach the authored archive transport'
    )
    assert not (tmp_path / 'outside.edi').exists(), (
        'Refused extraction must never publish the escaping member'
    )
    assert not [p for p in destination.rglob('*') if p.is_file() and p.suffix != '.zip'], (
        'Refused extraction must leave no extracted member'
    )


@pytest.mark.parametrize(
    ('interface', 'formats'),
    [
        ('python', ('ipynb',)),
        ('python', ('py',)),
        ('python-cli', ('ipynb',)),
        ('python-cli', ('py',)),
        ('python-cli', ('ipynb', 'py')),
    ],
)
def test_tutorial_format_flags_select_the_documented_files(
    collection, tmp_path, interface, formats
):
    destination = tmp_path / 'tutorials'
    if interface == 'python':
        function('download_tutorial')(
            'zulu-first', destination=str(destination), file_format=formats[0]
        )
    else:
        flags = [] if formats == ('ipynb',) else ['--' + name for name in formats]
        result = cli(collection, 'download-tutorial', 'zulu-first', '-d', destination, *flags)
        assert result.returncode == 0, (
            'The CLI tutorial format flags must complete: ' + result.stderr
        )
    expected = {
        f'zulu-first.{fmt}': (collection[0] / 'tutorials' / f'zulu-first.{fmt}').read_bytes()
        for fmt in formats
    }
    assert {p.name: p.read_bytes() for p in destination.iterdir()} == expected, (
        'Tutorial downloads must return only the requested independently authored formats'
    )


@pytest.mark.parametrize(
    ('interface', 'number'), [('python', 1), ('python', '1'), ('python-cli', '1')]
)
def test_tutorial_row_numbers_use_the_reference_learning_order(
    collection, tmp_path, interface, number
):
    destination = tmp_path / 'tutorials'
    if interface == 'python':
        path = Path(function('download_tutorial')(number, destination=str(destination)))
    else:
        result = cli(collection, 'download-tutorial', number, '-d', destination)
        assert result.returncode == 0, 'The CLI must resolve a one-based tutorial listing number'
        path = destination / 'zulu-first.ipynb'
    assert (
        path.name == 'zulu-first.ipynb'
        and path.read_bytes() == (collection[0] / 'tutorials/zulu-first.ipynb').read_bytes()
    ), 'A one-based tutorial row must resolve learning order before insertion order'


@pytest.mark.parametrize('interface', ['python', 'python-cli'])
@pytest.mark.parametrize('overwrite', [False, True])
def test_tutorial_overwrite_is_an_explicit_choice(collection, tmp_path, interface, overwrite):
    destination = tmp_path / 'tutorials'
    destination.mkdir()
    target = destination / 'zulu-first.ipynb'
    target.write_bytes(b'independent existing tutorial\n')
    if interface == 'python':
        function('download_tutorial')(
            'zulu-first', destination=str(destination), overwrite=overwrite
        )
    else:
        result = cli(
            collection,
            'download-tutorial',
            'zulu-first',
            '-d',
            destination,
            *(['--overwrite'] if overwrite else []),
        )
        assert result.returncode == 0, 'The CLI must honor the documented overwrite option'
    expected = (
        (collection[0] / 'tutorials/zulu-first.ipynb').read_bytes()
        if overwrite
        else b'independent existing tutorial\n'
    )
    assert target.read_bytes() == expected, (
        'Existing tutorial bytes must change only when overwrite is requested'
    )


@pytest.mark.parametrize('interface', ['python', 'python-cli'])
def test_download_all_tutorials_returns_every_notebook(collection, tmp_path, interface):
    destination = tmp_path / 'tutorials'
    if interface == 'python':
        paths = function('download_all_tutorials')(destination=str(destination))
        assert len(paths) == 2, 'The batch Python download must report every authored notebook'
    else:
        result = cli(collection, 'download-all-tutorials', '-d', destination)
        assert result.returncode == 0, 'The batch CLI download must complete'
    expected = {p.name: p.read_bytes() for p in (collection[0] / 'tutorials').glob('*.ipynb')}
    assert {p.name: p.read_bytes() for p in destination.iterdir()} == expected, (
        'Batch tutorial download must include each notebook and no unrequested scripts'
    )


@pytest.mark.parametrize('interface', ['python', 'python-cli'])
def test_tutorial_listing_numbers_follow_learning_order(collection, capsys, interface):
    if interface == 'python':
        function('list_tutorials')()
        output = capsys.readouterr().out
    else:
        result = cli(collection, 'list-tutorials')
        assert result.returncode == 0, 'The CLI must list the authored tutorial catalogue'
        output = result.stdout
    assert output.index('zulu-first') < output.index('alpha-second'), (
        'Tutorial learning order must precede alphabetical and insertion order'
    )
    assert re.search(r'\b1\b[^\n]*zulu-first', output), (
        'The first tutorial listing row must identify the same one-based download handle'
    )
