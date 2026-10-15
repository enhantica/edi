"""PRIVATE independent preference cases; no collection/build/runtime yet.

Owner94ffecaa5; accepted shipped capability map, original offline catalog choices.
No preferences key/schema inferred from private production changes.
"""
import json
import os
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
