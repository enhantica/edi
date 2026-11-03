"""Native startup after saving a project associated with a ChatGPT conversation."""

import json
import os
import shutil
import signal
from contextlib import suppress
from pathlib import Path

import pytest

from tests.system.py import test_e11_t5_dev_native_integration as native

ORIGINAL_TASK = 'Keep this ordinary saved project for the next startup.'
GENERIC_ACCOUNT_CHECK = '[account/read: ACCOUNT_IDENTITY_COMPARE]'
FALLBACK_SCOPE_ERROR = 'The approved account/project scope could not be prepared safely.'


def physical_identity(project):
    info = project.stat()
    return f'{info.st_dev}:{info.st_ino}'


def read_associations(settings):
    # Read the Qt-produced INI record without writing any of its inputs.
    row = next(
        line
        for line in settings.read_text(encoding='utf-8').splitlines()
        if line.startswith(r'Providers\chatgpt\sessions=')
    )
    payload = row.split('@ByteArray(', 1)[1].rsplit(')', 1)[0].replace(r'\"', '"')
    return row, json.loads(payload)


def project_association(settings, thread):
    _, index = read_associations(settings)
    return index['threads'][thread].get('project')


def capture_saved_conversation(folder):
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_UI_PROBE',
            native.ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe',
        )
    )
    home = folder / 'first-owner'
    home.mkdir()
    actor = native.MainActor(
        binary,
        home,
        {
            'turns': [[]],
            'session_fixture': {'threads': [], 'page_size': 12},
            'observe_context_continuity': True,
        },
        False,
    )
    try:
        project = native.copied_estimate_project(folder)
        assert actor.command('open', path=str(project))['reply']['opened'], (
            'Required: start with the real current saved project.'
        )
        actor.connect()
        actor.request(ORIGINAL_TASK)
        native._session_completed(actor, 1)
        thread = native._session_state(actor)['inputs'][0]['threadId']
        settings = Path(actor.command('inspect')['test_settings']['path'])
        original = project_association(settings, thread)
        assert original['identity'] == physical_identity(project), (
            'Required: the first connected conversation records the original project inode.'
        )
        native.qml(actor, 'Session.project.description="Ordinary edit before the second save."')
        # Save may publish twice. Holding the old directory prevents its inode from being reused.
        descriptor = os.open(project, os.O_RDONLY)
        try:
            assert actor.command('save')['reply']['saved'], (
                'Required: save the current project through the normal native Save procedure.'
            )
            identity = physical_identity(project)
        finally:
            os.close(descriptor)
        assert identity != original['identity'], (
            'Required: native Save actually replaces the associated directory inode.'
        )
        # Capture what Save itself persisted before teardown can write a fresh association.
        saved_settings = home / 'settings-at-save.ini'
        saved_settings.write_bytes(settings.read_bytes())
        workspace = Path(native._session_wire(actor, 'thread/start')[-1]['params']['cwd'])
        data_home = Path(actor.last['test_settings']['app_local_data'])
        workspace_parent = workspace.parent.parent.relative_to(data_home)
        manifest = native._capture_exact_cache_manifest(actor, 'after-second-save')
        sources = native._finish_genuine_restart_sources(actor, manifest)
        sources['settings_source'] = str(saved_settings)
        sources['workspace_parent'] = str(workspace_parent)
        return project, thread, {**original, 'identity': identity}, sources
    finally:
        actor.close()


def browser_report(actor):
    report = native.qml(actor, 'Session.assistant.workReportDocument()')
    return json.loads(report)['scope_coverage']['current_session_browser']


def startup_receipt(actor, thread):
    ui = actor.command('inspect')['ui']
    return {
        'connected': ui['connected'],
        'project': ui['project'].get('path'),
        'last_error': ui['last_error'],
        'sessions_error': native.qml(actor, 'Session.assistant.sessionsError'),
        'browser': browser_report(actor),
        'stderr': (actor.folder / 'host.stderr').read_text(encoding='utf-8', errors='replace'),
        'association': project_association(Path(actor.last['test_settings']['path']), thread),
        'new_threads': native._session_wire(actor, 'thread/start'),
    }


def observe_reopen(folder, sources, thread):
    with pytest.MonkeyPatch.context() as monkeypatch:
        actor = native._start_exact_original_fixture_restart(folder, monkeypatch, sources, [])
        try:
            actor.until(lambda row: row['ui']['connected'] or bool(row['ui']['last_error']))
            return startup_receipt(actor, thread)
        finally:
            actor.close()


