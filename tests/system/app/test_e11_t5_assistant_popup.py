"""Real Main popup checks under owner 99d50f71f; no provider fixture."""

import hashlib
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
    helper_bytes570 = (ROOT / 'tests/integration/py/assistant_vm_probe/approved_context.py').read_bytes()
    helper570 = owned / 'approved_context.py'
    helper570.write_bytes(helper_bytes570)
    assert helper570.read_bytes() == helper_bytes570, 'CTX570 SETUP: original copied Main peer has its exact shared dependency in the owned launch directory'
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
    # AcceptanceProbe verifies actual fresh Qt test destinations before an engine/Session;
    # the owned invocation path also gives this process a unique Qt application identity.
    environment['EDI_TEST_APP_STORAGE_ROOT'] = str(owned.resolve())
    environment['EDI_TEST_APP_STORAGE_ID'] = 'acceptance-' + hashlib.sha256(
        str(owned.resolve()).encode('utf-8')
    ).hexdigest()
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
    'requested-cell-profile-flags',
]


def visible187_script(case):
    """Original requested operations/addresses, never expected numerical fit output."""
    path = 'structure.atom_sites[La].adp_iso'
    other = 'structure.atom_sites[Ba].adp_iso'
    purpose = 'Original requested visible operation ' + case

    def call(tool, call_id, **arguments):
        return {'tool': tool, 'call_id': call_id, 'arguments': {'purpose': purpose, **arguments}}

    if case == 'requested-cell-profile-flags':
        cells609 = ['structure.cell.length_a', 'structure.cell.length_b',
                    'structure.cell.length_c', 'experiment.instrument.calib_twotheta_offset']
        profiles609 = ['experiment.peak.' + name for name in
                       ('broad_gauss_u', 'broad_gauss_v', 'broad_gauss_w', 'broad_lorentz_y')]
        return [
            [call('list_parameters', 'visible609-read'),
             call('set_free', 'visible609-baseline',
                  flags=[{'path': path, 'free': False} for path in cells609[1:] + profiles609])],
            [call('set_free', 'visible609-cells', flags=[{'path': path, 'free': True} for path in cells609])],
            [call('set_free', 'visible609-profile', flags=[{'path': path, 'free': True} for path in profiles609]),
             call('list_parameters', 'visible609-after')],
        ]

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
    if case == 'manual-override':
        calls += [
            call('inspect_project', 'visible481-fresh'),
            call('set_parameters', 'visible481-later',
                 values=[{'path': path, 'value': 0.7}]),
        ]
    return [calls]


@pytest.mark.parametrize('case', VISIBLE187_CASES)
def test_visible187_real_main_native_input_and_owner(case, tmp_path):  # noqa: PLR0914, PLR0915 -- finite Main/peer evidence in one existing actor
    if case == 'requested-cell-profile-flags':
        from tests.system.app.test_e11_t5_codex_agent import save211_files
        source609 = save211_files(ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project')
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'VA SETUP: actual freshly coherent Main runner is required'
    environment = popup171_owned_environment(tmp_path)
    environment['QT_QUICK_CONTROLS_HOVER_ENABLED'] = '1'
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config.pop('report_page_reply')
    config.update(scenario='native:script', native_turn_calls=visible187_script(case),
                  readonly409=True, vm319_record_packets=True)
    if case == 'manual-override':
        config['relation246_wait_for_usage'] = ['visible481-fresh']
        environment['EDI_ACCEPTANCE_REFERENCE'] = str(Path(config['trace']).parent.resolve())
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
    from tests.system.app.test_e11_t5_codex_agent import readonly409_policy
    readonly409_policy(trace)
    assert len(starts) == (3 if case == 'requested-cell-profile-flags' else 1) and all(
        row['params']['clientUserMessageId'] for row in starts
    ), (
        'VA: one genuinely admitted original input owns native authority without replay'
    )
    interrupts480 = [row for row in requests if row.get('method') == 'turn/interrupt']
    if case != 'close-owner':
        assert len(interrupts480) == (1 if case == 'fit-stop' else 0), (
            'ONLYSTOP480: ordinary/other-window/conflicting input sends NO whole-turn interrupt; explicit status AI Stop sends ONE'
        )
    assert not any(row.get('method') in {'account/login/start', 'account/logout'}
                   for row in requests), (
        'VA: native input cannot repair a lost account through another login/logout'
    )
    responses = [json.loads(line) for line in trace.with_suffix('.native-replies.jsonl')
                 .read_text().splitlines()]
    expected_calls = ([call for turn in config['native_turn_calls'] for call in turn]
                      if case == 'requested-cell-profile-flags' else config['native_turn_calls'][0])
    if case == 'fit-stop':
        originals482 = [row['original']['params'] for row in responses
                        if row['original']['params']['callId'] == 'visible185-action-fit-stop']
        assert len(originals482) == 1, 'STOP482: exact original fit RPC supplies independent scope'
        original_scope482 = originals482[0]
        assert all(type(original_scope482.get(key)) is str and original_scope482[key]
                   for key in ('threadId', 'turnId')), 'STOP482: original fit scope is nonempty typed identity'
        assert interrupts480[0]['params'] == {key: original_scope482[key]
                                             for key in ('threadId', 'turnId')}, (
            'STOP482: sole actual status Stop interrupt targets EXACT original thread/turn, no missing/wrong/extra scope'
        )
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
        if case == 'manual-override':
            actual481 = response['response']['result']
            body481 = json.loads(actual481['contentItems'][0]['text'])
            if original['call_id'] == 'visible185-action-manual-override':
                assert actual481['success'] is False and body481['status'] != 'edited', (
                    'FRESH481: exact old pending numeric write is refused/partial, never silently renewed'
                )
            elif original['call_id'] == 'visible481-fresh':
                assert actual481['success'] is True and isinstance(body481['parameters'], list), (
                    'FRESH481: fresh inspection really returns current parameter facts, not a refusal positive'
                )
                manual481 = [row for row in body481['parameters']
                             if row['path'] == 'structure.atom_sites[La].adp_iso']
                assert len(manual481) == 1 and manual481[0]['free'] is True and manual481[0]['value'] == 0.5, (
                    'FRESH481: actual wire inspection contains literal fixture 0.5 and genuine manual free=true'
                )
            elif original['call_id'] == 'visible481-later':
                assert actual481['success'] is True and body481['status'] == 'edited', (
                    'FRESH481: only separate newly requested 0.7 action succeeds after fresh inspection'
                )
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

    if case == 'requested-cell-profile-flags':
        from tests.system.app.test_e11_t5_codex_agent import save211_files
        assert len(responses) == 5 and all(row['response']['result']['success'] is True for row in responses), (
            'FLAGS609: actual normal setup and BOTH original ON arrays must succeed, not partial/refusal')
        finals609 = [json.loads(row['response']['result']['contentItems'][0]['text'])
                     for row in responses if row['original']['params']['callId'] in {'visible609-cells', 'visible609-profile'}]
        assert len(finals609) == 2 and all(row['status'] == 'edited' and row['complete'] is True
                                         and row['atomic'] is False and row['steps_completed'] == 4 for row in finals609), (
            'FLAGS609: exact complete settled-prefix facts include equal a; requested b/c/V/Y cannot disappear')
        facts609 = [json.loads(line.split('FLAGS609_RESULT ', 1)[1]) for line in result.stdout.splitlines()
                    if 'FLAGS609_RESULT ' in line]
        assert len(facts609) == 1 and facts609[0]['sameOwner'] is True
        assert save211_files(ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project') == source609, (
            'FLAGS609: actual source scientific documents remain byte-exact, no saving or source repair')

    if case == 'manual-override':
        events481 = [json.loads(line) for line in trace.with_suffix('.clear-events.jsonl').read_text().splitlines()]
        waits481 = [row for row in events481 if row['kind'] == 'relation246-waiting-after-edit']
        releases481 = [row for row in events481 if row['kind'] == 'relation246-release-after-observed-settlement']
        assert [row['call_id'] for row in waits481] == ['visible481-fresh'] and (
            [row['call_id'] for row in releases481] == ['visible481-fresh']
        ), 'FRESH481: exactly ONE successful original inspection owns the unchanged public barrier'
        reads481 = {row['id'] for row in requests if row.get('method') == 'account/rateLimits/read'}
        assert releases481[0]['read_id'] in reads481, (
            'FRESH481: genuine original Usage read releases the later action, no fabricated callback'
        )
        assert not trace.with_suffix('.native-wrong-envelope.jsonl').exists(), (
            'FRESH481: no old callback/envelope is replayed or adopted as new write authority'
        )


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


SLIDER231_CASES = [
    'native-platform', 'clean-tab-focus', 'full-precision', 'dirty-valid', 'dirty-invalid',
]


@pytest.mark.parametrize('case', SLIDER231_CASES)
def test_slider231_real_manual_value_display_chart_and_undo(case, tmp_path):  # noqa: PLR0914 -- finite real Main/manual evidence
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'SLIDER SETUP: actual coherent Main consumer required'
    environment = popup171_owned_environment(tmp_path)
    environment['QT_QUICK_CONTROLS_HOVER_ENABLED'] = '1'
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    original_config = config_path.read_bytes()
    fixture = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project'
    original_files = {str(path.relative_to(fixture)): path.read_bytes()
                      for path in fixture.rglob('*') if path.is_file()}
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::test_slider231_real_manual_publication_persists:' + case,
            '-o', '-,txt']
    try:
        result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                                text=True, timeout=90, check=False)
    except subprocess.TimeoutExpired as error:
        for stream in ('stdout', 'stderr'):
            received = getattr(error, stream) or b''
            raw = received if isinstance(received, bytes) else received.encode()
            destination = tmp_path / ('slider231-timeout.' + stream + '.log')
            destination.write_bytes(raw)
            error.add_note(str(destination) + '\n' + raw.decode(errors='backslashreplace'))
        raise
    (tmp_path / 'slider231.stdout.log').write_text(result.stdout, encoding='utf-8')
    (tmp_path / 'slider231.stderr.log').write_text(result.stderr, encoding='utf-8')
    (tmp_path / 'slider231-process.json').write_text(json.dumps({
        'argv': argv, 'returncode': result.returncode,
        'config_unchanged': config_path.read_bytes() == original_config,
    }, indent=2), encoding='utf-8')
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'FAIL!' not in output and (
        'PASS   : edi_app::AssistantPopup::test_slider231_real_manual_publication_persists('
        + case + ')' in output
    ), 'SLIDER: original manual slider/model/display/chart/Undo case must execute\n' + output
    assert config_path.read_bytes() == original_config, 'SLIDER: original owned input is immutable'
    assert {str(path.relative_to(fixture)): path.read_bytes()
            for path in fixture.rglob('*') if path.is_file()} == original_files, (
        'SLIDER: original independent scientific fixture bytes remain unchanged'
    )
    config = json.loads(original_config)
    trace = Path(config['trace'])
    requests = [json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines()]
    methods = [request.get('method') for request in requests]
    required = {'initialize', 'account/read', 'model/list', 'skills/list', 'thread/start'}
    assert required <= set(methods), (
        'SLIDER: actual managed peer genuinely connected through original bootstrap doors'
    )
    assert not any(method in {'turn/start', 'turn/steer', 'account/login/start', 'account/logout'}
                   for method in methods), (
        'SLIDER: genuine manual input needs no delegated turn, native tool or auth repair'
    )
    native = trace.with_suffix('.native-replies.jsonl')
    assert not native.exists() or not native.read_text(encoding='utf-8').strip(), (
        'SLIDER: no native response or hidden agent write substitutes for original slider events'
    )


