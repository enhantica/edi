"""Independent execution-path checks for the temporary CI policy."""

# ruff: noqa: PLR1702, PLW0717
# The literal temporary paths are shell-trace inputs; intercepted collectors write nothing there.

from __future__ import annotations

import fnmatch
import itertools
import json
import math
import re
import shlex
import subprocess
import tempfile
import tomllib

import yaml


def actions_number(item):
    if item is None:
        return 0.0
    if type(item) in {bool, int, float}:
        return float(item)
    if isinstance(item, str):
        if not item.isascii():
            message = 'unsupported non-ASCII Actions numeric coercion'
            raise ValueError(message)
        item = item.strip(' \t\r\n\v\f')
        if not item:
            return 0.0
        if re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', item):
            parsed = float(item)
            if math.isfinite(parsed):
                return parsed
            message = 'unsupported nonfinite Actions numeric coercion'
            raise ValueError(message)
        if item.lower().startswith(('0x', '0o')) or item.lower() in {
            'nan',
            'infinity',
            '+infinity',
            '-infinity',
        }:
            message = 'unsupported Actions numeric coercion form'
            raise ValueError(message)
    return math.nan


def actions_casefold(item):
    if not item.isascii():
        message = 'unsupported non-ASCII Actions case identity'
        raise ValueError(message)
    return item.lower()


def actions_equal(left, right):
    if isinstance(left, str) and isinstance(right, str):
        return actions_casefold(left) == actions_casefold(right)
    if type(left) is type(right):
        return left == right
    return actions_number(left) == actions_number(right)


def actions_truthy(item):
    return False if type(item) is float and math.isnan(item) else bool(item)


def actions_string(item):
    if item is None:
        return ''
    if isinstance(item, bool):
        return 'true' if item else 'false'
    if isinstance(item, str):
        return item
    if (
        type(item) in {int, float}
        and math.isfinite(item)
        and item == int(item)
        and abs(item) <= 2**53
    ):
        return str(int(item))
    message = 'unsupported Actions string conversion'
    raise ValueError(message)


def expression_tokens(text, ctx):
    # Scan literals before identifiers/operators: never rewrite their contents.
    grammar = re.compile(
        r"\s+|'(?:[^']|'')*'|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?"
        r'|[A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_-]*)*(?:\(\))?'
        r'|&&|\|\||==|!=|[!()]'
    )
    tokens, index = [], 0
    constants = {
        'true': True,
        'false': False,
        'null': None,
        'always()': True,
        'success()': True,
        'failure()': False,
        'cancelled()': False,
    }
    while index < len(text):
        match = grammar.match(text, index)
        if match is None:
            message = 'unsupported Actions expression syntax'
            raise ValueError(message)
        token = match[0]
        index = match.end()
        if token.isspace():
            continue
        if token in {'&&', '||', '==', '!=', '!', '(', ')'}:
            tokens.append((token, None))
            continue
        if token.startswith("'"):
            item = token[1:-1].replace("''", "'")
        elif token in constants:
            item = constants[token]
        elif token in ctx:
            item = ctx[token]
        elif token[0].isdigit() or token.startswith('-'):
            item = json.loads(token)
        else:
            message = 'unsupported Actions expression property/function: ' + token
            raise ValueError(message)
        if (
            type(item) not in {type(None), bool, int, float, str}
            or (type(item) is int and abs(item) > 2**53)
            or (type(item) is float and not math.isfinite(item))
        ):
            message = 'unsupported Actions expression value'
            raise ValueError(message)
        tokens.append(('atom', item))
    return tokens


