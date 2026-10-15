"""Actual QML owner, real offline OAuth and bounded URL observations."""

from __future__ import annotations

import base64
import importlib.util
import json
import os
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'e11_t5_ui_native', ROOT / 'tests/system/py/test_e11_t5_assistant_native.py'
)
native_protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(native_protocol)
signer = native_protocol.signer


class RealUi(native_protocol.Native):
    def __init__(self, binary):
        super().__init__(binary, reply_timeout=10)

    def ready(self):
        return self.last['ui']['connected']

    def send_text(self, text='Inspect the displayed project'):
        return self.command('send_text', text=text)


@pytest.fixture
def ui(monkeypatch):
    override = os.environ.get('EDI_ASSISTANT_UI_PROBE')
    binary = (
        Path(override)
        if override
        else ROOT / 'build/assistant-real-owner-tests/assistant_real_owner_probe'
    )
    assert binary.is_file(), (
        'I12/I16: the approved real Session/VM/native composition host must '
        'build before connected UI behavior can be measured'
    )
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    monkeypatch.setenv('QT_QUICK_BACKEND', 'software')
    actor = RealUi(binary)
    actor.command('inspect')
    try:
        yield actor
    finally:
        actor.close()


def authenticate(ui, signer, **kwargs):
    ui.authenticate(signer, **kwargs)
    assert ui.ready(), (
        'I12/I16: real loopback/signature/grant/catalog processing connects the '
        'actual Session-owned assistant'
    )
    assert ui.last['ui']['singleton_identity'], (
        'I16: supplied C++ Session, engine singleton lookup and real Main QML '
        'resolve to the exact same owner'
    )
    return ui.last


def copy_project(tmp_path, name):
    source = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project'
    target = tmp_path / name
    shutil.copytree(source, target)
    return target


def begin_request(ui):
    before = len(ui.last['requests'])
    ui.send_text()
    pending = [
        (index, request)
        for index, request in enumerate(ui.last['requests'][before:], start=before)
        if request['url'] == native_protocol.API + '/responses'
    ]
    if not pending:
        # A changed content scope may require another actual disclosure dialog.
        disclosure = ui.command('accept_dialog')
        assert disclosure['reply']['accepted'], (
            'I12: a withheld request exposes a real consent action instead of '
            'silently refusing ordinary UI use'
        )
        ui.send_text()
        pending = [
            (index, request)
            for index, request in enumerate(ui.last['requests'][before:], start=before)
            if request['url'] == native_protocol.API + '/responses'
        ]
    assert len(pending) == 1, (
        'I13/I16: one real composer action dispatches one current native request'
    )
    index, request = pending[0]
    ui.command('headers', index=index, status=200, headers=[['Content-Type', 'text/event-stream']])
    return index, request


def function_events(name, arguments, *, call_id='ui-call'):
    item = {
        'id': 'function-' + call_id,
        'type': 'function_call',
        'call_id': call_id,
        'name': name,
        'arguments': json.dumps(arguments, ensure_ascii=False, separators=(',', ':')),
        'status': 'completed',
    }
    return [
        {
            'type': 'response.output_item.added',
            'output_index': 0,
            'item': {**item, 'arguments': '', 'status': 'in_progress'},
        },
        {
            'type': 'response.function_call_arguments.done',
            'output_index': 0,
            'item_id': item['id'],
            'arguments': item['arguments'],
        },
        {'type': 'response.output_item.done', 'output_index': 0, 'item': item},
        {
            'type': 'response.completed',
            'response': {'id': 'response-' + call_id, 'status': 'completed', 'output': [item]},
        },
    ]


def proposal(summary, *, group_id='cell', path='structure.cell.length_a'):
    return {
        'summary': summary,
        'groups': [{'id': group_id, 'paths': [path]}],
        'budget': {'max_trials': 2, 'max_iterations': 7, 'max_elapsed_ms': 5000},
        'objective': {'absolute_tolerance': 0.0, 'relative_tolerance': 0.0},
    }