SL1_233_CASES = [
    'helper-preedit', 'helper-commit', 'helper-key', 'helper-query',
    'gap-preedit', 'gap-commit', 'gap-key', 'gap-query',
]


@pytest.mark.parametrize('case', SL1_233_CASES)
def test_sl1_233_original_focused_input_and_request_retirement(case, tmp_path):  # noqa: PLR0914, PLR0915 -- finite existing Main/RPC/Qt-event evidence
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'SL1 SETUP: fresh matching Main with typed Qt-event fixture required'
    environment = popup171_owned_environment(tmp_path)
    environment['QT_QUICK_CONTROLS_HOVER_ENABLED'] = '1'
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config.pop('report_page_reply')
    gap = case.startswith('gap-')
    call = {
        'tool': 'list_parameters' if gap else 'set_parameters',
        'call_id': 'sl1-233-original-' + case,
        'arguments': {'purpose': 'Preserve original focused user input during ' + case},
    }
    if not gap:
        call['arguments']['values'] = [{'path': 'structure.atom_sites[La].adp_iso', 'value': 0.6}]
    config.update(scenario='native:script', native_turn_calls=[[call]],
                  native_hold_after_calls=True)
    environment['EDI_ACCEPTANCE_REFERENCE'] = str(Path(config['trace']).parent.resolve())
    config_path.write_text(json.dumps(config), encoding='utf-8')
    original_config = config_path.read_bytes()
    fixture = ROOT / 'tests/fixtures/e04_t1/editable-project'
    original_files = {str(path.relative_to(fixture)): path.read_bytes()
                      for path in fixture.rglob('*') if path.is_file()}
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::test_sl1_233_focus_targeted_input_retires_original_work:' + case,
            '-o', '-,txt']
    try:
        result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                                text=True, timeout=90, check=False)
    except subprocess.TimeoutExpired as error:
        for stream in ('stdout', 'stderr'):
            received = getattr(error, stream) or b''
            raw = received if isinstance(received, bytes) else received.encode()
            destination = tmp_path / ('sl1-233-timeout.' + stream + '.log')
            destination.write_bytes(raw)
            error.add_note(str(destination) + '\n' + raw.decode(errors='backslashreplace'))
        raise
    (tmp_path / 'sl1-233.stdout.log').write_text(result.stdout, encoding='utf-8')
    (tmp_path / 'sl1-233.stderr.log').write_text(result.stderr, encoding='utf-8')
    (tmp_path / 'sl1-233-process.json').write_text(json.dumps({
        'argv': argv, 'returncode': result.returncode,
        'config_unchanged': config_path.read_bytes() == original_config,
    }, indent=2), encoding='utf-8')
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'FAIL!' not in output and (
        'PASS   : edi_app::AssistantPopup::'
        'test_sl1_233_focus_targeted_input_retires_original_work('
        + case + ')' in output
    ), 'SL1: actual original focus-event/Main/retirement case must execute\n' + output
    assert config_path.read_bytes() == original_config, (
        'SL1: prelaunch original script is immutable'
    )
    assert {str(path.relative_to(fixture)): path.read_bytes()
            for path in fixture.rglob('*') if path.is_file()} == original_files, (
        'SL1: original independent scientific fixture bytes remain unchanged'
    )
    requests = [json.loads(line) for line in Path(config['trace']).read_text(
        encoding='utf-8').splitlines()]
    starts = [request for request in requests if request.get('method') == 'turn/start']
    assert len(starts) == 1 and starts[0]['params'].get('clientUserMessageId'), (
        'SL1: one actual original admitted user objective, never fabricated pending work'
    )
    assert not any(request.get('method') in {'account/login/start', 'account/logout'}
                   for request in requests), (
        'SL1: original input retirement cannot repair/reset auth'
    )
    interrupts = [request for request in requests if request.get('method') == 'turn/interrupt']
    assert len(interrupts) == 1, (
        'ONLYSTOP480: each held original turn has exactly ONE interrupt authorized by its genuine sidebar/status AI Stop'
    )
    stop_receipts480 = [json.loads(line.split('ONLYSTOP480_NATIVE ', 1)[1])
                        for line in output.splitlines() if 'ONLYSTOP480_NATIVE ' in line]
    assert len(stop_receipts480) == 1 and stop_receipts480[0]['case'] == case and (
        stop_receipts480[0]['clicks'] == 1 and stop_receipts480[0]['preStopInterrupts'] == 0
        and stop_receipts480[0]['sameOwner'] is True
        and stop_receipts480[0]['controller'] is True
        and stop_receipts480[0]['stop'] == ('assistant.stop' if case == 'gap-query'
                                           else 'assistant.stopVisibleAction')
    ), 'ONLYSTOP480: SAME original native case proves zero prior wire interrupts and one explicit Stop input'
    replies = [json.loads(line) for line in Path(config['trace']).with_suffix(
        '.native-replies.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(replies) == 1, 'SL1: exact original reverse RPC settles once'
    original, response = replies[0]['original'], replies[0]['response']
    assert all(type(original['params'].get(key)) is str and original['params'][key]
               for key in ('threadId', 'turnId')), 'STOP482: independently captured original reverse RPC scope is nonempty and typed'
    assert interrupts[0]['params'] == {key: original['params'][key]
                                     for key in ('threadId', 'turnId')}, (
        'STOP482: sole sidebar/status Stop interrupt targets original RPC thread/turn EXACTLY, never the permissive peer default'
    )
    assert original['params']['tool'] == call['tool']
    assert original['params']['callId'] == call['call_id']
    assert original['params']['arguments'] == call['arguments']
    assert response['id'] == original['id'] != call['call_id'], (
        'SL1: original response envelope identity is distinct from model-provided call ID'
    )
    returned = response['result']
    assert len(returned['contentItems']) == 1
    assert returned['contentItems'][0]['type'] == 'inputText'
    decoded = json.loads(returned['contentItems'][0]['text'])
    if gap:
        assert returned['success'] is True and isinstance(decoded.get('parameters'), list) and (
            len(decoded['parameters']) > 0
        ), (
            'SL1 GAP: completed original read remains truthful during request retirement'
        )
    else:
        assert returned['success'] is False and isinstance(decoded.get('status'), str) and (
            decoded['status'] != 'edited' and isinstance(decoded.get('message'), str)
            and decoded['message']
        ), (
            'SL1 HELPER: original retirement cannot claim a cancelled scientific edit'
        )


@pytest.mark.parametrize('case', ['manual-shared', 'manual-varied', 'zero-new-aliases'])
def test_relation245_real_shared_manual_form_apply_and_one_undo(case, tmp_path):
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'REL SETUP: actual coherent Main runner is required'
    environment = popup171_owned_environment(tmp_path)
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config.pop('report_page_reply')
    config.update(scenario='native:script', native_turn_calls=[])
    config_path.write_text(json.dumps(config), encoding='utf-8')
    original_config = config_path.read_bytes()
    fixture = ROOT / 'tests/fixtures/e04_t1/editable-project'
    original_files = {str(path.relative_to(fixture)): path.read_bytes()
                      for path in fixture.rglob('*') if path.is_file()}
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::test_relation245_actual_shared_manual_append:' + case, '-o', '-,txt']
    try:
        result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                                text=True, timeout=90, check=False)
    except subprocess.TimeoutExpired as error:
        for stream in ('stdout', 'stderr'):
            received = getattr(error, stream) or b''
            raw = received if isinstance(received, bytes) else received.encode()
            destination = tmp_path / ('relation245-timeout.' + stream + '.log')
            destination.write_bytes(raw)
            error.add_note(str(destination) + '\n' + raw.decode(errors='backslashreplace'))
        raise
    (tmp_path / 'relation245.stdout.log').write_text(result.stdout)
    (tmp_path / 'relation245.stderr.log').write_text(result.stderr)
    (tmp_path / 'relation245-process.json').write_text(json.dumps({
        'argv': argv, 'returncode': result.returncode}, indent=2))
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'FAIL!' not in output and (
        'PASS   : edi_app::AssistantPopup::test_relation245_actual_shared_manual_append('
        + case + ')' in output
    ), 'REL: the original genuine manual staging/Apply/Undo/science case executes\n' + output
    assert config_path.read_bytes() == original_config, (
        'REL: one-time peer input remains unchanged'
    )
    assert {str(path.relative_to(fixture)): path.read_bytes()
            for path in fixture.rglob('*') if path.is_file()} == original_files, (
        'REL: real manual control does not rewrite independent scientific fixture bytes'
    )
    requests = [json.loads(line) for line in
                Path(config['trace']).read_text(encoding='utf-8').splitlines()]
    assert not any(request.get('method') in {
        'turn/start', 'account/login/start', 'account/logout'} for request in requests), (
        'REL: ordinary form shares the editor without delegated work or fabricated auth repair'
    )


RELATION246_CASES = [
    'owner-fit', 'varied-batch', 'zero-new-aliases', 'staged-draft',
    'stop', 'manual-takeover', 'resolved', 'cleanup-successor',
]


def relation246_script(case):
    purpose = 'Original complete same-site relation request ' + case
    arguments = {
        'purpose': purpose,
        'aliases': [
            {'id': 'rel246_la', 'path': 'structure.atom_sites[La].adp_iso'},
            {'id': 'rel246_ba', 'path': 'structure.atom_sites[Ba].adp_iso'},
        ],
        'constraints': [
            {'id': 'rel246_shared', 'expression': 'rel246_ba = rel246_la', 'enabled': True},
        ],
    }
    if case == 'varied-batch':
        arguments['aliases'].append({
            'id': 'rel246_co', 'path': 'structure.atom_sites[Co].adp_iso',
        })
        arguments['constraints'].append({
            'id': 'rel246_disabled', 'expression': 'rel246_co = 0.8', 'enabled': False,
        })
    if case == 'zero-new-aliases':
        arguments['aliases'] = []
    original = {'tool': 'add_relations', 'call_id': 'relation246-' + case,
                'arguments': arguments}
    calls = [original]
    if case == 'owner-fit':
        calls += [
            {'tool': 'set_free', 'call_id': 'relation246-free', 'arguments': {
                'purpose': purpose, 'flags': [
                    {'path': 'structure.atom_sites[La].adp_iso', 'free': True},
                ]}},
            {'tool': 'run_fit', 'call_id': 'relation246-fit', 'arguments': {'purpose': purpose}},
            {'tool': 'diagnostics', 'call_id': 'relation246-diagnostics',
             'arguments': {'purpose': purpose}},
        ]
    return calls


def relation253_owner_process_budget(calls):
    """Process backstop: sum this composed case's existing bounded windows.

    Ui.click's six fixed waits total18s, with an extra2s for names containing
    .tab.; rendered is2s+2s+QtTest's declared5s render default. Counts below
    include genuine manual preparation, three possible result Undos and normal
    init/cleanup. This does not extend any QML wait or production deadline.
    """
    arguments = calls[0]['arguments']
    texts = [text for row in arguments['aliases'] for text in (row['id'], row['path'])]
    texts += [text for row in arguments['constraints']
              for text in (row['id'], row['expression'])]
    relation_ms = 10000 + 1100 * (
        3 + 5 * (len(arguments['aliases']) + len(arguments['constraints']))
    ) + 100 * sum(len(text) + 4 for text in texts)
    free_path = calls[1]['arguments']['flags'][0]['path']
    free_ms = 10000 + 5 * 1100 + 100 * (4 + len(free_path)) + 2 * 500
    windows = {
        'manual_preparation_and_undo_ui_clicks': 25 * 18000,
        'ui_tab_checked_waits': 7 * 2000,
        'rendered_calls_including_init_and_cleanup': 16 * (2000 + 2000 + 5000),
        'instrument_group_discovery_and_expansion': 2 * 2000,
        'actual_bootstrap_readiness': 2 * 2000,
        'initial_prior_apply_and_postfit_science': 3 * 10000,
        'init_cleanup_project_selection': 3 * 2000,
        'body_and_conditional_cleanup_popup_visibility': 8000,
        # Two actual edit-settlement barriers, then unchanged aggregate wait.
        'original_composed_operation_observations': 3 * relation_ms + free_ms + 10000,
    }
    return {'windows_ms': windows, 'relation_observation_ms': relation_ms,
            'free_observation_ms': free_ms,
            'process_ms': max(90000, sum(windows.values()))}


@pytest.mark.parametrize('case', RELATION246_CASES)
def test_relation246_original_native_gui_science_and_retirement(case, tmp_path):  # noqa: PLR0912, PLR0914, PLR0915 -- finite original Main/RPC/worker receipts
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'REL RPC SETUP: genuinely matching Main consumer required'
    environment = popup171_owned_environment(tmp_path)
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config.pop('report_page_reply')
    calls = relation246_script(case)
    config.update(scenario='native:script', native_turn_calls=[calls])
    if case == 'owner-fit':
        config['relation246_wait_for_usage'] = [calls[0]['call_id'], 'relation246-free']
    if case == 'resolved':
        config['relation246_resolve_on_usage'] = calls[0]['call_id']
        config['native_hold_after_calls'] = True
    if case == 'cleanup-successor':
        successor = {**calls[0], 'call_id': 'relation246-successor'}
        config.update(native_turn_calls=[calls, [successor]], native_after_steer=[successor],
                      native_steer_count=1, native_hold_after_calls=True)
    config_path.write_text(json.dumps(config), encoding='utf-8')
    original_config = config_path.read_bytes()
    fixture = ROOT / 'tests/fixtures/e04_t1/editable-project'
    original_files = {str(path.relative_to(fixture)): path.read_bytes()
                      for path in fixture.rglob('*') if path.is_file()}
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::test_relation246_original_rpc_full_gui:' + case, '-o', '-,txt']
    process_seconds = 90
    if case == 'owner-fit':
        budget = relation253_owner_process_budget(calls)
        (tmp_path / 'relation253-process-budget.json').write_text(json.dumps(budget, indent=2))
        process_seconds = budget['process_ms'] / 1000
    try:
        result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                                text=True, timeout=process_seconds, check=False)
    except subprocess.TimeoutExpired as error:
        for stream in ('stdout', 'stderr'):
            received = getattr(error, stream) or b''
            raw = received if isinstance(received, bytes) else received.encode()
            destination = tmp_path / ('relation246-timeout.' + stream + '.log')
            destination.write_bytes(raw)
            error.add_note(str(destination) + '\n' + raw.decode(errors='backslashreplace'))
        raise
    (tmp_path / 'relation246.stdout.log').write_text(result.stdout, encoding='utf-8')
    (tmp_path / 'relation246.stderr.log').write_text(result.stderr, encoding='utf-8')
    (tmp_path / 'relation246-process.json').write_text(json.dumps({
        'argv': argv, 'returncode': result.returncode}, indent=2), encoding='utf-8')
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'FAIL!' not in output and (
        'PASS   : edi_app::AssistantPopup::test_relation246_original_rpc_full_gui('
        + case + ')' in output
    ), 'REL RPC: original actual GUI/science/interruption premises and outcomes execute\n' + output
    # Independent literal four-column measured-data loop of this committed fixture,
    # not a second invocation of Edi's reader or a producer-generated golden.
    measurement = original_files['experiments/hrpt.edi'].decode().split(
        '_data.intensity_meas_su\n', 1)[1]
    expected_observations = [[float(parts[0]), float(parts[2]), float(parts[3])]
                             for line in measurement.splitlines() if (parts := line.split())]
    observed_lines = [line.split('qml: RELATION246_INPUT ', 1)[1]
                      for line in result.stdout.splitlines() if 'qml: RELATION246_INPUT ' in line]
    assert len(observed_lines) == 1, 'REL INPUT SETUP: one actual independent input readback'
    assert json.loads(observed_lines[0])['observations'] == expected_observations, (
        'REL INPUT: every original measurement coordinate/intensity/literal sigma is preserved'
    )
    assert config_path.read_bytes() == original_config, (
        'REL RPC: prelaunch original script remains immutable after one-time process load'
    )
    loaded = json.loads(config_path.with_suffix('.peer-loaded.json').read_text(encoding='utf-8'))
    assert loaded['native_turn_calls'] == config['native_turn_calls'], (
        'REL RPC: ordinary peer actually consumed the original prelaunch script'
    )
    assert {str(path.relative_to(fixture)): path.read_bytes()
            for path in fixture.rglob('*') if path.is_file()} == original_files, (
        'REL RPC: original independent science/input/recipe bytes are never rewritten'
    )
    trace = Path(config['trace'])
    requests = [json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines()]
    inputs = [request for request in requests
              if request.get('method') in {'turn/start', 'turn/steer'}]
    assert len(inputs) == (2 if case == 'cleanup-successor' else 1), (
        'REL RPC: exactly the genuine original objective and explicit successor, no invented work'
    )
    assert all(request['params'].get('clientUserMessageId') for request in inputs), (
        'REL RPC: each actual admitted original input retains its identity'
    )
    assert not any(request.get('method') in {'account/login/start', 'account/logout'}
                   for request in requests), 'REL RPC: actual work never fabricates account repair'
    reply_path = trace.with_suffix('.native-replies.jsonl')
    replies = ([json.loads(line) for line in reply_path.read_text(encoding='utf-8').splitlines()]
               if reply_path.exists() else [])
    expected = [] if case == 'resolved' else calls
    if case == 'cleanup-successor':
        expected = [calls[0], successor]
    assert len(replies) == len(expected), 'REL RPC: every original live request settles once'
    assert len({row['response']['id'] for row in replies}) == len(replies), (
        'REL RPC: original envelopes cannot be answered twice across stage/cleanup/steer'
    )
    for receipt, call in zip(replies, expected, strict=True):
        original, response = receipt['original'], receipt['response']
        assert original['params']['tool'] == call['tool'], (
            'REL RPC: original canonical tool survives'
        )
        assert original['params']['callId'] == call['call_id'], (
            'REL RPC: original call identity survives staging and retirement'
        )
        assert original['params']['arguments'] == call['arguments'], (
            'REL RPC: full original purpose/arguments remain canonical'
        )
        assert response['id'] == original['id'] != call['call_id'], (
            'REL RPC: actual reverse envelope owns the response, never a model call ID substitute'
        )
        returned = response['result']
        assert len(returned['contentItems']) == 1, 'REL RPC: one original typed native result'
        assert returned['contentItems'][0]['type'] == 'inputText', (
            'REL RPC: original public result uses the real typed inputText envelope'
        )
        decoded = json.loads(returned['contentItems'][0]['text'])
        cancelled = case in {'stop', 'manual-takeover', 'staged-draft'} or (
            case == 'cleanup-successor' and call['call_id'] == calls[0]['call_id'])
        if cancelled:
            assert returned['success'] is False and decoded.get('status') != 'edited' and (
                isinstance(decoded.get('message'), str) and decoded['message']
            ), 'REL RPC: refused/retired original work cannot claim a committed edit'
        else:
            assert returned['success'] is True, (
                'REL RPC: genuine complete publication must not be applied_unconfirmed/refused'
            )
            if call['tool'] == 'run_fit':
                assert decoded['status'] in {'done', 'max_iterations', 'no_step'}, (
                    'REL RPC: actual fit outcome is not an unavailable/error substitute'
                )
            elif call['tool'] == 'diagnostics':
                assert 'diagnostics' in decoded, 'REL RPC: actual original diagnostics is returned'
            else:
                assert decoded['status'] == 'edited', 'REL RPC: scientific edit is fully confirmed'
    wrong = trace.with_suffix('.native-wrong-envelope.jsonl')
    assert not wrong.exists() or not wrong.read_text(encoding='utf-8').strip(), (
        'REL RPC: no original reply may arrive after server resolution or under the wrong envelope'
    )
    if case == 'resolved':
        events = [json.loads(line) for line in trace.with_suffix('.clear-events.jsonl').read_text(
            encoding='utf-8').splitlines()]
        resolved = [event for event in events if event['kind'] == 'relation246-original-resolved']
        assert len(resolved) == 1 and resolved[0]['call_id'] == calls[0]['call_id'], (
            'REL RESOLVE SETUP: genuine pending original resolution is actually emitted'
        )
        assert resolved[0]['arguments'] == calls[0]['arguments'], (
            'REL RESOLVE: actual original canonical arguments/identity survive public cancellation'
        )

    if case == 'owner-fit':
        events = [json.loads(line) for line in trace.with_suffix('.clear-events.jsonl').read_text(
            encoding='utf-8').splitlines()]
        waits = [event for event in events if event['kind'] == 'relation246-waiting-after-edit']
        releases = [event for event in events
                    if event['kind'] == 'relation246-release-after-observed-settlement']
        expected_barriers = [calls[0]['call_id'], 'relation246-free']
        assert [row['call_id'] for row in waits] == expected_barriers, (
            'REL OWNER SETUP: both exact original edits replied before public readiness release'
        )
        assert [row['call_id'] for row in releases] == expected_barriers, (
            'REL OWNER SETUP: actual optional reads release both original calls once'
        )
        optional = {row['id'] for row in requests
                    if row.get('method') == 'account/rateLimits/read'}
        assert all(row['read_id'] in optional for row in releases), (
            'REL OWNER SETUP: actual public requests supply release events, never invented state'
        )
        observed_ready = [json.loads(line.split('qml: RELATION246_SETTLED ', 1)[1])
                          for line in result.stdout.splitlines()
                          if 'qml: RELATION246_SETTLED ' in line]
        assert [row['callId'] for row in observed_ready] == expected_barriers and all(
            not row['calculating'] and row['computedCurrent'] and row['currentOwner']
            and row['canCancel'] and row['showingActions']
            for row in observed_ready
        ), 'REL OWNER SETUP: both actual original scientific settlement snapshots are retained'
        assert all(release['observed_at_ms'] >= ready['observedAtMs']
                   for release, ready in zip(releases, observed_ready, strict=True)), (
            'REL OWNER SETUP: earlier automatic reads cannot impersonate readiness release'
        )


