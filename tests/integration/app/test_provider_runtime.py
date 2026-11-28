# SPDX-License-Identifier: BSD-3-Clause
"""Run the desktop session with offline Claude and GitHub Copilot peers."""

import json
import os
import shlex
import shutil
import subprocess
import sys
import tomllib
import uuid
from pathlib import Path

import pytest

from tests.fixtures.assistant_providers.wire_peer import CLAUDE_KEY, CREDENTIALS, KEY_SENTINEL

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/assistant_providers/wire_peer.py'
BINARIES = ROOT / 'build/app/app'
PROBE = BINARIES / 'edi_assistant_ui_tests'
GUARD = BINARIES / 'edi_assistant_guard'
BUILTIN_TOOLS = {
    'agent',
    'bash',
    'edit',
    'glob',
    'grep',
    'powershell',
    'read',
    'shell',
    'terminal',
    'webfetch',
    'websearch',
    'web_fetch',
    'web_search',
    'write',
}


def stage_install(tmp_path, provider, receipt, scenario):
    install = tmp_path / 'install'
    binaries = install / 'bin'
    binaries.mkdir(parents=True)
    for binary in (PROBE, GUARD):
        try:
            os.link(binary, binaries / binary.name)
        except OSError:
            shutil.copy2(binary, binaries / binary.name)
    runtime = install / 'libexec/edi' / provider
    runtime.mkdir(parents=True)
    pin = ROOT / 'tools/deps' / f'{provider}-runtime/pixi.toml'
    metadata = tomllib.loads(pin.read_text(encoding='utf-8'))
    (runtime / 'edi-runtime.json').write_text(
        json.dumps({
            'runtime': provider,
            'version': metadata['package']['version'],
            'entrypoint': provider,
        }),
        encoding='utf-8',
    )
    executable = runtime / provider
    launcher = ' '.join(map(shlex.quote, [sys.executable, str(FIXTURE), provider]))
    executable.write_text(
        '#!/bin/sh\n'
        f'export EDI_PROVIDER_TEST_RECEIPT={shlex.quote(str(receipt))}\n'
        f'export EDI_PROVIDER_TEST_SCENARIO={shlex.quote(scenario)}\n'
        f'export EDI_PROVIDER_TEST_GUARD={shlex.quote(str(binaries / GUARD.name))}\n'
        f'exec {launcher} "$@"\n',
        encoding='utf-8',
    )
    executable.chmod(0o700)
    return binaries / PROBE.name, executable


def write_case(tmp_path, provider, mismatch, credential, scenario, receipt):
    sample = tmp_path / 'sample.txt'
    sample.write_text('xxvisibleyy', encoding='utf-8')
    files = [str(sample)]
    if scenario in {'attach-after-connect', 'refused-open'}:
        second = tmp_path / 'second.txt'
        second.write_text('additional context', encoding='utf-8')
        files.append(str(second))
    identity = 'selected@example.invalid' if provider == 'claude' else 'selected-user'
    other = 'other@example.invalid' if provider == 'claude' else 'other-user'
    account_id, other_id = (str(uuid.uuid4()) for _ in range(2))
    case = tmp_path / 'case.json'
    case.write_text(
        json.dumps({
            'provider': provider,
            'account': {
                'id': account_id,
                'provider': provider,
                'email': identity,
                'plan': 'pro',
                'host': 'github.com',
            },
            'runtimeEmail': 'different@example.invalid' if mismatch else identity,
            'otherId': other_id,
            'otherLogin': other,
            'mismatch': mismatch,
            'credential': credential,
            'scenario': scenario,
            'file': str(sample),
            'files': files,
            'runtimeReceipt': str(receipt),
        }),
        encoding='utf-8',
    )
    return case, account_id, other_id


