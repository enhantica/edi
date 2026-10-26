"""Durable-save and replacement-intent gates over the production Session callbacks."""

import base64
import hashlib
import io
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import edi
import pytest

from tests.conftest import crysta_reference_prefix
from tests.fixtures.scan_app.build_probe import fingerprint
from tests.fixtures.scan_screen.harness import pinned_browser, prepare_browser_toolchain

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def observer(tmp_path_factory):
    receipt_path = os.environ.get('EDI_TRANSACTION_RECEIPT')
    if receipt_path:
        receipt = json.loads(Path(receipt_path).read_text(encoding='utf-8'))
    else:
        directory = tmp_path_factory.mktemp('transaction-build')
        subprocess.run(
            [
                'pixi',
                'run',
                '-e',
                'app',
                'python',
                '-m',
                'tests.fixtures.project_transactions.build',
                '--root',
                str(ROOT),
                '--output',
                str(directory),
                '--sdk',
                str(crysta_reference_prefix()),
            ],
            cwd=ROOT,
            check=True,
        )
        receipt = json.loads((directory / 'observer/receipt.json').read_text(encoding='utf-8'))
    assert receipt['production'] == fingerprint(ROOT), (
        'A transaction receipt must bind the actual production sources under test'
    )
    binary = Path(receipt['binary'])
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == receipt['binary_sha256'], (
        'A transaction gate must execute the source-qualified observation binary'
    )
    for name, expected in receipt['linked'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected, (
            'The linked production and SDK artifacts must retain their qualified bytes'
        )
    for name, expected in receipt['sdk'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected, (
            'The qualified SDK headers and manifest must retain their compiled input bytes'
        )
    original = receipt['original_app_library']
    assert hashlib.sha256(Path(original['path']).read_bytes()).hexdigest() == original['sha256'], (
        'The observation boundary must retain its original production app archive identity'
    )
    return receipt


def observe(observer, group, tmp_path):
    result = subprocess.run(
        [observer['binary'], str(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment'), group],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    (tmp_path / (group + '.log')).write_text(result.stdout + result.stderr)
    assert result.returncode == 0, (
        'Every transaction observation must reach the actual production boundary: ' + result.stderr
    )
    rows = json.loads(result.stdout.splitlines()[-1])
    assert rows, 'A completed transaction group must contain actual observations'
    return rows


def test_newest_open_recent_or_recovery_intent_wins_in_both_completion_orders(observer, tmp_path):
    rows = observe(observer, 'overlap', tmp_path)
    assert len(rows) == 18, (
        'All ordered pairs of Open, Recent and recovery run in both completion orders'
    )
    for row in rows:
        assert row['olderRootRemoved'], (
            'A discarded superseded read removes its own temporary copy'
        )
        assert not row['loadErrors'], 'Superseded reads must be discarded silently'
        expected = ['newer', 'newer'] if row['newerFirst'] else [row['initial'], 'newer']
        assert [state['name'] for state in row['after']] == expected, (
            'Only the newest intent may publish; obsolete reads never replace even briefly: '
            + str(row)
        )


def test_pending_reads_recheck_new_edits_and_refuse_a_different_replacement(observer, tmp_path):
    rows = observe(observer, 'read-edits', tmp_path)
    assert len(rows) == 12, (
        'Every read route covers edits and example, New and desktop replacements'
    )
    for row in rows:
        assert row['olderRootRemoved'], 'A refused late read removes its temporary copy'
        if row['edit']:
            assert len(row['loadErrors']) == 1, (
                'Edits during a read must explain why it was not opened'
            )
            assert 'changed' in row['loadErrors'][0] and 'read' in row['loadErrors'][0], (
                'A late read refusal must explain the live project changed while being read'
            )
        else:
            assert not row['loadErrors'], 'A read for a different project is silently discarded'
        expected = 'different-project' if row['replacement'] else 'edited-while-reading'
        assert row['after'][0]['name'] == expected, (
            'A delayed read must recheck unsaved edits and initiating-project ownership: '
            + str(row)
        )
        assert row['after'][0]['modified'], (
            'Discarding an obsolete read must retain the live project unsaved state'
        )


def test_browser_save_waits_for_durable_success_and_preserves_refused_state(observer, tmp_path):
    rows = observe(observer, 'browser-save', tmp_path)
    assert len(rows) == 10, (
        'Browser, folder and ZIP places cover Save and moving Save as, success and refusal'
    )
    for row in rows:
        assert row['writes'], 'Every available-storage save must reach a held real write callback'
        assert row['finished'] == [row['ok']], (
            'Each durable write acknowledges its outcome once to replacement continuations'
        )
        assert row['pending']['modified'], (
            'A held browser write must leave the live project unsaved until durable success: '
            + str(row)
        )
        assert row['pending']['success'] == 0, 'A pending write must not announce Save success'
        assert row['pending']['drops'] == 0, 'A pending write must not delete recovery'
        if row['moving']:
            assert row['pending']['location'] == row['before']['location'], (
                'Moving Save as must retain the original place while its destination write is held'
            )
        if row['ok']:
            assert not row['after']['modified'], (
                'A confirmed durable write adopts a clean saved state'
            )
            assert row['success'] == 1, 'Exactly one confirmed write announces Save success'
        else:
            assert row['after'] == row['before'], (
                'Refused browser writes retain the working location, origin and unsaved state'
            )
            assert row['success'] == 0, 'A refused write must never announce success'
            assert row['errors'] == 1, 'A refused write must produce one visible failure signal'


def test_old_save_cannot_remove_new_recovery_and_unavailable_storage_is_not_success(
    observer, tmp_path
):
    rows = observe(observer, 'newer-recovery', tmp_path)
    assert len(rows) == 6, 'Every browser place exercises newer edits and unavailable storage'
    for row in rows:
        if row['unavailable'] and row['kind'] == 'browser':
            assert not row['pending']['returned'], (
                'Unavailable storage must not report successful Save to a replacement continuation'
            )
            assert row['after']['modified'], 'Unavailable storage must retain unsaved changes'
        elif row['editedAgain']:
            assert row['newer']['modified'], (
                'The older write overlaps an actual newer unsaved edit'
            )
            assert row['after']['modified'], (
                'Older durable success must not clear a newer unsaved revision'
            )
            assert row['after']['name'] == 'newer-unsaved-edit', (
                'A write completion retains the newer live edit'
            )
            assert row['drops'] == 0, 'An older Save completion must not delete newer recovery'


def test_desktop_refusal_preserves_location_origin_and_unsaved_state_then_retries(
    observer, tmp_path
):
    rows = observe(observer, 'desktop-save', tmp_path)
    assert len(rows) == 9, (
        'Folder, ZIP, example and read-only origins cover both formats and ordinary ZIP Save'
    )
    for row in rows:
        assert not row['result'], 'The independently blocked destination must refuse publication'
        assert row['error'], 'A refused destination must provide an explanation'
        assert row['refused'] == row['before'], (
            'Failed Save retains working path, ZIP location, origin and unsaved state: ' + str(row)
        )
        assert row['retryOk'], (
            'A refused Save must leave the project usable for a successful retry'
        )
        assert not row['afterRetry']['modified'], 'A successful retry commits the saved state'
        assert row['reopened'], 'The successfully retried output must reopen'
        assert row['reopenedName'] == 'unsaved-refusal-edit', (
            'A successful retry retains the exact unsaved edit'
        )


def browser_receipt(tmp_path, *, cleanup=None):
    node = shutil.which('node')
    chrome = os.environ.get('CHROME_HEADLESS_SHELL')
    if not chrome:
        prepare_browser_toolchain(dict(os.environ))
        chrome = str(
            pinned_browser(
                Path(os.environ.get('EDI_WASM_TOOLCHAIN', str(Path.home() / '.cache/edi-wasm')))
            )
        )
    assert node and chrome, 'The storage population gate requires pinned Node and real Chromium'
    source = ROOT / 'tests/fixtures/loop_parameter_ids/line-segment'
    expected = {
        path.relative_to(source).as_posix(): base64.b64encode(path.read_bytes()).decode()
        for path in source.rglob('*')
        if path.is_file()
    }
    inputs = tmp_path / 'input.json'
    inputs.write_text(json.dumps(expected), encoding='utf-8')
    output = tmp_path / 'output.json'
    result = subprocess.run(
        [
            node,
            str(ROOT / 'tests/fixtures/project_transactions/storage.mjs'),
            str(ROOT),
            str(inputs),
            str(output),
            chrome,
            cleanup or 'population',
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, (
        'Actual browser storage entry points must finish: ' + result.stderr
    )
    receipt = json.loads(output.read_text(encoding='utf-8'))
    return receipt, expected


def test_browser_save_as_replaces_old_entities_and_preserves_unrelated_destination_content(
    tmp_path,
):
    receipt, expected = browser_receipt(tmp_path)
    assert receipt['written']['ok'], 'The real browser must confirm destination write success'
    actual = receipt['actual']
    for name, value in expected.items():
        assert actual.get(name) == value, 'Every saved source member retains its complete bytes'
    assert 'structures/obsolete.edi' not in actual, (
        'Save as must remove obsolete structure documents'
    )
    assert 'experiments/obsolete.edi' not in actual, (
        'Save as must remove obsolete experiment documents'
    )
    unrelated = {
        'keep.txt': base64.b64encode(b'independent unrelated content').decode(),
        'photos/keep.txt': base64.b64encode(b'independent nested content').decode(),
    }
    assert actual == {**expected, **unrelated}, (
        'Replacing the project population must preserve every unrelated destination file'
    )
    reopened = tmp_path / 'reopened'
    for name, value in actual.items():
        path = reopened / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(value))
    original = edi.Project.load(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment')
    loaded = edi.Project.load(reopened)
    assert loaded.name == original.name, (
        'The written destination must reopen with the source identity'
    )
    assert len(loaded.structures) == len(original.structures), (
        'Reopening must load exactly the source structures'
    )
    assert len(loaded.experiments) == len(original.experiments), (
        'Reopening must load exactly the source experiments'
    )


def test_save_choice_releases_replacement_or_quit_only_after_durable_success(observer, tmp_path):
    rows = observe(observer, 'continuation', tmp_path)
    assert len(rows) == 8, (
        'Replacement and quit cover delayed success, failure, newer edits and unavailable storage'
    )
    for row in rows:
        pending = row['pending']
        assert pending['name'] == 'continuation-unsaved', (
            'The real unsaved-changes Save action retains the project while its write is held'
        )
        assert pending['modified'], (
            'A Save choice must retain unsaved state before durable success'
        )
        assert pending['visible'], 'Quit must not close the window before durable success'
        assert not pending['quitting'], 'A pending or unavailable write must not authorize quit'
        after = row['after']
        if row['changed']:
            assert row['edited'], 'The held write must overlap an actual later edit'
            assert after['name'] == 'changed-after-Save-choice', (
                'A continuation must retain edits made after the user chose Save'
            )
            assert after['modified'], 'A continuation must retain the newer unsaved revision'
            assert after['question'], 'An edit made during Save must be asked about again'
        elif not row['ok'] or row['unavailable']:
            assert after['name'] == 'continuation-unsaved', (
                'Failed or unavailable storage must never release replacement or quit'
            )
            assert after['modified'], 'Refused Save retains unsaved state'
            assert after['visible'], 'Refused Save retains the open window'
            assert not after['quitting'], 'Refused Save cannot authorize quitting'
        elif row['quit']:
            assert after['quitting'], 'Confirmed durable success may release the requested quit'
            assert not after['visible'], 'Confirmed quit actually closes the real window'
        else:
            assert not after['name'], (
                'Confirmed durable success releases the requested replacement'
            )


def test_archive_links_keep_lexical_member_identity_or_refuse_with_an_explanation(
    observer, tmp_path
):
    rows = observe(observer, 'archive-links', tmp_path)
    assert len(rows) == 4, (
        'The shared archive writer exercises internal, external, folder and broken links'
    )
    for row in rows:
        if row['kind'] in {'directory', 'broken'}:
            assert not row['ok'], 'A folder or broken link must refuse the whole archive'
            assert row['error'], 'An unsupported link must provide an explanatory refusal'
            continue
        assert row['ok'], (
            'A regular file link must be carried under its lexical project member name'
        )
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(row['archive']))) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names)), 'Every archive output member must be unique'
            assert all(
                not Path(name).is_absolute() and '..' not in Path(name).parts for name in names
            ), 'Every output member must remain lexically contained in the project'
            assert 'reports/alias.html' in names, (
                'The link must retain its own name in the archive'
            )
            expected = (
                b'independent report bytes\n'
                if row['kind'] == 'internal'
                else b'independent external bytes\n'
            )
            assert archive.read('reports/alias.html') == expected, (
                'The linked file must retain its independently authored bytes'
            )


def test_discard_during_a_pending_recovery_write_cannot_resurrect_recovery(tmp_path):
    receipt, _ = browser_receipt(tmp_path)
    race = receipt['recoveryRace']
    assert not race['discardedBeforeWriteSettled'], (
        'Discard must order after an already-started recovery write for the same place'
    )
    assert not race['recoveryPresent'], (
        'A recovery write held across Discard must never resurrect the discarded recovery'
    )


@pytest.mark.parametrize(
    ('stage', 'category', 'error'),
    [
        (stage, category, error)
        for category in ('structures', 'experiments')
        for stage, errors in (
            (
                'remove',
                (
                    'NotAllowedError',
                    'NoModificationAllowedError',
                    'UnknownError',
                    'Error',
                    'NotFoundError',
                ),
            ),
            ('lookup', ('NotAllowedError', 'UnknownError')),
            ('list', ('NotAllowedError', 'UnknownError')),
        )
        for error in errors
    ],
)
def test_required_browser_cleanup_failures_retain_inventory_and_retry(
    tmp_path, stage, category, error
):
    receipt, expected = browser_receipt(tmp_path, cleanup=f'cleanup:{stage}:{category}:{error}')
    rows = receipt['cleanup']
    assert [(r['stage'], r['category'], r['error']) for r in rows] == [(stage, category, error)], (
        'Each cleanup fault reaches its independently selected real browser handle boundary'
    )
    for row in rows:
        missing = row['stage'] == 'remove' and row['error'] == 'NotFoundError'
        assert row['first']['ok'] is missing, (
            'Only a proven missing entry permits cleanup to acknowledge success: ' + str(row)
        )
        assert row['attemptsBeforeRetry'] > 0, (
            'Every cleanup fault reaches an actual browser handle operation'
        )
        if row['stage'] == 'remove' and not missing:
            assert row['knownAfter'] == row['knownBefore'], (
                'A failed cleanup retains the old known population for retry'
            )
            assert row['recordAfter'] is None or not row['recordAfter'].get('saved', False), (
                'A failed cleanup never records the candidate as durably saved'
            )
            assert row['attemptsAfterRetry'] > row['attemptsBeforeRetry'], (
                'Retry must attempt the previously refused removal again'
            )
        assert row['retry']['ok'], 'Removing the injected fault permits the next real write'
        assert row['members'] == sorted([*expected, 'keep.txt']), (
            'A successful retry removes obsolete entities and preserves unrelated content'
        )
        assert row['knownAfterRetry'] == sorted(expected), (
            'Only successful reconciliation replaces the known saved population'
        )
