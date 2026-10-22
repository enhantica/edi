"""Real empty-Session handoff and fresh export; no OS-picker or model claim.

Independent input is the committed complete LBCO project, not an agent/candidate
golden. Frozen032cdefc9/brief96030b/addendum0ed861 define the result authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import sys
from operator import itemgetter
from pathlib import Path

import pytest

from tests.system.app import test_e11_t5_codex_agent as old
from tests.system.app.test_e11_t5_codex_agent import generic  # noqa: F401 -- shared real fixture

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project'


def hashes(root):
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob('*')
        if p.is_file() and not p.is_symlink()
    }


def original_loop(text, first):
    lines = text.splitlines()
    start = lines.index(first)
    end = start
    while end < len(lines) and lines[end].startswith('_'):
        end += 1
    names = lines[start:end]
    rows = []
    for line in lines[end:]:
        if not line.strip():
            continue
        if line.startswith(('_', 'loop_', 'data_')):
            break
        rows.append(dict(zip(names, shlex.split(line), strict=True)))
    return rows


def expected_input():
    text = (ORIGINAL / 'experiments/hrpt.edi').read_text()
    rows = original_loop(text, '_data.two_theta')
    excluded = original_loop(text, '_excluded_region.id')
    return {
        'axis': [float(v['_data.two_theta']) for v in rows],
        'intensity': [float(v['_data.intensity_meas']) for v in rows],
        'sigma': [float(v['_data.intensity_meas_su']) for v in rows],
        'exclusions': [
            [float(v['_excluded_region.start']), float(v['_excluded_region.end'])]
            for v in excluded
        ],
        'phases': ['lbco'],
    }


@pytest.fixture
def result_factory(request, tmp_path):
    create_generic = request.getfixturevalue('generic')
    original = hashes(ORIGINAL)
    fixture = tmp_path / 'original-input'
    for source in ORIGINAL.rglob('*.edi'):
        target = fixture / source.relative_to(ORIGINAL)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    assert len(hashes(fixture)) == 4, 'H2 SETUP: four original self-contained native files'

    def create(variant='complete'):
        actor, trace = create_generic('result:' + variant)
        config_path = trace.parent / 'peer-input.json'
        config = json.loads(config_path.read_text())
        config['result_fixture'] = str(fixture)
        config_path.write_text(json.dumps(config))
        old.connect(actor)
        assert not actor.last['vm']['project_present'], 'H2: initiating real Session is empty'
        return actor, trace

    yield create
    assert hashes(ORIGINAL) == original, (
        'H2: all committed original scientific bytes are preserved'
    )


def result_record(actor, trace):
    record = trace.with_suffix('.result.json')
    for _ in range(40):
        if record.is_file() and record.stat().st_size:
            observed = json.loads(record.read_text())
            metadata = observed['metadata']
            assert metadata is not None, (
                'H2: real admitted request carries app-owned result intent'
            )
            assert metadata['schema'] == 'edi.assistant.result/1', 'H2: exact result schema'
            intent = metadata['intent']
            assert isinstance(intent, str) and intent and '/' not in intent, (
                'H2: app-issued opaque intent is a safe nonempty path component'
            )
            assert metadata['receipt'] == f'.edi-result/{intent}/result.json', (
                'H2: actual app-owned receipt location is bound to this intent'
            )
            assert metadata['project'] == f'.edi-result/{intent}/project', (
                'H2: ordinary runtime candidate has the fixed admitted location'
            )
            assert observed['prepared'], (
                'H2 SETUP: peer saved original complete fixture and receipt'
            )
            return observed
        actor.command('inspect')
    pytest.fail('H2: genuine admitted turn reaches the ordinary owned-peer result boundary')


def start(actor, trace):
    draft = 'Create the original measured LBCO result'
    actor.command('send_text', text=draft)
    for _ in range(40):
        requests = old.started_requests(trace)
        assert len(requests) <= 1, 'H2: original input cannot be replayed or duplicated'
        if requests:
            params = requests[0]['params']
            assert (
                sum(
                    item.get('type') == 'text' and item.get('text') == draft
                    for item in params['input']
                )
                == 1
            ), 'H2: admitted wire identity belongs to this exact original draft once'
            identity = params.get('clientUserMessageId')
            assert isinstance(identity, str) and identity, (
                'H2: actual public admission supplies its original user identity'
            )
            actor.result_user_id = identity
            return result_record(actor, trace)
        actor.command('inspect')
    pytest.fail('H2: real public send reaches its actual published admission boundary')


def project_readback(state):
    assert state['project_present'], 'H2: actual native loader publishes the host project'
    data = state['project']['host_snapshot']['experiments']
    assert len(data) == 1, 'H2: original one-experiment project remains whole'
    for key, value in expected_input().items():
        assert data[0][key] == value, 'H2: original measured columns, exclusions and phase survive'
    assert data[0]['weight'] == 1.0, 'H2: original single-dataset default weight survives'
    return state['project']['host_snapshot']


def adopted(result_factory):
    actor, trace = result_factory()
    models = actor.last['vm']['models']
    account = actor.last['vm'].get('handoff', {}).get('account_label')
    observed = start(actor, trace)
    state = old.settle(actor, itemgetter('project_present'))
    project_readback(state)
    assert state['connected'] and state['models'] == models, (
        'H2: controlled settled bind preserves actual managed account and catalogue'
    )
    assert [row['id'] for row in old.users(actor, 'Create the original measured LBCO result')] == [
        actor.result_user_id
    ], 'H2: controlled bind retains the original admitted visible user identity'
    assert state['handoff']['account_label'] == account and account, (
        'H2: controlled bind preserves the actual public account identity'
    )
    assert any(
        row['kind'] == 'assistant' and row['text'] == 'Original offline reply'
        for row in state['messages']
    ), 'H2: adoption follows a genuinely retained complete original reply'
    return actor, trace, observed


def test_complete_original_result_is_sealed_and_keeps_real_account_history(result_factory):
    actor, trace, observed = adopted(result_factory)
    state = actor.last['vm']
    snapshot = project_readback(state)
    assert not Path(snapshot['path']).resolve().is_relative_to(Path(observed['cwd']).resolve()), (
        'H2: host loads an immutable snapshot outside the runtime writable root'
    )
    assert state['handoff']['needs_save_as'] and state['handoff']['needs_fresh_save_as'], (
        'H2: automatically adopted result remains unsaved until explicit fresh export'
    )
    assert state['context_consent_required'], (
        'H2: the newly adopted project requires fresh approval of its actual disclosed context'
    )
    (Path(observed['project']) / 'experiments/hrpt.edi').write_text('Late runtime mutation')
    actor.command('inspect')
    assert project_readback(actor.last['vm']) == snapshot, (
        'H2: runtime mutation after capture cannot change host-loaded data'
    )
    original_thread = next(v for v in old.records(trace) if v.get('method') == 'thread/start')
    if actor.last['vm']['context_consent_required']:
        actor.command('sign_in')
    actor.command('send_text', text='Inspect the adopted current project')
    old.settle(actor, lambda _value: len(old.started_requests(trace)) >= 2)
    threads = [v for v in old.records(trace) if v.get('method') == 'thread/start']
    assert (
        len(threads) == 2 and threads[-1]['params']['cwd'] != original_thread['params']['cwd']
    ), 'H2: next admitted context gets a fresh working copy rather than old execution authority'
    assert len([v for v in old.records(trace) if v.get('method') == 'account/login/start']) == 0, (
        'H2: controlled adoption does not replay account login'
    )


@pytest.mark.parametrize('variant', ['failed', 'hold'])
def test_receipt_without_successful_retained_completion_cannot_adopt(result_factory, variant):
    actor, trace = result_factory(variant)
    start(actor, trace)
    actor.command('inspect')
    assert not actor.last['vm']['project_present'], (
        'H2: saved files alone, failed turn and active turn never publish a host project'
    )
    if variant == 'hold':
        assert actor.last['vm']['can_cancel'], 'H2: real active work remains stoppable'


def actual_edi_result_outcome(state, intent):
    return next(
        (
            row
            for row in state['messages']
            if row.get('id') == 'edi-result-' + intent
            and row.get('kind') == 'activity'
            and row.get('payload', {}).get('type') == 'ediOutcome'
            and row['payload'].get('actor') == 'Edi'
            and row['payload'].get('intent') == intent
        ),
        None,
    )


@pytest.mark.parametrize(
    'variant',
    [
        'foreign',
        'hash',
        'undeclared',
        'symlink',
        'directories',
        'receipt-fifo',
        'data-fifo',
        'receipt-link',
        'depth',
        'duplicates',
        'receipt-bytes',
        'calculation-only',
    ],
)
def test_invalid_or_unclosed_result_never_replaces_empty_owner(result_factory, variant):
    actor, trace = result_factory(variant)
    observed = start(actor, trace)
    intent = observed['metadata']['intent']
    state = old.settle(
        actor,
        lambda value: (
            value['project_present']
            or bool(
                value['handoff']['last_error']
                or value['last_error']
                or actual_edi_result_outcome(value, intent)
            )
        ),
    )
    assert any(
        row.get('kind') == 'assistant'
        and row.get('status') == 'completed'
        and row.get('text') == 'Original offline reply'
        for row in state['messages']
    ), 'H2 SETUP: retained successful original precedes the actual app adoption/refusal outcome'
    assert not state['project_present'], (
        'H2: identity/hash/closure/link/represented-entry refusal preserves the empty Session'
    )
    outcome = actual_edi_result_outcome(state, intent)
    if outcome is not None:
        assert outcome['status'] == 'failed', 'H2: actual refusal cannot claim successful adoption'
        assert all(
            isinstance(outcome['payload'].get(key), str)
            and outcome['payload'][key]
            and len(outcome['payload'][key].encode()) <= 512
            for key in ('title', 'message')
        )
    assert state['handoff']['last_error'] or state['last_error'] or outcome is not None, (
        'H2: actual refusal has a bounded error or genuine same-intent chronological Edi failure'
    )
    assert all(
        len(value.encode()) <= 512
        for value in [state['handoff']['last_error'], state['last_error']]
    ), 'HLP: refusal explanations remain within the approved error-byte bound'


@pytest.mark.parametrize('retirement', ['clear', 'project', 'steer'])
def test_old_result_cannot_rebind_after_actual_owner_retirement(result_factory, retirement):
    actor, trace = result_factory('steer' if retirement == 'steer' else 'late')
    start(actor, trace)
    assert actor.last['vm']['can_cancel'], 'H2: original actual turn exists before retirement'
    if retirement == 'clear':
        actor.command('clear_history')
    elif retirement == 'project':
        actor.command('open', path=str(ORIGINAL))
        assert actor.last['reply']['opened'], 'H2 SETUP: real unrelated project owner opens'
    else:
        actor.command('send_text', text='New actual admitted input supersedes the old intent')
    state = old.settle(actor, lambda value: not value['can_cancel'])
    if retirement == 'project':
        assert state['project']['host_snapshot']['path'] == str(ORIGINAL), (
            'H2: late result cannot overwrite the independently opened current owner'
        )
    else:
        assert not state['project_present'], 'H2: retired original cannot revive an empty owner'


def begin_export(actor):
    surface = actor.last['vm']['handoff']
    assert all(surface[key] for key in ['begin_method', 'complete_method', 'cancel_method']), (
        'H2 SETUP: real production Session export callback surface is present'
    )
    result = actor.command('save_as_begin')['reply']
    assert result['invoked'] and result['intent'], (
        'H2: real Save As captures one initiating intent'
    )
    return result['intent']


@pytest.mark.parametrize('parent_alias', [False, True])
def test_fresh_parent_child_export_reopens_without_mutating_original_parent(
    result_factory, tmp_path, parent_alias
):
    actor, _, _ = adopted(result_factory)
    parent = tmp_path / 'Owned Desktop'
    parent.mkdir()
    if parent_alias:
        alias = tmp_path / 'Desktop alias'
        alias.symlink_to(parent, target_is_directory=True)
        parent = alias
    intent = begin_export(actor)
    result = actor.command(
        'save_as_complete', intent=intent, parent=str(parent), leaf='original-copy'
    )
    assert result['reply']['invoked'] and result['reply']['accepted'], (
        'H2: real callback publishes the independently prepared fresh child'
    )
    assert sorted(p.name for p in parent.iterdir()) == ['original-copy'], (
        'H2: no residual stage or unrelated parent replacement after publication'
    )
    snapshot = project_readback(result['vm'])
    assert Path(snapshot['path']).resolve() == (parent / 'original-copy').resolve(), (
        'H2: displayed Save target changes only to the committed child'
    )
    assert not result['vm']['handoff']['needs_save_as'], (
        'H2: exported result has its normal target'
    )
    again = actor.command('save_as_complete', intent=intent, parent=str(parent), leaf='duplicate')
    assert not again['reply']['accepted'] and not (parent / 'duplicate').exists(), (
        'H2: successful callback consumes its authority exactly once'
    )


def test_trusted_temporary_root_alias_uses_the_same_real_consumer(
    result_factory, monkeypatch, tmp_path
):
    real = tmp_path / 'actual-trusted-temporary-root'
    real.mkdir()
    alias = tmp_path / 'trusted-temporary-alias'
    alias.symlink_to(real, target_is_directory=True)
    binary = os.environ['EDI_ASSISTANT_WORKFLOW_VM_PROBE']
    launcher = tmp_path / 'actual-consumer-with-normal-temp-environment'
    launcher.write_text(
        f'#!{sys.executable}\nimport os,sys\n'
        f'os.environ["TMPDIR"]={str(alias)!r}\n'
        f'os.execv({binary!r}, [{binary!r}, *sys.argv[1:]])\n'
    )
    launcher.chmod(0o700)
    monkeypatch.setenv('EDI_ASSISTANT_WORKFLOW_VM_PROBE', str(launcher))
    actor, _, observed = adopted(result_factory)
    assert Path(observed['cwd']).resolve().is_relative_to(real), (
        'HLP SETUP: ordinary trusted TMPDIR alias reaches the actual real Session process'
    )
    project_readback(actor.last['vm'])


@pytest.mark.parametrize('collision', ['file', 'directory', 'symlink'])
def test_fresh_export_never_overwrites_even_an_empty_or_link_collision(
    result_factory, tmp_path, collision
):
    actor, _, _ = adopted(result_factory)
    parent = tmp_path / 'parent'
    parent.mkdir()
    destination = parent / 'original-copy'
    outside = tmp_path / 'outside-original'
    outside.write_text('Original outside bytes')
    if collision == 'file':
        destination.write_text('Original collision bytes')
    elif collision == 'directory':
        destination.mkdir()
    else:
        destination.symlink_to(outside)
    inode = destination.lstat().st_ino
    before = actor.last['vm']['project']['host_snapshot']
    intent = begin_export(actor)
    result = actor.command(
        'save_as_complete', intent=intent, parent=str(parent), leaf=destination.name
    )
    assert result['reply']['invoked'] and not result['reply']['accepted'], (
        'H2: real no-overwrite export refuses every existing final-name type'
    )
    assert (
        destination.lstat().st_ino == inode and outside.read_text() == 'Original outside bytes'
    ), 'H2: refusal preserves original collision identity and outside sentinel'
    if collision == 'file':
        assert destination.read_text() == 'Original collision bytes', 'H2: original bytes survive'
    assert result['vm']['project']['host_snapshot'] == before, (
        'H2: failed preparation/publication never changes displayed project/path'
    )


@pytest.mark.parametrize('retirement', ['cancel', 'manual', 'project'])
def test_export_callback_is_bound_before_dialogs_and_rejects_stale_owner(
    result_factory, tmp_path, retirement
):
    actor, _, _ = adopted(result_factory)
    parent = tmp_path / 'parent'
    parent.mkdir()
    intent = begin_export(actor)
    if retirement == 'cancel':
        assert actor.command('save_as_cancel', intent=intent)['reply']['invoked'], (
            'H2: actual production cancel callback is reached'
        )
    elif retirement == 'manual':
        parameter = actor.last['vm']['project']['parameters'][0]
        actor.command('manual_value', path=parameter['path'], value=parameter['value'] + 0.001)
        assert not actor.last['reply']['error'], (
            'H2 SETUP: actual editor accepts the manual change'
        )
    else:
        assert actor.command('open', path=str(ORIGINAL))['reply']['opened'], (
            'H2 SETUP: unrelated actual project becomes current'
        )
    before = actor.last['vm']['project']
    result = actor.command('save_as_complete', intent=intent, parent=str(parent), leaf='stale')
    assert not result['reply']['accepted'] and not list(parent.iterdir()), (
        'H2: cancelled or stale initiating revision cannot create destination-local output'
    )
    assert result['vm']['project'] == before, (
        'H2: stale callback preserves the actual current model'
    )


def test_export_leaf_is_one_component_not_arbitrary_typed_path(result_factory, tmp_path):
    actor, _, _ = adopted(result_factory)
    parent = tmp_path / 'parent'
    parent.mkdir()
    intent = begin_export(actor)
    result = actor.command('save_as_complete', intent=intent, parent=str(parent), leaf='../escape')
    assert not result['reply']['accepted'] and not (tmp_path / 'escape').exists(), (
        'H2: native fresh-leaf callback cannot grant arbitrary outside path access'
    )


def test_actual_queued_adoption_contains_notice_storage_failure_without_false_opening_failure(
    result_factory,
):
    actor, trace = result_factory('notice-storage')
    observed = start(actor, trace)
    intent = observed['metadata']['intent']
    assert actor.last['archive']['is_file'] and actor.last['archive']['bytes'] > 0
    armed = actor.command('arm_post_adoption_barrier', intent=intent)
    assert armed['reply']['armed'] and armed['reply']['archive_untouched']
    assert not any(
        event['kind'] == 'notice-terminal-emission' for event in old.clear_control_events(trace)
    ), 'NOTICE SETUP: only the public project-publication observer is armed before terminal'
    state = old.settle(
        actor,
        lambda value: (
            value['project_present'] or bool(value['handoff']['last_error'] or value['last_error'])
        ),
    )
    barrier = actor.last['notice_barrier']
    assert barrier.get('project_present') and barrier.get('fresh_save_as'), (
        'NOTICE SETUP: barrier actually fires after real managed project publication'
    )
    assert barrier.get('intent') == intent and not barrier.get('observer_error')
    assert barrier.get('is_directory') and (
        barrier['preserved_sha256'] == barrier['retained_sha256']
    ), (
        'NOTICE SETUP: retained terminal bytes stay preserved before notice storage refusal'
    )
    assert any(
        row.get('kind') == 'assistant'
        and row.get('status') == 'completed'
        and row.get('text') == 'Original offline reply'
        for row in barrier['retained_rows']
    ), 'NOTICE SETUP: genuine successful original was durably retained before project publication'
    project_readback(state)
    assert state['connected'] and state['handoff']['account_label'] == 'original@example.invalid'
    outcome = actual_edi_result_outcome(state, intent)
    if outcome is not None:
        assert outcome['status'] == 'completed', (
            'NOTICE: committed adoption cannot claim opening failed after storage error'
        )
    assert state['last_error'] or state['handoff']['last_error'] or outcome is not None, (
        'NOTICE: storage failure is contained and reconciled without an exception through Qt'
    )
    alive = actor.command('inspect')
    assert alive['vm']['project_present'], (
        'NOTICE: the actual owner still responds after queued failure'
    )
    project_readback(alive['vm'])
