"""Round-trip ownership through the real native and browser Session receivers.

Browser storage callbacks are injected; this observes the production browser
transaction branch, not packed WebAssembly UI. The Qt actor covers Home input.
"""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.scan_app.build_probe import fingerprint

ROOT = Path(__file__).resolve().parents[3]
ROUTES = [
    'desktop-folder',
    'desktop-archive',
    'desktop-example',
    'web-upload-folder',
    'web-upload-zip',
    'web-stored-folder',
    'web-stored-zip',
    'web-stored-browser',
    'web-recovery',
]


@pytest.fixture(scope='module')
def tutorial_observer():
    path = Path(
        os.environ.get(
            'EDI_TRANSACTION_RECEIPT', ROOT / 'build/tutorial-transactions/receipt.json'
        )
    )
    assert path.is_file(), (
        'Tutorial ownership requires the source-qualified project_transactions/build.py observer'
    )
    receipt = json.loads(path.read_text(encoding='utf-8'))
    assert receipt['production'] == fingerprint(ROOT), (
        'Tutorial ownership executes the exact current production Session and app inputs'
    )
    inputs = {**receipt['linked'], **receipt['sdk']}
    inputs[receipt['binary']] = receipt['binary_sha256']
    for item in receipt['original_app_library'], receipt['original_core_library']:
        inputs[item['path']] = item['sha256']
    for name, expected in receipt['fixture'].items():
        inputs[str(ROOT / 'tests/fixtures/project_transactions' / name)] = expected
    for name, expected in inputs.items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected, (
            'The ownership observer retains its actual compiled fixture, app and SDK identity: '
            + name
        )
    return receipt['binary']


def observe(binary, tmp_path, route, entry, ending, accident):
    group = f'tutorial/{route}/{entry}/{ending}/{accident}'
    result = subprocess.run(
        [binary, str(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment'), group],
        capture_output=True,
        text=True,
        timeout=25,
        check=False,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    (tmp_path / 'observation.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    assert result.returncode == 0, (
        'The accident must reach real project open, tutorial entry and explicit ending: '
        + result.stderr
    )
    rows = json.loads(result.stdout.splitlines()[-1])
    assert len(rows) == 1, 'Each ownership case executes its one requested accident'
    return rows[0]


def preserved_until_choice(row):
    assert row['accepted'] and row['distinct'], (
        'A scientific tutorial opens a distinct temporary project'
    )
    assert row['aliveDuring'] and row['bytesDuring'] and row['editDuring'], (
        'Entering Tutorials retains the original object, unsaved edit and backing bytes'
    )
    assert row['aliveBeforeChoice'] and row['bytesBeforeChoice'], (
        'An accidental second action cannot release the user project before explicit Keep'
    )


def restored_with_destination(row):
    assert row['restored'] and row['editAfter'] and row['filesAfter'], (
        'Stop or Discard returns the exact original object, unsaved edit and backing files'
    )
    assert row['after'] == row['before'], (
        'Returning from Tutorials retains the original save destination and upload provenance'
    )
    if row['route'].startswith('web-'):
        assert row['saveAccepted'] and row['write'] == {
            'key': row['before']['webKey'],
            'kind': row['before']['webKind'],
        }, 'The first real Save after Stop or Discard writes the original browser place'


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('entry', ['new', 'example'])
@pytest.mark.parametrize('ending', ['stop', 'discard', 'keep'])
def test_open_tutorial_then_choose_an_ending_keeps_the_user_destination(
    tutorial_observer, tmp_path, route, entry, ending
):
    # Accident: Tutorials is opened while a project with an ordinary save destination is edited.
    row = observe(tutorial_observer, tmp_path, route, entry, ending, 'ordinary')
    preserved_until_choice(row)
    if ending == 'keep':
        assert row['kept'], 'Explicit Keep retains the tutorial project as the active project'
        if route == 'desktop-folder':
            assert row['filesAfter'], 'Keep cannot delete the original saved folder'
        assert row['archiveUnchanged'], 'Keep cannot rewrite or remove the original archive'
    else:
        restored_with_destination(row)


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('entry', ['new', 'example'])
def test_home_starting_another_tutorial_cannot_overwrite_the_set_aside_owner(
    tutorial_observer, tmp_path, route, entry
):
    # Accident: a nonmodal tutorial leaves Home usable; Tutorials is selected a second time.
    row = observe(tutorial_observer, tmp_path, route, entry, 'stop', 'restart')
    preserved_until_choice(row)
    restored_with_destination(row)


@pytest.mark.parametrize('entry', ['new', 'example'])
def test_examples_reopening_the_original_example_cannot_reuse_its_extraction_folder(
    tutorial_observer, tmp_path, entry
):
    # Accident: Examples reopens the user's original bundled example during a tutorial.
    row = observe(tutorial_observer, tmp_path, 'desktop-example', entry, 'stop', 'reopen-example')
    preserved_until_choice(row)
    restored_with_destination(row)


@pytest.mark.parametrize('route', ['desktop-example', 'web-stored-browser'])
@pytest.mark.parametrize('entry', ['new', 'example'])
@pytest.mark.parametrize('generation', [1, 2, 3])
@pytest.mark.parametrize('ending', ['stop', 'discard', 'keep'])
def test_start_after_keep_never_recycles_the_kept_project_directory(
    tutorial_observer, tmp_path, route, entry, generation, ending
):
    # Accident: Keep, edit/import files into that project, then start the same tutorial again.
    row = observe(tutorial_observer, tmp_path, route, entry, ending, f'after-keep-{generation}')
    preserved_until_choice(row)
    assert row['directoryDistinct'], (
        'A later tutorial owns a different backing directory from the kept user project'
    )
    assert row['filesAfter'], (
        'Starting and ending a later tutorial never rewrites or deletes the kept project files'
    )
    if ending != 'keep':
        restored_with_destination(row)