def actions_expression(text, ctx):
    tokens = expression_tokens(text, ctx)
    precedence = {'||': 1, '&&': 2, '==': 3, '!=': 3}
    index = 0

    def parse(minimum=0):
        nonlocal index
        if index == len(tokens):
            message = 'missing Actions expression operand'
            raise ValueError(message)
        kind, item = tokens[index]
        index += 1
        if kind == 'atom':
            node = ('atom', item)
        elif kind == '!':
            node = ('!', parse(4))
        elif kind == '(':
            node = parse()
            if index == len(tokens) or tokens[index][0] != ')':
                message = 'unclosed Actions expression group'
                raise ValueError(message)
            index += 1
        else:
            message = 'unsupported Actions expression operand'
            raise ValueError(message)
        while index < len(tokens) and precedence.get(tokens[index][0], -1) >= minimum:
            operator = tokens[index][0]
            if operator in {'==', '!='} and node[0] in {'==', '!='}:
                message = 'unsupported chained Actions comparison'
                raise ValueError(message)
            index += 1
            node = (operator, node, parse(precedence[operator] + 1))
        return node

    def evaluate(node):
        operator = node[0]
        if operator == 'atom':
            return node[1]
        if operator == '!':
            return not actions_truthy(evaluate(node[1]))
        left = evaluate(node[1])
        if operator == '&&':
            return evaluate(node[2]) if actions_truthy(left) else left
        if operator == '||':
            return left if actions_truthy(left) else evaluate(node[2])
        equal = actions_equal(left, evaluate(node[2]))
        return equal if operator == '==' else not equal

    tree = parse()
    if index != len(tokens):
        message = 'unsupported trailing Actions expression'
        raise ValueError(message)
    return evaluate(tree)


def value(source, ctx):
    if source is None or isinstance(source, bool):
        return True if source is None else source
    text = str(source).strip().removeprefix('${{').removesuffix('}}').strip()
    return actions_expression(text, ctx)


def render(source, ctx):
    return re.sub(
        r'\$\{\{(.*?)\}\}',
        lambda match: actions_string(value(match[1], ctx)),
        actions_string(source),
    )


def runner_labels(source, ctx):
    if isinstance(source, str):
        match = re.fullmatch(r'\$\{\{\s*([\w.-]+)\s*\}\}', source)
        if match and match[1] in ctx:
            source = ctx[match[1]]
    if isinstance(source, list):
        if not all(isinstance(label, str) for label in source):
            message = 'unsupported structured runner labels'
            raise ValueError(message)
        return ' '.join(render(label, ctx) for label in source)
    return render(source, ctx)


def contexts(workflow, event, branch='main', cron=None, *, names=True):
    crons = schedule_crons(workflow) if event == 'schedule' else ['']
    if cron is not None:
        if cron not in crons:
            message = 'unconfigured schedule context'
            raise ValueError(message)
        crons = [cron]
    for scheduled in crons:
        yield from job_contexts(workflow, event, branch, scheduled, names=names)


