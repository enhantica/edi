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
CLAUDE_KEY = 'ANTHROPIC_API_KEY'
KEY_SENTINEL = 'fixture-api-key-never-displayed'


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
    # Offline readback from the pinned Claude CLI: both controls precede the first user message.
    session = option(argv, '--resume' if '--resume' in argv else '--session-id')
    qualified_tools = [f'mcp__edi__{name}' for name in tools]
    init_sent = False
    pending = os.environ.get('EDI_PROVIDER_TEST_SCENARIO') == 'pending-mcp'
    for line in sys.stdin:
        message = json.loads(line)
        if message['type'] == 'control_request':
            subtype = message['request']['subtype']
            if subtype == 'initialize':
                reply = {
                    'commands': [
                        {
                            'name': f'edi:{skill}',
                            'description': 'Bundled skill',
                            'argumentHint': '',
                        }
                        for skill in skills
                    ],
                    'models': [{'value': 'sonnet', 'displayName': 'Sonnet', 'description': ''}],
                    'account': {'email': identity, 'subscriptionType': 'pro'},
                }
                observe('claude-readback', identity=identity, session=session)
            elif subtype == 'mcp_status':
                status = 'pending' if pending else 'connected'
                server = {'name': 'edi', 'status': status, 'transport': 'stdio'}
                if not pending:
                    server['tools'] = [{'name': name, 'annotations': {}} for name in tools]
                observe('claude-mcp-status', status=status, session=session)
                pending = False
                reply = {'mcpServers': [server]}
            elif subtype == 'get_context_usage':
                reply = {
                    'categories': [
                        {'id': 'system_prompt', 'name': 'System prompt', 'kind': 'used'},
                        {'id': 'mcp_tools', 'name': 'MCP tools', 'kind': 'used'},
                        {'id': 'skills', 'name': 'Skills', 'kind': 'used'},
                    ],
                    'mcpTools': [
                        {'name': name, 'serverName': 'edi', 'tokens': 35, 'isLoaded': False}
                        for name in qualified_tools
                    ],
                }
            else:
                reply = {}
            observe('claude-control', subtype=subtype, session=session)
            write({
                'type': 'control_response',
                'response': {
                    'subtype': 'success',
                    'request_id': message['request_id'],
                    'response': reply,
                },
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
        if not init_sent:
            init_sent = True
            observe('claude-init', session=session)
            write({
                'type': 'system',
                'subtype': 'init',
                'session_id': session,
                'tools': ['Skill', *qualified_tools],
                'mcp_servers': [{'name': 'edi', 'status': 'connected'}],
                'plugins': [{'name': 'edi', 'path': option(argv, '--plugin-dir')}],
                'skills': [f'edi:{skill}' for skill in skills],
                'apiKeySource': 'user' if CLAUDE_KEY in os.environ else 'none',
                'model': 'sonnet',
                'cwd': str(Path.cwd()),
            })
        leaf = call_tool(request, prompt)
        write({
            'type': 'assistant',
            'session_id': session,
            'parent_tool_use_id': None,
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


def copilot_prompt(session, identity, mcp_request, prompt, scenario):
    if prompt.startswith('/user switch ') or prompt == '/user show':
        observe('account-command', text=prompt, session=session)
        if prompt == '/user show':
            login = 'different-user' if scenario == 'wrong-login' else identity
            host = 'other.ghe.com' if scenario == 'wrong-host' else 'github.com'
            observe('copilot-identity', login=login, host=host, session=session)
            acp_update(
                session,
                sessionUpdate='agent_message_chunk',
                content={'type': 'text', 'text': f'Signed in as @{login} on {host}'},
            )
        return
    observe('prompt', identity=identity, text=prompt, session=session)
    if mcp_request is None:
        raise ValueError('ACP prompt arrived before MCP discovery')
    if scenario == 'foreign-tool':
        call = {
            'toolCallId': 'fixture-foreign-call',
            'title': 'Unlisted fixture tool',
            'name': 'fixture_unlisted_tool',
            'kind': 'other',
            'status': 'pending',
        }
        write({
            'jsonrpc': '2.0',
            'id': 'fixture-permission',
            'method': 'session/request_permission',
            'params': {
                'sessionId': session,
                'toolCall': call,
                'options': [
                    {'optionId': 'yes', 'name': 'Allow once', 'kind': 'allow_once'},
                    {'optionId': 'no', 'name': 'Reject once', 'kind': 'reject_once'},
                ],
            },
        })
        answer = json.loads(sys.stdin.readline())
        if answer.get('id') != 'fixture-permission':
            raise ValueError('ACP must correlate the tool permission answer')
        observe('copilot-permission', outcome=answer.get('result', {}).get('outcome'))
        observe('copilot-foreign-tool', session=session)
        acp_update(session, sessionUpdate='tool_call', **{**call, 'status': 'in_progress'})
        return
    acp_update(
        session,
        sessionUpdate='agent_message_chunk',
        content={'type': 'text', 'text': call_tool(mcp_request, prompt)},
    )


def copilot(argv, identity, skills, resources):
    # ACP v1 initialize, session/new, session/prompt and agent_message_chunk.
    session = identity + '-session'
    scenario = os.environ.get('EDI_PROVIDER_TEST_SCENARIO', '')
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
                    {'name': 'user', 'description': 'Account actions'},
                    *({'name': skill, 'description': 'Bundled skill'} for skill in skills),
                ],
            )
            continue
        elif method == 'session/set_config_option':
            result = {'configOptions': COPILOT_MODELS}
        elif method == 'session/prompt':
            if params['sessionId'] != session:
                raise ValueError('ACP prompt used a different account session')
            prompt = ' '.join(part['text'] for part in params['prompt'] if part['type'] == 'text')
            copilot_prompt(session, identity, mcp_request, prompt, scenario)
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
        fixture_key_intact=os.environ.get(CLAUDE_KEY) == KEY_SENTINEL,
        updates_disabled=os.environ.get('DISABLE_UPDATES'),
        gh_config_empty=bool(
            gh_config and Path(gh_config).is_dir() and not any(Path(gh_config).iterdir())
        ),
        skills=skills,
    )
    if argv[:2] == ['auth', 'status']:
        write({
            'loggedIn': True,
            'authMethod': 'api-key' if CLAUDE_KEY in os.environ else 'claude.ai',
            'configDirectory': home,
        })
    elif argv[:2] == ['auth', 'login']:
        observe('claude-login-opened', pid=os.getpid())
        print('Opening browser: https://claude.ai/oauth/authorize', flush=True)
        print('Paste the sign-in code', flush=True)
        if sys.stdin.readline().strip() != 'offline-fixture-code':
            raise ValueError('The original Claude login must receive the fixture callback')
        observe('claude-login-completed', pid=os.getpid())
    elif argv[:1] == ['login']:
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
