"""Bounded argv contracts for  transports; unknown forms record and refuse."""

from pathlib import Path

# Embedded in subprocess substitutes so admission always precedes side effects.
COMMANDS = r'''
import json as _json, os as _os, sys as _sys, re as _re
from pathlib import Path as _Path
from urllib.parse import urlsplit as _urlsplit, parse_qs as _parse_qs


def command_refuse(why):
    root = next(
        (
            _os.environ[k]
            for k in (
                'E09_T75_RECORDS',
                'GUARD_FIXTURE',
                'SDK_FIXTURE',
                'UPDATE_FIXTURE',
                'FLOAT_TEST_ROOT',
                'DOWNLOAD_FIXTURE',
            )
            if k in _os.environ
        ),
        None,
    )
    if root:
        with (_Path(root) / 'unsupported-commands.jsonl').open('a') as output:
            output.write(_json.dumps([_sys.argv, why]) + '\n')
    print(' unsupported command form: ' + why, file=_sys.stderr)
    raise SystemExit(64)


def admit_args(args, valued=(), switches=(), counts=(0,), repeated=()):
    """Admit whole argv, normalize only supported operand forms, preserve order."""
    normalized = []
    operands = []
    seen = set()
    i = 0
    while i < len(args):
        token = args[i]
        i += 1
        key, sep, value = token.partition('=')
        if key not in valued and not sep:
            key = next(
                (
                    flag
                    for flag in valued
                    if len(flag) == 2 and token.startswith(flag) and len(token) > 2
                ),
                key,
            )
            if key != token:
                value = token[len(key) :]
                sep = 'attached'
        if key in valued:
            aliases = [
                pair
                for pair in (
                    ('--method', '-X'),
                    ('--write-out', '-w'),
                    ('--data', '-d'),
                    ('--request', '-X'),
                    ('--output', '-o'),
                    ('--repo', '-R'),
                    ('--header', '-H'),
                    ('--jq', '-q'),
                    ('--head', '-H'),
                    ('--base', '-B'),
                    ('--state', '-s'),
                    ('--limit', '-L'),
                    ('--workflow', '-w'),
                    ('--job', '-j'),
                    ('--pattern', '-p'),
                    ('--dir', '-D'),
                    ('--ref', '-r'),
                )
                if key in pair and set(pair) <= set(valued)
            ]
            canonical = aliases[0][0] if aliases else key
            if canonical in seen and key not in repeated and canonical not in repeated:
                command_refuse('duplicate semantic option ' + key)
            if key in seen and key not in repeated:
                command_refuse('duplicate ' + key)
            seen.add(key)
            seen.add(canonical)
            if not sep:
                if i == len(args) or args[i].startswith('-'):
                    command_refuse('missing operand ' + key)
                value = args[i]
                i += 1
            normalized.extend([canonical, value])
            continue
        if token in switches:
            if token in seen:
                command_refuse('duplicate ' + token)
            seen.add(token)
            normalized.append(token)
            continue
        if token.startswith('-'):
            command_refuse('unlisted option ' + token)
        normalized.append(token)
        operands.append(token)
    if counts is not None and len(operands) not in counts:
        command_refuse('positional shape ' + repr(operands))
    return normalized


# Each route definition owns both complete-form admission and its response effect.
# A new form cannot acquire JSON by falling through a handler's print statement.
def _option(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default


def _json_effect(value):
    return _json.dumps(value) + '\n'


def _project_effect(fields, query):
    def render(value):
        def project(row):
            # CLI spellings differ from REST; conversion is explicit, never full-record output.
            aliases = {'tagName': 'tag_name', 'isPrerelease': 'prerelease'}
            out = {}
            for key in fields:
                if key in row:
                    out[key] = row[key]
                elif key in aliases and aliases[key] in row:
                    out[key] = row[aliases[key]]
                elif key == 'headRefName' and 'head' in row:
                    out[key] = row['head']['ref']
                elif key == 'headRefOid' and 'head' in row:
                    out[key] = row['head']['sha']
                else:
                    command_refuse('unrepresented projected field ' + key)
            return out

        value = [project(row) for row in value] if isinstance(value, list) else project(value)
        if query == '.headRefName + " " + .baseRefName':
            return value['headRefName'] + ' ' + value['baseRefName'] + '\n'
        return _json_effect(value)

    return render


def _cli_json(args, fields):
    selected = _option(args, '--json')
    if not selected or selected not in fields:
        command_refuse('this CLI response requires its declared JSON projection')
    query = _option(args, '--jq')
    if query is not None and (selected, query) != (
        'headRefName,baseRefName',
        '.headRefName + " " + .baseRefName',
    ):
        command_refuse('unrepresented CLI query')
    return _project_effect(selected.split(','), query)


def _cli_list(args, fields, default):
    render = _cli_json(args, fields)
    limit = _option(args, '--limit', str(default))
    if not limit.isdigit() or int(limit) < 1:
        command_refuse('unrepresented CLI inventory limit')
    return lambda rows: render(rows[:int(limit)])


def _release_list(args):
    return _cli_list(args, {'tagName'}, 30)


def _delete_release(args):
    if not ({'--yes', '-y'} & set(args)):
        command_refuse('unrepresented interactive release deletion')
    return _silent(args)


def _release_text(args):
    # `release view` is used only as an existence probe. Preserve a human-text
    # representation; callers cannot parse the convenient REST fixture as JSON.
    return lambda value: 'release ' + value.get('tag_name', value.get('tagName', '')) + '\n'


def _silent(args):
    return lambda value: ''


def _plain_diff(args):
    return lambda value: value


_CLI_FORMS = {
    ('pr', 'view'): (
        ('--repo', '-R', '--json', '--jq', '-q'),
        (),
        (1,),
        lambda a: _cli_json(
            a,
            {
                'number,state,headRefName,headRefOid',
                'headRefName,baseRefName',
                'state,mergeCommit',
            },
        ),
    ),
    ('pr', 'list'): (
        (
            '--repo',
            '-R',
            '--json',
            '--head',
            '-H',
            '--base',
            '-B',
            '--state',
            '-s',
            '--limit',
            '-L',
        ),
        (),
        (0,),
        lambda a: _cli_list(a, {'number', 'number,headRefOid', 'number,headRefName'}, 30),
    ),
    ('run', 'list'): (
        ('--repo', '-R', '--workflow', '-w', '--branch', '--event', '--limit', '-L', '--json'),
        (),
        (0,),
        lambda a: _cli_list(a, {'headSha'}, 20),
    ),
    ('repo', 'view'): (
        ('--repo', '-R', '--json'),
        (),
        (0, 1),
        lambda a: _cli_json(a, {'nameWithOwner', 'name'}),
    ),
    ('pr', 'diff'): (('--repo', '-R'), (), (1,), _plain_diff),
    ('release', 'list'): (('--repo', '-R', '--json'), (), (0,), _release_list),
    ('release', 'view'): (('--repo', '-R'), (), (1,), _release_text),
    ('release', 'download'): (
        ('--repo', '-R', '--dir', '-D', '--pattern', '-p'),
        (),
        (1,),
        _silent,
    ),
    ('release', 'delete'): (
        ('--repo', '-R'),
        ('--yes', '-y', '--cleanup-tag'),
        (1,),
        _delete_release,
    ),
    ('workflow', 'run'): (('--repo', '-R', '--ref', '-r'), (), (1,), _silent),
}


def _api_form(args):
    global _gh_api_request
    endpoints = [x for x in args[1:] if x.startswith(('repos/', '/repos/', 'search/', 'https://'))]
    if len(endpoints) != 1:
        command_refuse('one API endpoint required')
    url = _urlsplit(endpoints[0])
    if url.netloc and (url.scheme, url.netloc) != ('https', 'api.github.com'):
        command_refuse('foreign API host')
    path = url.path.lstrip('/')
    query = _parse_qs(url.query, keep_blank_values=True)
    for i, flag in enumerate(args[:-1]):
        if flag in ('--field', '-f', '--raw-field', '-F'):
            key, sep, value = args[i + 1].partition('=')
            if not sep or key in query:
                command_refuse('ambiguous API field')
            query[key] = [value]
    if any(len(v) != 1 for v in query.values()):
        command_refuse('repeated API selector')
    q = {k: v[0] for k, v in query.items()}
    _gh_api_request = {'path': path, 'fields': q}
    collection = path.endswith(('/releases', '/files')) or path == 'search/issues'
    job_pages = path.endswith('/jobs') and '--paginate' in args
    if job_pages and args != ['api', '--paginate', '--slurp', path + '?filter=all']:
        command_refuse('unrepresented jobs page-array request')
    allowed = (
        {'per_page', 'page'}
        if path.endswith(('/runs', '/jobs', '/check-runs', '/commits', '/pulls', '/files'))
        else set()
    )
    if path.endswith('/runs'):
        allowed |= {'head_sha', 'event', 'branch'}
    if path.endswith('/pulls'):
        allowed |= {'head', 'base', 'state'}
    if path.endswith(('/check-runs', '/jobs')):
        allowed |= {'filter'}
        if q.get('filter', 'latest') not in ('latest', 'all'):
            command_refuse('unknown check-run filter')
    if path == 'search/issues':
        allowed = {'q', 'page', 'per_page'}
        if q.get('q', '').split() != ['repo:enhantica/edi', 'is:pr', 'is:open']:
            command_refuse('unrepresented search qualifiers')
    if path.endswith('/contents/pixi.toml'):
        allowed = {'ref'}
    if path.endswith('/merge'):
        allowed = {'sha', 'merge_method'}
        if not q.get('sha') or q.get('merge_method', 'merge') != 'squash':
            command_refuse('unrepresented merge mode or absent expected head')
    if path.endswith('/dispatches'):
        allowed = {'ref'}
    if set(q) - allowed:
        command_refuse('unrepresented API selector')
    for key in ('page', 'per_page'):
        if key in q and (
            not q[key].isdigit() or int(q[key]) < 1 or key == 'per_page' and int(q[key]) > 100
        ):
            command_refuse('unrepresented page range')
    if (('--paginate' in args) != ('--slurp' in args)
            or '--paginate' in args and not (collection or job_pages)):
        command_refuse('unrepresented page-array form')
    if '--paginate' in args and 'page' in q:
        command_refuse('explicit start page with automatic pagination')
    jq = _option(args, '--jq')
    if jq is not None and (path, jq) != ('repos/enhantica/edi', '.allow_forking'):
        command_refuse('unrepresented API query')
    binary = '/releases/assets/' in path
    for i, flag in enumerate(args[:-1]):
        if flag != '--header':
            continue
        name, sep, value = args[i + 1].partition(':')
        if not sep:
            command_refuse('malformed API header')
        name, value = name.lower(), value.strip().lower()
        permitted = (
            {'application/octet-stream'}
            if binary
            else {'application/vnd.github+json', 'application/json'}
        )
        if name == 'accept' and value in permitted:
            continue
        if name == 'x-github-api-version' and value == '2022-11-28':
            continue
        command_refuse('unrepresented API header/representation')
    if binary and not any(
        x.lower().replace(' ', '') == 'accept:application/octet-stream' for x in args
    ):
        command_refuse('binary asset requires octet-stream')
    if '--allow-escape-sequences' in args and not path.endswith('/logs'):
        command_refuse('raw log option on another resource')
    if path.endswith('/logs') and '--allow-escape-sequences' not in args:
        command_refuse('raw logs require the declared output form')

    def render(value):
        if binary:
            return value  # bytes, never a JSON asset record
        if path.endswith('/logs'):
            return value
        if job_pages:
            rows = value['jobs']
            pages = [{**value, 'jobs': rows[i:i + 30]} for i in range(0, len(rows), 30)]
            return _json_effect(pages or [{**value, 'jobs': []}])
        if collection:
            size = int(q.get('per_page', 30))
            page = int(q.get('page', 1))
            start = (page - 1) * size
            if isinstance(value, list):
                pages = [value[i : i + size] for i in range(0, len(value), size)] or [[]]
                value = pages if '--slurp' in args else value[start : start + size]
            elif path == 'search/issues':
                rows = value['items']
                pages = [
                    {**value, 'items': rows[i : i + size]} for i in range(0, len(rows), size)
                ] or [{**value, 'items': []}]
                value = (
                    pages if '--slurp' in args else {**value, 'items': rows[start : start + size]}
                )
            else:
                command_refuse('collection response shape')
        if jq:
            return _json_effect(value['allow_forking'])
        return _json_effect(value)

    return render


def gh_release_create_request():
    return _gh_release_create_request


def _release_create_form(args):
    global _gh_release_create_request
    # The one complete production spelling, before normalization can erase roles.
    if (
        len(args) < 11
        or args[:2] != ['release', 'create']
        or args[3] != '--target'
        or args[5:7] != ['--prerelease', '--title']
        or args[8] != '--notes'
        or args[2] != 'build-' + args[4]
        or args[7] != args[2]
        or not __import__('re').fullmatch(
            r'crysta SDK built and tested by run [0-9]+/[0-9]+', args[9]
        )
        or any(x.startswith('-') or '#' in x for x in args[10:])
    ):
        command_refuse('unrepresented complete release-create argv')
    _gh_release_create_request = {
        'tag': args[2], 'target': args[4], 'title': args[7], 'notes': args[9],
        'prerelease': True, 'assets': args[10:],
    }
    return _silent(args)


def _complete(args, *forms):
    # None denotes exactly one operand; flags and option order remain literal.
    # No alternate flag syntax or reordered request is inferred from a parser.
    return any(
        len(args) == len(form)
        and all(a == want if want is not None else bool(a) and not a.startswith('-')
                for a, want in zip(args, form))
        for form in forms
    )


def _emitted_gh(args):
    if args[:2] == ['release', 'create']:
        return  # separately owns its complete metadata/asset roles
    if args[:2] == ['release', 'download']:
        tail = args[5:]
        if (_complete(args[:5], ['release', 'download', None, '--dir', None])
                and tail and len(tail) % 2 == 0
                and all(_complete(tail[i:i+2], ['--pattern', None])
                        for i in range(0, len(tail), 2))):
            return
        command_refuse('unrepresented complete release-download argv')
    forms = [
        ['api', None],
        ['api', None, '--allow-escape-sequences'],
        ['api', '--paginate', '--slurp', 'repos/enhantica/crysta/releases'],
        ['api', 'repos/enhantica/edi', '--jq', '.allow_forking'],
        ['api', '--paginate', '--slurp', '-X', 'GET', 'search/issues', '-f',
         'q=repo:enhantica/edi is:pr is:open'],
        ['api', '--method', 'PUT', None, '-f', 'merge_method=squash', '-f', None],
        ['pr', 'view', None, '--json', None],
        ['pr', 'view', None, '--repo', None, '--json', None],
        ['pr', 'diff', None],
        ['pr', 'list', '--repo', None, '--state', None, '--json', None, '--head', None],
        ['pr', 'list', '--repo', None, '--base', 'main', '--json', 'number,headRefOid',
         '--head', None, '--state', None],
        ['run', 'list', '--workflow', 'ci.yml', '--event', 'workflow_dispatch', '--json',
         'headSha', '--limit', '50', '--branch', None],
        ['workflow', 'run', 'ci.yml', '--ref', None],
        ['release', 'view', None],
        ['release', 'delete', None, '--cleanup-tag', '--yes'],
    ]
    if len(args) == 4 and _re.fullmatch(
        r'repos/enhantica/(crysta|edi)/actions/runs/[0-9]+/jobs\?filter=all', args[-1]
    ):
        forms.append(['api', '--paginate', '--slurp', args[-1]])
    if not _complete(args, *forms):
        command_refuse('unrepresented complete gh argv')


def admit_gh(args):
    global _gh_effect
    if not args:
        command_refuse('empty gh')
    _emitted_gh(args)
    if args[:2] == ['release', 'create']:
        _gh_effect = _release_create_form(args)
        return args
    if args[0] == 'api':
        selected = [
            'api',
            *admit_args(
                args[1:],
                (
                    '--method',
                    '-X',
                    '--header',
                    '-H',
                    '--field',
                    '-f',
                    '--raw-field',
                    '-F',
                    '--jq',
                    '-q',
                ),
                ('--paginate', '--slurp', '--allow-escape-sequences'),
                (1,),
                ('--header', '-H', '--field', '-f', '--raw-field', '-F'),
            ),
        ]
        _gh_effect = _api_form(selected)
        return selected
    key = tuple(args[:2])
    if key not in _CLI_FORMS:
        command_refuse('unrepresented CLI route')
    valued, switches, count, effect = _CLI_FORMS[key]
    selected = [*args[:2], *admit_args(args[2:], valued, switches, count, ('--pattern', '-p'))]
    _gh_effect = effect(selected)  # required flags/defaults are checked before handler effects
    return selected


def gh_api_request():
    # This is the same admitted request captured by the renderer.
    return _gh_api_request


def emit_gh(value):
    output = _gh_effect(value)
    if isinstance(output, bytes):
        _sys.stdout.buffer.write(output)
    else:
        _sys.stdout.write(output)


def admit_curl(args, dispatch=False):
    global _curl_effect
    forms = (
        ['-fsS', '-H', None, '-H', 'Accept: application/vnd.github+json',
         'https://api.github.com/installation/repositories'],
        ['-fsSL', '--retry', '3', '-H', None, '-H', None, None],
        ['-fsSL', '--retry', '3', '-H', None, '-H', None, '-o', None, None],
        ['-sS', '-o', None, '-w', '%{http_code}', '-X', 'POST', '-H', None,
         '-H', 'Accept: application/vnd.github+json', '-H', 'X-GitHub-Api-Version: 2022-11-28',
         'https://api.github.com/repos/enhantica/edi/actions/workflows/crysta-sdk-update.yml/dispatches',
         '-d', '{"ref":"main"}'],
    )
    if not _complete(args, *forms):
        command_refuse('unrepresented complete curl argv')
    selected = admit_args(
        args,
        (
            '-X',
            '--request',
            '-o',
            '--output',
            '-H',
            '--header',
            '--retry',
            '-d',
            '--data',
            '--data-raw',
            '-w',
            '--write-out',
        )
        if dispatch
        else ('-X', '--request', '-o', '--output', '-H', '--header', '--retry'),
        (
            '-f',
            '-s',
            '-S',
            '-L',
            '-fsS',
            '-fsSL',
            '-sS',
            '-sSL',
            '--fail',
            '--silent',
            '--show-error',
            '--location',
        ),
        (1,),
        ('-H', '--header'),
    )
    if _option(selected, '--retry', '3') != '3':
        command_refuse('unrepresented retry policy')
    fmt = _option(selected, '--write-out')
    formats = {'%{http_code}': lambda status: str(status), '%{exitcode}': lambda status: '0'}
    if fmt is not None and fmt not in formats:
        command_refuse('unrepresented write-out format')
    urls = [v for v in selected if v.startswith('https://')]
    if len(urls) != 1:
        command_refuse('one curl resource required')
    binary = '/releases/assets/' in urls[0] or urls[0].startswith('https://fixture.invalid/')
    for i, flag in enumerate(selected[:-1]):
        if flag != '--header':
            continue
        name, sep, value = selected[i + 1].partition(':')
        name, value = name.lower(), value.strip().lower()
        if name == 'authorization' and value.startswith('bearer '):
            continue
        if name == 'accept' and value in (
            {'application/octet-stream'}
            if binary
            else {'application/vnd.github+json', 'application/json'}
        ):
            continue
        if name == 'x-github-api-version' and value == '2022-11-28':
            continue
        command_refuse('unrepresented curl header/representation')
    output = _option(selected, '--output')

    def render(payload, status):
        if output and output != '-':
            try:
                _Path(output).write_bytes(payload)
            except OSError:
                raise SystemExit(23)  # curl write failure; never invent --create-dirs
        else:
            _sys.stdout.buffer.write(payload)
        if fmt is not None:
            _sys.stdout.write(formats[fmt](status))

    _curl_effect = render
    return selected


def emit_curl(payload, status=200):
    _curl_effect(payload, status)


def admit_remote_git(args):
    i = next(
        (i for i, x in enumerate(args) if x in ('fetch', 'ls-remote', 'push', 'clone', 'pull')),
        None,
    )
    if i is None:
        return args  # delegated local Git executes its real semantics
    prefix = admit_args(args[:i], ('-C', '-c'), (), (0,))
    for index, flag in enumerate(prefix[:-1]):
        if flag == '-c' and prefix[index + 1] != 'http.https://github.com/.extraheader=':
            command_refuse('unlisted remote Git configuration')
    route = args[i]
    switches = {
        'fetch': ('-q', '--quiet'),
        'ls-remote': ('--heads',),
        'push': ('--delete',),
        'clone': (
            '--mirror',
            '--bare',
            '--no-checkout',
            '--no-single-branch',
            '-q',
            '--quiet',
        ),
    }
    if route not in switches:
        command_refuse('unlisted git operation ' + route)
    selected = admit_args(
        args[i + 1 :], ('--filter',) if route == 'clone' else (), switches[route], (2,)
    )
    if '--filter' in selected and selected[selected.index('--filter') + 1] != 'blob:none':
        command_refuse('unlisted clone filter')
    return [*prefix, route, *selected]


def admit_cmake(args):
    if args[:1] == ['--build']:
        tail = args[2:]
        if tail == ['--target', 'crysta_core', 'crysta_cli', 'crysta_tests', '-j']:
            return args
        command_refuse('unlisted CMake build form')
    if args[:1] == ['--install']:
        selected = admit_args(args, ('--install', '--prefix', '--config'), (), (0,))
        if '--prefix' not in selected:
            command_refuse('unlisted implicit package install prefix')
        if '--config' in selected and selected[selected.index('--config') + 1] != 'Release':
            command_refuse('unlisted package install configuration')
        return selected
    definitions = {
        'CMAKE_BUILD_TYPE': 'Release',
        'CRYSTA_CXX_PACKAGE': 'ON',
        'CRYSTA_LTO': 'OFF',
        'CRYSTA_SANITIZE': 'OFF',
        'CRYSTA_COVERAGE': 'OFF',
        'CRYSTA_LLVM_COVERAGE': 'OFF',
        'CMAKE_OSX_DEPLOYMENT_TARGET': None,
    }
    selected = {}
    rest = []
    for a in args:
        if a.startswith('-D'):
            k, sep, v = a[2:].partition('=')
            if not sep or k not in definitions or k in selected:
                command_refuse('unlisted CMake definition ' + a)
            if definitions[k] is not None and v != definitions[k]:
                command_refuse('wrong package definition ' + a)
            selected[k] = v
        else:
            rest.append(a)
    admit_args(rest, ('-S', '-B', '-G'), (), (0,))
    if (
        set(selected) != set(definitions)
        or len(rest) != 6
        or rest[rest.index('-G') + 1] != 'Ninja'
    ):
        command_refuse('incomplete CMake configure form')
    return args


def admit_cpp(args):
    return (
        admit_args(args, ('--build-dir',), (), (0,))
        if len(args) == 2
        else command_refuse('unlisted C++ tier form')
    )


def admit_ctest(args):
    selected = admit_args(
        args, ('--test-dir', '-C', '--build-config'), ('--output-on-failure',), (0,)
    )
    if '--test-dir' not in selected:
        command_refuse('unlisted implicit CTest tree')
    for flag in ('-C', '--build-config'):
        if flag in selected and selected[selected.index(flag) + 1] != 'Release':
            command_refuse('unlisted qualification configuration')
    return selected


def admit_corpus(args):
    if args[:2] != ['-m', 'pytest']:
        command_refuse('unlisted corpus interpreter form')
    values = [x for x in args[2:] if not x.startswith('--junitxml=')]
    if (
        values != ['-q', '-p', 'no:cacheprovider', 'tests/fitting/test_fitting_cases.py']
        or sum(x.startswith('--junitxml=') for x in args) != 1
    ):
        command_refuse('unlisted complete corpus form')
    return args
'''


def checked_program(program, tool):
    """Insert admission at the raw argv boundary, before any route grants an effect."""
    needle = 'a = sys.argv[1:]' if 'a = sys.argv[1:]' in program else 'a=sys.argv[1:]'
    validator = {
        'gh': 'admit_gh(a)',
        'cmake': 'admit_cmake(a)',
        'ctest': 'admit_ctest(a)',
        'cpp': 'admit_cpp(a)',
        'corpus': 'admit_corpus(a)',
        'git': 'admit_remote_git(a)',
        'curl': "admit_curl(a, any('/dispatches' in v for v in a))",
    }[tool]
    assert program.count(needle) == 1, (
        ' every substitute must expose exactly one raw argv admission boundary'
    )
    checked = program.replace(needle, COMMANDS + '\n' + needle + '\na=' + validator, 1)
    return checked.replace(
        'sys.exit(64)', "command_refuse('unsupported route resource or operation')"
    )


def assert_no_swallowed_refusal(root, success):
    assert not success or not (Path(root) / 'unsupported-commands.jsonl').exists(), (
        ' an unsupported command form must remain a gate red even when a caller swallows its exit'
    )