IMPORT267_CASES = [
    'manual-no-owner', 'manual-saved-empty', 'visible-no-owner', 'visible-saved-empty',
    'visible-stop', 'visible-manual-input', 'visible-close', 'visible-new-owner',
    'visible-source-refusal-close',
]


def import267_recipe():
    """Independent original PbSO4/CW recipe, same explicit14 fields as the Qt actor."""
    return {
        'project_name': 'Original measured PbSO4', 'description': 'Original typed independent import',
        'experiment_name': 'd1a', 'sample_form': 'powder', 'beam_mode': 'constant wavelength',
        'radiation_probe': 'neutron', 'scattering_type': 'bragg',
        'peak_profile': 'cwl-tch-pseudo-voigt', 'wavelength': 1.909, 'zero_offset': -0.001,
        'phase_scale': 1, 'background': [{'position': 10, 'intensity': 200},
                                      {'position': 155.85, 'intensity': 200}],
        'exclusions': [{'first': 10, 'second': 11}, {'first': 155, 'second': 155.85}],
        'initial_parameters': [{'path': path, 'value': value} for path, value in [
            ('experiment.peak.broad_gauss_u', 0.1), ('experiment.peak.broad_gauss_v', 0),
            ('experiment.peak.broad_gauss_w', 0.1), ('experiment.peak.broad_lorentz_x', 0),
            ('experiment.peak.broad_lorentz_y', 0.1)]],
    }