def literal_payload(ui, marker):
    return (
        '<b>'
        + marker
        + ' &amp;</b><img src="'
        + ui.last['image_url']
        + '"><a href="https://independent-fixture.invalid/action">link</a>'
    )


def assert_literal_renderer(ui, marker):
    candidates = [
        text
        for text in ui.last['ui']['texts']
        if text['visible'] and text['format'] >= 0 and marker in text['text']
    ]
    assert candidates, (
        'I12/I16: the untrusted witness reaches an actual visible text renderer, '
        'not only a backing object or model'
    )
    tokens = ['<b>' + marker, '</b>', '<img src=', '<a href=', '&amp;']
    assert all(all(token in text['display'] for token in tokens) for text in candidates), (
        'I12/I16: every rendered copy preserves the literal untrusted string '
        'rather than interpreting provider markup'
    )
    assert ui.last['image_requests'] == 0, (
        'I12: rendering provider text cannot initiate undeclared image network requests'
    )
    ui.command('click_link', marker=marker)
    assert ui.last['activated_urls'] == [], (
        'I12: literal provider text cannot activate the generic label external URL handler'
    )


def test_actual_owner_composition_has_one_session_and_real_lifetime(ui, signer):
    authenticate(ui, signer)
    assert ui.last['ui']['engine_parent'] and ui.last['ui']['cpp_ownership'], (
        'I16: the transferred actual Session has exactly the engine QObject '
        'owner and explicit C++ ownership'
    )
    ui.command('destroy')
    assert not ui.last['ui']['alive'], (
        'I10/I16: destroying the actual engine releases Session and its '
        'assistant before fixture services'
    )


@pytest.mark.parametrize('kind', ['null', 'parented', 'already-configured'])
def test_real_engine_refuses_invalid_owner_transfer_without_replacing_existing_owner(ui, kind):
    result = ui.command('configure_refusal', kind=kind)
    assert result['reply']['rejected'] and result['reply']['original_preserved'], (
        'I16: invalid ownership/configuration cannot replace or silently create '
        'a second real Session'
    )
    assert result['ui']['singleton_identity'], (
        'I16: refusal preserves the supplied owner in C++ singleton lookup and actual QML'
    )


@pytest.mark.parametrize('owner', ['session', 'vm'])
@pytest.mark.parametrize('index', range(8))
def test_required_services_validate_before_real_owner_or_vm_external_io(ui, owner, index):
    result = ui.command('missing_constructor', owner=owner, index=index)
    assert result['reply']['rejected'] and result['reply']['service_calls'] == 0, (
        'I12/I16: missing dependencies reject before real owner/VM '
        'store/network/browser/clock work or default fallback'
    )


def test_render_observers_have_real_bounded_image_and_url_positive_controls(ui):
    result = ui.command('calibrate_observer')
    assert result['reply']['image_requests'] > 0, (
        'I12: the independent rich-text control actually reaches the bounded '
        'loopback image observer'
    )
    assert result['reply']['link_hit'], (
        'I12: the actual generic Label link hit-test and mouse path is exercised by calibration'
    )
    assert result['reply']['url_activations'] == 1, (
        'I12: the independent URL control actually reaches the intercepted desktop URL handler'
    )
    assert result['image_requests'] == 0 and result['activated_urls'] == [], (
        'I12: control observations settle/reset before evaluating production renderers'
    )


@pytest.mark.parametrize('sink', ['plan', 'error', 'message', 'plan-details'])
def test_provider_text_is_literal_in_actual_plan_error_message_and_detail_renderers(
    ui, signer, sink
):
    ui.command('create', name='literal_source')
    authenticate(ui, signer)
    marker = 'UNTRUSTED-' + sink
    payload = literal_payload(ui, marker)
    index, _ = begin_request(ui)
    if sink == 'message':
        events = [
            {'type': 'response.output_text.delta', 'delta': payload},
            {
                'type': 'response.completed',
                'response': {'id': 'response-text', 'status': 'completed', 'output': []},
            },
        ]
    elif sink == 'error':
        events = function_events('propose_plan', proposal('Invalid path control', path=payload))
    else:
        events = function_events(
            'propose_plan',
            proposal(
                payload if sink == 'plan' else 'Plain summary',
                group_id=payload if sink == 'plan-details' else 'cell',
            ),
        )
    native_protocol.stream(ui, index, events, width=17)
    assert_literal_renderer(ui, marker)


