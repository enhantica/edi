"""Durable-save and replacement-intent gates over the production Session callbacks."""

import base64
import copy
import hashlib
import io
import json
import math
import os
import re
import shutil
import struct
import subprocess
import zipfile
from fractions import Fraction
from pathlib import Path

import edi
import pytest

from tests.conftest import crysta_reference_prefix
from tests.fixtures.project_save.boundaries import (
    agreement,
    bank_angle,
    mixed_project,
    ordinary_position,
    special_position,
)
from tests.fixtures.project_save.reference import six_digits
from tests.fixtures.scan_app.build_probe import fingerprint
from tests.fixtures.scan_screen.harness import pinned_browser, prepare_browser_toolchain
from tests.integration.py.test_anisotropic_adps import loop_rows

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
    for name, expected in receipt['fixture'].items():
        path = ROOT / 'tests/fixtures/project_transactions' / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, (
            'The observation binary must match the exact fixture sources being exercised'
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
    for key in ('original_app_library', 'original_core_library'):
        original = receipt[key]
        assert (
            hashlib.sha256(Path(original['path']).read_bytes()).hexdigest() == original['sha256']
        ), 'Every wrapped archive retains the identity of its original compiled production library'
    original = receipt['original_app_library']
    assert hashlib.sha256(Path(original['path']).read_bytes()).hexdigest() == original['sha256'], (
        'The observation boundary must retain its original production app archive identity'
    )
    return receipt


def observe(observer, group, tmp_path, source=None):
    result = subprocess.run(
        [
            observer['binary'],
            str(source or ROOT / 'tests/fixtures/loop_parameter_ids/line-segment'),
            group,
        ],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    (tmp_path / (group.replace('/', '_') + '.log')).write_text(result.stdout + result.stderr)
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


@pytest.mark.parametrize('kind', ['folder', 'zip'])
@pytest.mark.parametrize('second', ['save', 'move-folder', 'move-zip'])
@pytest.mark.parametrize('first_ok', [False, True])
@pytest.mark.parametrize('second_first', [False, True])
@pytest.mark.parametrize('second_ok', [False, True])
def test_pending_moving_save_refuses_every_competing_save_intent(
    observer, tmp_path, kind, second, first_ok, second_first, second_ok
):
    group = (
        f'save-conflict/{kind}/{second}/{int(first_ok)}/'
        f'{int(second_first)}/{int(second_ok)}/0/none'
    )
    row = observe(observer, group, tmp_path)[0]
    assert row['secondJobs'] == 0, (
        'A held moving save refuses both another destination picker and an ordinary write'
    )
    if second == 'save':
        assert not row['secondReturned'], 'A competing ordinary Save must explicitly refuse'
    assert row['afterSecond'] == row['pending'], (
        'A refused overlapping save changes no live scientific state or working place'
    )
    assert row['nextReturned'], 'Save authority is released after either first-write outcome'
    assert row['nextReached'], 'The next Save reaches a real write after settlement'
    assert not row['final']['modified'], 'The successfully retried next Save commits its revision'


@pytest.mark.parametrize('kind', ['folder', 'zip'])
@pytest.mark.parametrize('ok', [False, True])
def test_edit_during_moving_save_keeps_new_values_and_recovery(observer, tmp_path, kind, ok):
    row = observe(observer, f'save-conflict/{kind}/none/{int(ok)}/0/0/1/none', tmp_path)[0]
    assert row['edited']['modified'], 'The held write overlaps a genuinely newer unsaved edit'
    assert row['completed']['modified'], 'Older completion must retain the newer unsaved revision'
    assert row['completed']['parameters'] == row['edited']['parameters'], (
        'An older write cannot overwrite the new high-precision coordinate or uncertainty'
    )
    assert row['completed']['name'] == 'edited-during-moving-save', (
        'An older write cannot overwrite metadata edited while publication was held'
    )
    assert not row['drops'], 'The older completion cannot remove recovery for a newer revision'
    assert row['completed']['location'] == row['before']['location'], (
        'A local edit during publication keeps the original durable location'
    )
    assert row['completed']['path'] == row['before']['path'], (
        'A local edit during publication keeps the original working folder'
    )
    if ok:
        assert any('unsaved' in message.casefold() for message in row['messages']), (
            'A place written before a local refusal reports that the project stays unsaved'
        )
    assert row['nextReturned'], 'An edited held move releases save authority when it settles'
    assert row['nextReached'], 'The newer revision can actually be saved after settlement'
    assert not row['final']['modified'], 'The next durable success commits the newer revision'


@pytest.mark.parametrize('kind', ['folder', 'zip'])
@pytest.mark.parametrize('ok', [False, True])
@pytest.mark.parametrize('replacement', ['desktop', 'example', 'new'])
def test_late_moving_save_answer_cannot_change_a_replacement_project(
    observer, tmp_path, kind, ok, replacement
):
    row = observe(observer, f'save-conflict/{kind}/none/{int(ok)}/0/0/0/{replacement}', tmp_path)[
        0
    ]
    assert row['completed'] == row['replacementBefore'], (
        'An obsolete save answer changes no value, metadata, array, location or modified flag '
        'of a replacement project'
    )


@pytest.mark.parametrize('dirty', [False, True], ids=['clean', 'dirty'])
@pytest.mark.parametrize(
    ('route', 'kind'),
    [
        ('zip-as-missing', 'folder'),
        ('zip-as-blocked', 'folder'),
        ('zip-save', 'zip'),
        ('web-save', 'browser'),
        ('web-save', 'folder'),
        ('web-save', 'zip'),
        ('web-move', 'folder'),
        ('web-move', 'zip'),
    ],
)
def test_failed_publication_restores_the_complete_high_precision_live_snapshot(
    observer, tmp_path, route, kind, dirty
):
    group = f'rollback/{route}/{kind}/' + ('dirty' if dirty else 'clean')
    row = observe(observer, group, tmp_path)[0]
    assert row['before']['modified'] is dirty, (
        'Rollback covers both a genuinely clean origin and an already unsaved edit'
    )
    assert any(
        p['value'] == 1.23456789 and not p['free'] and not p['uncertainty']
        for p in row['before']['parameters']
    ), (
        'The pre-publication snapshot includes a no-su fixed value '
        'actually moved by six-digit rounding'
    )
    assert any(bank.get('calculated') for bank in row['before']['scientific']['banks']), (
        'Rollback starts with actual calculated arrays, not an uncalculated placeholder'
    )
    assert row['refused'] == row['before'], (
        'Failed publication restores exact live values, uncertainties, metadata, arrays, '
        'shown arrays, location and modified flag'
    )
    assert row['retry'], 'Removing the independent publication fault permits a real retry'
    assert not row['afterRetry']['modified'], 'The successful retry commits its durable snapshot'
    assert any(p['value'] == 1.23457 for p in row['afterRetry']['parameters']), (
        'Successful retry adopts the independently rounded six-digit witness'
    )


@pytest.mark.parametrize('kind', ['folder', 'zip'])
@pytest.mark.parametrize(
    'intents',
    [(first, second) for first in ('save', 'move', 'copy') for second in ('save', 'move', 'copy')],
)
@pytest.mark.parametrize('first_ok', [False, True])
@pytest.mark.parametrize('second_first', [False, True])
@pytest.mark.parametrize('second_ok', [False, True])
def test_all_save_intents_share_authority_even_when_the_picker_aliases_the_current_place(
    observer, tmp_path, kind, intents, first_ok, second_first, second_ok
):
    first, second = intents
    group = (
        f'save-alias-{first}/{kind}/{second}/{int(first_ok)}/'
        f'{int(second_first)}/{int(second_ok)}/0/none'
    )
    row = observe(observer, group, tmp_path)[0]
    assert row['secondJobs'] == 0, (
        'Save, moving Save as and Save a copy share one authority even with a new key '
        'for the current physical folder or ZIP'
    )
    assert row['afterSecond'] == row['edited'], (
        'Every refused competing intent leaves the newer live revision completely unchanged'
    )
    if second == 'save':
        assert not row['secondReturned'], 'A refused competing Save returns failure'
    assert row['thirdJobs'] == 0, (
        'Refusing an overlap retains the first write authority against another intent or format'
    )
    if row['third'] == 'save':
        assert not row['thirdReturned'], 'A refused third ordinary Save returns failure'
    assert row['afterThird'] == row['edited'], (
        'A second refusal changes no live values, arrays, metadata or working place'
    )
    if first_ok and first != 'copy':
        assert not row['completed']['modified'], (
            'A successful unchanged owned Save or moving Save as commits the first revision'
        )
    if not row['completed']['modified']:
        assert row['firstDurableParameters'] == row['completed']['parameters'], (
            'After settlement, a clean live project matches its actual durable place'
        )
    if not first_ok:
        assert row['completed'] == row['pending'], (
            'A refused first write preserves the exact live revision and working place'
        )
    assert row['nextReturned'], 'Either first-write outcome releases authority for another Save'
    assert row['nextReached'], 'The next Save reaches the actual write boundary'
    assert not row['final']['modified'], 'A completed next Save is clean'
    assert row['durableParameters'], 'The acknowledged place contains a real reopenable model'
    assert row['durableParameters'] == row['final']['parameters'], (
        'A clean project agrees with the last acknowledged immutable payload in its durable place'
    )


@pytest.mark.parametrize('kind', ['folder', 'zip'])
@pytest.mark.parametrize(
    'intents',
    [(first, second) for first in ('save', 'move', 'copy') for second in ('save', 'move', 'copy')],
)
@pytest.mark.parametrize('first_ok', [False, True])
@pytest.mark.parametrize('second_first', [False, True])
@pytest.mark.parametrize('second_ok', [False, True])
def test_write_authority_survives_replacement_even_with_distinct_keys_for_one_physical_place(
    observer, tmp_path, kind, intents, first_ok, second_first, second_ok
):
    first, second = intents
    group = (
        f'save-replaced-{first}/{kind}/{second}/{int(first_ok)}/'
        f'{int(second_first)}/{int(second_ok)}/0/Recent'
    )
    check_replacement_authority(observe(observer, group, tmp_path)[0])


@pytest.mark.parametrize('replacement', ['Open', 'recovery', 'desktop', 'example', 'new'])
@pytest.mark.parametrize('first', ['save', 'move', 'copy'])
def test_every_project_replacement_route_retains_the_owned_write_token(
    observer, tmp_path, replacement, first
):
    second = {'save': 'copy', 'move': 'save', 'copy': 'move'}[first]
    group = f'save-replaced-{first}/folder/{second}/1/1/1/0/{replacement}'
    check_replacement_authority(observe(observer, group, tmp_path)[0])


def check_replacement_authority(row):
    assert row['secondJobs'] == 0, (
        'Replacing a project preserves the session-owned write token against Save, '
        'moving Save as and copy, even when a new key names the same physical place'
    )
    if row['second'] == 'save':
        assert not row['secondReturned'], (
            'A held write token refuses ordinary Save after replacement'
        )
    assert row['afterSecond'] == row['replacementBefore'], (
        'A refused write never changes the replacement project or its working place'
    )
    assert row['thirdJobs'] == 0, (
        'Refusing a competing write never releases the old token for another intent or format'
    )
    assert row['afterThird'] == row['replacementBefore'], (
        'A second refusal preserves all replacement values, arrays, metadata and modified state'
    )
    assert row['completed'] == row['replacementBefore'], (
        'Only the owned completion releases the old token; its late answer never adopts, '
        'moves, cleans or otherwise changes the replacement project'
    )
    assert row['nextReturned'], 'The owned completion releases the token after either outcome'
    assert row['nextReached'], 'A replacement can write after the earlier owned write has settled'
    assert not row['final']['modified'], (
        'A later acknowledged Save commits the replacement revision'
    )
    assert row['durableParameters'] == row['final']['parameters'], (
        'Ordered writes leave a clean replacement equal to the actual last durable payload'
    )


@pytest.mark.parametrize(
    'route',
    [
        'zip-save',
        'zip-as',
        'zip-copy',
        'folder-as',
        'folder-copy',
        'folder-copy-current',
        'zip-copy-current',
        'web-save-browser',
        'web-save-folder',
        'web-save-zip',
        'web-move-folder',
        'web-move-zip',
        'web-copy-folder',
        'web-copy-zip',
    ],
)
def test_a_running_fit_refuses_every_save_before_staging_or_publication(observer, tmp_path, route):
    row = observe(observer, f'fit-save/{route}/already', tmp_path)[0]
    assert row['runningReached'], 'The refusal is observed while a real fit is running'
    assert not row['returned'], 'A running fit refuses the requested save'
    assert row['after'] == row['before'], (
        'A refused save during fitting changes no values, arrays, metadata or working place'
    )
    assert row['jobs'] == 0, 'A running fit starts no picker, browser write or recovery write'
    assert row['publications'] == 0, 'A running fit publishes no archive'
    assert row['stages'] == 0, 'A running fit creates no staging folder'
    assert row['folderUnchanged'], 'Refusal leaves all existing working-folder bytes unchanged'
    assert row['archiveUnchanged'], 'Refusal leaves the existing ZIP bytes unchanged'
    assert not row['destinationCreated'], 'Refusal publishes no new Save as destination'


@pytest.mark.parametrize(
    'route',
    [
        'web-save-browser',
        'web-save-folder',
        'web-save-zip',
        'web-move-folder',
        'web-move-zip',
        'web-copy-folder',
        'web-copy-zip',
    ],
)
def test_a_fit_started_during_a_browser_write_refuses_local_adoption_and_movement(
    observer, tmp_path, route
):
    row = observe(observer, f'fit-save/{route}/during', tmp_path)[0]
    assert row['runningReached'], 'A real fit starts before the held write acknowledges success'
    assert row['after'] == row['before'], (
        'A write completed during a fit neither adopts values nor changes the live working place'
    )
    assert row['after']['modified'], 'A published place cannot make a fitting live project clean'
    assert row['after']['path'] == row['heldBefore']['path'], (
        'The live project retains its original working folder after local adoption is refused'
    )
    assert not row['drops'], 'Refused local adoption retains recovery'
    assert any('unsaved' in message.casefold() for message in row['messages']), (
        'A write completed during a fit reports that the live project stays unsaved'
    )


@pytest.mark.parametrize('route', ['zip-save', 'zip-as'])
def test_successful_desktop_zip_publication_uses_exactly_one_staged_snapshot(
    observer, tmp_path, route
):
    row = observe(observer, f'fit-save/{route}/success', tmp_path)[0]
    assert row['returned'], 'The independent writable ZIP destination accepts Save'
    assert row['publications'] == 1, 'A desktop ZIP save publishes exactly one archive'
    assert len(row['sources']) == 1, 'The one archive delegates to the actual production writer'
    assert row['after']['path'] == row['sources'][0], (
        'The open project works in the same staged snapshot used for the archive'
    )
    assert row['after']['parameters'] == row['archivedParameters'], (
        'The adopted live values, uncertainties and free flags equal an independent archive reopen'
    )
    assert not row['after']['modified'], 'Successful publication commits the adopted snapshot'


@pytest.mark.parametrize('dirty', [False, True], ids=['clean', 'dirty'])
@pytest.mark.parametrize(
    ('route', 'kind'),
    [
        ('zip-save', 'zip'),
        ('zip-as', 'folder'),
        ('web-save', 'browser'),
        ('web-save', 'folder'),
        ('web-save', 'zip'),
        ('web-move', 'folder'),
        ('web-move', 'zip'),
    ],
)
def test_publication_is_followed_only_by_an_infallible_prepared_live_commit(
    observer, tmp_path, route, kind, dirty
):
    group = f'after-publication/{route}/{kind}/' + ('dirty' if dirty else 'clean')
    row = observe(observer, group, tmp_path)[0]
    assert row['before']['modified'] is dirty, (
        'Post-publication observations start with both clean and dirty exact-value projects'
    )
    assert row['published'], (
        'The injected refusal becomes active only after actual durable success'
    )
    assert not row['exception'], 'No fallible post-publication operation escapes the save caller'
    assert not row['calls'], (
        'All fallible load, write and file-based adoption work finishes before durable publication'
    )
    assert row['returned'], (
        'An acknowledged unchanged save commits its fully prepared live snapshot'
    )
    assert row['ownFolderExists'], 'The live project never points into a removed staging folder'
    assert row['ownFolderReadable'], 'The live working folder remains a valid reopenable project'
    assert not row['after']['modified'], 'The successfully published unchanged snapshot is clean'
    assert row['after']['parameters'] == row['publishedParameters'], (
        'The prepared live values and uncertainties equal the actual durable published snapshot'
    )


@pytest.mark.parametrize('kind', ['line-segment', 'polynomial', 'chebyshev'])
@pytest.mark.parametrize('web', [False, True], ids=['desktop', 'web'])
@pytest.mark.parametrize('empty', [False, True], ids=['points', 'empty'])
@pytest.mark.parametrize('provenance', ['stale', 'absent'])
def test_app_save_to_preserves_every_due_background_cell_and_publishes_only_current_arrays(
    observer, tmp_path, web, empty, provenance, kind
):

    source = mixed_project(tmp_path / 'input', empty=empty, provenance=provenance, kind=kind)
    row = observe(observer, 'mixed-web' if web else 'mixed-desktop', tmp_path, source)[0]
    assert not row['error'], 'The independently valid mixed-bank project accepts Save to'
    expected = copy.deepcopy(row['before'])

    def rounded_bits(value):
        number = struct.unpack('>d', int(value, 16).to_bytes(8, 'big'))[0]
        return format(struct.unpack('>Q', struct.pack('>d', six_digits(number)))[0], 'x')

    for point in expected['points']:
        point['value'] = rounded_bits(point['value'])
    for term in expected['terms']:
        term['value'] = rounded_bits(term['value'])
    expected.pop('pointsDigest')
    for stage in ('immediate', 'after', 'file'):
        actual = {key: value for key, value in row[stage].items() if key != 'pointsDigest'}
        assert actual == expected, (
            'Save rounds and adopts due ordinary values without estimating; row identities, '
            'free flags, settings, mode, absent constants and raw input provenance are retained'
        )
    assert row['livePointsCoherent'], 'The live due digest matches its rounded adopted rows'
    assert row['filePointsCoherent'], 'The reopened due digest matches its written rounded rows'
    assert row['after']['pointsDigest'] == row['file']['pointsDigest'], (
        'The file and adopted live due background share the same reconciled points digest'
    )
    for column in ('calculated', 'background'):
        values = row['shownAfter']['due'][column]
        absent = all(
            value is None
            or not math.isfinite(struct.unpack('>d', int(value, 16).to_bytes(8, 'big'))[0])
            for value in values
        )
        assert absent or values == row['shownBefore']['due'][column], (
            'The app clears or retains stale due arrays and never publishes a new due calculation'
        )
    assert row['shownBefore']['current']['calculated'], (
        'The app-array observation reaches a populated actual current-bank PatternModel'
    )
    assert row['inputs'] == ([1.23457, 1.23457] if kind == 'line-segment' else [1.23457]), (
        'The current bank adopts independently rounded six-digit background inputs'
    )
    assert row['liveCurrent'] == [1.23457] * 4, (
        'Zero scale and rounded constant background independently fix the live pattern'
    )
    assert row['fileCurrent'] == row['liveCurrent'], 'The file and live current pattern agree'
    assert row['freshCurrent'] == row['liveCurrent'], (
        'A fresh reopen and calculation agrees with the saved current pattern'
    )
    expected_bits = format(struct.unpack('>Q', struct.pack('>d', 1.23457))[0], 'x')
    assert row['shownAfter']['current']['calculated'] == [expected_bits] * 4, (
        'The actual app PatternModel publishes the rounded current-bank calculated columns'
    )
    records = loop_rows(row['analysis'], '_fit_result_bank')
    current = next((r for r in records if r['_fit_result_bank.experiment_id'] == 'current'), None)
    assert current is not None, 'The current bank retains its real persisted agreement record'
    live = next(bank for bank in row['scientificAfter']['banks'] if bank['name'] == 'current')
    stored = next(bank for bank in row['fileScience']['banks'] if bank['name'] == 'current')
    fresh = next(bank for bank in row['freshScience']['banks'] if bank['name'] == 'current')
    for name in ('rp', 'rwp', 'chi'):
        assert live[name] == stored[name], (
            'Live current-bank agreement factors equal the written ones'
        )
        fresh_value = struct.unpack('>d', int(fresh[name], 16).to_bytes(8, 'big'))[0]
        stored_value = struct.unpack('>d', int(stored[name], 16).to_bytes(8, 'big'))[0]
        assert float(format(fresh_value, '.6g')) == stored_value, (
            'Fresh current-bank factors agree at the independent six-digit saved precision'
        )
    for key, value in agreement(1.23457).items():
        assert float(current['_fit_result_bank.' + key]) == pytest.approx(
            float(format(value, '.6g')), rel=1e-12
        ), 'Saved current-bank factors match independent weighted residuals of the rounded pattern'


@pytest.mark.parametrize('kind', ['special', 'ordinary', 'bank-normal', 'bank-exact'])
@pytest.mark.parametrize('surface', ['field', 'Text'])
def test_actual_app_fields_and_text_decode_to_exact_save_policy_values(
    observer, tmp_path, kind, surface
):

    if kind == 'special':
        source = special_position(tmp_path / 'input')
        names = ('fract_x', 'fract_y', 'fract_z')
        expected = [1 / 3, 2 / 3, 1 / 4]
    elif kind == 'ordinary':
        source = ordinary_position(tmp_path / 'input')
        names, expected = ('fract_x',), [0.123457]
    else:
        source = bank_angle(tmp_path / 'input', exact=kind == 'bank-exact')
        names = ('setup_twotheta_bank',)
        expected = [94.90931761529106 if kind == 'bank-exact' else 94.9093]
    row = observe(observer, 'exact-fields', tmp_path, source)[0]
    if surface == 'field':
        actual = []
        for name in names:
            fields = [
                item
                for item in row['fields']
                if item['name'] == name
                and (item['block'] == 'bank' if kind.startswith('bank') else item['row'] == 'A')
            ]
            assert len(fields) == 1, (
                'The native QML field binds exactly one independently named live item'
            )
            item = fields[0]
            assert item['text'], 'The actual ParameterField displays a nonempty native text value'
            assert not item['fileSu'], 'Fixed and symmetry-fixed fields invent no uncertainty'
            actual.append(float(Fraction(item['text'])))
            assert float(Fraction(item['editText'])).hex() == expected[len(actual) - 1].hex(), (
                'Focusing a field retains the exact same saved-policy value'
            )
    elif kind.startswith('bank'):
        match = re.search(r'(?m)^_instrument.setup_twotheta_bank\s+(\S+)', row['experimentText'])
        assert match is not None, 'The real Experiment Text tab exposes its bank-angle file token'
        actual = [float(match[1])]
    else:
        atoms = loop_rows(row['structureText'], '_atom_site')
        atom = next((a for a in atoms if a['_atom_site.id'] == 'A'), None)
        assert atom is not None, 'The real Structure Text tab retains the authored atom A'
        actual = [float(atom['_atom_site.' + name]) for name in names]
    assert [value.hex() for value in actual] == [value.hex() for value in expected], (
        'The actual app surface decodes to canonical thirds, six-digit ordinary values '
        'or the full-precision bank angle under the all-exact fallback'
    )
