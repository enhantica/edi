"""Independent execution-path checks for the temporary CI policy."""

# ruff: noqa: PLR1702, PLW0717
# The literal temporary paths are shell-trace inputs; intercepted collectors write nothing there.

from __future__ import annotations

import ast
import fnmatch
import itertools
import json
import re
import shlex
import subprocess
import tempfile
import tomllib

import yaml


def value(source, ctx):
    if source is None or isinstance(source, bool):
        return True if source is None else source
    text = str(source).strip().removeprefix('${{').removesuffix('}}').strip()
    for key in sorted(ctx, key=len, reverse=True):
        text = re.sub(r'(?<![\w.])' + re.escape(key) + r'(?![\w.])', repr(ctx[key]), text)
    for call, result in [
        ('always()', True),
        ('success()', True),
        ('failure()', False),
        ('cancelled()', False),
    ]:
        text = text.replace(call, repr(result))
    text = re.sub(r'\btrue\b', 'True', text)
    text = re.sub(r'\bfalse\b', 'False', text)
    text = re.sub(r'!(?!=)', ' not ', text.replace('&&', ' and ').replace('||', ' or ')).strip()
    tree = ast.parse(text, mode='eval')
    allowed = (
        ast.Expression,
        ast.Constant,
        ast.List,
        ast.Tuple,
        ast.Dict,
        ast.BoolOp,
        ast.And,
        ast.Or,
        ast.UnaryOp,
        ast.Not,
        ast.Compare,
        ast.Eq,
        ast.NotEq,
        ast.Load,
    )
    if any(not isinstance(n, allowed) for n in ast.walk(tree)):
        raise ValueError('unsupported workflow expression: ' + str(source))
    return eval(compile(tree, '<ci-policy>', 'eval'), {'__builtins__': {}}, {})  # noqa: S307


def render(source, ctx):
    return re.sub(r'\$\{\{(.*?)\}\}', lambda m: str(value(m[1], ctx)), str(source))


def contexts(workflow, event, branch='main'):
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
                'github.event.pull_request.number': 79 if branch == 'slot-a' else 80,
                'github.event.pull_request.head.repo.fork': False,
                'github.event.pull_request.head.sha': '79' * 20,
                'github.sha': '79' * 20,
                'github.token': 'trace-only-token',
                'github.base_ref': 'main' if event == 'pull_request' else '',
                'github.head_ref': branch if event == 'pull_request' else '',
                'github.run_id': 790,
                'github.run_attempt': 2,
                'github.event.schedule': '0 3 * * *' if event == 'schedule' else '',
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
            runner = render(job.get('runs-on', ''), ctx)
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
            yield render(job.get('name', key), ctx), job, ctx, platform


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


def event_refs(workflow):
    triggers = workflow.get('on', workflow.get(True))
    if isinstance(triggers, str):
        triggers = [triggers]
    if isinstance(triggers, list):
        triggers = dict.fromkeys(triggers)
    if not isinstance(triggers, dict):
        message = 'workflow triggers are required for concurrency execution contexts'
        raise TypeError(message)
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
        if event == 'push':
            refs += tuple(p for p in config.get('branches', []) if not any(c in p for c in '*?!['))
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
            yield event, branch


def concurrency_errors(workflows):
    errors, identities = [], {}
    for wi, workflow in enumerate(workflows):
        for event, branch in event_refs(workflow):
            for name, job, ctx, _platform in contexts(workflow, event, branch):
                for scope, spec in [
                    ('workflow', workflow.get('concurrency')),
                    ('job:' + name, job.get('concurrency')),
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
                    identity = render(item['group'], ctx)
                    owner = (wi, branch, scope)
                    previous = identities.setdefault(identity, owner)
                    if previous != owner:
                        errors.append('effective collision ' + identity)
                    later = dict(ctx, **{'github.run_id': 791})
                    if identity == render(item['group'], later):
                        errors.append(
                            'queued run replacement: ' + event + ' ' + branch + ' ' + scope
                        )
    return errors


def run_settings(workflow, job, step, ctx):
    defaults = {
        **workflow.get('defaults', {}).get('run', {}),
        **job.get('defaults', {}).get('run', {}),
    }
    shell = step.get('shell', defaults.get('shell'))
    if shell not in {None, 'bash'}:
        raise ValueError('unsupported workflow shell: ' + str(shell))
    directory = step.get('working-directory', defaults.get('working-directory', '.'))
    if directory != '.':
        raise ValueError('unsupported workflow working directory: ' + str(directory))
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
                    raise ValueError('ambiguous selected task ' + name)
                tasks[name] = spec
        return tasks

    def closure(name, selected, stack=()):
        tasks = declarations(selected)
        if (name, selected) in stack or name not in tasks:
            raise ValueError('unresolvable selected task ' + name)
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
            timeout=2,
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
    if args.count(name) > 1:
        raise ValueError('ambiguous duplicated selection option ' + name)
    if name not in args:
        return None
    index = args.index(name) + 1
    if index == len(args):
        raise ValueError('missing selection option argument ' + name)
    return args[index]


def execution_errors(root, workflow, policy, event, platform, group, expected=None):  # noqa: PLR0912, PLR0915, PLR0914
    errors = []
    if group not in policy.get('groups', {}):
        return ['missing selected group']
    if not policy.get('execution_report', {}).get('run', {}).get('command'):
        return ['missing production execution collector']
    covered = []
    for name, job, ctx, actual_platform in contexts(
        workflow, event, 'repair-topic' if event == 'workflow_dispatch' else 'main'
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
            except (ValueError, KeyError, StopIteration, subprocess.TimeoutExpired):
                errors.append('unprovable execution path')
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
        workflow, event, 'repair-topic' if event == 'workflow_dispatch' else 'main'
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