def hold_account_reply(folder, name, account):
    fifo = folder / f'{name}.fifo'
    os.mkfifo(fifo, 0o600)
    return {
        'release_fifo': str(fifo),
        'ready': str(folder / f'{name}.ready.json'),
        'result': {
            'account': {'type': 'chatgpt', **account},
            'requiresOpenaiAuth': False,
        },
    }


def connect_offer(actor, *, acknowledge_open_failure):
    if acknowledge_open_failure:
        actor.until(lambda _row: native.qml(actor, 'refusal.opened'))
        delivery = actor.command('dialog_ok', name='refusal.dialog', role='ok')['reply']
        assert delivery['pressed_changes'] > 0, (
            'Required: acknowledge the ordinary Open refusal with its actual OK button.'
        )
        actor.until(lambda _row: not native.qml(actor, 'refusal.visible'))

    ready = actor.until(
        lambda row: (
            native._unique_input_control(row, 'home.start') is not None
            or native._unique_input_control(row, 'assistant.connection', fully=True) is not None
        )
    )
    if native._unique_input_control(ready, 'home.start') is not None:
        actor.command('click', name='home.start')
        actor.until(
            lambda row: (
                native._unique_input_control(row, 'assistant.connection', fully=True) is not None
            )
        )
    actor.command('click', name='assistant.connection')

    def disclosure():
        return native.qml(
            actor,
            '(function(){const dialog=testAppObjects.snapshot().find(x=>'
            'x&&typeof x.beginOffer==="function"&&x.opened&&x.assistant===Session.assistant);'
            'return dialog?{title:dialog.title,offer:!!dialog.approvalOwner,'
            'identity:dialog.disclosedContextIdentity,current:Session.assistant.contextConsentIdentity'
            '}:null;})()',
        )

    actor.until(
        lambda row: native._original_context_disclosure_present(row) and disclosure() is not None
    )
    return disclosure()


def arm_reopen_retirement(actor, successor):
    return native.qml(
        actor,
        '(function(){const vm=Session.assistant;const w=Qt.createQmlObject('
        '\'import QtQuick; Item {objectName:"startup.retirement";property int hits:0;'
        "property bool opened:false}',window.contentItem);"
        'const retire=function(){'
        'if(!w.hits&&/unavailable or changed|moved, replaced or changed/.test('
        'vm.lastError+vm.sessionsError)){'
        'w.hits++;vm.cancelSessionSelection();w.opened=Session.openProject('
        + json.dumps(successor.as_uri())
        + ');}};vm.lastErrorChanged.connect(retire);'
        'vm.sessionsErrorChanged.connect(retire);return true;})()',
    )


def stage_reopen_disruption(actor, sources, thread, scenario):
    if scenario == 'archived':
        settings = Path(actor.last['test_settings']['path'])
        old_row, index = read_associations(settings)
        index['threads'][thread]['archived'] = True
        escaped = json.dumps(index, separators=(',', ':')).replace('"', r'\"')
        prefix = old_row.split('@ByteArray(', 1)[0]
        suffix = old_row.rsplit(')', 1)[1]
        new_row = prefix + '@ByteArray(' + escaped + ')' + suffix
        text = settings.read_text(encoding='utf-8')
        settings.write_text(text.replace(old_row, new_row, 1), encoding='utf-8')
    if scenario == 'prepare':
        root = Path(actor.last['test_settings']['app_local_data'])
        parent = root / sources['workspace_parent']
        parent.parent.mkdir(parents=True, exist_ok=True)
        parent.write_text('Occupied fixture-owned workspace location.\n', encoding='utf-8')
        return parent
    return None