def job_contexts(workflow, event, branch, scheduled, *, names=True):
    for key, job in workflow['jobs'].items():
        matrix = job.get('strategy', {}).get('matrix', {})
        axes = {k: v for k, v in matrix.items() if k not in {'include', 'exclude'}}
        rows = [dict(zip(axes, row, strict=True)) for row in itertools.product(*axes.values())]
        if not axes:
            rows = []
        rows += matrix.get('include', [])
        for row in rows or [{}]:
            if any(
                all(row.get(k) == v for k, v in item.items()) for item in matrix.get('exclude', [])
            ):
                continue
            ctx = {
                'github.event_name': event,
                'github.job': key,
                'github.workflow': workflow.get('name', ''),
                'github.ref': (
                    'refs/pull/' + ('79' if branch == 'slot-a' else '80') + '/merge'
                    if event == 'pull_request'
                    else 'refs/heads/' + branch
                ),
                'github.ref_name': ('79/merge' if branch == 'slot-a' else '80/merge')
                if event == 'pull_request'
                else branch,
                'github.event.pull_request.number': (79 if branch == 'slot-a' else 80)
                if event == 'pull_request'
                else '',
                'github.event.pull_request.head.repo.fork': False
                if event == 'pull_request'
                else '',
                'github.event.pull_request.head.sha': '79' * 20 if event == 'pull_request' else '',
                'github.sha': '79' * 20,
                'github.token': 'trace-only-token',
                'github.base_ref': 'main' if event == 'pull_request' else '',
                'github.head_ref': branch if event == 'pull_request' else '',
                'github.run_id': 790,
                'github.run_attempt': 2,
                'github.event.schedule': scheduled,
                'runner.temp': '/tmp/ci-selection-probe',
                'inputs.core_only': False,
                'needs.changes.result': 'success',
                'needs.changes.outputs.app_build': 'true',
                'needs.changes.outputs.crysta_sha': '79' * 20,
                **{'matrix.' + k: v for k, v in row.items()},
            }
            for step in job.get('steps', []):
                if step.get('id'):
                    ctx['steps.' + step['id'] + '.outcome'] = 'success'
                    if str(step.get('uses', '')).startswith('actions/create-github-app-token@'):
                        ctx['steps.' + step['id'] + '.outputs.token'] = 'trace-only-token'
            runner = runner_labels(job.get('runs-on', ''), ctx)
            osx = 'macOS' in runner or 'macos-' in runner
            arm64 = (
                'ARM64' in runner
                or 'arm64' in runner
                or any(
                    label in runner
                    for label in ('macos-14', 'macos-15', 'macos-26', 'macos-latest')
                )
            )
            platform = (
                'osx-arm64'
                if osx and arm64
                else 'osx-64'
                if osx
                else 'linux-64'
                if 'Linux' in runner or 'ubuntu-' in runner
                else ''
            )
            ctx['runner.os'] = 'macOS' if osx else 'Linux'
            ctx['runner.arch'] = 'ARM64' if arm64 else 'X64'
            yield render(job.get('name', key), ctx) if names else key, job, ctx, platform


def triggers_for(workflow):
    triggers = workflow.get('on', workflow.get(True))
    if isinstance(triggers, str):
        triggers = [triggers]
    if isinstance(triggers, list):
        triggers = dict.fromkeys(triggers)
    if not isinstance(triggers, dict):
        message = 'workflow triggers are required for execution contexts'
        raise TypeError(message)
    return triggers


def schedule_crons(workflow):
    configured = triggers_for(workflow).get('schedule')
    if not isinstance(configured, list) or not configured:
        message = 'schedule requires declared cron payloads'
        raise ValueError(message)
    crons = []
    for item in configured:
        if not isinstance(item, dict) or set(item) != {'cron'}:
            message = 'unsupported schedule payload'
            raise ValueError(message)
        cron = item['cron']
        if not isinstance(cron, str) or len(cron.split()) != 5:
            message = 'unsupported cron payload'
            raise ValueError(message)
        crons.append(cron)
    return list(dict.fromkeys(crons))


def event_refs(workflow):  # noqa: PLR0912
    triggers = triggers_for(workflow)
    for event in ('pull_request', 'push', 'schedule', 'workflow_dispatch'):
        if event not in triggers:
            continue
        config = triggers[event] or {}
        refs = (
            ('main',)
            if event == 'schedule'
            else ('slot-a', 'slot-b')
            if event == 'pull_request'
            else ('main', 'slot-a', 'slot-b', 'repair-topic')
        )
        if event == 'schedule':
            schedule_crons(workflow)
        elif not isinstance(config, dict):
            message = 'unsupported event configuration'
            raise TypeError(message)
        if event == 'push':
            refs += tuple(p for p in config.get('branches', []) if not any(c in p for c in '*?!['))
        visited = []
        for branch in dict.fromkeys(refs):
            if event in {'push', 'pull_request'}:
                target = 'main' if event == 'pull_request' else branch
                patterns = config.get('branches', ['*'])
                allowed = not any(not p.startswith('!') for p in patterns)
                for pattern in patterns:
                    if fnmatch.fnmatchcase(target, pattern.removeprefix('!')):
                        allowed = not pattern.startswith('!')
                if not allowed or any(
                    fnmatch.fnmatchcase(target, p) for p in config.get('branches-ignore', [])
                ):
                    continue
            visited.append(branch)
        if not visited:
            message = 'unrepresented configured event/ref: ' + event
            raise ValueError(message)
        if event in {'push', 'pull_request'}:
            targets = ['main'] if event == 'pull_request' else visited
            for pattern in config.get('branches', []):
                if not pattern.startswith('!') and not any(
                    fnmatch.fnmatchcase(target, pattern) for target in targets
                ):
                    message = 'unrepresented configured branch pattern: ' + pattern
                    raise ValueError(message)
        for branch in visited:
            yield event, branch