def import267_process_budget(recipe):
    """Existing90s Main envelope plus this finite original public paced workload."""
    def spelling(value):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    texts = [recipe[key] for key in ['project_name', 'experiment_name', 'description']]
    texts += [spelling(recipe[key]) for key in ['wavelength', 'zero_offset', 'phase_scale']]
    for row in recipe['background']:
        texts += [spelling(row['position']), spelling(row['intensity'])]
    for row in recipe['exclusions']:
        texts += [spelling(row['first']), spelling(row['second'])]
    for row in recipe['initial_parameters']:
        texts += [row['path'], spelling(row['value'])]
    rows = sum(len(recipe[key]) for key in ['background', 'exclusions', 'initial_parameters'])
    clicks = 3 + 1 + 3 + 3 + len(texts) + rows + 1
    scalar_keys = sum(len(text) + 2 for text in texts)
    combo_keys = (2 + 1) + (2 + 1) + (2 + 5)
    paced = clicks * (500 + 100 + 500) + 100 * (scalar_keys + combo_keys)
    return {'ordinary_process_ms': 90000, 'paced_clicks': clicks, 'scalar_keys': scalar_keys,
            'combo_keys': combo_keys, 'public_paced_workload_ms': paced,
            'process_ms': 90000 + paced,
            'provenance': 'Existing Main wrapper90s; public237 helper move500/press100/relax500/scalar100; complete literal recipe/controls. No production deadline or Qt assertion bound changed.'}


@pytest.mark.parametrize('case', IMPORT267_CASES)
def test_import267_real_main_manual_visible_creation_and_retirement(case, tmp_path):
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'IMPORT267 SETUP: genuinely matching actual Main Qt consumer required'
    environment = popup171_owned_environment(tmp_path)
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text())
    config.pop('report_page_reply')
    manual = case in {'manual-no-owner', 'manual-saved-empty'}
    cancelled = not manual and case not in {'visible-no-owner', 'visible-saved-empty'}
    recipe = import267_recipe()
    calls = [
        {'tool': 'inspect_project', 'call_id': 'import265-before-' + case,
         'arguments': {'purpose': 'Inspect original genuinely selected import source addresses'}},
        {'tool': 'create_cwl_project', 'call_id': 'import265-create-' + case,
         'arguments': {'purpose': 'Import the original selected PbSO4 and measured XYE through actual controls',
                       'cif_file_id': {'$original_selected_name': 'PbSO4-Wyckoff.cif'},
                       'data_file_id': {'$original_selected_name': 'observed.xye'}, 'recipe': recipe}},
    ]
    if not manual:
        config.update(scenario='native:script', native_turn_calls=[calls], native_import267=True)
    config_path.write_text(json.dumps(config))
    original_config = config_path.read_bytes()
    originals = [ROOT / 'tests/fixtures/assistant/reference/PbSO4-Wyckoff.cif',
                 Path('/tmp/relay-e11-t5-tests/seq85-private/inputs/observed.xye')]
    original_bytes = [path.read_bytes() for path in originals]
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::test_import265_actual_manual_and_visible_creation:' + case,
            '-o', '-,txt']
    budget = import267_process_budget(recipe)
    (tmp_path / 'import267-budget.json').write_text(json.dumps(budget, indent=2))
    try:
        result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                                text=True, timeout=90 if manual else budget['process_ms'] / 1000,
                                check=False)
    except subprocess.TimeoutExpired as error:
        for stream in ['stdout', 'stderr']:
            value = getattr(error, stream) or b''
            raw = value if isinstance(value, bytes) else value.encode('utf-8')
            destination = tmp_path / ('import267-timeout.' + stream + '.log')
            destination.write_bytes(raw)
            error.add_note(str(destination) + '\n' + raw.decode(errors='backslashreplace'))
        raise
    (tmp_path / 'import267.stdout.log').write_text(result.stdout)
    (tmp_path / 'import267.stderr.log').write_text(result.stderr)
    (tmp_path / 'import267-process.json').write_text(json.dumps({'argv': argv,
        'returncode': result.returncode, 'case': case, 'budget': budget}, indent=2))
    output = result.stdout + result.stderr
    assert not any('NativeCwlImportDialog.qml:' in line and (
        'Cannot assign [undefined] to QString' in line
    ) for line in output.splitlines()), (
        'IMPORT285: genuine import row loading never assigns undefined text to a QString control\n' + output
    )
    assert result.returncode == 0 and 'FAIL!' not in output and (
        'PASS   : edi_app::AssistantPopup::test_import265_actual_manual_and_visible_creation('
        + case + ')' in output
    ), 'IMPORT267: genuine Main form/native/retirement/science/Undo premises must execute\n' + output
    assert config_path.read_bytes() == original_config and (
        [path.read_bytes() for path in originals] == original_bytes
    ), 'IMPORT267: complete original prelaunch objective and immutable input bytes are unchanged'
    trace = Path(config['trace'])
    if manual:
        assert not trace.exists() and not config_path.with_suffix('.peer-pid').exists(), (
            'IMPORT267: genuine offline manual form never silently starts a provider peer'
        )
    else:
        loaded = json.loads(config_path.with_suffix('.peer-loaded.json').read_text())
        assert loaded['native_turn_calls'] == [calls], (
            'IMPORT267: actual process consumes the complete original script before any RPC'
        )
        requests = [json.loads(line) for line in trace.read_text().splitlines()]
        assert len([x for x in requests if x.get('method') == 'turn/start']) == 1, (
            'IMPORT267: one original admitted user objective owns this actual creation attempt'
        )
        assert not any(x.get('method') in {'account/login/start', 'account/logout'} for x in requests), (
            'IMPORT267: scientific staging never repairs/replaces the original managed account'
        )
        replies = [json.loads(line) for line in trace.with_suffix('.native-replies.jsonl').read_text().splitlines()]
        assert len(replies) == 2 and len({x['response']['id'] for x in replies}) == 2, (
            'IMPORT270: settled preserved-process staging answers BOTH original reverse RPCs exactly once'
        )
        first = replies[0]
        assert first['original']['params']['callId'] == calls[0]['call_id'] and first['response']['result']['success'], (
            'IMPORT267 SETUP: original public inspect discloses actual selected IDs before creation'
        )
        disclosed = json.loads(first['response']['result']['contentItems'][0]['text'])['selected_files']['files']
        selected = {name: [x['id'] for x in disclosed if x['name'] == name and x['text_readable']]
                    for name in ['PbSO4-Wyckoff.cif', 'observed.xye']}
        assert all(len(value) == 1 for value in selected.values()), (
            'IMPORT267 SETUP: original disclosed source addresses are unique and readable'
        )
        emitted = [json.loads(line) for line in trace.with_suffix('.native-emitted.jsonl').read_text().splitlines()]
        assert len(emitted) == 2 and len({row['id'] for row in emitted}) == 2 and [
            row['params']['callId'] for row in emitted
        ] == [row['call_id'] for row in calls], (
            'IMPORT267: exactly the two actual original RPCs were genuinely emitted before response/adoption checks'
        )
        assert emitted[1]['params']['tool'] == 'create_cwl_project' and (
            emitted[1]['params']['arguments'] == {**calls[1]['arguments'],
                'cif_file_id': selected['PbSO4-Wyckoff.cif'][0],
                'data_file_id': selected['observed.xye'][0]}
        ), 'IMPORT267: staged creation carries original complete recipe and genuine disclosed current IDs'
        if len(replies) == 2:
            original, response = replies[1]['original'], replies[1]['response']
            assert original['params']['callId'] == calls[1]['call_id'] and (
                original['params']['tool'] == 'create_cwl_project'
                and original['params']['arguments'] == {**calls[1]['arguments'],
                    'cif_file_id': selected['PbSO4-Wyckoff.cif'][0],
                    'data_file_id': selected['observed.xye'][0]}
                and response['id'] == original['id']
            ), 'IMPORT267: original opaque addresses/complete recipe/purpose and RPC envelope remain canonical'
            outcome = json.loads(response['result']['contentItems'][0]['text'])
            if cancelled:
                assert not response['result']['success'] and not outcome.get('adopted'), (
                    'IMPORT267: genuinely retired pre-Apply stage never claims scientific success'
                )
            else:
                assert response['result']['success'] and outcome['adopted'] and outcome['presentation_complete'] and (
                    outcome['status'] == ('completed' if case.endswith('saved-empty') else 'created')
                ), (
                    'IMPORT267: actual original host result proves adoption and complete presentation'
                )
    if not cancelled:
        observations = [json.loads(line.split('qml: IMPORT265_INPUT ', 1)[1])
                        for line in result.stdout.splitlines() if 'qml: IMPORT265_INPUT ' in line]
        expected = [list(map(float, line.split())) for line in original_bytes[1].decode().splitlines()
                    if line.strip() and not line.lstrip().startswith('#')]
        assert len(observations) == 1 and observations[0]['observations'] == expected, (
            'IMPORT267: every actual measured coordinate/intensity/original supplied sigma matches immutable source'
        )
        original_blocks = [line.strip()[5:] for line in original_bytes[0].decode().splitlines()
                           if line.strip().lower().startswith('data_')]
        assert original_blocks == ['pbso4-phase'], (
            'IMPORT281 SETUP: immutable original CIF declares exactly its known nonempty datablock key'
        )
        assert observations[0]['weight'] == 1 and observations[0]['links'] == [[original_blocks[0], True]], (
            'IMPORT267: real imported measured dataset keeps its sole original enabled phase and unit weight'
        )