def observe_failure(folder, sources, thread, scenario):
    replies = {}

    def prepare_peer(peer_folder, config):
        account = dict(sources['actual_account'])
        if scenario == 'different-account':
            account['email'] = 'another-account@example.invalid'
        replies['preflight'] = hold_account_reply(peer_folder, 'preflight', account)
        replies['unapproved'] = hold_account_reply(peer_folder, 'unapproved', account)
        config['fixture_account_read_response'] = replies['preflight']
        if scenario == 'continuation':
            config['session_fixture']['resume_error'] = True

    with pytest.MonkeyPatch.context() as monkeypatch:
        actor = native._start_exact_original_fixture_restart(
            folder, monkeypatch, sources, [], prepare_peer=prepare_peer
        )
        try:
            preflight = replies['preflight']
            actor.until(lambda _row: Path(preflight['ready']).is_file())
            initial = native._session_wire(actor, 'account/read')[-1]
            native._session_configure(
                actor,
                fixture_account_read_response=None
                if scenario == 'continuation'
                else replies['unapproved'],
            )
            if scenario == 'retired':
                arm_reopen_retirement(actor, folder / 'successor-project')
            obstruction = stage_reopen_disruption(actor, sources, thread, scenario)
            if scenario == 'cancel':
                native.qml(actor, 'Session.assistant.cancelSessionSelection()')
                return startup_receipt(actor, thread)

            if scenario == 'transport':
                owner = actor.command('usage_transport_snapshot')['reply']
                assert owner['original_vm_child'], (
                    'Required: stop only the original process serving the held account preflight.'
                )
                os.kill(int(owner['peer_pid']), signal.SIGKILL)
            else:
                native._release_original_usage_reply(
                    actor, preflight, initial['id'], method='account/read'
                )
            # A missing settlement is part of the observed product result.
            with suppress(AssertionError):
                actor.until(
                    lambda row: (
                        row['ui']['connected']
                        or bool(row['ui']['last_error'])
                        or bool(native.qml(actor, 'Session.assistant.sessionsError'))
                        or Path(replies['unapproved']['ready']).is_file()
                    ),
                    seconds=6,
                )
            if obstruction is not None:
                obstruction.unlink()
            result = startup_receipt(actor, thread)
            result['preconsent_reads'] = native._session_wire(actor, 'account/read')
            result['preconsent_turns'] = native._session_wire(actor, 'turn/start')
            result['resumes'] = native._session_wire(actor, 'thread/resume')
            if scenario == 'retired':
                marker = '(' + native.control_expression('startup.retirement') + ')'
                result.update(
                    retired=native.qml(actor, marker + '.hits'),
                    successor_opened=native.qml(actor, marker + '.opened'),
                    expected_successor=str(folder / 'successor-project'),
                )
            # Capture any premature connection before trying the genuine user offer.
            if (
                len(result['preconsent_reads']) == (2 if scenario == 'continuation' else 1)
                and not result['connected']
                and FALLBACK_SCOPE_ERROR not in json.dumps(result)
                and GENERIC_ACCOUNT_CHECK not in json.dumps(result)
            ):
                try:
                    result['offer'] = connect_offer(
                        actor, acknowledge_open_failure=scenario in {'malformed', 'prepare'}
                    )
                except AssertionError as error:
                    result['offer_error'] = str(error)
                result['offer_reads'] = native._session_wire(actor, 'account/read')
                result['offer_threads'] = native._session_wire(actor, 'thread/start')
                result['offer_turns'] = native._session_wire(actor, 'turn/start')
            return result
        finally:
            actor.close()


@pytest.fixture(scope='module')
def startup_observations(tmp_path_factory):
    folder = tmp_path_factory.mktemp('owner-startup')
    project, thread, expected, sources = capture_saved_conversation(folder)
    receipts = {'success': observe_reopen(folder, sources, thread)}
    (folder / 'original-fixture-restart').rename(folder / 'successful-restart')
    project_file = project / 'project.edi'
    project_bytes = project_file.read_bytes()
    for scenario in (
        'different-account',
        'cancel',
        'archived',
        'transport',
        'prepare',
        'continuation',
        'malformed',
        'changed-project',
        'retired',
    ):
        if scenario == 'malformed':
            # Change document bytes without replacing the authenticated directory.
            project_file.write_text('data_invalid\nloop_\n', encoding='utf-8')
            assert physical_identity(project) == expected['identity'], (
                'Required: malformed project still passes the physical identity check.'
            )
        if scenario == 'changed-project':
            displaced = project.rename(folder / 'displaced-original-project')
            shutil.copytree(displaced, project)
            shutil.copytree(displaced, folder / 'successor-project')
            assert physical_identity(project) != expected['identity'], (
                'Required: a complete replacement at the same path has a different identity.'
            )
        receipts[scenario] = observe_failure(folder, sources, thread, scenario)
        if scenario == 'malformed':
            project_file.write_bytes(project_bytes)
        (folder / 'original-fixture-restart').rename(folder / scenario)
        (folder / 'startup-receipts.json').write_text(
            json.dumps(receipts, indent=2), encoding='utf-8'
        )
    return thread, expected, receipts


def assert_no_generic_account_check(receipt):
    assert GENERIC_ACCOUNT_CHECK not in json.dumps(receipt), (
        'Required: a startup project reopen never surfaces the generic account-check message.'
    )


