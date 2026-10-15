"""PRIVATE independent preference cases; no collection/build/runtime yet.

Owner94ffecaa5; accepted shipped capability map, original offline catalog choices.
No preferences key/schema inferred from private production changes.
"""
import hashlib
import json
import os
import stat
import subprocess
from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.system.app import test_e11_t5_vm_retention as prior

signer = prior.signer
SOL = 'gpt-6.1-sol'
LUNA = 'gpt-6-luna'


def catalog(*ids):
    return {'models': [
        {'slug': name, 'display_name': 'Original offline ' + name, 'visibility': 'list'}
        for name in ids
    ]}


@pytest.fixture
def launch(tmp_path, monkeypatch):
    binary = Path(os.environ['EDI_ASSISTANT_SETTINGS_VM_PROBE'])
    assert binary.is_file(), 'I13/preferences: real configured-engine Session consumer must build first'
    profile = tmp_path / 'owned-profile'
    profile.mkdir()
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    monkeypatch.setenv('QT_QUICK_BACKEND', 'software')
    monkeypatch.setenv('EDI_TEST_SETTINGS_ROOT', str(profile))

    @contextmanager
    def start(offered=None):
        actor = prior.Component(binary)
        actor.catalog = catalog(SOL, LUNA) if offered is None else offered
        actor.command('inspect')
        store = Path(actor.last['settings_file'])
        assert store.is_relative_to(profile), 'I13/preferences: actual canonical store belongs to this owned profile'
        try:
            yield actor
        finally:
            actor.close()
            assert actor.process.returncode == 0, 'I13/preferences: actual process exits before the same-store restart'

    return start


def connected(actor, signer):
    actor.authenticate(signer)
    assert actor.ready(), 'I12/I13/preferences: current real signed offline catalog establishes readiness'
    offered = [row['id'] for row in actor.last['vm']['models'] if row['available']]
    assert actor.last['vm']['selected_model'] in offered, 'I13/preferences: visible selected model belongs to actual available catalog'
    assert not prior.responses(actor), 'I13/preferences: authentication and preference restore cause no inference'


def choose(actor, model=LUNA, effort='none'):
    actor.command('select_model', id=model)
    actor.command('select_effort', id=effort)
    assert pair(actor) == (model, effort), 'I13/preferences: original fixture choices are set by genuine public user actions'


def pair(actor):
    return actor.last['vm']['selected_model'], actor.last['vm']['selected_effort']


def finish_signout(actor):
    actor.command('sign_out')
    revocations = [(i, r) for i, r in enumerate(actor.last['requests'])
                   if r['url'] == prior.native.AUTH + '/independent-revoke' and not r['cancelled']]
    assert len(revocations) == 1, 'I12/preferences: current sign-out has a genuine pending fixture revocation'
    actor.respond(revocations[0][0], None)
    actor.handled.add(revocations[0][0])


def test_user_choice_roundtrips_through_actual_store_and_process_restart(launch, signer):
    with launch() as first:
        connected(first, signer)
        choose(first)
        store = first.last['settings_file']
    assert Path(store).is_file(), 'I13/preferences: real user selection leaves an actual local settings store'
    with launch() as restarted:
        assert restarted.last['settings_file'] == store, 'I13/preferences: restart revisits the exact same owned store'
        assert not restarted.ready(), 'I12/preferences: remembered preference cannot fabricate pre-catalog readiness'
        connected(restarted, signer)
        assert pair(restarted) == (LUNA, 'none'), 'I13/preferences: available original user choice survives a genuine process restart'


def test_clear_signout_and_transient_empty_catalog_do_not_clobber_choice(launch, signer):
    with launch() as first:
        connected(first, signer)
        choose(first)
        first.command('clear_history')
        finish_signout(first)
        first.catalog = catalog()
        first.authenticate(signer)
        assert not first.ready(), 'I12/I13/preferences: empty catalog is not silently promoted to available models'
        assert not prior.responses(first), 'I13/preferences: Clear/sign-out/empty catalog never send a prompt'
    with launch() as restored:
        connected(restored, signer)
        assert pair(restored) == (LUNA, 'none'), 'I13/preferences: transient empty/sign-out/Clear preserve remembered user choices'