@pytest.mark.parametrize('popup', [False, True], ids=['collapsed', 'popup'])
def test_provider_model_display_name_is_literal_in_both_actual_catalog_views(ui, signer, popup):
    marker = 'UNTRUSTED-MODEL'
    payload = literal_payload(ui, marker)
    ui.catalog = {
        'models': [{'slug': 'gpt-6.1-sol', 'display_name': payload, 'visibility': 'list'}]
    }
    authenticate(ui, signer)
    ui.command('select_model', id='gpt-6.1-sol')
    if popup:
        ui.command('popup', name='assistant.model')
    assert_literal_renderer(ui, marker)


def test_verified_account_caption_does_not_treat_signed_display_metadata_as_markup(ui, signer):
    marker = 'UNTRUSTED-ACCOUNT'
    # Quoted address local-parts permit markup; signature validation grants no text-format trust.
    email = '"' + literal_payload(ui, marker).replace('"', "'") + '"@example.invalid'
    authenticate(ui, signer, claims_patch={'email': email})
    assert_literal_renderer(ui, marker)


@pytest.mark.parametrize('status', ['failed', 'incomplete'])
def test_streamed_failure_after_public_text_is_visible_in_the_real_panel(ui, signer, status):
    authenticate(ui, signer)
    index, _ = begin_request(ui)
    native_protocol.stream(
        ui,
        index,
        [
            {
                'type': 'response.output_text.delta',
                'delta': 'A partial answer with Ångström units',
            },
            {
                'type': 'response.' + status,
                'response': {
                    'id': 'response-failure',
                    'status': status,
                    'error': {
                        'code': 'subscription_sharing_usage_limit_exceeded',
                        'message': 'Independent fixture limit',
                    },
                },
            },
        ],
        width=5,
    )
    state = ui.last['ui']
    assert state['last_error'] or any(
        row['status'] not in {'', 'completed'} for row in state['messages']
    ), (
        'I13/I16: actual panel history/error presentation retains an incomplete '
        'provider outcome after successful HTTP'
    )
    assert not state['can_cancel'], 'I10/I13: the failed stream settles actual UI execution state'


def test_queued_old_native_tool_cannot_create_a_plan_after_real_project_replacement(
    ui, signer, tmp_path
):
    first, second = copy_project(tmp_path, 'first'), copy_project(tmp_path, 'second')
    assert ui.command('open', path=str(first))['reply']['opened'], (
        'I4: real Session loads the first independent writable project copy'
    )
    authenticate(ui, signer)
    index, _ = begin_request(ui)
    events = function_events('propose_plan', proposal('OLD REQUEST PLAN'))
    wire = ''.join('data: ' + json.dumps(e, ensure_ascii=False) + '\n\n' for e in events).encode()
    result = ui.command(
        'callback_then_open',
        callback={'op': 'data', 'index': index, 'base64': base64.b64encode(wire).decode()},
        path=str(second),
    )
    assert result['reply']['opened'], (
        'I4: actual Session replaces the project before queued native deliveries run'
    )
    assert not result['ui']['pending_plan'], (
        'I2/I7: queued old-project native work cannot be retagged into a new actual owner binding'
    )
    assert result['requests'][index]['cancelled'], (
        'I7/I10: project replacement retires the originating native request'
    )