def concurrency_errors(workflows):
    errors, identities = [], {}
    for wi, workflow in enumerate(workflows):
        for event, branch in event_refs(workflow):
            for _name, job, ctx, _platform in contexts(workflow, event, branch, names=False):
                for scope, spec in [
                    ('workflow', workflow.get('concurrency')),
                    ('job:' + ctx['github.job'], job.get('concurrency')),
                ]:
                    if spec is None or (scope != 'workflow' and not value(job.get('if'), ctx)):
                        continue
                    item = (
                        {'group': spec, 'cancel-in-progress': False}
                        if isinstance(spec, str)
                        else spec
                    )
                    if value(item.get('cancel-in-progress', False), ctx) is not False:
                        errors.append('cancelling ' + event + ' ' + branch + ' ' + scope)
                    identity = actions_casefold(render(item['group'], ctx))
                    owner = (
                        wi,
                        branch,
                        scope,
                        json.dumps(
                            {key: val for key, val in ctx.items() if key.startswith('matrix.')}
                            if scope != 'workflow'
                            else {},
                            sort_keys=True,
                        ),
                    )
                    previous = identities.setdefault(identity, owner)
                    if previous != owner:
                        errors.append('effective collision ' + identity)
                    later = dict(ctx, **{'github.run_id': 791})
                    if identity == actions_casefold(render(item['group'], later)):
                        errors.append(
                            'queued run replacement: ' + event + ' ' + branch + ' ' + scope
                        )
    return errors


def prerequisites_ready(workflow, job, ctx, seen=()):
    needs = job.get('needs', [])
    needs = [needs] if isinstance(needs, str) else needs
    for key in needs:
        if key in seen or key not in workflow['jobs']:
            return False
        predecessor = workflow['jobs'][key]
        if not value(predecessor.get('if'), ctx) or not prerequisites_ready(
            workflow, predecessor, ctx, (*seen, key)
        ):
            return False
    return True


def run_settings(workflow, job, step, ctx):
    defaults = {
        **workflow.get('defaults', {}).get('run', {}),
        **job.get('defaults', {}).get('run', {}),
    }
    shell = step.get('shell', defaults.get('shell'))
    if shell not in {None, 'bash'}:
        message = 'unsupported workflow shell: ' + str(shell)
        raise ValueError(message)
    directory = step.get('working-directory', defaults.get('working-directory', '.'))
    if directory != '.':
        message = 'unsupported workflow working directory: ' + str(directory)
        raise ValueError(message)
    combined = {**workflow.get('env', {}), **job.get('env', {}), **step.get('env', {})}
    if any(
        key in {'PATH', 'BASH_ENV', 'ENV', 'SHELLOPTS', 'BASHOPTS'} or key.startswith('E09_')
        for key in combined
    ):
        message = 'unsupported shell/probe environment override'
        raise ValueError(message)
    return shell, {key: render(val, ctx) for key, val in combined.items()}


def probe(root, workflow, job, step, ctx, policy, fail=''):
    shell, run_env = run_settings(workflow, job, step, ctx)
    return trace(root, step['run'], ctx, policy, fail, shell=shell, run_env=run_env)