def test_unavailable_model_fallback_does_not_replace_remembered_choice(launch, signer):
    with launch() as first:
        connected(first, signer)
        choose(first)
    with launch(catalog(SOL)) as unavailable:
        connected(unavailable, signer)
        assert pair(unavailable) == (SOL, ''), 'I13/preferences: unavailable Luna/none truthfully falls back to available Sol/provider default'
        assert unavailable.last['vm']['last_error'], 'I13/preferences: unavailable remembered choice receives a visible explanation'
    with launch() as restored:
        connected(restored, signer)
        assert pair(restored) == (LUNA, 'none'), 'I13/preferences: automatic fallback is not persisted as a new user choice'


def test_explicit_provider_default_is_remembered_after_high(launch, signer):
    with launch() as first:
        connected(first, signer)
        choose(first, SOL, 'high')
        choose(first, SOL, '')
    with launch() as restored:
        connected(restored, signer)
        assert pair(restored) == (SOL, ''), 'I13/preferences: deliberate Provider default remains distinct from stale explicit high'
        restored.command('sign_in')
        index = prior.begin(restored, 'Original preference wire control')
        body = json.loads(restored.last['requests'][index]['body'])
        assert 'effort' not in body.get('reasoning', {}), 'I13/preferences: remembered Provider default omits explicit effort on actual mock wire'
        restored.command('cancel')


def test_busy_refused_setters_do_not_change_active_or_saved_choice(launch, signer):
    with launch() as busy:
        connected(busy, signer)
        choose(busy)
        busy.command('sign_in')
        index = prior.begin(busy, 'Original active operation preference fence')
        before = busy.last['requests'][index].copy()
        busy.command('select_model', id=SOL)
        busy.command('select_effort', id='high')
        assert pair(busy) == (LUNA, 'none'), 'I2/I13/preferences: busy user setters cannot drift the genuine active operation'
        assert busy.last['requests'][index] == before, 'I2/I13/preferences: refused busy selection leaves original physical request unchanged'
        assert len(prior.responses(busy)) == 1, 'I13/preferences: busy preference changes create no extra physical send'
        busy.command('cancel')
    with launch() as restored:
        connected(restored, signer)
        assert pair(restored) == (LUNA, 'none'), 'I13/preferences: refused busy choices do not overwrite persistent user intent'


def test_bounded_malformed_owned_settings_keep_truthful_catalog_fallback(launch, signer):
    with launch() as first:
        connected(first, signer)
        choose(first)
        store = Path(first.last['settings_file'])
    store.write_bytes(b'[unterminated\nnot-an-edi-preference=unavailable\n')
    with launch(catalog(SOL)) as malformed:
        connected(malformed, signer)
        assert pair(malformed) == (SOL, ''), 'I13/preferences: malformed owned settings cannot invent unavailable model/effort authority'
        assert not prior.responses(malformed), 'I13/preferences: malformed settings recovery performs no inference'


def qualify_read(path):
    # A separate real Qt process cannot warm or repair the subject's QSettings cache.
    result = subprocess.run(
        [os.environ['EDI_ASSISTANT_SETTINGS_VM_PROBE'], '--settings-read-qualifier', str(path)],
        capture_output=True, text=True, timeout=3, check=True,
    )
    value = json.loads(result.stdout)
    assert value['path'] == str(path), 'I13/PREF1: independent Qt reader addresses the exact original owned path'
    assert value['effective_uid'] == os.geteuid(), 'I13/PREF1: Qt and Python access controls use the same actual effective uid'
    return value


def test_read_only_qualifier_distinguishes_absence_denial_and_same_file_recovery(launch):
    root = Path(os.environ['EDI_TEST_SETTINGS_ROOT'])
    path = root / 'original-read-qualifier.ini'
    absent = qualify_read(path)
    assert not absent['exists'] and not absent['qfile_opened'], 'I13/PREF1: independently confirmed absence is not a readable file'
    assert absent['qsettings_status'] == 0 and absent['key_count'] == 0, 'I13/PREF1: genuine absent INI has actual Qt NoError and no keys'
    raw = b'[OriginalQualifier]\nmarker=harmless independently planted local data\n'
    path.write_bytes(raw)
    original = path.stat()
    mode = stat.S_IMODE(original.st_mode)
    try:
        readable = qualify_read(path)
        assert readable['qfile_opened'] and readable['qsettings_status'] == 0, 'I13/PREF1: original legal INI is actually readable with Qt NoError'
        path.chmod(0)
        with pytest.raises(PermissionError):
            path.read_bytes()
        refused = qualify_read(path)
        assert not refused['qfile_opened'] and refused['qsettings_status'] == 1, 'I13/PREF1: reached same-uid denial produces actual Qt AccessError, not confirmed absence'
    finally:
        path.chmod(mode)
    recovered = qualify_read(path)
    assert recovered['qfile_opened'] and recovered['qsettings_status'] == 0, 'I13/PREF1: identical original path becomes genuinely readable with Qt NoError after permission recovery'
    assert path.read_bytes() == raw and path.stat().st_ino == original.st_ino, 'I13/PREF1: read-only qualification preserves original inode and complete bytes'


