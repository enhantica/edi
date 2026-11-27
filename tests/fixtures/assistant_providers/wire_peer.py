# SPDX-License-Identifier: BSD-3-Clause
"""Local stream-json and ACP peers. The configured MCP server does the tool work."""

import json
import os
import subprocess
import sys
from contextlib import ExitStack, contextmanager
from pathlib import Path

MCP_VERSION = '2025-11-25'
TOOL = 'read_selected_file'
COPILOT_MODELS = [
    {
        'id': 'model',
        'name': 'Model',
        'category': 'model',
        'type': 'select',
        'currentValue': 'gpt-4.1',
        'options': [{'value': 'gpt-4.1', 'name': 'GPT-4.1'}],
    }
]
CREDENTIALS = {
    'ANTHROPIC_API_KEY',
    'ANTHROPIC_AUTH_TOKEN',
    'ANTHROPIC_BASE_URL',
    'ANTHROPIC_PROFILE',
    'CLAUDE_CODE_OAUTH_TOKEN',
    'CLAUDE_CODE_USE_BEDROCK',
    'CLAUDE_CODE_USE_VERTEX',
    'CLAUDE_CODE_USE_FOUNDRY',
    'CLAUDECODE',
    'COPILOT_GITHUB_TOKEN',
    'COPILOT_GH_HOST',
    'COPILOT_ALLOW_ALL',
    'COPILOT_MODEL',
    'COPILOT_PROVIDER_API_KEY',
    'COPILOT_PROVIDERS_CONFIG',
    'GH_TOKEN',
    'GITHUB_TOKEN',
    'GH_HOST',
}


def observe(event, **fields):
    with Path(os.environ['EDI_PROVIDER_TEST_RECEIPT']).open('a', encoding='utf-8') as receipt:
        receipt.write(json.dumps({'event': event, **fields}) + '\n')


def write(message, stream=sys.stdout):
    print(json.dumps(message), file=stream, flush=True)


def response(request, result):
    return {'jsonrpc': '2.0', 'id': request['id'], 'result': result}


