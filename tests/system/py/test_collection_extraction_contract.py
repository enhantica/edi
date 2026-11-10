# SPDX-License-Identifier: BSD-3-Clause
"""Closed names, failed-operation cleanup and completed-cache admission from first principles."""

import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def reference(directory, name):
    spec = importlib.util.spec_from_file_location(
        directory + '_' + name, ROOT / 'tests/fixtures' / directory / (name + '.py')
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SPEC = importlib.util.spec_from_file_location(
    'destination_boundary', Path(__file__).with_name('test_download_destination_boundary.py')
)
BOUNDARY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOUNDARY)
NAMES = reference('extraction_reference', 'names')


def recorded_source(paths, temporary, monkeypatch):
    compiled = Path(os.environ.get('EDI_TRANSPORT_FIXTURE_DIR', ROOT / 'build/recorded-transport'))
    receipt = compiled / 'sources.json'
    assert (
        receipt.is_file()
        and json.loads(receipt.read_text(encoding='utf-8'))
        == reference('native_transport', 'build').sources()
    ), 'Cache-refetch witnesses require the source-matched recorded transport fixture'
    trace = temporary / 'cache-transport.jsonl'
    settings = {
        'LD_PRELOAD': str(compiled / 'liboffline_guard.so'),
        'EDI_REFERENCE_CURL_LIBRARY': str(compiled / 'librecorded_curl.so'),
        'EDI_REFERENCE_LOADER_TRACE': str(temporary / 'cache-loader.log'),
        'EDI_REFERENCE_NETWORK_TRACE': str(temporary / 'cache-network.log'),
        'EDI_REFERENCE_TRANSPORT_ROOT': str(paths['collection']),
        'EDI_REFERENCE_TRANSPORT_TRACE': str(trace),
        'PYTHONPATH': str(ROOT / 'tests/fixtures/download_reference')
        + os.pathsep
        + os.environ.get('PYTHONPATH', ''),
    }
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    for name in ('EDI_REFERENCE_PRIMARY_OUTAGE', 'EDI_REFERENCE_MISSING_CURL'):
        monkeypatch.delenv(name, raising=False)
    probe = subprocess.run(
        [
            sys.executable,
            '-B',
            '-c',
            (
                'import ctypes; '
                'assert ctypes.CDLL(None).recorded_guard_ready()==6193; '
                'assert ctypes.CDLL("libcurl.so.4").recorded_transport_ready()==3187'
            ),
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert probe.returncode == 0, (
        'The offline guard and recorded native replies must be active before any cache request: '
        + probe.stderr
    )
    paths['collection'] = 'https://raw.githubusercontent.com/enhantica/edi-data/main/'
    return trace


def assert_refetched(trace):
    assert trace.is_file() and any(
        json.loads(line)['path'] == 'project.zip'
        for line in trace.read_text(encoding='utf-8').splitlines()
    ), 'An unadmitted cache must actually refetch the authored archive through recorded transport'
    assert not trace.with_name('cache-network.log').exists(), (
        'A cache witness must never attempt a real network operation'
    )


@pytest.fixture(scope='module', autouse=True)
def normal_entrances(tmp_path_factory):
    for interface in BOUNDARY.INTERFACES:
        paths = BOUNDARY.context(tmp_path_factory.mktemp('structural-control') / 'case')
        fixture = reference('destination_reference', 'collection')
        fixture.make(paths['collection'])
        result, output = BOUNDARY.invoke(interface, paths, 'safe-project')
        assert result.returncode == 0 and output is not None and output.exists(), (
            'Every structural-contract entrance must first complete a valid authored transfer'
        )
        if interface in BOUNDARY.PUBLIC:
            assert (output / 'project.edi').read_bytes() == fixture.PROJECT, (
                'The structural-contract control must extract the authored project'
            )


@pytest.mark.parametrize('field', ['id', 'file'])
@pytest.mark.parametrize('population', ['devices', 'closed-grammar'])
def test_shared_index_admission_enforces_the_closed_name_contract(tmp_path, field, population):
    root = tmp_path / 'collection'
    reference('destination_reference', 'collection').make(root)
    initial = json.loads((root / 'index.json').read_text(encoding='utf-8'))
    load = importlib.import_module('edi').load_collection
    load(str(root))  # A broken reader or invalid fixture cannot count as name rejection.
    values = NAMES.device_names() if population == 'devices' else NAMES.excluded_names()
    exercised = 0
    for value in values:
        if field == 'file' and value == 'left/right':
            continue  # A slash separates two valid path segments; it is not an id character.
        index = json.loads(json.dumps(initial))
        if field == 'id':
            index['entries'][0]['id'] = value
        else:
            index['entries'][0]['files'][0]['path'] = 'files/' + value
        (root / 'index.json').write_text(json.dumps(index), encoding='utf-8')
        with pytest.raises(
            (ValueError, RuntimeError),
            match=r'name|path|segment|invalid|reserved|index|entry|id|file',
        ):
            load(str(root))
        exercised += 1
    assert exercised > 0, 'The closed-name contract must exercise its independent name population'


@pytest.mark.parametrize('field', ['id', 'file'])
def test_ordinary_names_near_device_spellings_remain_admissible(tmp_path, field):
    root = tmp_path / 'collection'
    reference('destination_reference', 'collection').make(root)
    initial = json.loads((root / 'index.json').read_text(encoding='utf-8'))
    for name in NAMES.VALID:
        index = json.loads(json.dumps(initial))
        if field == 'id':
            index['entries'][0]['id'] = name
        else:
            index['entries'][0]['files'][0]['path'] = 'files/' + name
        (root / 'index.json').write_text(json.dumps(index), encoding='utf-8')
        parsed = importlib.import_module('edi').load_collection(str(root))
        assert parsed is not None, 'The closed grammar must admit ordinary nonreserved names'


@pytest.mark.parametrize('interface', BOUNDARY.INTERFACES)
@pytest.mark.parametrize('identity', ['cOn.TxT', 'pRn.tar.gz', 'COM9.EDI', 'lPt7'])
def test_reserved_ids_are_refused_by_every_shared_entrance(tmp_path, interface, identity):
    paths = BOUNDARY.context(tmp_path / 'case')
    reference('destination_reference', 'collection').make(paths['collection'], identity)
    result, _ = BOUNDARY.exercise(interface, paths, identity)
    assert result.returncode != 0, 'Every collection entrance must refuse reserved device ids'
    assert BOUNDARY.FIXTURE.snapshot(paths['destination']) == {'.tmp': ('directory',)}, (
        'A refused reserved id must publish no destination artifact'
    )


@pytest.mark.parametrize('interface', BOUNDARY.PUBLIC)
@pytest.mark.parametrize(
    'member',
    [
        'cOn/project.edi',
        'reference/NuL.txt',
        'reference/cOm9.edi',
        'reference/COM¹.txt',
        'reference/CONIN$',
    ],
)
def test_reserved_archive_segments_are_refused_before_publication(tmp_path, interface, member):
    paths = BOUNDARY.context(tmp_path / 'case')
    reference('destination_reference', 'collection').make(paths['collection'], member=member)
    result, _ = BOUNDARY.invoke(interface, paths, 'safe-project')
    assert result.returncode != 0, 'Every archive path segment must obey the closed name grammar'
    assert BOUNDARY.FIXTURE.snapshot(paths['destination']) == {'.tmp': ('directory',)}, (
        'A reserved archive segment must leave no published file or project'
    )


@pytest.mark.parametrize('interface', BOUNDARY.PUBLIC)
def test_failed_explicit_directory_creation_cannot_publish_a_project(tmp_path, interface):
    paths = BOUNDARY.context(tmp_path / 'case')
    BOUNDARY.FIXTURE.make(paths['collection'], member='directory-conflict')
    result, _ = BOUNDARY.invoke(interface, paths, 'safe-project')
    assert result.returncode > 0, (
        'A directory entry conflicting with a regular file must be refused'
    )
    assert BOUNDARY.FIXTURE.snapshot(paths['destination']) == {'.tmp': ('directory',)}, (
        'A failed directory creation must publish no incomplete project or archive'
    )


@pytest.mark.skipif(
    not sys.platform.startswith('linux'), reason='Move cookies are a Linux observer'
)
def test_publication_observer_requires_rename_even_when_copy_outputs_match(tmp_path):
    for operation in ('rename', 'copy'):
        root = tmp_path / operation
        root.mkdir()
        destination = root / 'destination'
        destination.mkdir()
        with BOUNDARY.WATCH.Publications(root) as observer:
            stage = Path(tempfile.mkdtemp(dir=root))
            (stage / 'project.edi').write_bytes(BOUNDARY.FIXTURE.PROJECT)
            published = destination / 'published'
            if operation == 'rename':
                stage.rename(published)
            else:
                shutil.copytree(stage, published)
                shutil.rmtree(stage)
            moves = [row for row in observer.changes() if row['destination'] == published]
        assert (published / 'project.edi').read_bytes() == BOUNDARY.FIXTURE.PROJECT, (
            'Both publication controls must have identical authored output bytes'
        )
        if operation == 'rename':
            assert moves == [{'kind': 'rename', 'source': stage, 'destination': published}], (
                'The publication observer must reach the actual atomic directory rename'
            )
        else:
            assert moves == [{'kind': 'create', 'destination': published}], (
                'A copied tree must be observed as directory creation'
            )


TRANSPORTS = [
    'local',
    pytest.param(
        'recorded',
        marks=pytest.mark.skipif(
            not sys.platform.startswith('linux'),
            reason='Recorded native HTTPS uses the Linux loader',
        ),
    ),
]


@pytest.mark.parametrize('transport', TRANSPORTS)
@pytest.mark.parametrize('interface', BOUNDARY.PUBLIC)
def test_a_project_cache_without_completion_is_fetched_again(
    tmp_path, monkeypatch, interface, transport
):
    paths = BOUNDARY.context(tmp_path / 'case')
    fixture = reference('destination_reference', 'collection')
    file = fixture.make(paths['collection'])
    cached = paths['destination'] / ('safe-project-' + file['sha256'][:12]) / 'reference'
    cached.mkdir(parents=True)
    (cached / 'project.edi').write_bytes(b'data_project\n_project.name incomplete-cache\n')
    trace = recorded_source(paths, tmp_path, monkeypatch) if transport == 'recorded' else None
    result, output = BOUNDARY.invoke(interface, paths, 'safe-project')
    assert result.returncode == 0, 'A cache without completion must permit a fresh verified fetch'
    assert output is not None and (output / 'project.edi').read_bytes() == fixture.PROJECT, (
        'An existing project marker alone must not admit an incomplete cache'
    )
    assert (output / 'structures/readme.txt').read_bytes() == b'independent archive member\n', (
        'Refetch must complete every independently authored member, not just its project marker'
    )
    if trace is not None:
        assert_refetched(trace)


@pytest.mark.parametrize('transport', TRANSPORTS)
@pytest.mark.parametrize('interface', BOUNDARY.PUBLIC)
def test_completion_is_bound_to_the_full_index_digest(tmp_path, monkeypatch, interface, transport):
    paths = BOUNDARY.context(tmp_path / 'case')
    file = BOUNDARY.FIXTURE.make(paths['collection'])
    index_path = paths['collection'] / 'index.json'
    trace = recorded_source(paths, tmp_path, monkeypatch) if transport == 'recorded' else None
    first, output = BOUNDARY.invoke(interface, paths, 'safe-project')
    assert first.returncode == 0 and output is not None, (
        'A completion-digest witness must first publish the valid authored project'
    )
    if trace is not None:
        trace.write_text('', encoding='utf-8')
    index = json.loads(index_path.read_text(encoding='utf-8'))
    original = file['sha256']
    forged = original[:-1] + ('0' if original[-1] != '0' else '1')
    assert forged[:12] == original[:12] and forged != original, (
        'The completion witness must retain the cache-name prefix while changing the full digest'
    )
    index['entries'][0]['files'][0]['sha256'] = forged
    index_path.write_text(json.dumps(index), encoding='utf-8')
    result, _ = BOUNDARY.invoke(interface, paths, 'safe-project')
    assert result.returncode > 0 and any(
        word in result.stderr.casefold() for word in ('sha', 'digest', 'hash')
    ), 'A completion marker for another full digest must trigger refetch and integrity refusal'
    if trace is not None:
        assert_refetched(trace)


def prove_file_failure(compiled, tmp_path, failure):
    env = {
        **os.environ,
        'LD_PRELOAD': str(compiled / 'librecorded_file_failures.so'),
        'EDI_REFERENCE_IO_FAILURE': failure,
    }
    for backend in ('cpp', 'stdio', 'posix'):
        control, trace = tmp_path / ('control-' + backend), tmp_path / (backend + '.trace')
        control_env = {
            **env,
            'EDI_REFERENCE_IO_ROOT': str(control),
            'EDI_REFERENCE_IO_TRACE': str(trace),
        }
        result = subprocess.run(
            [str(compiled / 'file_operation_control'), str(control), backend],
            env=control_env,
            capture_output=True,
            timeout=5,
            check=False,
        )
        assert result.returncode == (0 if failure == 'none' else 1) and trace.is_file(), (
            'Each independent standard writer must first prove the requested I/O outcome: '
            + backend
        )
        assert failure == 'none' or any(
            line.startswith(failure + ' ')
            for line in trace.read_text(encoding='utf-8').splitlines()
        ), 'Every standard writer must first prove the requested I/O refusal channel'
    return env


def failure_fixture():
    root = Path(
        os.environ.get('EDI_FILE_FAILURE_FIXTURE_DIR', ROOT / 'build/recorded-file-failures')
    )
    receipt = root / 'sources.json'
    assert receipt.is_file(), 'Build the recorded file-operation fixture explicitly before use'
    assert (
        json.loads(receipt.read_text(encoding='utf-8'))
        == reference('extraction_reference', 'build').sources()
    ), 'The operation-failure fixture must match its committed source hashes'
    return root


@pytest.mark.skipif(
    not sys.platform.startswith('linux'),
    reason='These operation faults use the Linux GNU stream ABI',
)
@pytest.mark.parametrize('interface', BOUNDARY.PUBLIC)
@pytest.mark.parametrize('failure', ['none', 'write', 'flush', 'close'])
def test_failed_member_io_cannot_publish_any_destination_artifact(
    tmp_path, monkeypatch, interface, failure
):
    compiled = failure_fixture()
    env = prove_file_failure(compiled, tmp_path, failure)
    paths = BOUNDARY.context(tmp_path / 'case')
    record = reference('destination_reference', 'collection').make(paths['collection'])
    published = paths['destination'] / ('safe-project-' + record['sha256'][:12])
    operation_trace = tmp_path / 'operation.trace'
    for key, value in {
        **env,
        'EDI_REFERENCE_IO_ROOT': str(paths['root']),
        'EDI_REFERENCE_IO_TRACE': str(operation_trace),
    }.items():
        if key.startswith('EDI_REFERENCE_IO_') or key == 'LD_PRELOAD':
            monkeypatch.setenv(key, value)
    before = reference('destination_reference', 'collection').snapshot(paths['root'])
    with BOUNDARY.WATCH.Publications(paths['root']) as publication:
        result, output = BOUNDARY.invoke(interface, paths, 'safe-project')
        moves = [move for move in publication.changes() if move['destination'] == published]
    assert operation_trace.is_file(), (
        'The actual extraction must reach the member I/O observer: ' + result.stderr
    )
    lines = operation_trace.read_text(encoding='utf-8').splitlines()
    directories = [line.split('|') for line in lines if line.startswith('stage|')]
    stages = [row for row in directories if Path(row[1]).parent == paths['destination'].parent]
    opened = [Path(line.removeprefix('opened|')) for line in lines if line.startswith('opened|')]
    if failure != 'none':
        assert any(line.startswith(failure + ' ') for line in lines), (
            'The actual extraction must reach the requested authored member I/O failure'
        )
        assert result.returncode > 0, (
            'A failed write, flush or close must report failure without crashing'
        )
        assert BOUNDARY.FIXTURE.snapshot(paths['destination']) == {'.tmp': ('directory',)}, (
            'A failed write, flush or close must publish nothing under the requested destination'
        )
        assert not moves, 'A failed extraction must never publish a partial tree, even transiently'
    roots = [
        row
        for row in directories
        if not any(
            Path(row[1]) != Path(other[1]) and Path(row[1]).is_relative_to(Path(other[1]))
            for other in directories
        )
    ]
    assert roots and all(
        int(mode) & 0o077 == 0 and int(owner) == os.geteuid() for _, _, mode, owner in roots
    ), 'Fresh staging roots must be private to the calling user; observed ' + str(roots)
    assert stages and opened, (
        'Extraction must create fresh private staging in the requested output parent; observed '
        + str(directories)
    )
    assert all(
        int(mode) & 0o077 == 0 and int(owner) == os.geteuid() for _, _, mode, owner in stages
    ), 'Fresh extraction staging must be private to the calling user'
    assert all(any(path.is_relative_to(Path(stage[1])) for stage in stages) for path in opened), (
        'Every extracted member must be written inside fresh private staging before publication'
    )
    if failure == 'none':
        assert result.returncode == 0 and output is not None, (
            'The unfaulted stage-check-publish control must complete'
        )
        assert (output / 'project.edi').read_bytes() == BOUNDARY.FIXTURE.PROJECT, (
            'Successful publication must contain the independently authored project bytes'
        )
        assert len(moves) == 1 and any(
            moves[0].get('source') == Path(stage[1]) for stage in roots
        ), 'A completed extraction must publish its fresh staged tree by one directory rename'
        return
    assert any(line.startswith(failure + ' ') for line in lines), (
        'The actual extraction must reach the requested authored member I/O failure'
    )
    assert result.returncode > 0, (
        'A failed write, flush or close must report failure without crashing'
    )
    assert BOUNDARY.FIXTURE.snapshot(paths['destination']) == {'.tmp': ('directory',)}, (
        'A failed write, flush or close must publish nothing under the destination'
    )
    assert reference('destination_reference', 'collection').snapshot(paths['root']) == before, (
        'A failed extraction must remove private staging and preserve unrelated outside state'
    )


@pytest.mark.skipif(
    not sys.platform.startswith('linux'), reason='The I/O policy observer is Linux-only'
)
@pytest.mark.parametrize('failure', ['none', 'write', 'flush', 'close'])
def test_io_policy_accepts_an_independent_correct_private_publisher(
    tmp_path, monkeypatch, failure
):
    def invoke(_interface, paths, _selector, *, overwrite=False):
        assert not overwrite, 'The independent publisher control must begin without replacement'
        result = subprocess.run(
            [
                sys.executable,
                '-B',
                str(ROOT / 'tests/fixtures/extraction_reference/publisher.py'),
                str(paths['collection']),
                str(paths['destination']),
            ],
            cwd=paths['process'],
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result, Path(result.stdout.strip()) if result.returncode == 0 else None

    monkeypatch.setattr(BOUNDARY, 'invoke', invoke)
    test_failed_member_io_cannot_publish_any_destination_artifact(
        tmp_path, monkeypatch, 'python', failure
    )