def task_commands(text, environment='default'):
    manifest = tomllib.loads(text)

    def declarations(selected):
        declaration = manifest.get('environments', {}).get(selected, {})
        features = (
            declaration if isinstance(declaration, list) else declaration.get('features', [])
        )
        tasks = dict(manifest.get('tasks', {}))
        for feature in features:
            for name, spec in (
                manifest.get('feature', {}).get(feature, {}).get('tasks', {}).items()
            ):
                if name in tasks and tasks[name] != spec:
                    message = 'ambiguous selected task ' + name
                    raise ValueError(message)
                tasks[name] = spec
        return tasks

    def closure(name, selected, stack=()):
        tasks = declarations(selected)
        if (name, selected) in stack or name not in tasks:
            message = 'unresolvable selected task ' + name
            raise ValueError(message)
        spec = tasks[name]
        if isinstance(spec, str):
            return [(name, spec, {})]
        result = []
        for child in spec.get('depends-on', []):
            task = child if isinstance(child, str) else child['task']
            scope = selected if isinstance(child, str) else child.get('environment', selected)
            result += closure(task, scope, (*stack, (name, selected)))
        cmd = spec.get('cmd', '')
        result.append((
            name,
            shlex.join(cmd) if isinstance(cmd, list) else cmd,
            spec.get('env', {}),
        ))
        return result

    resolved = {}
    for name in declarations(environment):
        try:
            resolved[name] = closure(name, environment)
        except ValueError:
            resolved[name] = [(name, 'return 96', {})]
    return resolved


def smoke_errors(selected, witnesses):
    return [
        category for category, required in witnesses.items() if not set(required) <= set(selected)
    ]


def trace(root, script, ctx, policy, fail='', *, shell=None, run_env=None):  # noqa: PLR0914
    runner = policy.get('execution_report', {}).get('run', {}).get('command', [])
    validator = policy.get('execution_report', {}).get('command', [])
    if not runner or not validator:
        message = 'missing actual runner/validator interface'
        raise ValueError(message)
    targets = {
        next(w for w in cmd if w.endswith('.py')): role
        for role, cmd in [('collector', runner), ('validator', validator)]
    }
    manifest_text = (root / 'pixi.toml').read_text()
    environments = list(
        dict.fromkeys(['default', *tomllib.loads(manifest_text).get('environments', {})])
    )
    functions, dispatches = [], []
    for ei, environment in enumerate(environments):
        tasks = task_commands(manifest_text, environment)
        for name, commands in tasks.items():
            body = []
            for invoked_task, cmd, env in commands:
                if cmd:
                    bindings = ' '.join(
                        k + '=' + shlex.quote(render(v, ctx)) for k, v in env.items()
                    )
                    body.append(
                        '( '
                        + ('export ' + bindings + '; ' if bindings else '')
                        + render(cmd, ctx)
                        + (' "$@"' if invoked_task == name == 'sdk-pack' else '')
                        + ' )'
                    )
            function = 't_e' + str(ei) + '_' + name.replace('-', '_')
            functions.append(function + '() {\n' + '\n'.join(body or [':']) + '\n}')
            arguments = '' if name == 'sdk-pack' else '[ "$#" -eq 0 ] || return 94; '
            dispatches.append(
                shlex.quote(environment + ':' + name)
                + ') shift; '
                + arguments
                + function
                + ' "$@";;'
            )
    dispatch = '\n'.join(dispatches)
    cases = '\n'.join(
        shlex.quote(target)
        + ') printf "E09TRACE %s\\n" '
        + shlex.quote(role)
        + '; printf "%s\\n" "$*"; '
        + ('return 97' if fail == role else 'return 0')
        + ';;'
        for target, role in targets.items()
    )
    stub = (
        """python() { local target=$1; shift; case "$target" in
"""
        + cases
        + """
*) return 0;; esac; }
python3() { python "$@"; }
pixi() { [ "$1" = run ] || return 91; shift; local scope=default
 while [ "${1:-}" = -e ] || [ "${1:-}" = --environment ]; do scope=$2; shift 2; done
 [ "${1:-}" != --skip-deps ] || return 93
 case "$scope:$1" in
"""
        + dispatch
        + """
 *:bash) shift; bash "$@";; *:python|*:python3) shift; python "$@";;
 *) return 92;; esac; }
bash() { case "$1" in
 tools/ci/pack-sdk.sh|tools/ci/sdk-smoke/run.sh) [ "$E09_QUAL_FAIL" != yes ];;
 *) return 0;; esac; }
coverage() { return 0; }
pytest() { return 0; }
"""
    )
    env = {
        **(run_env or {}),
        'E09_QUAL_FAIL': 'yes' if fail == 'qualification' else 'no',
        'PATH': '/usr/bin:/bin',
        'RUNNER_TEMP': '/tmp/ci-selection-probe',
        'GITHUB_SHA': '79' * 20,
        'GITHUB_RUN_ID': '790',
        'GITHUB_RUN_ATTEMPT': '2',
        'GITHUB_EVENT_NAME': ctx['github.event_name'],
    }
    # Only commands on the collector's dependency path enter this bounded probe.
    # Candidate task bodies are dry-run inputs, including inline cleanup commands.
    # Never execute them from the checkout or its shared build directory.
    with tempfile.TemporaryDirectory(prefix='ci-cadence-trace-') as scratch:
        env['GITHUB_WORKSPACE'] = scratch
        result = subprocess.run(
            [
                '/bin/bash',
                *(
                    ['--noprofile', '--norc', '-e', '-o', 'pipefail']
                    if shell == 'bash'
                    else ['-e']
                ),
                '-c',
                '\n'.join(functions) + '\n' + stub + '\n' + render(script, ctx),
            ],
            cwd=scratch,
            env=env,
            text=True,
            capture_output=True,
            # Scheduling contention must not masquerade as an invalid invocation.
            timeout=10,
            check=False,
        )
    lines = result.stdout.splitlines()
    observations = [
        (line.removeprefix('E09TRACE '), shlex.split(lines[i + 1]))
        for i, line in enumerate(lines[:-1])
        if line.startswith('E09TRACE ')
    ]
    return result.returncode, observations


