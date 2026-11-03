"""Native startup after saving a project associated with a ChatGPT conversation."""

import json
import os
from pathlib import Path

import pytest

from tests.system.py import test_e11_t5_dev_native_integration as native

ORIGINAL_TASK = 'Keep this ordinary saved project for the next startup.'
GENERIC_ACCOUNT_CHECK = '[account/read: ACCOUNT_IDENTITY_COMPARE]'
FALLBACK_SCOPE_ERROR = 'The approved account/project scope could not be prepared safely.'


def physical_identity(project):
    info = project.stat()
    return f'{info.st_dev}:{info.st_ino}'


def project_association(settings, thread):
    # Read the Qt-produced INI record without writing any of its inputs.
    row = next(
        line
        for line in settings.read_text(encoding='utf-8').splitlines()
        if line.startswith(r'Providers\chatgpt\sessions=')
    )
    payload = row.split('@ByteArray(', 1)[1].rsplit(')', 1)[0].replace(r'\"', '"')
    return json.loads(payload)['threads'][thread].get('project')


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
        manifest = native._capture_exact_cache_manifest(actor, 'after-second-save')
        sources = native._finish_genuine_restart_sources(actor, manifest)
        sources['settings_source'] = str(saved_settings)
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


def observe_unavailable(folder, sources, thread):
    replies = {}

    def prepare_peer(peer_folder, config):
        for stage in ('preflight', 'fallback'):
            replies[stage] = hold_account_reply(peer_folder, stage, sources['actual_account'])
        config['fixture_account_read_response'] = replies['preflight']

    with pytest.MonkeyPatch.context() as monkeypatch:
        actor = native._start_exact_original_fixture_restart(
            folder, monkeypatch, sources, [], prepare_peer=prepare_peer
        )
        try:
            preflight = replies['preflight']
            actor.until(lambda _row: Path(preflight['ready']).is_file())
            initial = native._session_wire(actor, 'account/read')[-1]
            native._session_configure(actor, fixture_account_read_response=replies['fallback'])
            native._release_original_usage_reply(
                actor, preflight, initial['id'], method='account/read'
            )
            fallback = replies['fallback']
            ready = Path(fallback['ready'])
            actor.until(
                lambda row: (
                    ready.is_file()
                    or row['ui']['connected']
                    or GENERIC_ACCOUNT_CHECK in row['ui']['last_error']
                    or row['ui']['last_error'] == FALLBACK_SCOPE_ERROR
                )
            )
            failure = startup_receipt(actor, thread)
            if not ready.is_file():
                return failure, failure
            resumed = native._session_wire(actor, 'account/read')[-1]
            native._release_original_usage_reply(
                actor, fallback, resumed['id'], method='account/read'
            )
            actor.until(lambda row: row['ui']['connected'])
            return failure, startup_receipt(actor, thread)
        finally:
            actor.close()


@pytest.fixture(scope='module')
def startup_observations(tmp_path_factory):
    folder = tmp_path_factory.mktemp('owner-startup')
    project, thread, expected, sources = capture_saved_conversation(folder)
    success = observe_reopen(folder, sources, thread)
    displaced = project.rename(folder / 'displaced-original-project')
    assert not project.exists() and physical_identity(displaced) == expected['identity'], (
        'Required: displace the original project without changing the saved record.'
    )
    (folder / 'original-fixture-restart').rename(folder / 'successful-restart')
    failure, fallback = observe_unavailable(folder, sources, thread)
    receipts = {'success': success, 'failure': failure, 'fallback': fallback}
    (folder / 'startup-receipts.json').write_text(json.dumps(receipts, indent=2), encoding='utf-8')
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


def test_unavailable_startup_project_reports_reopen_cause_and_connects_a_new_thread(
    startup_observations,
):
    thread, expected, receipts = startup_observations
    failure, fallback = receipts['failure'], receipts['fallback']
    assert_no_generic_account_check(failure)
    assert_no_generic_account_check(fallback)
    account_check = failure['browser']['account_check']
    cause = account_check.get('reopen_failure', '')
    assert (
        account_check['stage'] == 'SAVED_PROJECT_REOPEN' and 'unavailable or changed' in cause
    ), 'Required: startup reports the saved-project reopen stage and its actual cause.'
    assert cause in failure['sessions_error'], (
        'Required: the concrete reopen cause reaches the user-facing Sessions error.'
    )
    assert fallback['association'] == expected, (
        'Required: fallback preserves the original thread association and its saved identity.'
    )
    assert (
        fallback['connected']
        and not fallback['project']
        and fallback['browser']['runtime_thread'] not in {'', thread}
        and fallback['new_threads']
    ), 'Required: fallback connects a distinct conversation without substituting a project.'