def test_startup_reopens_the_associated_project_after_ordinary_save(startup_observations):
    thread, expected, receipts = startup_observations
    result = receipts['success']
    assert_no_generic_account_check(result)
    assert result['association'] == expected, (
        'Required: ordinary Save persists the new physical identity for the original thread.'
    )
    assert (
        result['connected']
        and result['project'] == expected['location']
        and result['browser']['startup_transition'].get('accepted_target') == thread
        and result['browser']['runtime_thread'] == thread
    ), 'Required: startup connects and reopens the same project and original conversation.'


def assert_connect_requires_new_consent(receipt, *, reads=1):
    assert_no_generic_account_check(receipt)
    assert FALLBACK_SCOPE_ERROR not in json.dumps(receipt), (
        'Required: failed startup never attempts to prepare unapproved account or project scope.'
    )
    assert (
        not receipt['connected']
        and not receipt['new_threads']
        and not receipt['preconsent_turns']
        and len(receipt['preconsent_reads']) == reads
    ), 'Required: only the correlated reopen reads precede explicit new connection consent.'
    offer = receipt.get('offer') or {}
    assert (
        offer.get('title') == 'Connect ChatGPT'
        and offer.get('offer')
        and offer.get('identity')
        and offer['identity'] == offer.get('current')
        and receipt['offer_reads'] == receipt['preconsent_reads']
        and not receipt['offer_threads']
        and not receipt['offer_turns']
    ), 'Required: the genuine Connect ChatGPT dialog offers exact scope before any new thread.'


def test_unavailable_startup_project_reports_reopen_cause_and_connects_a_new_thread(
    startup_observations,
):
    _, expected, receipts = startup_observations
    result = receipts['changed-project']
    assert result['association'] == expected, (
        'Required: the original thread association and its saved identity are preserved.'
    )
    assert 'moved, replaced or changed' in result['sessions_error'] and not result['project'], (
        'Required: report the changed original project without opening its replacement.'
    )
    assert_connect_requires_new_consent(result)


def test_different_account_reopen_does_not_authorize_fresh_context(startup_observations):
    _, expected, receipts = startup_observations
    result = receipts['different-account']
    assert result['association'] == expected and not result['project'], (
        'Required: an account mismatch preserves the original association and does not open it.'
    )
    assert 'account' in result['sessions_error'].lower(), (
        'Required: startup gives the different account as the plain cause.'
    )
    assert_connect_requires_new_consent(result)


def test_reopen_retired_during_failure_publication_cannot_authorize_context(startup_observations):
    _, _, receipts = startup_observations
    result = receipts['retired']
    assert (
        result['retired'] == 1
        and result['successor_opened']
        and result['project'] == result['expected_successor']
    ), 'Required: actual project replacement retires the reopen before queued work can run.'
    assert_connect_requires_new_consent(result)


@pytest.mark.parametrize(
    ('scenario', 'words'),
    [
        ('malformed', ('project',)),
        ('transport', ('process', 'transport')),
        ('archived', ('archiv', 'unavailable', 'no longer')),
        ('prepare', ('prepar', 'workspace', 'directory')),
        ('continuation', ('bootstrap', 'resume', 'reconnect')),
    ],
)
def test_automatic_reopen_handoff_settles_with_its_own_cause(
    startup_observations, scenario, words
):
    thread, expected, receipts = startup_observations
    result = receipts[scenario]
    detail = result['sessions_error'].lower()
    assert any(word in detail for word in words), (
        'Required: the failed ordinary Open or transport supplies its concrete cause.'
    )
    assert 'cancelled' not in detail and result['association'] == expected, (
        'Required: automatic failure keeps the record and is distinct from a cancellation.'
    )
    assert not result['browser']['loading'] and not result['browser']['startup_target'], (
        'Required: failed automatic selection releases its original startup operation.'
    )
    reads = 1
    if scenario == 'continuation':
        assert [row['params']['threadId'] for row in result['resumes']] == [thread], (
            'Required: the rejected continuation was the actual original thread, attempted once.'
        )
        reads = 2
    assert_connect_requires_new_consent(result, reads=reads)


def test_intentional_startup_cancel_does_not_report_failed_open(startup_observations):
    _, expected, receipts = startup_observations
    result = receipts['cancel']
    assert (
        'cancel' in result['sessions_error'].lower()
        and not result['browser']['startup_transition'].get('reopen_failure')
        and not result['connected']
        and not result['new_threads']
        and result['association'] == expected
    ), 'Required: intentional cancellation settles without a reopen failure or replacement thread.'
