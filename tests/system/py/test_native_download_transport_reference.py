# SPDX-License-Identifier: BSD-3-Clause
"""Standalone CLI transport A over authored data, without OS or network mutation."""

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / 'tests/fixtures'
pytestmark = pytest.mark.skipif(
    not sys.platform.startswith('linux'), reason='This loader fixture exercises Linux transport A'
)


def reference(directory, name):
    spec = importlib.util.spec_from_file_location(
        directory + '_' + name, FIXTURES / directory / (name + '.py')
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def recorded(tmp_path):
    compiled = Path(os.environ.get('EDI_TRANSPORT_FIXTURE_DIR', ROOT / 'build/recorded-transport'))
    receipt = compiled / 'sources.json'
    assert receipt.is_file(), 'The recorded native transport must be explicitly built before use'
    assert json.loads(receipt.read_text()) == reference('native_transport', 'build').sources(), (
        'The native transport fixture binaries must match their authored source receipt'
    )
    root = tmp_path / 'collection'
    data = reference('download_reference', 'build')
    index = data.build(root)
    reference('download_reference', 'tutorials').build(root)
    artifact = Path(importlib.import_module('edi._edi').__file__).resolve().parents[2]
    cli = os.environ.get('EDI_NATIVE_CLI', str(artifact / 'cli/easydiffraction'))
    env = {
        **os.environ,
        'LD_PRELOAD': str(compiled / 'liboffline_guard.so'),
        'EDI_REFERENCE_CURL_LIBRARY': str(compiled / 'librecorded_curl.so'),
        'EDI_REFERENCE_LOADER_TRACE': str(tmp_path / 'loader.log'),
        'EDI_REFERENCE_NETWORK_TRACE': str(tmp_path / 'network.log'),
        'EDI_REFERENCE_TRANSPORT_TRACE': str(tmp_path / 'transport.jsonl'),
        'EDI_REFERENCE_TRANSPORT_ROOT': str(root),
    }
    for name in (
        'EDI_COLLECTION',
        'EDI_TUTORIALS',
        'EDI_REFERENCE_MISSING_CURL',
        'EDI_REFERENCE_PRIMARY_OUTAGE',
    ):
        env.pop(name, None)
    return root, index, data, cli, env


def invoke(recorded, *arguments, missing=False):
    env = dict(recorded[4])
    if missing:
        env['EDI_REFERENCE_MISSING_CURL'] = '1'
    probe = """import ctypes, os
assert ctypes.CDLL(None).recorded_guard_ready() == 6193
if os.environ.get('EDI_REFERENCE_MISSING_CURL'):
    try: ctypes.CDLL('libcurl.so.4')
    except OSError: pass
    else: raise RuntimeError('missing-library fixture did not intercept libcurl')
else:
    assert ctypes.CDLL('libcurl.so.4').recorded_transport_ready() == 3187
"""
    ready = subprocess.run(
        [sys.executable, '-B', '-c', probe],
        env=env,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert ready.returncode == 0, (
        'Offline loader substitution and the network guard must be proven before the CLI runs: '
        + ready.stderr
    )
    result = subprocess.run(
        [recorded[3], *map(str, arguments)],
        env=env,
        capture_output=True,
        text=True,
        timeout=12,
        check=False,
    )
    network = Path(env['EDI_REFERENCE_NETWORK_TRACE'])
    assert not network.exists(), (
        'A recorded native download must never attempt a real network call'
    )
    return result


def rows(recorded):
    trace = Path(recorded[4]['EDI_REFERENCE_TRANSPORT_TRACE'])
    assert trace.is_file(), 'The native behavior witness must reach the recorded OS transport'
    return [json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines()]


def complete(result):
    assert result.returncode == 0, 'The documented native download must complete: ' + result.stderr


@pytest.mark.parametrize('selector', ['alpha-data', '1'])
def test_native_ids_and_listing_numbers_resolve_the_authored_entry(recorded, tmp_path, selector):
    listing = invoke(recorded, 'list-data')
    complete(listing)
    assert listing.stdout.index('alpha-data') < listing.stdout.index('zeta-data'), (
        'Native listing numbers must use the documented alphabetical data order'
    )
    destination = tmp_path / 'output'
    complete(invoke(recorded, 'download-data', selector, '-d', destination))
    assert (destination / 'alpha.xye').read_bytes() == recorded[2].MEASUREMENT, (
        'A native id and its listing number must return the independently authored bytes'
    )
    assert any(row['path'] == 'data/alpha.xye' for row in rows(recorded)), (
        'Native selection must reach the same authored file as the Python and app references'
    )


def test_native_project_extraction_returns_the_authored_project(recorded, tmp_path):
    destination = tmp_path / 'output'
    complete(invoke(recorded, 'download-data', 'proj-reference', '-d', destination))
    projects = list(destination.rglob('project.edi'))
    assert len(projects) == 1 and projects[0].read_bytes() == recorded[2].PROJECT, (
        'The native project download must extract the one authored project document'
    )
    assert any(row['path'] == 'data/project.zip' for row in rows(recorded)), (
        'Native project extraction must reach the recorded project archive'
    )


def test_native_dead_primary_falls_back_to_the_recorded_mirror(recorded, tmp_path):
    recorded[4]['EDI_REFERENCE_PRIMARY_OUTAGE'] = '1'
    destination = tmp_path / 'output'
    complete(invoke(recorded, 'download-data', 'alpha-data', '-d', destination))
    assert (destination / 'alpha.xye').read_bytes() == recorded[2].MEASUREMENT, (
        'Native mirror fallback must return the same independently authored bytes'
    )
    trace = rows(recorded)
    assert trace[0]['location'] == 'primary', 'The primary must be attempted before fallback'
    assert {'location': 'mirror', 'path': 'data/alpha.xye'} in trace, (
        'An unavailable primary must reach the recorded data mirror'
    )


def test_native_wrong_digest_refuses_without_a_destination_file(recorded, tmp_path):
    root, index = recorded[:2]
    index['entries'][1]['files'][0]['sha256'] = '0' * 64
    (root / 'index.json').write_text(json.dumps(index))
    destination = tmp_path / 'output'
    result = invoke(recorded, 'download-data', 'alpha-data', '-d', destination)
    assert result.returncode != 0, 'The native CLI must refuse the independently wrong digest'
    trace = rows(recorded)
    assert any(row['path'] == 'data/alpha.xye' for row in trace), (
        'Native digest refusal must inspect the actual recorded file'
    )
    assert not any(row['location'] == 'mirror' for row in trace), (
        'Native integrity refusal must not be treated as a primary outage'
    )
    assert not destination.exists() or not list(destination.rglob('*')), (
        'Native digest refusal must publish no destination file'
    )


def test_native_answered_missing_file_does_not_become_an_outage(recorded, tmp_path):
    (recorded[0] / 'data/alpha.xye').unlink()
    result = invoke(recorded, 'download-data', 'alpha-data', '-d', tmp_path / 'output')
    assert result.returncode != 0, 'An answered missing file must be refused'
    assert not any(row['location'] == 'mirror' for row in rows(recorded)), (
        'An HTTP missing-file answer must not trigger mirror fallback'
    )


def test_native_refused_extraction_publishes_no_member(recorded, tmp_path):
    recorded[2].refuse_archive(recorded[0], recorded[1])
    destination = tmp_path / 'output'
    result = invoke(recorded, 'download-data', 'proj-reference', '-d', destination)
    assert result.returncode != 0, 'The native CLI must refuse the verified unsafe archive'
    assert any(row['path'] == 'data/project.zip' for row in rows(recorded)), (
        'Native extraction refusal must reach the authored archive bytes'
    )
    assert not (tmp_path / 'outside.edi').exists(), (
        'Native archive refusal must never publish the escaping member'
    )
    assert not [
        path for path in destination.rglob('*') if path.is_file() and path.suffix != '.zip'
    ], 'Native archive refusal must leave no extracted file'


def test_missing_libcurl_has_a_clear_message_and_preserves_local_commands(recorded, tmp_path):
    complete(invoke(recorded, '--help', missing=True))
    local = tmp_path / 'local'
    complete(
        invoke(
            recorded,
            'download-data',
            'alpha-data',
            '--source',
            recorded[0],
            '-d',
            local,
            missing=True,
        )
    )
    assert (local / 'alpha.xye').read_bytes() == recorded[2].MEASUREMENT, (
        'A Linux system without libcurl must retain local collection downloads'
    )
    result = invoke(
        recorded, 'download-data', 'alpha-data', '-d', tmp_path / 'remote', missing=True
    )
    text = (result.stdout + result.stderr).lower()
    assert result.returncode != 0 and 'libcurl' in text and 'install' in text, (
        'Missing Linux libcurl must produce a plain dependency and installation message'
    )
    assert not Path(recorded[4]['EDI_REFERENCE_TRANSPORT_TRACE']).exists(), (
        'Missing-library refusal must occur before a transfer is performed'
    )


@pytest.mark.parametrize('formats', [('ipynb',), ('py',), ('ipynb', 'py')])
def test_native_tutorial_formats_return_only_requested_files(recorded, tmp_path, formats):
    destination = tmp_path / 'tutorials'
    flags = [] if formats == ('ipynb',) else ['--' + name for name in formats]
    complete(invoke(recorded, 'download-tutorial', '1', '-d', destination, *flags))
    expected = {
        f'zulu-first.{fmt}': (recorded[0] / 'tutorials' / f'zulu-first.{fmt}').read_bytes()
        for fmt in formats
    }
    assert {p.name: p.read_bytes() for p in destination.iterdir()} == expected, (
        'Native tutorial numbers must follow learning order and return only requested formats'
    )


def test_native_tutorial_batch_returns_every_authored_notebook(recorded, tmp_path):
    destination = tmp_path / 'tutorials'
    complete(invoke(recorded, 'download-all-tutorials', '-d', destination))
    expected = {p.name: p.read_bytes() for p in (recorded[0] / 'tutorials').glob('*.ipynb')}
    assert {p.name: p.read_bytes() for p in destination.iterdir()} == expected, (
        'Native tutorial batch must include every authored notebook and no unrequested script'
    )


@pytest.mark.parametrize('overwrite', [False, True])
def test_native_tutorial_overwrite_requires_the_explicit_flag(recorded, tmp_path, overwrite):
    destination = tmp_path / 'tutorials'
    destination.mkdir()
    target = destination / 'zulu-first.ipynb'
    target.write_bytes(b'independent edited tutorial\n')
    complete(
        invoke(
            recorded,
            'download-tutorial',
            'zulu-first',
            '-d',
            destination,
            *(['--overwrite'] if overwrite else []),
        )
    )
    expected = (
        (recorded[0] / 'tutorials/zulu-first.ipynb').read_bytes()
        if overwrite
        else b'independent edited tutorial\n'
    )
    assert target.read_bytes() == expected, (
        'Native tutorial download must preserve edits unless overwrite was requested'
    )