def run_probe(tmp_path, provider, *, mismatch=False, credential=False, scenario=''):
    assert PROBE.is_file() and GUARD.is_file(), (
        'The provider check requires the desktop assistant UI test and guard from this build'
    )
    receipt = tmp_path / 'wire.jsonl'
    case, account_id, other_id = write_case(
        tmp_path, provider, mismatch, credential, scenario, receipt
    )
    probe, _ = stage_install(tmp_path, provider, receipt, scenario)
    home = tmp_path / 'home'
    home.mkdir()
    config = home / '.config/gh'
    config.mkdir(parents=True)
    (config / 'hosts.yml').write_text('github.com:\n  user: inherited-user\n', encoding='utf-8')

    env = {
        key: os.environ[key] for key in ('LD_LIBRARY_PATH', 'QT_PLUGIN_PATH') if key in os.environ
    }
    if provider == 'copilot':
        env.update(dict.fromkeys(CREDENTIALS, 'inherited-offline-sentinel'))
    elif credential:
        env[CLAUDE_KEY] = KEY_SENTINEL
    env.update({
        'HOME': str(home),
        'PATH': str(tmp_path),
        'XDG_CONFIG_HOME': str(home / '.config'),
        'XDG_DATA_HOME': str(home / '.data'),
        'XDG_CACHE_HOME': str(home / '.cache'),
        'QT_QPA_PLATFORM': 'offscreen',
        'QT_QUICK_BACKEND': 'software',
        'EDI_ONLINE_SOURCES': ';'.join(
            f'{name}={(ROOT / "tests/fixtures/online_sources" / folder).as_uri()}/'
            for name, folder in (('cod', 'cod'), ('easydiffraction', 'easydiffraction'))
        ),
        'EDI_PROVIDER_TEST_CASE': str(case),
    })
    result = subprocess.run(
        [str(probe), 'accountTurn'],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=12,
    )
    assert result.returncode == 0, (
        f'The {provider} desktop account journey must complete ({scenario or "tool turn"}).\n'
        + result.stdout
        + result.stderr
    )
    assert receipt.is_file(), 'The desktop probe must reach the selected real runtime launch path'
    rows = [json.loads(line) for line in receipt.read_text(encoding='utf-8').splitlines()]
    expected_homes = {(provider, account_id)}
    if provider == 'claude' and not (mismatch or credential or scenario == 'refused-open'):
        expected_homes.add((provider, other_id))
    return rows, check_launches(rows, home, (provider, account_id), expected_homes)


def check_launches(rows, home, selected_home, expected_homes):
    launches = [row for row in rows if row['event'] == 'launch']
    assert launches, 'The offline peer must record the runtime launches'
    homes = [Path(row['home']).parts[-2:] for row in launches]
    assert homes[0] == selected_home and set(homes) == expected_homes, (
        'Each login must stay in the selected home and a switch must reach the other home'
    )
    assert all(Path(row['home']).is_relative_to(home) for row in launches), (
        'Account homes must live in the isolated application data directory'
    )
    if selected_home[0] == 'copilot':
        assert all(not row['credentials'] for row in launches), (
            'Copilot must receive no inherited credential or account-routing variable'
        )
    return launches


def probe_tool_catalogue(tmp_path, provider):
    rows, launches = run_probe(tmp_path, provider)
    stream_flag = '--output-format' if provider == 'claude' else '--acp'
    turns = [row for row in launches if stream_flag in row['argv']]
    assert turns, 'The app must launch the requested runtime in its documented streaming mode'
    skills = {
        path.parent.name: path.read_text(encoding='utf-8')
        for path in (ROOT / 'data/assistant/skills').glob('*/SKILL.md')
    }
    assert skills and all(turn['skills'] == skills for turn in turns), (
        'The provider must discover the approved bundled skills byte for byte'
    )
    configs = [row['names'] for row in rows if row['event'] == 'mcp-config']
    assert configs and all(names == ['edi'] for names in configs), (
        'The runtime must receive edi as its sole MCP server'
    )
    catalogues = [row['names'] for row in rows if row['event'] == 'mcp-tools']
    assert catalogues and all('read_selected_file' in names for names in catalogues), (
        'The runtime must discover the selected-file tool through MCP'
    )
    assert all(
        not BUILTIN_TOOLS.intersection(name.lower() for name in names) for names in catalogues
    ), 'The tool catalogue must contain no shell, file, web or agent built-ins'
    return rows, turns, catalogues


