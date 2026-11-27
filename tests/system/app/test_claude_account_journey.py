# SPDX-License-Identifier: BSD-3-Clause
"""Desktop journeys spanning an installed Claude runtime and the app session."""

import json
import os

import pytest

from tests.integration.app.test_provider_runtime import probe_tool_catalogue, run_probe


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
    replies = [row['result'] for row in rows if row['event'] == 'mcp-reply']
    assert len(replies) == 1 and not replies[0].get('isError'), (
        'The app dispatcher must return a successful MCP reply for this attached-file read'
    )
    assert any(
        json.loads(item['text']).get('selected_text', {}).get('text') == 'visible'
        for item in replies[0]['content']
    ), 'The MCP result must include exactly the requested seven bytes from the selected file'


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