def option(args, name):
    values = []
    for index, token in enumerate(args):
        if token == name:
            if index + 1 == len(args) or args[index + 1].startswith('--'):
                message = 'missing selection option argument ' + name
                raise ValueError(message)
            values.append(args[index + 1])
        elif token.startswith(name + '='):
            values.append(token[len(name) + 1 :])
    if len(values) > 1:
        message = 'ambiguous duplicated selection option ' + name
        raise ValueError(message)
    if values and not values[0]:
        message = 'empty selection option argument ' + name
        raise ValueError(message)
    return values[0] if values else None


def selection_workflow(workflow, policy, group):
    # Resolve display names only for jobs whose execution/publication this proof claims.
    task = policy['groups'][group]['task']
    selected = {
        key: job
        for key, job in workflow['jobs'].items()
        if any(
            group in step.get('run', '')
            or task in step.get('run', '')
            or (
                str(step.get('uses', '')).startswith('actions/upload-artifact@')
                and 'crysta-sdk-' in str(step.get('with', {}).get('name', ''))
            )
            for step in job.get('steps', [])
        )
    }
    return {**workflow, 'jobs': selected}


def execution_errors(root, workflow, policy, event, platform, group, expected=None):
    refs = [branch for actual_event, branch in event_refs(workflow) if actual_event == event]
    if not refs:
        message = 'unconfigured execution event'
        raise ValueError(message)
    if event in {'push', 'schedule'} and 'main' not in refs:
        message = 'unrepresented main execution ref'
        raise ValueError(message)
    crons = schedule_crons(workflow) if event == 'schedule' else [None]
    return [
        error
        for cron in crons
        for error in execution_context_errors(
            root, workflow, policy, event, platform, group, expected, cron=cron
        )
    ]


