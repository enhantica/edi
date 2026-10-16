"""Real Main popup checks under owner 99d50f71f; no provider fixture."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def popup171_owned_environment(captures):
    # Every possible full-actor invocation is deliberately guarded against a
    # bundled/default vendor runtime, including the original popup fixture.
    owned = captures / 'owned-peer'
    owned.mkdir(exist_ok=True)
    executable = owned / 'codex'
    executable.write_text(
        f'#!{sys.executable}\n'
        + (ROOT / 'tests/integration/py/assistant_vm_probe/codex_stdio_peer.py').read_text()
    )
    executable.chmod(0o700)
    config = owned / 'peer-input.json'
    config.write_text(
        json.dumps({
            'scenario': 'fileauth',
            'report_page_reply': True,
            'trace': str(owned / 'original-client-lines.jsonl'),
        })
    )
    environment = {
        **os.environ,
        'QT_QPA_PLATFORM': 'offscreen',
        'QT_QUICK_BACKEND': 'software',
        'EDI_CODEX_DEVELOPMENT_EXECUTABLE': str(executable.resolve()),
        'EDI_TEST_CODEX_PEER_INPUT': str(config.resolve()),
    }
    for key, leaf in [
        ('TMPDIR', 'tmp'),
        ('XDG_CONFIG_HOME', 'config'),
        ('XDG_DATA_HOME', 'data'),
        ('XDG_CACHE_HOME', 'cache'),
    ]:
        directory = owned / leaf
        directory.mkdir(exist_ok=True)
        environment[key] = str(directory.resolve())
    return environment


@pytest.fixture(scope='module')
def popup_receipt(tmp_path_factory):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'I16/popup: coherent real native Quick Test runner is required'
    captures = Path(
        os.environ.get('EDI_ASSISTANT_POPUP_CAPTURE_DIR', tmp_path_factory.mktemp('popup'))
    )
    captures.mkdir(parents=True, exist_ok=True)
    try:
        return subprocess.run(
            [
                str(runner),
                '-input',
                str(Path(__file__).with_name('tst_assistant_popup.qml')),
                'AssistantPopup::test_home_appbar_only_and_no_auto_dismiss',
                'AssistantPopup::test_workflow_same_sidebar_and_live_state',
                'AssistantPopup::test_keyboard_can_return_to_appbar',
                'AssistantPopup::test_focus_restore_uses_current_scope',
                'AssistantPopup::test_navigation_keeps_visible_popup_fixed',
                '-o',
                '-,txt',
            ],
            cwd=captures,
            env=popup171_owned_environment(captures),
            capture_output=True,
            text=True,
            timeout=90,  # Prior whole-actor operational allowance; Qt assertions stay bounded.
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        # subprocess may retain bytes even with text=True. Keep raw evidence and
        # expose it in the unchanged timeout failure; never turn timeout into pass.
        for stream in ('stdout', 'stderr'):
            value = getattr(error, stream) or b''
            raw = value if isinstance(value, bytes) else value.encode('utf-8')
            destination = captures / ('popup-timeout.' + stream + '.log')
            destination.write_bytes(raw)
            error.add_note(
                str(destination) + '\n' + raw.decode('utf-8', errors='backslashreplace')
            )
        raise


@pytest.mark.parametrize(
    'case',
    [
        'test_home_appbar_only_and_no_auto_dismiss',
        'test_workflow_same_sidebar_and_live_state',
        'test_keyboard_can_return_to_appbar',
        'test_focus_restore_uses_current_scope',
        'test_navigation_keeps_visible_popup_fixed',
    ],
)
def test_actual_popup_owner_contract(popup_receipt, case):
    output = popup_receipt.stdout + popup_receipt.stderr
    assert f'PASS   : edi_app::AssistantPopup::{case}(' in output, (
        'I16/popup: genuine Main executes the owner appbar-only sidebar contract: '
        + case
        + '\n'
        + output
    )
    assert 'FAIL!' not in output and popup_receipt.returncode == 0, (
        'I16/popup: all actual popup rows and capture callbacks '
        'complete without a hidden failure\n' + output
    )


def test_report171_real_retained_anchor_navigates_current_main_report(tmp_path):
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'REPORT171 SETUP: coherent actual Main Qt runner required'
    environment = popup171_owned_environment(tmp_path)
    # Declared supported test hover policy, not production/Mac default proof.
    environment['QT_QUICK_CONTROLS_HOVER_ENABLED'] = '1'
    try:
        result = subprocess.run(
            [
                str(runner),
                '-input',
                str(Path(__file__).with_name('tst_assistant_popup.qml')),
                'AssistantPopup::test_report171_chat_anchor_uses_existing_current_report_page',
                '-o',
                '-,txt',
            ],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        for stream in ('stdout', 'stderr'):
            value = getattr(error, stream) or b''
            raw = value if isinstance(value, bytes) else value.encode()
            destination = tmp_path / ('report171-timeout.' + stream + '.log')
            destination.write_bytes(raw)
            error.add_note(str(destination) + '\n' + raw.decode(errors='backslashreplace'))
        raise
    output = result.stdout + result.stderr
    for case in ['current', 'replacement', 'missing', 'disabled', 'protected-other']:
        assert (
            'PASS   : edi_app::AssistantPopup::'
            'test_report171_chat_anchor_uses_existing_current_report_page(' + case + ')'
        ) in output, (
            'REPORT171: real retained anchor executes current-page/guard case '
            + case
            + '\n'
            + output
        )
    assert result.returncode == 0 and 'FAIL!' not in output, (
        'REPORT171: all actual pointer/navigation cases settle within original actor bound\n'
        + output
    )


VISIBLE187_CASES = [
    'default-off', 'analysis-value-free', 'wavelength', 'manual-override',
    'dirty-valid-value', 'dirty-invalid-value', 'dirty-valid-free', 'dirty-invalid-free',
    'dirty-valid-fit', 'dirty-invalid-fit', 'real-fit', 'fit-stop', 'close-owner',
    'unsupported-values', 'unsupported-free', 'unsupported-relations', 'normal-relations',
]


def visible187_script(case):
    """Original requested operations/addresses, never expected numerical fit output."""
    path = 'structure.atom_sites[La].adp_iso'
    other = 'structure.atom_sites[Ba].adp_iso'
    purpose = 'Original requested visible operation ' + case

    def call(tool, call_id, **arguments):
        return {'tool': tool, 'call_id': call_id, 'arguments': {'purpose': purpose, **arguments}}

    identifier = 'visible185-action-' + case
    calls = [call('list_parameters', 'visible185-read-' + case)]
    if case == 'analysis-value-free':
        calls += [
            call('set_parameters', 'visible185-value-' + case,
                 values=[{'path': path, 'value': 0.6}]),
            call('set_free', identifier, flags=[{'path': path, 'free': True}]),
        ]
    elif case.endswith('-fit') or case in {'real-fit', 'fit-stop'}:
        calls.append(call('run_fit', identifier))
    elif case.endswith('-free'):
        flags = [{'path': path, 'free': True}]
        if case == 'unsupported-free':
            flags.append({'path': other, 'free': True})
        calls.append(call('set_free', identifier, flags=flags))
    elif case in {'unsupported-relations', 'normal-relations'}:
        calls.append(call(
            'add_relations', identifier,
            aliases=[{'id': 'visible_original_la', 'path': path},
                     {'id': 'visible_original_ba', 'path': other}],
            constraints=[{'id': 'visible_original_shared',
                          'expression': 'visible_original_ba = visible_original_la',
                          'enabled': True}],
        ))
    else:
        values = [{'path': 'experiment.instrument.setup_wavelength' if case == 'wavelength'
                   else path, 'value': 1.49 if case == 'wavelength' else 0.6}]
        if case == 'unsupported-values':
            values.append({'path': other, 'value': 0.7})
        calls.append(call('set_parameters', identifier, values=values))
    return [calls]


@pytest.mark.parametrize('case', VISIBLE187_CASES)
def test_visible187_real_main_native_input_and_owner(case, tmp_path):  # noqa: PLR0914, PLR0915 -- finite Main/peer evidence in one existing actor
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'VA SETUP: actual freshly coherent Main runner is required'
    environment = popup171_owned_environment(tmp_path)
    environment['QT_QUICK_CONTROLS_HOVER_ENABLED'] = '1'
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config.pop('report_page_reply')
    config.update(scenario='native:script', native_turn_calls=visible187_script(case))
    config_path.write_text(json.dumps(config), encoding='utf-8')
    original_config = config_path.read_bytes()
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::test_visible185_actual_native_manual_interaction:' + case,
            '-o', '-,txt']
    try:
        result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                                text=True, timeout=90, check=False)
    except subprocess.TimeoutExpired as error:
        for stream in ('stdout', 'stderr'):
            value = getattr(error, stream) or b''
            raw = value if isinstance(value, bytes) else value.encode()
            destination = tmp_path / ('visible187-timeout.' + stream + '.log')
            destination.write_bytes(raw)
            error.add_note(str(destination) + '\n' + raw.decode(errors='backslashreplace'))
        raise
    (tmp_path / 'visible187.stdout.log').write_text(result.stdout)
    (tmp_path / 'visible187.stderr.log').write_text(result.stderr)
    (tmp_path / 'visible187-process.json').write_text(json.dumps({
        'argv': argv, 'returncode': result.returncode, 'case': case,
        'original_config_unchanged': original_config == config_path.read_bytes(),
        'actual_frames': sorted(path.name for path in tmp_path.glob('visible185-*.png')),
    }, indent=2))
    output = result.stdout + result.stderr
    expected = ('PASS   : edi_app::AssistantPopup::'
                'test_visible185_actual_native_manual_interaction(' + case + ')')
    assert expected in output and result.returncode == 0 and 'FAIL!' not in output, (
        'VA: actual Main row must execute real model/input/worker/Undo premises and outcomes\n'
        + output
    )
    assert original_config == config_path.read_bytes(), (
        'VA: original prelaunch native operations cannot be rewritten after the peer reads them'
    )
    loaded = json.loads(config_path.with_suffix('.peer-loaded.json').read_text())
    assert loaded['native_turn_calls'] == config['native_turn_calls'], (
        'VA: genuine managed peer consumed the complete original native script'
    )
    trace = Path(config['trace'])
    requests = [json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines()]
    starts = [row for row in requests if row.get('method') == 'turn/start']
    assert len(starts) == 1 and starts[0]['params']['clientUserMessageId'], (
        'VA: one genuinely admitted original input owns native authority without replay'
    )
    assert not any(row.get('method') in {'account/login/start', 'account/logout'}
                   for row in requests), (
        'VA: native input cannot repair a lost account through another login/logout'
    )
    responses = [json.loads(line) for line in trace.with_suffix('.native-replies.jsonl')
                 .read_text().splitlines()]
    expected_calls = config['native_turn_calls'][0]
    if case == 'close-owner':
        assert 1 <= len(responses) <= len(expected_calls), (
            'VA4: actual owner retirement may revoke the old call, never duplicate it'
        )
    else:
        assert len(responses) == len(expected_calls), (
            'VA: every original supported/refused native RPC settles exactly once'
        )
    envelopes = set()
    for response, original in zip(responses, expected_calls, strict=case != 'close-owner'):
        observed = response['original']
        assert observed['params']['callId'] == original['call_id'] and (
            observed['params']['tool'], observed['params']['arguments']
        ) == (original['tool'], original['arguments']), (
            'VA: original call identity, purpose and complete arguments remain canonical'
        )
        assert response['response']['id'] == observed['id'] != original['call_id'], (
            'VA: host answers original reverse envelope, not the item call ID'
        )
        assert observed['id'] not in envelopes, 'VA: each original reverse RPC is answered once'
        envelopes.add(observed['id'])
        content = response['response']['result']['contentItems']
        assert len(content) == 1 and content[0]['type'] == 'inputText', (
            'VA: actual host outcome uses the pinned typed original response channel'
        )
        decoded = json.loads(content[0]['text'])
        if original['call_id'].startswith('visible185-action-') and (
            case.startswith(('dirty-', 'unsupported-'))
        ):
            assert response['response']['result']['success'] is False and (
                decoded['status'] in {'refused', 'unavailable'}
                and isinstance(decoded.get('message'), str) and decoded['message']
            ), 'VA: actual before-write failure is truthful, bounded and never a success'


DRAFT226_CASES = [
    'normal-text-id', 'visible-text-id', 'normal-integer', 'visible-integer',
    'normal-number', 'visible-number', 'normal-partial', 'visible-partial',
    'normal-formatted', 'visible-formatted',
    'normal-text-formatted', 'visible-text-formatted',
]


@pytest.mark.parametrize('case', DRAFT226_CASES)
def test_draft226_common_editor_preserves_real_user_work(case, tmp_path):  # noqa: PLR0914, PLR0915 -- finite Main/wire preservation receipts
    """Actual common editor/focus/core/Undo and original native wire; no guard-property mirror."""
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'DRAFT1 SETUP: actual freshly matching Main consumer required'
    environment = popup171_owned_environment(tmp_path)
    environment['QT_QUICK_CONTROLS_HOVER_ENABLED'] = '1'
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config.pop('report_page_reply')
    call = {'tool': 'set_parameters', 'call_id': 'draft226-action-' + case,
            'arguments': {'purpose': 'Preserve my draft during the requested parameter edit',
                          'values': [{'path': 'structure.cell.length_a'
                                      if case.endswith('text-formatted')
                                      else 'experiment.instrument.setup_wavelength',
                                      'value': 10.4 if case.endswith('text-formatted')
                                      else 1.49}]}}
    config.update(scenario='native:script', native_turn_calls=[[call]])
    config_path.write_text(json.dumps(config), encoding='utf-8')
    original_config = config_path.read_bytes()
    fixture = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project'
    original_files = {str(path.relative_to(fixture)): path.read_bytes()
                      for path in fixture.rglob('*') if path.is_file()}
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::test_draft226_common_editor_preserves_user_work:' + case,
            '-o', '-,txt']
    try:
        result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                                text=True, timeout=90, check=False)
    except subprocess.TimeoutExpired as error:
        for stream in ('stdout', 'stderr'):
            value = getattr(error, stream) or b''
            raw = value if isinstance(value, bytes) else value.encode()
            path = tmp_path / ('draft226-timeout.' + stream + '.log')
            path.write_bytes(raw)
            error.add_note(str(path) + '\n' + raw.decode(errors='backslashreplace'))
        raise
    (tmp_path / 'draft226.stdout.log').write_text(result.stdout)
    (tmp_path / 'draft226.stderr.log').write_text(result.stderr)
    (tmp_path / 'draft226-process.json').write_text(json.dumps({
        'argv': argv, 'returncode': result.returncode, 'case': case,
        'original_config_unchanged': config_path.read_bytes() == original_config,
    }, indent=2))
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'FAIL!' not in output and (
        'PASS   : edi_app::AssistantPopup::test_draft226_common_editor_preserves_user_work('
        + case + ')'
    ) in output, 'DRAFT1: the original actual common-editor/Main row must execute\n' + output
    assert config_path.read_bytes() == original_config, (
        'DRAFT1: prelaunch script remains immutable'
    )
    loaded = json.loads(config_path.with_suffix('.peer-loaded.json').read_text())
    assert loaded['native_turn_calls'] == [[call]], (
        'DRAFT1: real owned peer consumed the exact script'
    )
    trace = Path(config['trace'])
    requests = [json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines()]
    turns = [row for row in requests if row.get('method') == 'turn/start']
    assert len(turns) == 1 and turns[0]['params']['clientUserMessageId'], (
        'DRAFT1: one genuinely admitted original input owns this request'
    )
    assert not any(row.get('method') in {'account/login/start', 'account/logout'}
                   for row in requests), 'DRAFT1: account is never repaired by login/logout'
    replies = [json.loads(line) for line in trace.with_suffix('.native-replies.jsonl')
               .read_text().splitlines()]
    assert len(replies) == 1, 'DRAFT1: original native action receives exactly one response'
    original, response = replies[0]['original'], replies[0]['response']
    assert original['params']['callId'] == call['call_id'] and (
        original['params']['tool'], original['params']['arguments']
    ) == (call['tool'], call['arguments']), (
        'DRAFT1: original native arguments/identity stay canonical'
    )
    assert response['id'] == original['id'] != call['call_id'], (
        'DRAFT1: host answers original reverse envelope rather than call ID'
    )
    content = response['result']['contentItems']
    assert len(content) == 1 and content[0]['type'] == 'inputText'
    outcome = json.loads(content[0]['text'])
    if case.endswith('formatted'):
        assert response['result']['success'] and outcome['status'] == 'edited', (
            'DRAFT1: genuinely unedited formatted field allows real work'
        )
    else:
        assert not response['result']['success'] and (
            outcome['status'] in {'refused', 'unavailable'}
        )
        assert isinstance(outcome.get('message'), str) and outcome['message'], (
            'DRAFT1: actual before-write refusal retains a truthful original-channel explanation'
        )
    assert {str(path.relative_to(fixture)): path.read_bytes()
            for path in fixture.rglob('*') if path.is_file()} == original_files, (
        'DRAFT1: real input/edit/Undo cannot rewrite the independent source fixture'
    )


EXPOSURE229_CASES = [
    'visible-extra', 'visible-filtered', 'visible-offscreen', 'normal-page',
    'assistant-fit-modal', 'manual-fit-modal',
]


@pytest.mark.parametrize('case', EXPOSURE229_CASES)
def test_exposure229_genuine_navigation_filters_and_modal_origin(case, tmp_path):  # noqa: PLR0914, PLR0915 -- one finite actual Main/RPC/worker receipt
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'EXPOSURE SETUP: freshly matching actual Main consumer required'
    environment = popup171_owned_environment(tmp_path)
    environment['QT_QUICK_CONTROLS_HOVER_ENABLED'] = '1'
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config.pop('report_page_reply')
    purpose = 'Original navigation and result presentation request ' + case
    path = ('experiment.preferred_orientation[lbco].march_r'
            if case == 'visible-offscreen' else 'structure.atom_sites[La].adp_iso')
    value = 0.9 if case == 'visible-offscreen' else 0.6
    identifier = 'exposure229-action-' + case
    if case == 'manual-fit-modal':
        calls = []
    elif case == 'assistant-fit-modal':
        calls = [{'tool': 'run_fit', 'call_id': identifier,
                  'arguments': {'purpose': purpose}}]
    else:
        calls = [
            {'tool': 'set_parameters', 'call_id': 'exposure229-value-' + case,
             'arguments': {'purpose': purpose, 'values': [{'path': path, 'value': value}]}},
            {'tool': 'set_free', 'call_id': identifier,
             'arguments': {'purpose': purpose, 'flags': [{'path': path, 'free': True}]}},
        ]
    config.update(scenario='native:script', native_turn_calls=[calls])
    config_path.write_text(json.dumps(config), encoding='utf-8')
    original_config = config_path.read_bytes()
    fixture = ROOT / ('docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project'
                      if case.endswith('fit-modal') else 'tests/fixtures/e04_t1/editable-project')
    original_files = {str(path.relative_to(fixture)): path.read_bytes()
                      for path in fixture.rglob('*') if path.is_file()}
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::test_exposure229_existing_manual_controls:' + case, '-o', '-,txt']
    try:
        result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                                text=True, timeout=90, check=False)
    except subprocess.TimeoutExpired as error:
        for stream in ('stdout', 'stderr'):
            received = getattr(error, stream) or b''
            raw = received if isinstance(received, bytes) else received.encode()
            destination = tmp_path / ('exposure229-timeout.' + stream + '.log')
            destination.write_bytes(raw)
            error.add_note(str(destination) + '\n' + raw.decode(errors='backslashreplace'))
        raise
    (tmp_path / 'exposure229.stdout.log').write_text(result.stdout)
    (tmp_path / 'exposure229.stderr.log').write_text(result.stderr)
    (tmp_path / 'exposure229-process.json').write_text(json.dumps({
        'argv': argv, 'returncode': result.returncode, 'config_unchanged':
        config_path.read_bytes() == original_config}, indent=2))
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'FAIL!' not in output and (
        'PASS   : edi_app::AssistantPopup::test_exposure229_existing_manual_controls('
        + case + ')' in output
    ), 'EXPOSURE: the original actual Main control/RPC/worker case must execute\n' + output
    assert config_path.read_bytes() == original_config, (
        'EXPOSURE: prelaunch original script is immutable'
    )
    assert {str(path.relative_to(fixture)): path.read_bytes()
            for path in fixture.rglob('*') if path.is_file()} == original_files, (
        'EXPOSURE: original independent scientific fixture bytes remain unchanged'
    )
    trace = Path(config['trace'])
    requests = [json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines()]
    starts = [request for request in requests if request.get('method') == 'turn/start']
    assert len(starts) == (0 if case == 'manual-fit-modal' else 1), (
        'EXPOSURE: one actual original input; manual control needs no delegated turn'
    )
    if starts:
        assert starts[0]['params'].get('clientUserMessageId'), (
            'EXPOSURE: actual original input has its own identity'
        )
    assert not any(request.get('method') in {'account/login/start', 'account/logout'}
                   for request in requests), (
        'EXPOSURE: navigation and fitting cannot repair/reset genuine auth'
    )
    reply_path = trace.with_suffix('.native-replies.jsonl')
    replies = ([json.loads(line) for line in reply_path.read_text(encoding='utf-8').splitlines()]
               if reply_path.exists() else [])
    assert len(replies) == len(calls), (
        'EXPOSURE: one actual original response per requested native operation'
    )
    for receipt, expected in zip(replies, calls, strict=True):
        original, response = receipt['original'], receipt['response']
        assert original['params']['tool'] == expected['tool']
        assert original['params']['callId'] == expected['call_id']
        assert original['params']['arguments'] == expected['arguments']
        assert response['id'] == original['id'] != original['params']['callId'], (
            'EXPOSURE: actual original reverse envelope owns the response, not model call ID'
        )
        result = response['result']
        assert result['success'] is True, (
            'EXPOSURE: actual operation is confirmed, never applied_unconfirmed'
        )
        content = result['contentItems']
        assert len(content) == 1 and content[0]['type'] == 'inputText'
        decoded = json.loads(content[0]['text'])
        assert decoded['status'] in (
            {'done', 'max_iterations', 'no_step'} if expected['tool'] == 'run_fit' else {'edited'}
        ), 'EXPOSURE: actual native outcome is truthful; worker success does not imply convergence'