@contextmanager
def mcp_connection(server):
    # MCP 2025-11-25 lifecycle, stdio transport and tools examples.
    executable = Path(server['command']).resolve()
    if executable != Path(os.environ['EDI_PROVIDER_TEST_GUARD']).resolve():
        raise ValueError('The fixture only starts the MCP guard from the test build')
    if server.get('args') != ['mcp']:
        raise ValueError('The configured guard must run in MCP mode')
    with subprocess.Popen(
        [str(executable), *server.get('args', [])],
        env={**os.environ, **server.get('env', {})},
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        encoding='utf-8',
    ) as process:

        def request(method, params, request_id):
            write(
                {'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params},
                process.stdin,
            )
            result = json.loads(process.stdout.readline())
            if result.get('id') != request_id or result.get('jsonrpc') != '2.0':
                raise ValueError(f'MCP response does not match request {request_id}')
            return result['result']

        try:
            ready = request(
                'initialize',
                {
                    'protocolVersion': MCP_VERSION,
                    'capabilities': {},
                    'clientInfo': {'name': 'offline-test', 'version': '1.0'},
                },
                1,
            )
            if 'tools' not in ready['capabilities']:
                raise ValueError('The MCP server did not advertise tools')
            write({'jsonrpc': '2.0', 'method': 'notifications/initialized'}, process.stdin)
            tools = request('tools/list', {}, 2)['tools']
            names = sorted(tool['name'] for tool in tools)
            observe('mcp-tools', names=names)
            yield names, request
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()


def tool_arguments(prompt):
    return {
        'file_id': prompt.split('fixture-file-id=', 1)[1].split()[0],
        'offset': 2,
        'max_bytes': 7,
        'purpose': 'Read the attached sample',
    }


def call_tool(request, prompt):
    reply = request('tools/call', {'name': TOOL, 'arguments': tool_arguments(prompt)}, 3)
    observe('mcp-reply', result=reply)
    return '\n'.join(entry['text'] for entry in reply['content'] if entry['type'] == 'text')


def option(argv, key):
    return argv[argv.index(key) + 1]


def mcp_config(argv, flag):
    value = option(argv, flag).removeprefix('@')
    raw = value if value.lstrip().startswith('{') else Path(value).read_text(encoding='utf-8')
    servers = json.loads(raw)['mcpServers']
    observe('mcp-config', names=sorted(servers))
    return servers['edi']


def claude(argv, identity, skills, tools, request):
    # Claude Code's print-mode stream-json uses user, assistant, system and result messages.
    session = option(argv, '--resume' if '--resume' in argv else '--session-id')
    for line in sys.stdin:
        message = json.loads(line)
        if message['type'] == 'control_request':
            initialization = message['request']['subtype'] == 'initialize'
            write({
                'type': 'control_response',
                'response': {
                    'subtype': 'success',
                    'request_id': message['request_id'],
                    'response': {
                        'commands': [
                            {
                                'name': f'edi:{skill}',
                                'description': 'Bundled skill',
                                'argumentHint': '',
                            }
                            for skill in skills
                        ],
                        'models': [
                            {'value': 'sonnet', 'displayName': 'Sonnet', 'description': ''}
                        ],
                        'account': {'email': identity, 'subscriptionType': 'pro'},
                    }
                    if initialization
                    else {},
                },
            })
            if initialization:
                write({
                    'type': 'system',
                    'subtype': 'init',
                    'session_id': session,
                    'tools': ['Skill', *(f'mcp__edi__{name}' for name in tools)],
                    'mcp_servers': [{'name': 'edi', 'status': 'connected'}],
                    'model': 'sonnet',
                    'cwd': str(Path.cwd()),
                })
            continue
        if message['type'] != 'user':
            continue
        content = message['message']['content']
        prompt = (
            content
            if isinstance(content, str)
            else ' '.join(part['text'] for part in content if part['type'] == 'text')
        )
        observe('prompt', identity=identity, text=prompt, session=session)
        leaf = call_tool(request, prompt)
        write({
            'type': 'assistant',
            'session_id': session,
            'message': {
                'id': 'msg_offline_fixture',
                'type': 'message',
                'role': 'assistant',
                'model': 'sonnet',
                'content': [{'type': 'text', 'text': leaf}],
                'stop_reason': 'end_turn',
                'stop_sequence': None,
                'usage': {'input_tokens': 16, 'output_tokens': 8},
            },
        })
        write({
            'type': 'result',
            'subtype': 'success',
            'is_error': False,
            'result': leaf,
            'session_id': session,
            'num_turns': 1,
        })


def acp_update(session, **update):
    write({
        'jsonrpc': '2.0',
        'method': 'session/update',
        'params': {'sessionId': session, 'update': update},
    })


def copilot(argv, identity, skills, resources):
    # ACP v1 initialize, session/new, session/prompt and agent_message_chunk.
    session = identity + '-session'
    mcp_request = None
    for line in sys.stdin:
        request = json.loads(line)
        params = request.get('params', {})
        method = request.get('method')
        if method == 'initialize':
            observe('acp-client', capabilities=params.get('clientCapabilities', {}))
            result = {
                'protocolVersion': 1,
                'agentCapabilities': {'loadSession': True},
                'agentInfo': {'name': 'copilot', 'version': '1.0'},
                'authMethods': [],
            }
        elif method in {'session/new', 'session/load'}:
            if params.get('mcpServers'):
                raise ValueError('The same MCP server must not be installed twice')
            if mcp_request is None:
                _, mcp_request = resources.enter_context(
                    mcp_connection(mcp_config(argv, '--additional-mcp-config'))
                )
            result = (
                {'sessionId': session, 'configOptions': COPILOT_MODELS}
                if method == 'session/new'
                else {'configOptions': COPILOT_MODELS}
            )
            write(response(request, result))
            acp_update(
                session,
                sessionUpdate='available_commands_update',
                availableCommands=[
                    {'name': skill, 'description': 'Bundled skill'} for skill in skills
                ],
            )
            continue
        elif method == 'session/set_config_option':
            result = {'configOptions': COPILOT_MODELS}
        elif method == 'session/prompt':
            if params['sessionId'] != session:
                raise ValueError('ACP prompt used a different account session')
            prompt = ' '.join(part['text'] for part in params['prompt'] if part['type'] == 'text')
            observe('prompt', identity=identity, text=prompt, session=session)
            if mcp_request is None:
                raise ValueError('ACP prompt arrived before MCP discovery')
            acp_update(
                session,
                sessionUpdate='agent_message_chunk',
                content={'type': 'text', 'text': call_tool(mcp_request, prompt)},
            )
            result = {'stopReason': 'end_turn'}
        elif 'id' in request:
            write({
                'jsonrpc': '2.0',
                'id': request['id'],
                'error': {'code': -32601, 'message': 'Method not found'},
            })
            continue
        else:
            continue
        write(response(request, result))


def main():
    provider = sys.argv[1]
    argv = sys.argv[2:]
    home = os.environ['CLAUDE_CONFIG_DIR' if provider == 'claude' else 'COPILOT_HOME']
    account = Path(home) / 'fixture-account.txt'
    identity = account.read_text(encoding='utf-8').strip()
    skill_root = (
        Path(option(argv, '--plugin-dir')) / 'skills'
        if provider == 'claude' and '--plugin-dir' in argv
        else Path(os.environ.get('COPILOT_SKILLS_DIRS', '/nonexistent'))
    )
    skills = {
        skill.parent.name: skill.read_text(encoding='utf-8')
        for skill in sorted(skill_root.glob('*/SKILL.md'))
    }
    gh_config = os.environ.get('GH_CONFIG_DIR')
    observe(
        'launch',
        argv=argv,
        home=home,
        credentials=sorted(CREDENTIALS.intersection(os.environ)),
        updates_disabled=os.environ.get('DISABLE_UPDATES'),
        gh_config_empty=bool(
            gh_config and Path(gh_config).is_dir() and not any(Path(gh_config).iterdir())
        ),
        skills=skills,
    )
    if argv[:2] == ['auth', 'status']:
        write({'loggedIn': True, 'authMethod': 'claude.ai', 'email': identity})
    elif argv[:2] == ['auth', 'login'] or argv[:1] == ['login']:
        return
    else:
        with ExitStack() as resources:
            if provider == 'claude':
                names, request = resources.enter_context(
                    mcp_connection(mcp_config(argv, '--mcp-config'))
                )
                claude(argv, identity, skills, names, request)
            else:
                copilot(argv, identity, skills, resources)


if __name__ == '__main__':
    main()