def test_project_disclosure_is_bound_to_the_actual_project_sent_after_switch(ui, signer):
    ui.command('create', name='bound_disclosure_A')
    authenticate(ui, signer)
    earlier = len(ui.last['ui']['disclosures'])
    ui.command('create', name='bound_disclosure_B')
    _, request = begin_request(ui)
    assert 'bound_disclosure_B' in request['body'], (
        'I1/I15: outgoing inference actually describes the selected current project witness'
    )
    fresh = ui.last['ui']['disclosures'][earlier:]
    assert fresh and 'bound_disclosure_B' in json.dumps(fresh, ensure_ascii=False), (
        'I12/I15: outgoing project disclosure is bound to a newly displayed '
        'current-project consent context'
    )


def test_actual_ui_archive_is_bounded_with_many_small_provider_deltas(ui, signer):
    authenticate(ui, signer)
    index, _ = begin_request(ui)
    native_protocol.stream(
        ui,
        index,
        [{'type': 'response.output_text.delta', 'delta': 'x'} for _ in range(513)]
        + [
            {
                'type': 'response.completed',
                'response': {'id': 'bounded', 'status': 'completed', 'output': []},
            }
        ],
    )
    messages = ui.last['ui']['messages']
    assert len(messages) <= 512, (
        'I3/I16: small provider records cannot bypass the complete real UI message-count cap'
    )
    assert (
        len(json.dumps(messages, ensure_ascii=False, separators=(',', ':')).encode()) <= 2097152
    ), (
        'I3/I16: complete real UI rows including payload/metadata fit the '
        'declared archive byte bound'
    )


@pytest.mark.parametrize('sink', ['question', 'option'])
def test_human_question_and_option_captions_are_literal_in_actual_panel(ui, signer, sink):
    authenticate(ui, signer)
    marker = 'UNTRUSTED-' + sink
    payload = literal_payload(ui, marker)
    index, _ = begin_request(ui)
    args = {
        'text': payload if sink == 'question' else 'Choose a public check',
        'options': [
            {
                'id': 'inspect',
                'label': payload if sink == 'option' else 'Inspect',
                'description': 'Read the current state',
            },
            {'id': 'wait', 'label': 'Wait', 'description': 'Leave current state unchanged'},
        ],
        'recommended': 'inspect',
        'allow_free_text': True,
    }
    native_protocol.stream(ui, index, function_events('ask_question', args), width=7)
    assert ui.last['ui']['pending_question'], (
        'I3/I16: the actual nonmutating human hold remains visible after provider completion'
    )
    assert_literal_renderer(ui, marker)


@pytest.mark.parametrize('popup', [False, True], ids=['collapsed', 'popup'])
def test_effort_options_use_reviewed_capabilities_and_ignore_untrusted_catalog_labels(
    ui, signer, popup
):
    marker = 'UNTRUSTED-EFFORT'
    payload = literal_payload(ui, marker)
    ui.catalog = {
        'models': [
            {
                'slug': 'gpt-6.1-sol',
                'display_name': 'Independent model',
                'visibility': 'list',
                'supported_reasoning_efforts': [
                    {'reasoning_effort': 'high', 'display_name': payload}
                ],
                'reasoning_efforts': [payload],
            }
        ]
    }
    authenticate(ui, signer)
    assert ui.last['ui']['available_efforts'] == ['low', 'medium', 'high', 'xhigh', 'max'], (
        'I13/I16: actual effort choices come from the reviewed exact-model capability mapping'
    )
    ui.command('select_effort', id='high')
    if popup:
        ui.command('popup', name='assistant.effort')
    assert not any(marker in text['text'] for text in ui.last['ui']['texts']), (
        'I12/I16: undocumented provider effort labels never enter collapsed or popup renderers'
    )
    before = len(ui.last['requests'])
    ui.command('select_effort', id=payload)
    assert ui.last['ui']['selected_effort'] == 'high' and ui.last['ui']['last_error'], (
        'I13: an unsupported effort selection preserves the valid choice and reports refusal'
    )
    assert len(ui.last['requests']) == before, (
        'I13: malformed effort metadata or selection cannot dispatch inference work'
    )
    assert ui.last['image_requests'] == 0 and ui.last['activated_urls'] == [], (
        'I12: rejecting undocumented effort metadata causes no image or URL side effects'
    )
