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