@pytest.mark.parametrize('case', ['manual-add', 'manual-update', 'manual-remove', 'visible-add-cw',
    'visible-update-tof', 'visible-remove', 'stop', 'manual-takeover', 'preexisting-draft', 'new-owner'])
def test_background285_actual_main_stage_and_original_rpc(case, tmp_path):
    from tests.system.app.test_e11_t5_codex_agent import background285_fixture
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'BG SETUP: actual coherent normal Main Qt consumer is required'
    environment = popup171_owned_environment(tmp_path)
    environment['EDI_ACCEPTANCE_REFERENCE'] = str(tmp_path)
    source = background285_fixture(tmp_path, 'tof' if case == 'visible-update-tof' else 'cw')
    original = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()}
    manual = case in {'manual-add', 'manual-update', 'manual-remove'}
    operation = 'remove' if case in {'manual-remove', 'visible-remove'} else (
        'update' if case in {'manual-update', 'visible-update-tof'} else 'add')
    args = {'purpose': 'Original independently requested defined background edit',
            'experiment': 'experiment', 'operation': operation,
            'id': 'p1' if operation != 'add' else 'native-bg-original'}
    if operation != 'remove':
        args.update(position=4200.0 if case == 'visible-update-tof' else 21.5 if operation == 'update' else 32.5,
                    intensity=19.75, free=True)
    calls = [{'tool': 'edit_background', 'call_id': 'background285-' + case, 'arguments': args}]
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text());config.pop('report_page_reply')
    if not manual: config.update(scenario='native:script', native_turn_calls=[calls])
    config_path.write_text(json.dumps(config));original_config = config_path.read_bytes()
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::test_background285_real_stage_and_original_rpc:' + case, '-o', '-,txt']
    # Existing90s Main transport allowance; new single-operation observation is
    # independently derived in the actor, without changing unrelated bounds.
    result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                            text=True, timeout=90, check=False)
    (tmp_path / 'background285.stdout.log').write_text(result.stdout)
    (tmp_path / 'background285.stderr.log').write_text(result.stderr)
    (tmp_path / 'background285-process.json').write_text(json.dumps({'argv': argv, 'returncode': result.returncode}, indent=2))
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'FAIL!' not in output and (
        'PASS   : edi_app::AssistantPopup::test_background285_real_stage_and_original_rpc(' + case + ')' in output
    ), 'BG: genuine Main original stage/events/science/currentness/Undo assertions all execute\n' + output
    assert config_path.read_bytes() == original_config and original == {
        str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()
    }, 'BG: original complete request and every input scientific file remain byte-exact'
    trace = Path(config['trace'])
    if manual:
        assert not trace.exists() and not config_path.with_suffix('.peer-pid').exists(), (
            'BG: ordinary manual stage needs no provider connection or fake account'
        )
        return
    loaded = json.loads(config_path.with_suffix('.peer-loaded.json').read_text())
    assert loaded['native_turn_calls'] == [calls], (
        'BG: actual owned process consumes the whole predeclared original request before bootstrap'
    )
    requests = [json.loads(line) for line in trace.read_text().splitlines()]
    assert len([x for x in requests if x.get('method') == 'turn/start']) == 1 and not any(
        x.get('method') in {'account/login/start', 'account/logout'} for x in requests
    ), 'BG: one original objective and genuine account survive without a login/steer substitute'
    emitted = [json.loads(line) for line in trace.with_suffix('.native-emitted.jsonl').read_text().splitlines()]
    replies = [json.loads(line) for line in trace.with_suffix('.native-replies.jsonl').read_text().splitlines()]
    assert len(emitted) == len(replies) == 1 and emitted[0]['params']['callId'] == calls[0]['call_id'] and (
        emitted[0]['params']['tool'] == 'edit_background' and emitted[0]['params']['arguments'] == args
        and replies[0]['response']['id'] == emitted[0]['id'] == replies[0]['original']['id']
    ), 'BG: actual complete original native arguments and once-only reverse RPC envelope are canonical'
    assert not trace.with_suffix('.native-wrong-envelope.jsonl').exists(), (
        'BG: no response substitutes call identity for the original request envelope'
    )
    response = replies[0]['response']['result']
    outcome = json.loads(response['contentItems'][0]['text'])
    cancelled = case in {'stop', 'manual-takeover', 'preexisting-draft', 'new-owner'}
    assert response['success'] is (not cancelled), (
        'BG: actual original native response reports success only for genuine confirmed requested edit'
    )
    if cancelled:
        assert outcome['status'] not in {'edited', 'applied_unconfirmed'}, (
            'BG: pre-Apply retirement/refusal never hides a scientific write as cancellation'
        )
    else:
        assert outcome['status'] == 'edited', 'BG: genuine visible Apply is confirmed with strict original edited status'


@pytest.mark.parametrize('case', ['unchanged-draft', 'new-identical-draft', 'active-ime',
                                  'server-refusal', 'new-file-sent-revoke'])
def test_ux289_original_ack_consumes_only_submitted_presentation(case, tmp_path):
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'UX289 SETUP: genuine coherent Main runner is required'
    environment = popup171_owned_environment(tmp_path)
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text())
    config.pop('report_page_reply')
    calls = [
        {'tool': 'inspect_project', 'call_id': 'ux289-original-inspect',
         'arguments': {'purpose': 'Inspect original selected source scope after the original input ACK'}},
        {'tool': 'list_parameters', 'call_id': 'ux289-original-parameters',
         'arguments': {'purpose': 'Read actual original project parameters without changing science'}},
    ]
    config.update(scenario='native:script', ux289_hold_input=True, native_turn_calls=[calls],
                  ux295_refuse_original_input=case == 'server-refusal')
    config_path.write_text(json.dumps(config))
    original_config = config_path.read_bytes()
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::test_ux289_original_ack_consumes_only_submitted_presentation:' + case,
            '-o', '-,txt']
    try:
        result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                                text=True, timeout=90, check=False)
    except subprocess.TimeoutExpired as error:
        for stream in ('stdout', 'stderr'):
            raw = getattr(error, stream) or b''
            if isinstance(raw, str):
                raw = raw.encode()
            (tmp_path / ('ux289-timeout.' + stream + '.log')).write_bytes(raw)
        raise
    (tmp_path / 'ux289.stdout.log').write_text(result.stdout)
    (tmp_path / 'ux289.stderr.log').write_text(result.stderr)
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'FAIL!' not in output and (
        'PASS   : edi_app::AssistantPopup::test_ux289_original_ack_consumes_only_submitted_presentation('
        + case + ')' in output
    ), 'UX289: exact real pending/ACK/revision/chip/native/account premises and outcomes must execute\n' + output
    assert not any(('Binding loop detected' in line and any(name in line for name in (
        'assistantHomeFocusCovered', 'implicitHeight', 'AssistantComposer', 'AssistantPanel'
    ))) or ('Cannot assign [undefined]' in line and any(name in line for name in (
        'AssistantComposer', 'AssistantMessage', 'AssistantPanel', 'NativeCwlImportDialog'
    ))) for line in output.splitlines()), 'UX289: covered real UX paths emit no named Qt binding/undefined warning\n' + output
    assert original_config == config_path.read_bytes(), 'UX289: original peer inputs cannot change after launch'
    trace = Path(config['trace'])
    requests = [json.loads(line) for line in trace.read_text().splitlines()]
    starts = [row for row in requests if row.get('method') == 'turn/start']
    assert len(starts) == 1 and starts[0]['params']['clientUserMessageId'], (
        'UX289: one real original start owns the exact acknowledged user identity'
    )
    assert not any(row.get('method') in {'turn/steer', 'account/login/start', 'account/logout'}
                   for row in requests), 'UX289: original ACK cannot fabricate another input/account transaction'
    events = [json.loads(line) for line in trace.with_suffix('.clear-events.jsonl').read_text().splitlines()]
    received = [row for row in events if row['kind'] == 'ux289-original-input-received']
    released = [row for row in events if row['kind'] == 'ux289-original-ack-release']
    assert len(received) == len(released) == 1 and (
        received[0]['request_id'] == released[0]['request_id'] == starts[0]['id']
        and released[0]['client_user_message_id'] == starts[0]['params']['clientUserMessageId']
        and any(row.get('method') == 'account/rateLimits/read' and row['id'] == released[0]['read_id']
                for row in requests)
    ), 'UX289: genuine public optional read releases exactly the previously received original ACK'
    if case == 'server-refusal':
        refused = [row for row in events if row['kind'] == 'ux295-original-input-refused']
        assert len(refused) == 1 and refused[0]['response'] == {
            'id': starts[0]['id'], 'error': {'code': -32600,
            'message': 'Original explicit input admission refusal'}
        }, 'UX295: exact original real server error envelope is emitted once instead of ACK'
        assert not trace.with_suffix('.native-replies.jsonl').exists() and not trace.with_suffix(
            '.native-emitted.jsonl').exists(), (
            'UX295: real original admission refusal emits no native call or fabricated native response'
        )
        return
    responses = [json.loads(line) for line in trace.with_suffix('.native-replies.jsonl').read_text().splitlines()]
    assert len(responses) == len(calls), 'UX289: both original real native reads settle once after chip consumption'
    for response, call in zip(responses, calls, strict=True):
        assert response['original']['params']['callId'] == call['call_id'] and (
            response['response']['id'] == response['original']['id']
            and response['response']['result']['success'] is True
        ), 'UX289: native authority survives presentation consumption on the original successful RPC channel'