def test_failed_preference_read_retries_on_same_live_owner_after_storage_recovers(launch, signer):
    with launch() as seed:
        connected(seed, signer)
        choose(seed)
        store = Path(seed.last['settings_file'])
    assert store.is_file(), 'I13/PREF1: genuine public user preference must exist before testing its read failure'
    raw = store.read_bytes()
    original = store.stat()
    mode = stat.S_IMODE(original.st_mode)
    facts = {'original_sha256': hashlib.sha256(raw).hexdigest(), 'inode': original.st_ino}
    try:
        store.chmod(0)
        with pytest.raises(PermissionError):
            store.read_bytes()
        refused = qualify_read(store)
        assert not refused['qfile_opened'] and refused['qsettings_status'] == 1, 'I13/PREF1: unreadable genuine store reaches independently qualified real Qt access failure'
        with launch() as recovering:
            connected(recovering, signer)
            facts['before_recovery'] = {'pair': pair(recovering), 'error': recovering.last['vm']['last_error'], 'can_cancel': recovering.last['vm']['can_cancel']}
            store.chmod(mode)
            facts['same_bytes_after_restore'] = store.read_bytes() == raw
            facts['same_inode_after_restore'] = store.stat().st_ino == original.st_ino
            readable = qualify_read(store)
            facts['qt_readable_after_restore'] = readable['qfile_opened'] and readable['qsettings_status'] == 0
            recovering.command('inspect')  # Existing idle opportunity, no preference setter/rewrite.
            facts['after_idle'] = {'pair': pair(recovering), 'error': recovering.last['vm']['last_error']}
            finish_signout(recovering)
            connected(recovering, signer)
            facts['after_reconnect'] = {'pair': pair(recovering), 'error': recovering.last['vm']['last_error']}
            facts['physical_inferences'] = len(prior.responses(recovering))
            facts['original_store_after_recovery'] = store.read_bytes() == raw
    finally:
        store.chmod(mode)
    print(json.dumps({'PREF1': facts}, ensure_ascii=False))
    # Defer semantic predicates until genuine recovery has been attempted and all facts retained.
    assert facts['before_recovery']['error'] and len(facts['before_recovery']['error'].encode()) <= prior.MESSAGE_BYTES, 'I13/PREF1: failed genuine store read has a bounded visible error instead of silently confirming absence'
    assert facts['same_bytes_after_restore'] and facts['same_inode_after_restore'] and facts['qt_readable_after_restore'], 'I13/PREF1: recovery uses the same independently readable original store, not a user-choice replacement'
    assert facts['after_reconnect']['pair'] == (LUNA, 'none'), 'I13/PREF1: same live owner retries failed load and restores actual user choice after genuine reconnect'
    assert facts['physical_inferences'] == 0 and facts['original_store_after_recovery'], 'I13/PREF1: read recovery neither sends inference nor rewrites the original user choice'


def test_confirmed_absent_store_is_a_legal_available_default(launch, signer):
    with launch(catalog(SOL)) as absent:
        store = Path(absent.last['settings_file'])
        assert not store.exists(), 'I13/PREF1: new isolated profile genuinely has no remembered choice'
        qualified = qualify_read(store)
        assert qualified['qsettings_status'] == 0 and qualified['key_count'] == 0, 'I13/PREF1: confirmed absent configured store is Qt NoError rather than access failure'
        connected(absent, signer)
        assert pair(absent) == (SOL, ''), 'I13/PREF1: genuine absence permits a current available model with Provider default'
        assert not prior.responses(absent), 'I13/PREF1: absent preference restoration never fabricates an inference'
