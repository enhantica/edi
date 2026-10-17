"""Existing message command bounded FIFO: independent reviewed packet710585daf.

Original planted strings and recorded requests define chronology, not event counts
or a running-state setter. Real VM pending-row/consent/retention and genuine moving
fit boundary witnesses are separate from these public Controller observations.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'queued_protocol', ROOT / 'tests/integration/py/test_e11_t5_assistant_protocol.py'
)
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)
host = protocol.host


def queue(host, text):
    return host.user(
        'message', connection_id='connection-A', model=protocol.MODEL, effort='high', text=text
    )


def humans(request):
    return [
        row
        for row in request['history']
        if row.get('type') == 'message' and row.get('role') == 'user'
    ]


@pytest.mark.parametrize('boundary', ['provider-only', 'read-tool-result'])
def test_admitted_pending_humans_preserve_original_work_and_deliver_fifo_once(host, boundary):
    started = host.start()
    original = host.binding()
    initial_count = len(started['requests'])
    planted = ['FIRST pending Ångström instruction', 'SECOND pending PbSO₄ instruction']
    acknowledgments = []
    for text in planted:
        result = queue(host, text)
        assert result['reply']['ok'], (
            'FIFO: current-owner busy message admits without confirmation'
        )
        receipt = result['reply']['value']
        assert receipt.get('queued') is True and receipt.get('turn_id') == original['turn_id'], (
            'FIFO: pending acknowledgement keeps the original active turn authority'
        )
        identity = receipt.get('queued_message_id')
        assert isinstance(identity, str) and identity, (
            'FIFO: each pending original has stable identity'
        )
        acknowledgments.append(identity)
        assert len(result['requests']) == initial_count and host.binding() == original, (
            'FIFO: pending humans do not cancel or replace the physical active provider request'
        )
        assert result['snapshot'] == started['snapshot'], (
            'FIFO: admission grants no project mutation'
        )
    assert len(set(acknowledgments)) == len(planted), (
        'FIFO: distinct admitted humans have distinct IDs'
    )
    if boundary == 'read-tool-result':
        assert host.tool('inspect_project', call_id='original-read-outcome')['reply']['ok'], (
            'FIFO: original current-owner inspection remains usable'
        )
    settled = host.provider('turn_finished', **original, status='completed')
    assert len(settled['requests']) == initial_count + 1, (
        'FIFO: one genuinely settled successful boundary dispatches one continuation'
    )
    request = settled['requests'][-1]
    pending = [row['text'] for row in humans(request) if row['text'] in planted]
    assert pending == planted, 'FIFO: original texts enter actual next wire once in arrival order'
    if boundary == 'read-tool-result':
        history = request['history']
        call = [
            i
            for i, row in enumerate(history)
            if row.get('type') == 'tool_call' and row.get('call_id') == 'original-read-outcome'
        ]
        result = [
            i
            for i, row in enumerate(history)
            if row.get('type') == 'tool_result' and row.get('call_id') == 'original-read-outcome'
        ]
        first_human = next(i for i, row in enumerate(history) if row.get('text') == planted[0])
        assert len(call) == len(result) == 1 and call[0] < result[0] < first_human, (
            'FIFO: complete actual original tool outcome precedes queued humans on provider wire'
        )
    late = host.provider('turn_finished', **original, status='completed')
    assert len(late['requests']) == initial_count + 1, (
        'FIFO: retired completion cannot duplicate delivery'
    )


def test_pending_prose_cannot_answer_a_real_human_question(host):
    host.start()
    scope = host.binding()
    question = host.tool(
        'ask_question',
        {
            'text': 'Choose an independently declared next check',
            'options': [
                {'id': 'read', 'label': 'Read', 'description': 'Read current state'},
                {'id': 'wait', 'label': 'Wait', 'description': 'Preserve current state'},
            ],
            'recommended': 'read',
            'allow_free_text': True,
        },
        call_id='original-question',
    )
    assert question['reply']['ok'], 'FIFO: the actual trusted question hold is admitted first'
    identity = question['reply']['value']['question_id']
    count = len(question['requests'])
    pending = queue(host, 'read is merely queued prose, never my trusted answer')
    assert pending['reply']['ok'] and pending['state']['pending_question_id'] == identity, (
        'FIFO: queued text leaves genuine question authority pending'
    )
    held = host.provider('turn_finished', **scope, status='completed')
    assert len(held['requests']) == count and held['state']['pending_question_id'] == identity, (
        'FIFO: provider completion cannot bypass a genuine human answer boundary'
    )
    answered = host.user('answer', question_id=identity, answer='wait')
    assert answered['reply']['ok'] and len(answered['requests']) == count + 1, (
        'FIFO: only the explicit answer resumes actual question settlement once'
    )
    history = answered['requests'][-1]['history']
    result = next(
        i
        for i, row in enumerate(history)
        if row.get('type') == 'tool_result'
        and row.get('call_id') == 'original-question'
        and row.get('result', {}).get('answer') == 'wait'
    )
    queued = next(
        i
        for i, row in enumerate(history)
        if row.get('text') == 'read is merely queued prose, never my trusted answer'
    )
    assert result < queued, (
        'FIFO: complete original human answer precedes queued human instruction'
    )


@pytest.mark.parametrize('retirement', ['stop', 'detach', 'changed-connection'])
def test_retired_pending_authority_never_dispatches_on_old_completion(host, retirement):
    host.start()
    original = host.binding()
    queued = queue(host, 'Retire this exact pending instruction without sending it')
    assert queued['reply']['ok'], (
        'FIFO: retirement witness begins with real admitted pending authority'
    )
    count = len(queued['requests'])
    if retirement == 'stop':
        retired = host.user('cancel')
    elif retirement == 'detach':
        retired = host.command('detach')
    else:
        retired = host.provider(
            'connection',
            connection_id='connection-B',
            status='ready',
            capabilities=[
                {
                    'id': protocol.MODEL,
                    'display_name': 'Original B',
                    'efforts': ['high'],
                    'attachment_types': [],
                }
            ],
        )
    after = host.provider('turn_finished', **original, status='completed')
    assert len(after['requests']) == count, (
        'FIFO: retired original completion cannot send pending work'
    )
    assert after['snapshot'] == retired['snapshot'], (
        'FIFO: late completion cannot change retired scope'
    )


def test_oversize_pending_admission_preserves_original_request_and_prior_pending_text(host):
    host.start()
    original = host.binding()
    admitted = queue(host, 'Already admitted original pending human')
    assert admitted['reply']['ok'], 'FIFO: a valid pending original precedes bounded refusal'
    count = len(admitted['requests'])
    refused = queue(host, 'x' * 1048577)  # Limits::message_bytes inclusive1048576, ADR0037.
    assert not refused['reply']['ok'], (
        'FIFO: encoded-message admission refuses an oversized command before queue growth'
    )
    assert len(refused['requests']) == count and refused['snapshot'] == admitted['snapshot'], (
        'FIFO: over-budget pending admission leaves active physical work and project untouched'
    )
    settled = host.provider('turn_finished', **original, status='completed')
    assert [
        row['text']
        for row in humans(settled['requests'][-1])
        if row['text'] == 'Already admitted original pending human'
    ] == ['Already admitted original pending human'], (
        'FIFO: a later refused admission cannot consume or duplicate the earlier pending original'
    )


def test_combined_pending_originals_share_existing_history_bytes_without_eviction(host):
    host.start()
    original = host.binding()
    # ADR0037 history_bytes2097152: four600000-byte pending originals cannot fit.
    # Other actual retaining roles may exhaust first; do not invent their copy count.
    # Every individual command stays below message_bytes1048576.
    planted = []
    refused = None
    before = host.last
    for index in range(4):
        text = str(index) + 'x' * 599999
        observed = queue(host, text)
        if not observed['reply']['ok']:
            refused = observed
            break
        planted.append(text)
        before = observed
    assert planted and refused is not None, (
        'FIFO: bounded aggregate originals reach actual refusal without inventing retaining copies'
    )
    assert refused['reply']['code'] == 'edi.assistant.resource_exhausted', (
        'FIFO: pending originals consume existing finite retaining quotas before growth'
    )
    assert (
        refused['snapshot'] == before['snapshot'] and refused['requests'] == before['requests']
    ), 'FIFO: aggregate pending refusal cannot cancel active work or mutate the project'
    settled = host.provider('turn_finished', **original, status='completed')
    actual = [row['text'] for row in humans(settled['requests'][-1]) if row['text'] in planted]
    assert actual == planted, (
        'FIFO: quota refusal preserves each admitted original without truncation or eviction'
    )


def test_queued_prose_cannot_approve_a_real_pending_plan(host):
    host.start()
    original = host.binding()
    proposed = host.tool(
        'propose_plan',
        {
            'summary': 'An independently scoped cell change requires trusted approval',
            'groups': [{'id': 'cell', 'paths': ['structure.cell.length_a']}],
            'budget': {'max_trials': 3, 'max_iterations': 7, 'max_elapsed_ms': 5000},
            'objective': {'absolute_tolerance': 0.125, 'relative_tolerance': 0.003},
        },
        call_id='original-plan-proposal',
    )
    assert proposed['reply']['ok'] and proposed['state']['pending_plan_id'], (
        'FIFO: a real scoped proposal establishes the separate trusted approval door'
    )
    plan = proposed['state']['pending_plan_id']
    count = len(proposed['requests'])
    pending = queue(host, 'Approve this plan is queued prose, not my trusted approval action')
    assert pending['reply']['ok'] and pending['reply']['value'].get('queued') is True, (
        'FIFO: a pending plan may retain a human followup without granting approval'
    )
    held = host.provider('turn_finished', **original, status='completed')
    assert len(held['requests']) == count and held['state']['pending_plan_id'] == plan, (
        'FIFO: queued prose and provider completion cannot bypass a real approval hold'
    )
    assert (
        held['snapshot'] == proposed['snapshot'] and held['apply_count'] == proposed['apply_count']
    ), 'FIFO: untrusted approval-looking queued text performs no scientific write'
    approved = host.user(
        'approve_plan', plan_id=plan, project_id='project-A', revision=held['state']['revision']
    )
    assert approved['reply']['ok'] and len(approved['requests']) == count + 1, (
        'FIFO: only the real current trusted approval action resumes the held plan'
    )