@pytest.mark.parametrize('case', ['hidden-activity', 'folder-caption'])
def test_ux289_real_main_activity_and_folder_presentation(case, tmp_path):
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'UX289 SETUP: actual coherent Main consumer is required'
    environment = popup171_owned_environment(tmp_path)
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text())
    config.pop('report_page_reply')
    calls = [
        {'tool': 'inspect_project', 'call_id': 'ux289-working-first',
         'arguments': {'purpose': 'Read original project before actual two-tool request gap'}},
        {'tool': 'list_parameters', 'call_id': 'ux289-working-second',
         'arguments': {'purpose': 'Finish original read-only two-tool objective after genuine public observation'}},
    ]
    if case == 'hidden-activity':
        config.update(scenario='native:script', native_turn_calls=[calls],
                      readonly409=True, vm319_record_packets=True,
                      relation246_wait_for_usage=['ux289-working-first'])
    config_path.write_text(json.dumps(config))
    original = config_path.read_bytes()
    function = ('test_ux289_hidden_activity_uses_real_original_request' if case == 'hidden-activity'
                else 'test_ux289_folder_caption_preserves_actual_grant')
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::' + function, '-o', '-,txt']
    result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                            text=True, timeout=90, check=False)
    (tmp_path / 'ux289-ui.stdout.log').write_text(result.stdout)
    (tmp_path / 'ux289-ui.stderr.log').write_text(result.stderr)
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'FAIL!' not in output and (
        'PASS   : edi_app::AssistantPopup::' + function + '()' in output
    ), 'UX289: real original activity/scope controls and identity assertions must execute\n' + output
    assert original == config_path.read_bytes(), 'UX289: actual original peer configuration remains immutable'
    assert not any(('Binding loop detected' in line and any(name in line for name in (
        'assistantHomeFocusCovered', 'implicitHeight', 'AssistantWorking', 'AssistantComposer',
        'AssistantMessage.qml', 'AssistantConnectionDialog.qml'
    ))) or ('Cannot assign [undefined]' in line and any(name in line for name in (
        'AssistantWorking', 'AssistantPanel', 'AssistantComposer', 'NativeCwlImportDialog'
    ))) for line in output.splitlines()), 'UX289: covered real presentation paths emit no named Qt loop/undefined warning\n' + output
    if case == 'hidden-activity':
        trace = Path(config['trace'])
        replies = [json.loads(line) for line in trace.with_suffix('.native-replies.jsonl').read_text().splitlines()]
        # Same existing independently declared readOnly409 contract; no subject-policy echo.
        from test_e11_t5_codex_agent import readonly409_policy
        readonly409_policy(trace)
        actions472 = [json.loads(line.split('GUI470_STANDARD_ACTION ',1)[1]) for line in result.stdout.splitlines()
                      if 'GUI470_STANDARD_ACTION ' in line]
        assert [row['role'] for row in actions472] == ['sign-in','approve-context'] and (
            [row['text'] for row in actions472] == ['Sign in with ChatGPT','Approve context']
            and [row['connectedBefore'] for row in actions472] == [False,True]
        ), 'GUI472: actual original busy setup reaches independent FULL sign-in/approval labels and semantic roles once'
        frames471 = [json.loads(line.split('GUI471_WORKING ', 1)[1]) for line in result.stdout.splitlines()
                     if 'GUI471_WORKING ' in line]
        assert [row['name'] for row in frames471] == [
            'ux471-panel-robot-light', 'ux471-panel-logo-light',
            'ux471-status-robot-light', 'ux471-status-logo-light'], (
            'GUI471: actual original busy vehicle captures declared panel then genuinely hidden status variants'
        )
        assert all((tmp_path / ('visible185-' + row['name'] + '.png')).is_file()
                   and (tmp_path / ('visible185-' + row['name'] + '.png')).stat().st_size > 0
                   for row in frames471), 'GUI471: all four original actual-Window native capture artifacts must exist'
        assert len({row['owner'] for row in frames471}) == 1, 'GUI471: all genuine panel/status frames retain SAME actual scientific owner'
        assert [row['variant'] for row in frames471] == [2, 1, 2, 1] and all(
            row['state'] == 'agent_active' and row['canCancel'] is True
            and row['receiver'] and row['owner'] for row in frames471
        ), 'GUI471: deterministic rendering never substitutes fake VM busy or fabricated owner identity'
        assert len(replies) == 2 and all(row['response']['result']['success'] is True
                                       for row in replies), 'UX289: both real native reads succeed once on original envelopes'
        assert [row['original']['params']['callId'] for row in replies] == [row['call_id'] for row in calls], (
            'UX289: actual tool sequence remains the predeclared original multi-tool objective'
        )


@pytest.mark.parametrize('case', ['add-refused-input', 'remove-refused-input', 'add-new-owner',
                                  'remove-new-owner', 'add-nested-add', 'remove-nested-add',
                                  'logout-refused-input', 'logout-picker'])
def test_ux300_original_public_notification_and_retirement(case, tmp_path):
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'UX300 SETUP: genuine coherent normal Main consumer is required'
    environment = popup171_owned_environment(tmp_path)
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    original_config = config_path.read_bytes()
    config = json.loads(original_config)
    logout = case.startswith('logout-')
    function = ('test_ux300_real_signout_retires_despite_same_owner_notification' if logout
                else 'test_ux300_real_selection_notification_keeps_original_authority')
    row = case.removeprefix('logout-') if logout else case
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::' + function + ':' + row, '-o', '-,txt']
    result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                            text=True, timeout=90, check=False)
    (tmp_path / 'ux300.stdout.log').write_text(result.stdout)
    (tmp_path / 'ux300.stderr.log').write_text(result.stderr)
    (tmp_path / 'ux300-process.json').write_text(json.dumps({'argv': argv, 'returncode': result.returncode}, indent=2))
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'FAIL!' not in output and (
        'PASS   : edi_app::AssistantPopup::' + function + '(' + row + ')' in output
    ), 'UX300: genuine original Qt notifications/public owner action/lifecycle and scientific guards all execute\n' + output
    assert config_path.read_bytes() == original_config, 'UX300: actual original owned peer inputs remain byte-exact'
    assert not any(('Binding loop detected' in line and any(name in line for name in (
        'assistantHomeFocusCovered', 'implicitHeight', 'AssistantComposer', 'AssistantPanel'
    ))) or ('Cannot assign [undefined]' in line and any(name in line for name in (
        'AssistantComposer', 'AssistantMessage', 'AssistantPanel', 'NativeCwlImportDialog'
    ))) for line in output.splitlines()), 'UX300: covered callback/lifecycle UI emits no named binding/undefined warnings\n' + output
    trace = Path(config['trace'])
    if not logout:
        assert not trace.exists() and not config_path.with_suffix('.peer-pid').exists(), (
            'UX300: ordinary offline selection/model notification requires no provider process/account'
        )
        return
    requests = [json.loads(line) for line in trace.read_text().splitlines()]
    assert len([x for x in requests if x.get('method') == 'account/logout']) == 1, (
        'UX300: actual explicit sign-out reaches exactly one original logout RPC'
    )
    assert not any(x.get('method') in {'turn/start', 'turn/steer', 'account/login/start'}
                   for x in requests), 'UX300: nested refused input/picker cannot become a new Send/account transaction'
    assert not trace.with_suffix('.native-emitted.jsonl').exists(), (
        'UX300: genuine logout retirement never fabricates a native scientific invocation'
    )

# Independent PUBLIC381/381v2 ordered scalar arrays; same original native Main vehicle.
ARRAY450_CASES = ['normal-values', 'singleton', 'values', 'free', 'all-noop-values',
                  'all-noop-free', 'mixed-values', 'invalid-last', 'manual-draft', 'stop', 'takeover']


def array450_calls(case):
    assert case in ARRAY450_CASES, 'ARRAY450 SETUP: finite original-control case inventory'
    la = 'structure.atom_sites[La].adp_iso'
    ba = 'structure.atom_sites[Ba].adp_iso'
    co = 'structure.atom_sites[Co].adp_iso'
    wavelength = 'experiment.instrument.setup_wavelength'
    cell = 'structure.cell.length_a'
    sentinel = {'tool': 'set_parameters', 'call_id': 'array450-sentinel', 'arguments': {
        'purpose': 'Establish independent prior recorded Undo before ordered array',
        'values': [{'path': wavelength, 'value': 1.495}]}}
    tool = 'set_free' if case in {'free', 'all-noop-free'} else 'set_parameters'
    values = [{'path': la, 'value': 0.6}, {'path': wavelength, 'value': 1.49},
              {'path': cell, 'value': 3.89}]
    if case == 'singleton':
        values = [{'path': la, 'value': 0.6}]
    elif case == 'all-noop-values':
        values = [{'path': la, 'value': 0.5}, {'path': wavelength, 'value': 1.495}, {'path': cell, 'value': 3.88}]
    elif case == 'mixed-values':
        values = [{'path': la, 'value': 0.5}, {'path': ba, 'value': 0.7}, {'path': cell, 'value': 3.88}]
    elif case == 'invalid-last':
        values = [{'path': la, 'value': 0.6}, {'path': 'original.absent.parameter', 'value': 4.0}]
    elif case in {'stop', 'takeover'}:
        values = [{'path': la, 'value': 0.6}, {'path': ba, 'value': 0.7}, {'path': co, 'value': 0.8}]
    flags = [{'path': la, 'free': case == 'all-noop-free'}, {'path': ba, 'free': True},
             {'path': co, 'free': case == 'all-noop-free'}]
    main = {'tool': tool, 'call_id': 'array450-action-' + case, 'arguments': {
        'purpose': 'Original ordered original-control array ' + case,
        **({'flags': flags} if tool == 'set_free' else {'values': values})}}
    return [sentinel, main]


def array450_result(case, call, result):
    assert type(result) is dict and type(result.get('success')) is bool, 'ARRAY450: actual original typed host result is mandatory'
    contents = result.get('contentItems')
    assert type(contents) is list and len(contents) == 1 and type(contents[0]) is dict and (
        contents[0].get('type') == 'inputText' and type(contents[0].get('text')) is str
    ), 'ARRAY450: exact one official typed inputText carries actual result, no guessed success fallback'
    value = json.loads(contents[0]['text'])
    assert type(value) is dict and type(value.get('status')) is str, 'ARRAY450: genuine result JSON is an object with actual status'
    if case in {'invalid-last', 'manual-draft'}:
        assert result['success'] is False and value['status'] in {'refused', 'unavailable'} and (
            type(value.get('message')) is str and value['message']
        ), 'ARRAY450: initially blocked/invalid original call is a real typed before-input refusal'
    else:
        incomplete = case in {'stop', 'takeover'}
        assert result['success'] is (not incomplete), 'ARRAY450: partial/incomplete native work cannot be successful whole-array completion'
        assert value['status'] == ('partial' if incomplete else 'unchanged' if case.startswith('all-noop-') else 'edited'), (
            'ARRAY450: settled noops, changed science and factual interrupted prefix have DISTINCT truthful status'
        )
        if case not in {'normal-values', 'singleton'}:
            entries = call['arguments'].get('values', call['arguments'].get('flags'))
            assert type(value.get('steps_completed')) is int and value['steps_completed'] == (1 if incomplete else len(entries)), (
                'ARRAY450: exact settled requested prefix INCLUDES noops and excludes uncommitted current entry'
            )
            assert type(value.get('complete')) is bool and value['complete'] is (not incomplete) and (
                type(value.get('atomic')) is bool and value['atomic'] is False
            ), 'ARRAY450: visible multi-entry is factual per-control work, never hidden atomic fallback'
            assert type(value.get('calculation_pending')) is bool, 'ARRAY450: actual native pending-calculation fact is typed, never assumed converged/fit'
    return value


