# SPDX-License-Identifier: BSD-3-Clause
"""Desktop account journeys with installed Claude and GitHub Copilot runtimes."""

import json
import os
import subprocess

import pytest

from tests.integration.app.test_provider_runtime import (
    probe_tool_catalogue,
    require_selected_file_reply,
    run_probe,
    stage_install,
)


@pytest.mark.skipif(os.name == 'nt', reason='The offline CLI fixture is a shell script')
def test_claude_shows_edi_tool_reply_and_switches_accounts(tmp_path):
    rows, turns, _ = probe_tool_catalogue(tmp_path, 'claude')
    for turn in turns:
        argv = turn['argv']
        assert turn['updates_disabled'] == '1', 'Claude must run with DISABLE_UPDATES=1'
        assert '--strict-mcp-config' in argv and '--tools' in argv, (
            'Claude must use a private MCP config and an explicit built-in tool selection'
        )
        assert argv[argv.index('--tools') + 1] == 'Skill', (
            'Claude may retain the bundled skill loader as its single built-in tool'
        )
        assert (
            '--setting-sources' in argv and argv[argv.index('--setting-sources') + 1] == 'local'
        ), 'Claude must leave user and project settings out of the runtime'
        assert '--session-id' in argv and '--resume' not in argv, (
            'A newly selected account must not resume a thread owned by another account'
        )
    prompts = [row for row in rows if row['event'] == 'prompt']
    assert len(prompts) == 1 and prompts[0]['identity'] == 'selected@example.invalid', (
        'The tool-using prompt must run once under the selected account'
    )
    session_events = [row for row in rows if row.get('session') == prompts[0]['session']]
    before_init = [
        row['subtype'] if row['event'] == 'claude-control' else row['event']
        for row in session_events
        if row['event'] in {'claude-control', 'prompt', 'claude-init'}
    ]
    assert before_init[:6] == [
        'initialize',
        'mcp_status',
        'get_context_usage',
        'get_usage',
        'prompt',
        'claude-init',
    ], 'The Claude turn process must read identity, tools and plan usage before input causes init'
    require_selected_file_reply(rows)


@pytest.mark.skipif(os.name == 'nt', reason='The offline CLI fixture is a shell script')
@pytest.mark.parametrize('provider', ['claude', 'copilot'])
def test_first_turn_reaches_the_connected_runtime_after_attaching_files(tmp_path, provider):
    rows, _ = run_probe(tmp_path, provider, scenario='attach-after-connect')
    prompts = [row['identity'] for row in rows if row['event'] == 'prompt']
    expected = 'selected@example.invalid' if provider == 'claude' else 'selected-user'
    assert prompts == [expected], (
        'The first attached-file prompt must reach the selected login once'
    )
    require_selected_file_reply(rows)


@pytest.mark.skipif(os.name == 'nt', reason='The offline CLI fixture is a shell script')
def test_refused_conversation_open_keeps_the_account_connected(tmp_path):
    rows, _ = run_probe(tmp_path, 'claude', scenario='refused-open')
    assert any(row['event'] == 'claude-readback' for row in rows), (
        'The offline runtime must verify the account before the later conversation is refused'
    )
    assert not any(row['event'] in {'prompt', 'mcp-reply'} for row in rows), (
        'A refused conversation open must send no input and execute no tool'
    )


@pytest.mark.skipif(os.name == 'nt', reason='The offline CLI fixture is a shell script')
def test_claude_waits_for_the_mcp_catalogue_before_input(tmp_path):
    rows, _ = run_probe(tmp_path, 'claude', scenario='pending-mcp')
    (prompt,) = [row for row in rows if row['event'] == 'prompt']
    observed = [
        row['status']
        for row in rows[: rows.index(prompt)]
        if row['event'] == 'claude-mcp-status' and row['session'] == prompt['session']
    ]
    assert observed[0] == 'pending' and observed[-1] == 'connected', (
        'The same turn runtime must wait for its pending MCP connection before accepting input'
    )
    require_selected_file_reply(rows)


@pytest.mark.skipif(os.name == 'nt', reason='The offline CLI fixture is a shell script')
def test_claude_discloses_inherited_credential_before_input(tmp_path):
    rows, launches = run_probe(tmp_path, 'claude', credential=True)
    assert all(launch['fixture_key_intact'] for launch in launches), (
        'Claude must receive the user supplied credential without changing its value'
    )
    assert any(row['event'] == 'claude-readback' for row in rows), (
        'Claude must read back the active principal before the Account dialog presents it'
    )
    assert not any(row['event'] == 'prompt' for row in rows), (
        'Checking the active credential disclosure must never send a user prompt'
    )


@pytest.mark.skipif(os.name == 'nt', reason='The offline CLI fixture is a shell script')
@pytest.mark.parametrize('action', ['delayed-callback', 'cancel'])
def test_claude_interactive_login_stays_owned_until_callback_or_cancel(tmp_path, action):
    receipt = tmp_path / 'login.jsonl'
    probe, executable = stage_install(tmp_path, 'claude', receipt, '')
    home = tmp_path / 'account'
    home.mkdir()
    env = {
        key: os.environ[key] for key in ('LD_LIBRARY_PATH', 'QT_PLUGIN_PATH') if key in os.environ
    }
    env.update({
        'HOME': str(tmp_path),
        'PATH': str(tmp_path),
        'QT_QPA_PLATFORM': 'offscreen',
        'EDI_PROVIDER_TEST_CASE': 'login',
        'EDI_PROVIDER_TEST_LOGIN_HOME': str(home),
        'EDI_PROVIDER_TEST_LOGIN_EXECUTABLE': str(executable),
    })
    if action == 'cancel':
        env['EDI_PROVIDER_TEST_CANCEL_LOGIN'] = '1'
    result = subprocess.run(
        [str(probe), 'claudeSignIn'],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=8,
    )
    assert result.returncode == 0, (
        'The original Claude process must survive an elapsed deadline or stop on Cancel.\n'
        + result.stdout
        + result.stderr
    )
    rows = [json.loads(line) for line in receipt.read_text(encoding='utf-8').splitlines()]
    login = [row for row in rows if row['event'].startswith('claude-login-')]
    assert [row['event'] for row in login] == (
        ['claude-login-opened']
        if action == 'cancel'
        else ['claude-login-opened', 'claude-login-completed']
    ), 'Only the delayed callback must finish the original offline login'
    assert len({row['pid'] for row in login}) == 1, (
        'A delayed callback must finish on the original process without starting another login'
    )