@pytest.mark.skipif(os.name == 'nt', reason='The offline CLI fixture is a shell script')
def test_copilot_shows_edi_tool_reply_after_account_readback(tmp_path):
    rows, turns, catalogues = probe_tool_catalogue(tmp_path, 'copilot')
    for turn in turns:
        argv = turn['argv']
        assert {'--no-auto-update', '--disable-builtin-mcps', '--available-tools'} <= set(argv), (
            'Copilot must disable updates and use a closed tool list with built-in MCP off'
        )
        assert not {'--allow-all', '--yolo'}.intersection(argv), (
            'Copilot must never be started with a blanket permission grant'
        )
        allowed = [argv[index + 1] for index, arg in enumerate(argv[:-1]) if arg == '--allow-tool']
        assert allowed == ['skill', 'edi'], (
            'Copilot may pre-allow only the skill loader and the edi MCP server'
        )
        assert turn['gh_config_empty'], 'Copilot must not see an inherited gh login'
        available = argv[argv.index('--available-tools') + 1].split(',')
        assert any(
            len(available) == len(names) + 1
            and set(available) == {'skill', *(f'edi-{name}' for name in names)}
            for names in catalogues
        ), 'Copilot can be launched with exactly the edi catalogue and the skill loader'
    capabilities = [row['capabilities'] for row in rows if row['event'] == 'acp-client']
    assert capabilities and all(
        not capability.get('fs') and not capability.get('terminal') for capability in capabilities
    ), 'ACP must not offer file access or a terminal to Copilot'
    commands = [row for row in rows if row['event'] == 'account-command']
    assert [row['text'] for row in commands] == ['/user switch selected-user', '/user show'], (
        'Copilot must confirm the requested login and host in the same ACP session'
    )
    assert len({row['session'] for row in commands}) == 1, (
        'Copilot account selection and readback must share a session'
    )
    (identity,) = [row for row in rows if row['event'] == 'copilot-identity']
    (prompt,) = [row for row in rows if row['event'] == 'prompt']
    assert (
        identity['login'] == prompt['identity'] == 'selected-user'
        and identity['host'] == 'github.com'
        and identity['session'] == prompt['session'] == commands[0]['session']
        and rows.index(identity) < rows.index(prompt)
    ), 'The selected login and host must be confirmed in the same session before user input'
    require_selected_file_reply(rows)


def require_selected_file_reply(rows):
    replies = [row['result'] for row in rows if row['event'] == 'mcp-reply']
    assert len(replies) == 1 and not replies[0].get('isError'), (
        'The dispatcher must return a successful MCP reply for the attached-file read'
    )
    assert any(
        json.loads(item['text']).get('selected_text', {}).get('text') == 'visible'
        for item in replies[0]['content']
    ), 'The MCP reply must carry exactly the selected bytes from the attached sample'


@pytest.mark.skipif(os.name == 'nt', reason='The offline CLI fixture is a shell script')
@pytest.mark.parametrize('scenario', ['wrong-login', 'wrong-host'])
def test_copilot_refuses_input_for_a_different_account(tmp_path, scenario):
    rows, _ = run_probe(tmp_path, 'copilot', scenario=scenario)
    (identity,) = [row for row in rows if row['event'] == 'copilot-identity']
    assert (identity['login'], identity['host']) == (
        ('different-user', 'github.com')
        if scenario == 'wrong-login'
        else ('selected-user', 'other.ghe.com')
    ), 'The turn runtime must report the mismatched login or host'
    assert not any(row['event'] in {'prompt', 'mcp-reply'} for row in rows), (
        'An account that fails the live proof must receive no prompt or tool call'
    )


@pytest.mark.skipif(os.name == 'nt', reason='The offline CLI fixture is a shell script')
def test_copilot_denies_permission_and_stops_an_unlisted_tool(tmp_path):
    rows, _ = run_probe(tmp_path, 'copilot', scenario='foreign-tool')
    (permission,) = [row for row in rows if row['event'] == 'copilot-permission']
    assert permission['outcome'] == {'outcome': 'selected', 'optionId': 'no'}, (
        'Copilot must receive the reject-once answer to an unlisted tool permission request'
    )
    assert [
        row['event']
        for row in rows
        if row['event'] in {'prompt', 'copilot-permission', 'copilot-foreign-tool', 'mcp-reply'}
    ] == ['prompt', 'copilot-permission', 'copilot-foreign-tool'], (
        'The runtime must attempt the unlisted tool without calling the edi MCP dispatcher'
    )


@pytest.mark.skipif(os.name == 'nt', reason='The offline CLI fixture is a shell script')
def test_claude_identity_mismatch_refuses_before_a_prompt(tmp_path):
    rows, _ = run_probe(tmp_path, 'claude', mismatch=True)
    assert [row['identity'] for row in rows if row['event'] == 'claude-readback'] == [
        'different@example.invalid'
    ], 'The mismatched principal must come from the turn runtime, after the home check succeeds'
    assert not any(row['event'] == 'prompt' for row in rows), (
        'A Claude login for a different account must be refused before any user prompt reaches it'
    )