@pytest.mark.parametrize('case', ARRAY450_CASES)
def test_array450_ordered_parameters_and_flags_use_original_controls(case, tmp_path):
    from tests.system.app.test_e11_t5_codex_agent import ux345_default_scattering_project
    reference = tmp_path / 'reference'; reference.mkdir()
    fixture = ux345_default_scattering_project(reference); fixture.rename(reference / 'project')
    original_files = {str(p.relative_to(reference)): p.read_bytes() for p in reference.rglob('*') if p.is_file()}
    calls = array450_calls(case)
    (reference / 'array450.json').write_text(json.dumps({'case': case, 'calls': calls}))
    environment = popup171_owned_environment(tmp_path)
    environment['EDI_ACCEPTANCE_REFERENCE'] = str(reference)
    environment['QT_QUICK_CONTROLS_HOVER_ENABLED'] = '1'
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text()); config.pop('report_page_reply')
    config.update(scenario='native:script', native_turn_calls=[[calls[0]], [calls[1]]],
                  native_array451_policy={'family': '450', 'case': case}, vm319_record_packets=True)
    config_path.write_text(json.dumps(config)); config_bytes = config_path.read_bytes()
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'ARRAY450 SETUP: genuinely bound future normal Main consumer required; no old binary relabel'
    function = 'test_array450_ordered_original_controls:' + case
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::' + function, '-o', '-,txt']
    try:
        result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                                text=True, timeout=90, check=False)
    except subprocess.TimeoutExpired as error:
        for stream in ('stdout', 'stderr'):
            data = getattr(error, stream) or b''
            raw = data if isinstance(data, bytes) else data.encode('utf-8')
            target = tmp_path / ('array450-timeout.' + stream + '.log'); target.write_bytes(raw)
            error.add_note(str(target) + '\n' + raw.decode(errors='backslashreplace'))
        raise
    (tmp_path / 'array450.stdout.log').write_text(result.stdout)
    (tmp_path / 'array450.stderr.log').write_text(result.stderr)
    (tmp_path / 'array450-process.json').write_text(json.dumps({'argv': argv, 'returncode': result.returncode,
                                                             'timeout': 90, 'case': case}, indent=2))
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'FAIL!' not in output and (
        'PASS   : edi_app::AssistantPopup::test_array450_ordered_original_controls(' + case + ')' in output
    ), 'ARRAY450: genuine actual Main row reaches ALL strict native/input/science/Undo/currentness assertions\n' + output
    assert config_path.read_bytes() == config_bytes and original_files == {
        str(p.relative_to(reference)): p.read_bytes() for p in reference.rglob('*') if p.is_file() and p.name != 'array450.json'
    }, 'ARRAY450: full predeclared script and every independently owned scientific source byte remain exact'
    assert json.loads((reference / 'array450.json').read_text()) == {'case': case, 'calls': calls}, 'ARRAY450: independent operands cannot be repaired after bootstrap'
    loaded = json.loads(config_path.with_suffix('.peer-loaded.json').read_text())
    assert loaded['sha256'] == hashlib.sha256(config_bytes).hexdigest() and loaded['native_turn_calls'] == config['native_turn_calls'], (
        'ARRAY450: actual owned process consumed BOTH independently fixed original calls once'
    )
    trace = Path(config['trace'])
    requests = [json.loads(line) for line in trace.read_text().splitlines()]
    starts = [row for row in requests if row.get('method') == 'turn/start']
    assert len(starts) == 2 and not any(row.get('method') in {'turn/steer', 'account/login/start', 'account/logout'} for row in requests), (
        'ARRAY450: distinct prior sentinel and one original array are genuine current turns, no replay/steer/auth repair'
    )
    replies = [json.loads(line) for line in trace.with_suffix('.native-replies.jsonl').read_text().splitlines()]
    emitted = [json.loads(line) for line in trace.with_suffix('.native-emitted.jsonl').read_text().splitlines()]
    assert len(emitted) == len(replies) == 2 and not trace.with_suffix('.native-wrong-envelope.jsonl').exists(), (
        'ARRAY450: both original requests are actually emitted and answered once, no missing or unrelated refusal'
    )
    assert len({row['id'] for row in emitted}) == 2, 'ARRAY450: genuine original reverse envelopes are distinct'
    for index, call in enumerate(calls):
        original, response = replies[index]['original'], replies[index]['response']
        assert original['id'] == emitted[index]['id'] == response['id'] != call['call_id'] and (
            original['params']['callId'] == emitted[index]['params']['callId'] == call['call_id']
            and original['params']['tool'] == emitted[index]['params']['tool'] == call['tool']
            and original['params']['arguments'] == emitted[index]['params']['arguments'] == call['arguments']
        ), 'ARRAY450: exact literal whole-array arguments/purpose/tool and original RPC identity survive once-only visible work'
        array450_result('singleton' if index == 0 else case, call, response['result'])
    receipts = [json.loads(line.split('ARRAY450_RESULT ', 1)[1]) for line in result.stdout.splitlines() if 'ARRAY450_RESULT ' in line]
    assert len(receipts) == 1 and receipts[0]['case'] == case and receipts[0]['sameOwner'] is True, (
        'ARRAY450: reached native input/result boundary has one original-owner receipt'
    )
    users = receipts[0]['users']
    expected_texts = ['Original450 establish the independent prior Undo sentinel', 'Original ordered visible array ' + case]
    assert len(users) == 2 and all(row['status'] == 'completed' for row in users) and [row['text'] for row in users] == expected_texts and (
        [row['params']['clientUserMessageId'] for row in starts] == [row['id'] for row in users]
    ), 'ARRAY450: original user identities, literal ordered objectives and genuine ACKs bond to exactly their actual wire turns'

# PUBLIC original category/model roles + PUBLIC383 retirement; no private producer oracle.
ARRAY451_CASES = ['hidden-change', 'hidden-noop', 'removed-noop', 'applied-replacement']


def array451_calls(case):
    assert case in ARRAY451_CASES, 'ARRAY451 SETUP: finite original model/lifetime cases only'
    def call(identifier, values):
        return {'tool': 'set_parameters', 'call_id': identifier, 'arguments': {
            'purpose': 'Independent original current-member and retirement witness', 'values': values}}
    la = 'structure.atom_sites[La].adp_iso'
    wavelength = 'experiment.instrument.setup_wavelength'
    hidden = 'experiment.instrument.calib_d_to_tof_linear'
    if case == 'applied-replacement':
        return [call('array451-original-A', [{'path': la, 'value': 0.6},
                                            {'path': 'structure.atom_sites[Ba].adp_iso', 'value': 0.7}])]
    values = ([{'path': wavelength, 'value': 1.496}, {'path': la, 'value': 0.5}]
              if case == 'removed-noop' else [{'path': la, 'value': 0.6},
                 {'path': hidden, 'value': 123.0 if case == 'hidden-noop' else 123.5}])
    return [call('array451-sentinel', [{'path': wavelength, 'value': 1.495}]),
            call('array451-normal', values), call('array451-visible', values)]


def array451_result(case, index, result):
    assert type(result) is dict and type(result.get('success')) is bool, 'ARRAY451: typed original outer success is mandatory'
    items = result.get('contentItems')
    assert type(items) is list and len(items) == 1 and type(items[0]) is dict and (
        items[0].get('type') == 'inputText' and type(items[0].get('text')) is str
    ), 'ARRAY451: exact one original typed result, no missing/unrelated/admission fallback'
    value = json.loads(items[0]['text'])
    assert type(value) is dict and type(value.get('status')) is str, 'ARRAY451: original result is a JSON object'
    if case == 'applied-replacement':
        assert result['success'] is False and value['status'] == 'applied_unconfirmed', (
            'ARRAY451: known actual scientific application stays factual despite original authority retirement')
        assert type(value.get('steps_completed')) is int and value['steps_completed'] == 0, (
            'ARRAY451: actually applied but not settled first entry is NOT a settled prefix')
        assert value.get('complete') is False and value.get('atomic') is False, (
            'ARRAY451: old original multi-entry result is incomplete and non-atomic')
        if 'request_retired' in value:
            assert value['request_retired'] is True, 'ARRAY451: optional retirement authority fact is additive and typed'
        assert type(value.get('calculation_pending')) is bool, 'ARRAY451: original pending-science fact is typed, not guessed Current'
    elif index < 2:
        assert result['success'] is True and value['status'] == 'edited', (
            'ARRAY451: same exact lawful normal request MUST really succeed; setup/early refusal is never a positive')
    else:
        assert result['success'] is False and value['status'] in {'refused', 'unavailable'} and (
            type(value.get('message')) is str and value['message']
        ), 'ARRAY451: later known unmapped/removed original member refuses the WHOLE visible array before earlier input'
    return value