def execution_context_errors(root, workflow, policy, event, platform, group, expected, *, cron):  # noqa: PLR0913, PLR0912, PLR0915, PLR0914
    errors = []
    if group not in policy.get('groups', {}):
        return ['missing selected group']
    if not policy.get('execution_report', {}).get('run', {}).get('command'):
        return ['missing production execution collector']
    covered = []
    for name, job, ctx, actual_platform in contexts(
        selection_workflow(workflow, policy, group),
        event,
        'repair-topic' if event == 'workflow_dispatch' else 'main',
        cron,
    ):
        if (
            actual_platform != platform
            or not value(job.get('if'), ctx)
            or not prerequisites_ready(workflow, job, ctx)
        ):
            continue
        if expected and name != expected['job']:
            continue
        if job.get('continue-on-error') or job.get('strategy', {}).get('fail-fast', False):
            errors.append('advisory/cancelling execution job')
        steps = job.get('steps', [])
        selected = []
        for i, step in enumerate(steps):
            if 'run' not in step or not value(step.get('if'), ctx):
                continue
            if group not in step['run'] and policy['groups'][group]['task'] not in step['run']:
                continue
            try:
                code, observations = probe(root, workflow, job, step, ctx, policy)
                collectors = [
                    args
                    for role, args in observations
                    if role == 'collector' and option(args, '--group') == group
                ]
                if code or len(collectors) != 1:
                    errors.append('collector path absent, duplicate or unsuccessful')
                    continue
                args = collectors[0]
                output = option(args, '--output-dir')
                if option(args, '--platform') != platform or not output:
                    errors.append('collector platform/output mismatch')
                    continue
                if (
                    step.get('continue-on-error')
                    or probe(root, workflow, job, step, ctx, policy, 'collector')[0] == 0
                ):
                    errors.append('collector failure swallowed')
                validations = [a for role, a in observations if role == 'validator']
                validate_steps = (
                    [step] if any(role == 'validator' for role, _args in observations) else []
                )
                for later in steps[i + 1 :]:
                    if 'run' not in later or not value(later.get('if'), ctx):
                        continue
                    target = next(
                        w for w in policy['execution_report']['command'] if w.endswith('.py')
                    )
                    if target not in later['run']:
                        continue
                    code2, observed = probe(root, workflow, job, later, ctx, policy)
                    validations.extend(a for role, a in observed if role == 'validator')
                    validate_steps.append(later)
                    if code2:
                        errors.append('validator control unsuccessful')
                matched = [
                    a
                    for a in validations
                    if option(a, '--expected') == output + '/expected.json'
                    and option(a, '--report') == output + '/results.json'
                    and option(a, '--platform') == platform
                ]
                if len(matched) != 1:
                    errors.append('disconnected validation')
                errors.extend(
                    'validator failure swallowed'
                    for validation in validate_steps
                    if (
                        validation.get('continue-on-error')
                        or probe(root, workflow, job, validation, ctx, policy, 'validator')[0] == 0
                    )
                    and (validation is not step or validations)
                )
                uploads = [
                    s
                    for s in steps[i + 1 :]
                    if str(s.get('uses', '')).startswith('actions/upload-artifact@')
                    and value(s.get('if'), ctx)
                    and render(s.get('with', {}).get('name', ''), ctx)
                    == 'ci-selection-' + platform
                ]
                if (
                    len(uploads) != 1
                    or render(uploads[0]['with'].get('path', ''), ctx).rstrip('/') != output
                ):
                    errors.append('disconnected report upload')
                elif (
                    uploads[0].get('continue-on-error')
                    or uploads[0]['with'].get('if-no-files-found') != 'error'
                ):
                    errors.append('advisory report retention')
                if expected:
                    for title in expected['steps']:
                        found = [
                            s
                            for s in steps
                            if s.get('name') == title
                            and value(s.get('if'), ctx)
                            and not s.get('continue-on-error')
                        ]
                        if len(found) != 1:
                            errors.append('independent required step absent ' + title)
                selected.append(i)
            except (ValueError, KeyError, StopIteration, subprocess.TimeoutExpired) as exc:
                errors.append('unprovable execution path: ' + type(exc).__name__)
        if selected:
            covered.append(name)
        sdk_uploads = [
            s
            for s in steps
            if str(s.get('uses', '')).startswith('actions/upload-artifact@')
            and 'crysta-sdk-' in str(s.get('with', {}).get('name', ''))
        ]
        if sdk_uploads:
            frozen = json.loads((root / 'tests/fixtures/ci_cadence/baseline.json').read_text())

            prior = yaml.safe_load(frozen['files']['.github/workflows/ci.yml'])
            prior['jobs'] = {
                key: candidate
                for key, candidate in prior['jobs'].items()
                if any(
                    step.get('name', '').startswith(('Pack and qualify', 'SDK consumer smoke'))
                    or 'crysta-sdk-' in str(step.get('with', {}).get('name', ''))
                    for step in candidate.get('steps', [])
                )
            }
            qualified = [
                s
                for _n, j, c, p in contexts(prior, 'pull_request')
                if p == platform
                for s in j.get('steps', [])
                if s.get('name', '').startswith(('Pack and qualify', 'SDK consumer smoke'))
            ]
            for requirement in qualified:
                matching = [
                    s
                    for s in steps
                    if s.get('name') == requirement['name']
                    and value(s.get('if'), ctx)
                    and not s.get('continue-on-error')
                ]
                if len(matching) != 1 or matching[0].get('run') != requirement['run']:
                    errors.append('published SDK lacks frozen same-job qualification')
                else:
                    try:
                        good, _ = probe(root, workflow, job, matching[0], ctx, policy)
                        bad, _ = probe(
                            root, workflow, job, matching[0], ctx, policy, 'qualification'
                        )
                        if good or not bad:
                            errors.append('SDK qualification absent or failure swallowed')
                    except (ValueError, KeyError, StopIteration, subprocess.TimeoutExpired):
                        errors.append('unprovable SDK qualification invocation')
            old_uploads = [
                s
                for _n, j, c, p in contexts(prior, 'pull_request')
                if p == platform
                for s in j.get('steps', [])
                if str(s.get('uses', '')).startswith('actions/upload-artifact@')
                and 'crysta-sdk-' in str(s.get('with', {}).get('name', ''))
            ]
            for upload in sdk_uploads:
                if ctx.get('matrix.sdk', platform) != platform:
                    errors.append('SDK qualification platform mismatch')
                if render(upload.get('with', {}).get('path', ''), ctx).rstrip('/') not in {
                    render(s['with']['path'], ctx).rstrip('/') for s in old_uploads
                }:
                    errors.append('SDK upload does not retain the qualified package directory')
                if not value(upload.get('if'), ctx) or upload.get('continue-on-error'):
                    errors.append('unqualified SDK upload boundary')
                if qualified and steps.index(upload) < max(
                    steps.index(s)
                    for s in steps
                    if s.get('name') in {q['name'] for q in qualified}
                ):
                    errors.append('SDK upload precedes qualification')
    for name, job, ctx, actual_platform in contexts(
        selection_workflow(workflow, policy, group),
        event,
        'repair-topic' if event == 'workflow_dispatch' else 'main',
        cron,
    ):
        if (
            actual_platform != platform
            or not value(job.get('if'), ctx)
            or not prerequisites_ready(workflow, job, ctx)
        ):
            continue
        errors.extend(
            'SDK upload disconnected from required full execution'
            for step in job.get('steps', [])
            if str(step.get('uses', '')).startswith('actions/upload-artifact@')
            and 'crysta-sdk-' in str(step.get('with', {}).get('name', ''))
            and value(step.get('if'), ctx)
            and name not in covered
        )
    if len(covered) != 1:
        errors.append('required platform selection must execute in exactly one connected job')
    return errors
