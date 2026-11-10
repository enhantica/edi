# SPDX-License-Identifier: BSD-3-Clause
"""A collection grants no filesystem authority beyond the requested destination."""

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def reference(name):
    spec = importlib.util.spec_from_file_location(
        'destination_reference_' + name,
        ROOT / 'tests/fixtures/destination_reference' / (name + '.py'),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = reference('collection')
WATCH = reference('watch')
INTERFACES = ['python', 'module-cli', 'native-cli', 'legacy-python', 'legacy-cli']
PUBLIC = INTERFACES[:3]
SELECTIONS = [
    (interface, selector) for interface in PUBLIC for selector in ('id', 'number', 'number-string')
]
SELECTIONS += [(interface, 'id') for interface in INTERFACES[3:]]
PYTHON_CALL = """import json, os, sys
import edi
interface, source, destination, selector, overwrite = json.loads(sys.argv[1])
try:
    if interface == 'python':
        path = edi.download_data(
            selector, destination=destination, source=source, overwrite=overwrite)
    else:
        path = edi.load_collection(source).fetch(selector, destination)
except Exception as problem:
    print(type(problem).__name__ + ': ' + str(problem), file=sys.stderr)
    sys.exit(1)
print('__BOUNDARY_PATH__' + os.fspath(path))
"""


def context(root):
    root.mkdir(parents=True, exist_ok=True)
    paths = {name: root / name for name in ('destination', 'outside', 'process', 'collection')}
    for name in ('destination', 'outside', 'process'):
        paths[name].mkdir()
    (paths['destination'] / '.tmp').mkdir()
    (paths['outside'] / 'canary').write_bytes(FIXTURE.CANARY)
    return {'root': root, **paths}


def invoke(interface, paths, selector, *, overwrite=False):
    destination, source = paths['destination'], paths['collection']
    env = {
        **os.environ,
        'TMPDIR': str(destination / '.tmp'),
        'TMP': str(destination / '.tmp'),
        'TEMP': str(destination / '.tmp'),
        'PYTHONDONTWRITEBYTECODE': '1',
        'EDI_COLLECTION': str(source),
    }
    if interface in {'python', 'legacy-python'}:
        request = [interface, str(source), str(destination), selector, overwrite]
        command = [sys.executable, '-B', '-c', PYTHON_CALL, json.dumps(request)]
    elif interface == 'legacy-cli':
        command = [
            sys.executable,
            '-B',
            '-m',
            'edi',
            'collection',
            '--source',
            str(source),
            'fetch',
            str(selector),
            '--into',
            str(destination),
        ]
    else:
        if interface == 'native-cli':
            artifact = Path(importlib.import_module('edi._edi').__file__).resolve().parents[2]
            native = os.environ.get(
                'EDI_NATIVE_CLI',
                str(
                    artifact
                    / ('cli/easydiffraction.exe' if os.name == 'nt' else 'cli/easydiffraction')
                ),
            )
            prefix = [native]
        else:
            prefix = [sys.executable, '-B', '-m', 'edi']
        command = [
            *prefix,
            'download-data',
            str(selector),
            '--source',
            str(source),
            '-d',
            str(destination),
        ]
        if overwrite:
            command.append('--overwrite')
    result = subprocess.run(
        command,
        cwd=paths['process'],
        env=env,
        capture_output=True,
        text=True,
        timeout=12,
        check=False,
    )
    lines = result.stdout.splitlines()
    path = lines[-1].removeprefix('__BOUNDARY_PATH__') if lines else ''
    if interface in {'module-cli', 'native-cli'} and ' is at ' in path:
        path = path.split(' is at ', 1)[1]
    return result, Path(path) if path else None


def exercise(interface, paths, selector, *, overwrite=False):
    destination = paths['destination']
    requested = destination.resolve()
    outside_before = FIXTURE.snapshot(paths['root'], destination)
    inside_before = FIXTURE.snapshot(destination)
    with WATCH.Watch(paths['root'], destination, allow_private_staging=True) as observer:
        result, output = invoke(interface, paths, selector, overwrite=overwrite)
        events = observer.events()
    assert not events, (
        'A download must never modify the controlled outside tree, even transiently: '
        + str(events)
    )
    assert FIXTURE.snapshot(paths['root'], destination) == outside_before, (
        'A download must preserve every outside file, directory and symlink'
    )
    assert destination.resolve() == requested, 'A download must not redirect the destination root'
    assert result.returncode >= 0, (
        'Malformed collection input must not crash the interface process'
    )
    if result.returncode == 0:
        assert (
            output is not None and output.exists() and output.resolve().is_relative_to(requested)
        ), 'Every successful output path must resolve within the requested destination'
    inside_after = FIXTURE.snapshot(destination)
    for name, value in inside_after.items():
        if inside_before.get(name) != value:
            assert (destination / name).resolve().is_relative_to(requested), (
                'A newly published output must not be an escaping symlink'
            )
    return result, output


@pytest.fixture(scope='module', autouse=True)
def established_interfaces(tmp_path_factory):
    for interface in INTERFACES:
        for kind in ('project', 'data'):
            paths = context(tmp_path_factory.mktemp('boundary-control') / 'case')
            record = FIXTURE.make(paths['collection'], kind=kind)
            result, output = exercise(interface, paths, 'safe-project')
            assert result.returncode == 0, (
                'Each interface must first complete a valid authored download: ' + result.stderr
            )
            if kind == 'project' and interface in PUBLIC:
                assert (
                    output.is_dir() and (output / 'project.edi').read_bytes() == FIXTURE.PROJECT
                ), 'A normal project download must extract the independently authored project'
                expected = paths['destination'] / ('safe-project-' + record['sha256'][:12])
                assert output.resolve().is_relative_to(expected.resolve()), (
                    'The cache fixture must exercise the documented project destination layout'
                )
            else:
                expected = (paths['collection'] / record['path']).read_bytes()
                assert output.read_bytes() == expected, (
                    'A normal file or opaque fetch must return the authored bytes'
                )
    return True


@pytest.mark.parametrize(('interface', 'selection'), SELECTIONS)
@pytest.mark.parametrize(
    'form',
    [
        'parent',
        'absolute',
        'backslash-parent',
        'drive-absolute',
        'drive-relative',
        'extended-drive',
    ],
)
def test_resolved_entry_ids_cannot_escape_the_destination(tmp_path, interface, selection, form):
    paths = context(tmp_path / 'case')
    identity = FIXTURE.attack_id(form, paths['outside'])
    FIXTURE.make(paths['collection'], identity)
    selector = identity if selection == 'id' else 1 if selection == 'number' else '1'
    exercise(interface, paths, selector)


@pytest.mark.parametrize('interface', INTERFACES)
@pytest.mark.parametrize('form', ['parent', 'absolute', 'drive', 'symlink'])
def test_archive_members_cannot_grant_outside_write_authority(tmp_path, interface, form):
    paths = context(tmp_path / 'case')
    member = FIXTURE.archive_member(form, paths['outside'])
    FIXTURE.make(paths['collection'], member=member, outside=paths['outside'])
    exercise(interface, paths, 'safe-project')


@pytest.mark.parametrize('interface', INTERFACES)
def test_existing_output_symlink_cannot_redirect_a_file_write(tmp_path, interface):
    paths = context(tmp_path / 'case')
    FIXTURE.make(paths['collection'], kind='data')
    try:
        (paths['destination'] / 'payload.xye').symlink_to(paths['outside'] / 'canary')
    except OSError:
        pytest.skip('This platform cannot create the controlled symlink fixture')
    exercise(interface, paths, 'safe-project')


@pytest.mark.parametrize('interface', INTERFACES)
@pytest.mark.parametrize('link_kind', ['symlink', 'hardlink'])
def test_existing_staging_links_cannot_modify_an_outside_file(tmp_path, interface, link_kind):
    paths = context(tmp_path / 'case')
    FIXTURE.make(paths['collection'], kind='data')
    staging = paths['destination'] / 'payload.xye.partial'
    try:
        if link_kind == 'symlink':
            staging.symlink_to(paths['outside'] / 'canary')
        else:
            staging.hardlink_to(paths['outside'] / 'canary')
    except OSError:
        pytest.skip('This platform cannot create the controlled staging link')
    exercise(interface, paths, 'safe-project')


@pytest.mark.parametrize('interface', PUBLIC)
@pytest.mark.parametrize('link_kind', ['directory', 'project-marker'])
def test_nested_cached_links_cannot_return_an_outside_project(tmp_path, interface, link_kind):
    paths = context(tmp_path / 'case')
    record = FIXTURE.make(paths['collection'])
    cached = paths['destination'] / ('safe-project-' + record['sha256'][:12])
    cached.mkdir()
    (paths['outside'] / 'project.edi').write_bytes(FIXTURE.PROJECT)
    child = cached / 'reference'
    if link_kind != 'directory':
        child.mkdir()
    try:
        if link_kind == 'directory':
            child.symlink_to(paths['outside'], target_is_directory=True)
        else:
            (child / 'project.edi').symlink_to(paths['outside'] / 'project.edi')
    except OSError:
        pytest.skip('This platform cannot create the controlled cached descendant link')
    result, output = exercise(interface, paths, 'safe-project')
    if result.returncode == 0:
        assert (output / 'project.edi').resolve().is_relative_to(paths['destination'].resolve()), (
            'A successful cached project marker must itself resolve inside the destination'
        )


@pytest.mark.parametrize('interface', INTERFACES)
def test_unrelated_destination_child_does_not_redirect_root_resolution(tmp_path, interface):
    paths = context(tmp_path / 'case')
    FIXTURE.make(paths['collection'], kind='data')
    unrelated = paths['destination'] / 'x'
    try:
        unrelated.symlink_to(paths['outside'], target_is_directory=True)
    except OSError:
        pytest.skip('This platform cannot create the unrelated child symlink')
    result, _ = exercise(interface, paths, 'safe-project')
    assert result.returncode == 0, (
        'An unrelated child symlink must not change the destination or refuse a valid download'
    )


@pytest.mark.parametrize('interface', PUBLIC)
def test_failed_extraction_cannot_become_a_successful_cache_on_retry(tmp_path, interface):
    paths = context(tmp_path / 'case')
    FIXTURE.make(paths['collection'], member='conflict')
    first, _ = exercise(interface, paths, 'safe-project')
    assert first.returncode != 0, (
        'An archive whose child requires replacing a regular parent file must be refused'
    )
    second, _ = exercise(interface, paths, 'safe-project')
    assert second.returncode != 0, (
        'Retrying an incomplete extraction must not admit its project marker as a complete cache'
    )


@pytest.mark.parametrize('interface', PUBLIC)
@pytest.mark.parametrize('overwrite', [False, True])
def test_project_cache_symlink_cannot_escape_during_reuse_or_replacement(
    tmp_path, interface, overwrite
):
    paths = context(tmp_path / 'case')
    record = FIXTURE.make(paths['collection'])
    cached = paths['outside'] / 'cached'
    cached.mkdir()
    (cached / 'project.edi').write_bytes(FIXTURE.PROJECT)
    link = paths['destination'] / ('safe-project-' + record['sha256'][:12])
    try:
        link.symlink_to(cached, target_is_directory=True)
    except OSError:
        pytest.skip('This platform cannot create the controlled cache symlink fixture')
    exercise(interface, paths, 'safe-project', overwrite=overwrite)


@pytest.mark.parametrize('interface', PUBLIC)
@pytest.mark.parametrize('selector', [-1, 0, 2, '../outside/selector', 'C:../outside/selector'])
def test_invalid_listing_handles_are_not_filesystem_paths(tmp_path, interface, selector):
    paths = context(tmp_path / 'case')
    FIXTURE.make(paths['collection'])
    result, _ = exercise(interface, paths, selector)
    assert result.returncode != 0, (
        'An out-of-range ordinal or unknown path-like key must be refused'
    )