@pytest.mark.parametrize('case', ARRAY451_CASES)
def test_array451_current_original_member_and_retirement(case, tmp_path):
    from tests.system.app.test_e11_t5_codex_agent import ux345_default_scattering_project
    reference = tmp_path / 'reference'; reference.mkdir()
    fixture = ux345_default_scattering_project(reference); fixture.rename(reference / 'project')
    experiment = reference / 'project/experiments/hrpt.edi'
    original = experiment.read_bytes()
    marker = b'_instrument.calib_twotheta_offset 0.6()\n'
    assert original.count(marker) == 1 and b'_instrument.calib_d_to_tof_linear' not in original, (
        'ARRAY451 SETUP: exact original CW experiment admits one independent extra declared free TOF scalar')
    if case.startswith('hidden-'):
        experiment.write_bytes(original.replace(marker, marker + b'_instrument.calib_d_to_tof_linear 123.0()\n'))
        assert experiment.read_bytes().replace(b'_instrument.calib_d_to_tof_linear 123.0()\n', b'') == original, (
            'ARRAY451 SETUP: removing ONLY own free unused instrument declaration reconstructs exact original experiment')
    shutil.copytree(reference / 'project', reference / 'replacement')
    before = {str(p.relative_to(reference)): p.read_bytes() for p in reference.rglob('*') if p.is_file()}
    calls = array451_calls(case)
    (reference / 'array451.json').write_text(json.dumps({'case': case, 'calls': calls}))
    environment = popup171_owned_environment(tmp_path)
    environment['EDI_ACCEPTANCE_REFERENCE'] = str(reference)
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text()); config.pop('report_page_reply')
    config.update(scenario='native:script', native_turn_calls=[[call] for call in calls],
                  native_array451_policy={'family': '451', 'case': case}, vm319_record_packets=True)
    config_path.write_text(json.dumps(config)); config_bytes = config_path.read_bytes()
    runner = Path(os.environ['EDI_APP_TEST_RUNNER'])
    assert runner.is_file(), 'ARRAY451 SETUP: future genuinely bound normal Main consumer required'
    argv = [str(runner), '-input', str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::test_array451_original_member:' + case, '-o', '-,txt']
    try:
        result = subprocess.run(argv, cwd=tmp_path, env=environment, capture_output=True,
                                text=True, timeout=90, check=False)
    except subprocess.TimeoutExpired as error:
        for stream in ('stdout', 'stderr'):
            value = getattr(error, stream) or b''
            raw = value if isinstance(value, bytes) else value.encode('utf-8')
            path = tmp_path / ('array451-timeout.' + stream + '.log'); path.write_bytes(raw)
            error.add_note(str(path) + '\n' + raw.decode(errors='backslashreplace'))
        raise
    (tmp_path / 'array451.stdout.log').write_text(result.stdout)
    (tmp_path / 'array451.stderr.log').write_text(result.stderr)
    (tmp_path / 'array451-process.json').write_text(json.dumps({'argv': argv, 'returncode': result.returncode, 'timeout': 90}))
    assert result.returncode == 0 and 'FAIL!' not in result.stdout + result.stderr and (
        'PASS   : edi_app::AssistantPopup::test_array451_original_member(' + case + ')' in result.stdout
    ), 'ARRAY451: actual normal success and genuine native original-control/replacement assertions all reach\n' + result.stdout + result.stderr
    assert config_path.read_bytes() == config_bytes and before == {
        str(p.relative_to(reference)): p.read_bytes() for p in reference.rglob('*') if p.is_file() and p.name != 'array451.json'
    }, 'ARRAY451: exact own fixture bytes/science and original peer script remain unchanged'
    loaded = json.loads(config_path.with_suffix('.peer-loaded.json').read_text())
    assert loaded['sha256'] == hashlib.sha256(config_bytes).hexdigest() and loaded['native_turn_calls'] == [[call] for call in calls], (
        'ARRAY451: actual original peer consumed exactly the immutable ordered scripts')
    trace = Path(config['trace'])
    requests = [json.loads(line) for line in trace.read_text().splitlines()]
    starts = [row for row in requests if row.get('method') == 'turn/start']
    assert len(starts) == len(calls) and not any(row.get('method') == 'turn/steer' for row in requests), (
        'ARRAY451: every original request is emitted once, no extra retry/steer/repair turn')
    emitted = [json.loads(line) for line in trace.with_suffix('.native-emitted.jsonl').read_text().splitlines()]
    replies = [json.loads(line) for line in trace.with_suffix('.native-replies.jsonl').read_text().splitlines()]
    assert len(emitted) == len(replies) == len(calls) and len({row['id'] for row in emitted}) == len(calls), (
        'ARRAY451: all original complete reverse envelopes are distinct and answered exactly once')
    assert not trace.with_suffix('.native-wrong-envelope.jsonl').exists(), 'ARRAY451: no wrong/late original envelope is tolerated'
    for index, call in enumerate(calls):
        original, response = replies[index]['original'], replies[index]['response']
        assert original == emitted[index] and response['id'] == original['id'] != call['call_id'], (
            'ARRAY451: response belongs to the exact independently captured original reverse envelope')
        assert original['params']['callId'] == call['call_id'] and original['params']['tool'] == call['tool'] and (
            original['params']['arguments'] == call['arguments'] and original['params']['namespace'] is None
        ), 'ARRAY451: exact full literal purpose/operands/native tool survive original request authority'
        array451_result(case, index, response['result'])
    receipts = [json.loads(line.split('ARRAY451_RESULT ', 1)[1]) for line in result.stdout.splitlines() if 'ARRAY451_RESULT ' in line]
    assert len(receipts) == 1 and receipts[0]['case'] == case, 'ARRAY451: one original native boundary receipt is mandatory'
    if case == 'applied-replacement':
        assert starts[0]['params']['clientUserMessageId'] == receipts[0]['oldUser']['id'] and receipts[0]['oldUser']['text'] == 'Original451 0' and receipts[0]['oldUser']['status'] == 'completed', ('ARRAY451: original actual user ID/ACK and objective bond to SAME old wire request before replacement')
        assert receipts[0]['applied'] == [0.6] and receipts[0]['replacements'] == 1 and receipts[0]['bUntouched'] is True, (
            'ARRAY451: original applied receipt and actual synchronous B replacement are facts, not prepared uncertainty')
    else:
        assert receipts[0]['normalSucceeded'] is True and receipts[0]['zeroVisibleInput'] is True, (
            'ARRAY451: exact SAME normal operands succeeded before known-route visible refusal; no early-refusal laundering')
        users = receipts[0]['users']
        assert [row['text'] for row in users] == ['Original451 ' + str(i) for i in range(3)] and (
            all(row['status'] == 'completed' for row in users)
        ), 'ARRAY451: original literal ordered user messages have genuine matching ACKs'
        assert [row['params']['clientUserMessageId'] for row in starts] == [row['id'] for row in users], (
            'ARRAY451: every actual user ID bonds independently to corresponding original wire request')


def test_read625_real_main_both_modes_read_without_project(tmp_path):
    from tests.system.app.test_e11_t5_codex_agent import readonly409_policy, records, rpc83_context_inputs
    environment = popup171_owned_environment(tmp_path)
    config_path = Path(environment['EDI_TEST_CODEX_PEER_INPUT'])
    config = json.loads(config_path.read_text())
    config.pop('report_page_reply')
    calls = [[{'tool':'read_selected_file','call_id':'read625-main-'+str(mode),
               'arguments':{'purpose':'Read independent selected text','file_id':{'$read625_current_ordinal':0},
                            'offset':0,'max_bytes':65536}}] for mode in range(2)]
    config.update(scenario='native:script',native_turn_calls=calls,readonly409=True,vm319_record_packets=True,read625=True)
    config_path.write_text(json.dumps(config)); original_config = config_path.read_bytes()
    runner = Path(os.environ['EDI_APP_TEST_RUNNER']); assert runner.is_file()
    argv = [str(runner),'-input',str(Path(__file__).with_name('tst_assistant_popup.qml')),
            'AssistantPopup::test_read625_selected_text_is_same_read_in_both_modes','-o','-,txt']
    result = subprocess.run(argv,cwd=tmp_path,env=environment,capture_output=True,text=True,timeout=90,check=False)
    (tmp_path/'read625.stdout.log').write_text(result.stdout);(tmp_path/'read625.stderr.log').write_text(result.stderr)
    assert result.returncode == 0 and 'FAIL!' not in result.stdout and (
        'PASS   : edi_app::AssistantPopup::test_read625_selected_text_is_same_read_in_both_modes()' in result.stdout)
    assert config_path.read_bytes() == original_config
    trace = Path(config['trace']); readonly409_policy(trace)
    requests = records(trace); starts = [r for r in requests if r.get('method')=='turn/start']
    replies = [json.loads(s) for s in trace.with_suffix('.native-replies.jsonl').read_text().splitlines()]
    emitted = [json.loads(s) for s in trace.with_suffix('.native-emitted.jsonl').read_text().splitlines()]
    assert len(starts)==len(replies)==len(emitted)==2 and len({r['response']['id']for r in replies})==2
    assert not any(r.get('method')in{'turn/interrupt','account/login/start'}for r in requests)
    assert sum(r.get('method')=='account/logout'for r in requests)==1  # original explicit fixture teardown
    for index,(start,reply,request) in enumerate(zip(starts,replies,emitted,strict=True)):
        offered = rpc83_context_inputs(start['params']);assert len(offered)==1
        selection = offered[0]['selected_files'];assert len(selection['files'])==1
        selected = selection['files'][0]
        assert selected['bytes']==18 and type(selected['id'])is str and selected['id']
        expected = {'purpose':'Read independent selected text','file_id':selected['id'],'offset':0,'max_bytes':65536}
        assert request['params']['arguments']==expected and request['item']['arguments']==expected
        assert request['params']['callId']=='read625-main-'+str(index) and reply['original']==request
        assert reply['response']['id']==request['id']!=request['params']['callId']
        value = json.loads(reply['response']['result']['contentItems'][0]['text'])
        assert reply['response']['result']['success'] is True
        assert value['selected_text']['collection_id']==selection['collection_id']
        assert value['selected_text']['generation']==selection['generation']
    assert not trace.with_suffix('.native-wrong-envelope.jsonl').exists()


def test_structure634_real_main_initial_atom_and_ordinary_cues(tmp_path):
    from tests.system.app.test_e11_t5_codex_agent import readonly409_policy, records
    env=popup171_owned_environment(tmp_path);config_path=Path(env['EDI_TEST_CODEX_PEER_INPUT']);config=json.loads(config_path.read_text());config.pop('report_page_reply')
    S={'$structure634':'structure'};A={'$structure634':'first_atom'};B={'$structure634':'appended_atom'}
    def call(tool,**arguments):return {'tool':tool,'arguments':{'purpose':'Original independent structure634 action',**arguments}}
    turns=[
        [call('create_structure'),call('inspect_project'),call('list_parameters')],
        [call('edit_structure',structure=S,operation='rename',value='Main634'),
         call('edit_atom',structure=S,operation='text',atom=A,field='label',value='First634'),
         call('edit_atom',structure=S,operation='text',atom=A,field='typeSymbol',value='57Fe')],
        [call('edit_atom',structure=S,operation='append'),call('inspect_project')],
        [call('edit_atom',structure=S,operation='text',atom=B,field='label',value='Second634')],
        [call('edit_structure',structure=S,operation='rename',value='Main634'),
         call('edit_atom',structure=S,operation='text',atom=A,field='label',value='First634'),
         call('edit_atom',structure=S,operation='text',atom=A,field='typeSymbol',value='57Fe')],
        [call('edit_atom',structure=S,operation='remove',atom=B)],
    ]
    for i,group in enumerate(turns):
        for j,entry in enumerate(group):entry['call_id']=f'structure634-main-{i}-{j}'
    config.update(scenario='native:script',native_turn_calls=turns,structure634=True,readonly409=True,vm319_record_packets=True)
    config_path.write_text(json.dumps(config));before=config_path.read_bytes();env['EDI_ACCEPTANCE_REFERENCE']=str(tmp_path)
    argv=[os.environ['EDI_APP_TEST_RUNNER'],'-input',str(Path(__file__).with_name('tst_assistant_popup.qml')),
          'AssistantPopup::test_structure634_original_main_row_reuse_and_noop_before_cue','-o','-,txt']
    result=subprocess.run(argv,cwd=tmp_path,env=env,capture_output=True,text=True,timeout=90,check=False)
    (tmp_path/'structure634.stdout.log').write_text(result.stdout);(tmp_path/'structure634.stderr.log').write_text(result.stderr)
    assert result.returncode==0 and 'FAIL!'not in result.stdout and 'PASS   : edi_app::AssistantPopup::test_structure634_original_main_row_reuse_and_noop_before_cue()'in result.stdout
    assert config_path.read_bytes()==before;trace=Path(config['trace']);readonly409_policy(trace);requests=records(trace)
    emitted=[json.loads(s)for s in trace.with_suffix('.native-emitted.jsonl').read_text().splitlines()];replies=[json.loads(s)for s in trace.with_suffix('.native-replies.jsonl').read_text().splitlines()]
    assert len(emitted)==len(replies)==sum(map(len,turns)) and len({r['id']for r in emitted})==len(emitted)
    assert len([r for r in requests if r.get('method')=='turn/start'])==len(turns)
    for sent,reply in zip(emitted,replies,strict=True):
        assert reply['original']==sent and reply['response']['id']==sent['id']!=sent['params']['callId'] and reply['response']['result']['success'] is True
    facts=[json.loads(line.split('STRUCTURE634_MAIN_RESULT ',1)[1])for line in result.stdout.splitlines()if 'STRUCTURE634_MAIN_RESULT 'in line]
    assert len(facts)==1 and all(facts[0][k] is True for k in ['ownerSame','firstSame','realUndo'])
    assert [facts[0][k]for k in ['keys','clicked','activated']]==[0,0,0]
    assert not any(r.get('method')in{'turn/interrupt','account/login/start'}for r in requests)
    assert not trace.with_suffix('.native-wrong-envelope.jsonl').exists()
