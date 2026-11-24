"""Exercise critical PR workflow paths with offline process/action transports."""

import copy
import fnmatch
import os
import re
import shlex
import subprocess
import sys

from tests.fixtures.e09_t75_workflow import active


def matrix_cases(job):
    matrix = job.get('strategy', {}).get('matrix', {})
    return matrix.get('include', [{}])


def resolve(value, matrix):
    value = str(value)
    for key, item in matrix.items():
        value = re.sub(r'\$\{\{\s*matrix\.' + re.escape(key) + r'\s*\}\}', str(item), value)
    return value


SYSTEM_EVENTS = ('schedule', 'workflow_dispatch')
APP_CACHE_PATHS = (
    'build/app/app/edi_app',
    'build/app/app/edi_app_tests',
    'build/app/app/edi_assistant_guard',
    'build/tutorial-transactions',
)


def reachable(node, jobs, matrix, event='push'):
    node = copy.deepcopy(node)
    if 'if' in node:
        condition = str(node['if']) if not isinstance(node['if'], bool) else node['if']
        if isinstance(condition, str):
            for key, item in matrix.items():
                condition = condition.replace('matrix.' + key, repr(item))
        node['if'] = condition
    assert active(
        node,
        event,
        states=dict.fromkeys(jobs, 'success'),
        outputs={('inputs', 'run'): 'true'},
        bindings={'runner.os': matrix.get('platform')},
    ), f'The required workflow artifact or time-gate path must execute on {event}'
    continuation = node.get('continue-on-error', False)
    if isinstance(continuation, str):
        continuation = active({'if': continuation}, event, states=dict.fromkeys(jobs, 'success'))
    assert not continuation, 'A required artifact or time-gate failure must fail its workflow job'


def needs(job):
    value = job.get('needs', [])
    return {value} if isinstance(value, str) else set(value)


def dependencies(jobs, name, visited=frozenset()):
    if name in visited:
        return set()
    direct = needs(jobs[name])
    assert direct <= jobs.keys(), 'Critical workflow dependencies must name actual jobs'
    return direct | {
        ancestor for child in direct for ancestor in dependencies(jobs, child, visited | {name})
    }


def require_events(workflow, events_required):
    events = workflow.get('on', workflow.get(True, {}))
    assert set(events_required) <= set(events), 'Required workflow events retain their triggers'


def run_boundary(command, root, kind, code, shell='bash'):
    root.mkdir(parents=True, exist_ok=True)
    binary = root / 'bin'
    binary.mkdir(exist_ok=True)
    marker = root / 'executed'
    marker.unlink(missing_ok=True)
    gate = root / 'tools/ci/system_shard_time.py'
    gate.parent.mkdir(parents=True, exist_ok=True)
    gate.write_text(
        'import os, pathlib, sys\n'
        'pathlib.Path(os.environ["BOUNDARY_MARKER"]).write_text("timing")\n'
        'sys.exit(int(os.environ["BOUNDARY_EXIT"]))\n'
    )
    pixi = binary / 'pixi'
    pixi.write_text(
        '#!' + sys.executable + '\nimport os, pathlib, sys\n'
        'assert "app-build" in sys.argv, "unsupported workflow task transport"\n'
        'pathlib.Path(os.environ["BOUNDARY_MARKER"]).write_text("app")\n'
        'sys.exit(int(os.environ["BOUNDARY_EXIT"]))\n'
    )
    pixi.chmod(0o755)
    env = {
        **os.environ,
        'PATH': str(binary) + ':' + os.environ['PATH'],
        'BOUNDARY_MARKER': str(marker),
        'BOUNDARY_EXIT': str(code),
        'RUNNER_TEMP': str(root),
    }
    script = root / 'step.sh'
    script.write_text(command)
    shell = 'bash -e {0}' if shell is None else shell
    shell = 'bash --noprofile --norc -e -o pipefail {0}' if shell == 'bash' else shell
    assert '{0}' in shell, 'A critical workflow shell must have an executable script boundary'
    argv = [str(script) if word == '{0}' else word for word in shlex.split(shell)]
    result = subprocess.run(
        argv, cwd=root, env=env, capture_output=True, text=True, timeout=2, check=False
    )
    assert marker.is_file() and marker.read_text() == kind, (
        'The real workflow command must execute its required process, not echo or comment it'
    )
    assert (result.returncode == 0) == (code == 0), (
        'The critical workflow command must propagate the actual process verdict'
    )


def workflow_shell(workflow, job, step):
    default = workflow.get('defaults', {}).get('run', {}).get('shell')
    default = job.get('defaults', {}).get('run', {}).get('shell', default)
    return step.get('shell', default)


def artifact_routes(workflow, root):
    require_events(workflow, ('pull_request', 'push', *SYSTEM_EVENTS))
    for event in SYSTEM_EVENTS:
        _artifact_routes(workflow, root / event, event)


def app_uploads(workflow, root, event):
    jobs = workflow['jobs']
    producers = {
        name: job
        for name, job in jobs.items()
        if job.get('name') != 'app · Windows'
        and any('app-build' in s.get('run', '') for s in job.get('steps', []))
    }
    assert producers, 'System shards require a normal-app artifact producer'
    uploads = {}
    for name, job in producers.items():
        static_platform = job.get('env', {}).get('APP_PLATFORM')
        placements = [{'platform': static_platform}] if static_platform else matrix_cases(job)
        for matrix in placements:
            reachable(job, jobs, matrix, event)
            build_steps = [s for s in job['steps'] if 'app-build' in s.get('run', '')]
            build_step = build_steps[0]
            reachable(build_step, jobs, matrix, event)
            for code in (0, 1):
                run_boundary(
                    resolve(build_step['run'], matrix),
                    root / name,
                    'app',
                    code,
                    workflow_shell(workflow, job, build_step),
                )
            artifacts = [
                s
                for s in job['steps']
                if any(route in s.get('uses', '') for route in ('upload-artifact', 'cache/save'))
                and 'edi_app' in str(s.get('with', {}).get('path', ''))
            ]
            assert artifacts, 'The normal app must be uploaded beyond screenshot outputs'
            for step in artifacts:
                reachable(step, jobs, matrix, event)
                options = step['with']
                cached = 'cache/save' in step.get('uses', '')
                if cached:
                    assert (
                        isinstance(options.get('path'), str)
                        and tuple(sorted(options['path'].splitlines())) == APP_CACHE_PATHS
                    ), (
                        'The app cache must transfer exactly the app, native test runner '
                        'assistant guard and tutorial observer package'
                    )
                    binding = 'env.APP_PLATFORM' if static_platform else 'matrix.platform'
                    assert (
                        options.get('key') == 'edi-app-${{ ' + binding + ' }}-${{ github.run_id }}'
                    ), 'The app cache identity must bind the platform and this exact workflow run'
                identity = options['key' if cached else 'name']
                if static_platform:
                    identity = identity.replace('${{ env.APP_PLATFORM }}', static_platform)
                resource = cached, resolve(identity, matrix)
                assert resource not in uploads, 'An app resource has only one workflow producer'
                uploads[resource] = name
    return uploads


def _artifact_routes(workflow, root, event):
    jobs = workflow['jobs']
    uploads = app_uploads(workflow, root, event)
    consumers = {
        name: job
        for name, job in jobs.items()
        if any('system-tests' in s.get('run', '') for s in job.get('steps', []))
    }
    assert consumers, 'The artifact gate must observe every actual system consumer'
    for name, job in consumers.items():
        for matrix in matrix_cases(job):
            reachable(job, jobs, matrix, event)
            downloads = [
                s
                for s in job['steps']
                if 'download-artifact' in s.get('uses', '')
                or (
                    'cache/restore' in s.get('uses', '')
                    and 'edi-app-' in str(s.get('with', {}).get('key', ''))
                )
            ]
            matched = False
            for step in downloads:
                cached = 'cache/restore' in step.get('uses', '')
                options = step.get('with', {})
                if cached:
                    assert (
                        options.get('key') == 'edi-app-${{ matrix.platform }}-${{ github.run_id }}'
                    ), 'The restored app must bind the platform and this exact workflow run'
                    assert options.get('fail-on-cache-miss') is True and not options.get(
                        'restore-keys'
                    ), 'The app cache must fail closed without falling back to another run'
                    assert (
                        isinstance(options.get('path'), str)
                        and tuple(sorted(options['path'].splitlines())) == APP_CACHE_PATHS
                    ), (
                        'System reuse must restore exactly the app, native test runner '
                        'assistant guard and tutorial observer package'
                    )
                pattern = resolve(
                    options.get('key' if cached else 'name', options.get('pattern', '')), matrix
                )
                compatible = [
                    producer
                    for (producer_cached, artifact), producer in uploads.items()
                    if producer_cached == cached and fnmatch.fnmatch(artifact, pattern)
                ]
                if compatible:
                    reachable(step, jobs, matrix, event)
                    assert len(compatible) == 1 and compatible[0] in dependencies(jobs, name), (
                        'Each system consumer must wait for its unique platform artifact producer'
                    )
                    matched = True
            assert matched, 'Every system matrix case must restore the producer app artifact'
            for step in job['steps']:
                if 'system-tests' in step.get('run', ''):
                    reachable(step, jobs, matrix, event)
                assert 'app-build' not in step.get('run', ''), (
                    'System consumers must not compile a second app'
                )


def timing_route(workflow, root):
    require_events(workflow, ('schedule',))
    jobs = workflow['jobs']
    systems = {
        name
        for name, job in jobs.items()
        if any('system-tests' in s.get('run', '') for s in job.get('steps', []))
    }
    found = False
    for name, job in jobs.items():
        steps = [
            s for s in job.get('steps', []) if 'tools/ci/system_shard_time.py' in s.get('run', '')
        ]
        if not steps:
            continue
        assert systems and systems <= dependencies(jobs, name), (
            'The nightly comparator must depend on every completed system job'
        )
        reachable(job, jobs, {}, event='schedule')
        for step in steps:
            reachable(step, jobs, {}, event='schedule')
            for code in (0, 1, 2):
                run_boundary(
                    step['run'], root / name, 'timing', code, workflow_shell(workflow, job, step)
                )
        found = True
    assert found, 'The nightly workflow must invoke and enforce the same tested shard comparator'
    for slow in (False, True):
        timing_evidence(workflow, root / ('slow' if slow else 'green'), slow=slow)


def timing_evidence(workflow, root, *, slow=False, api_mutation=None):  # noqa: PLR0914, PLR0915
    """Run the workflow's actual nightly collector and replay against independent REST pages."""
    import collections  # noqa: PLC0415
    import json  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    import yaml  # noqa: PLC0415

    from tests.integration.py.test_nightly_and_branch_artifacts import (  # noqa: PLC0415
        nightly_history,
        page,
    )

    root.mkdir(parents=True, exist_ok=True)
    job = workflow['jobs']['system-time']
    matrix = workflow['jobs']['system']['strategy']['matrix']['include']
    inventory = collections.Counter(row['platform'] for row in matrix)
    history = nightly_history()
    history['shards'] = {sha: dict(inventory) for sha in history['shards']}
    for rid in history['runs']:
        template = history['jobs'][rid][0]['jobs'][0]
        jobs = [
            {
                **template,
                'id': 100 + index,
                'name': f'system · {row["platform"]} · {row["part"]}/{inventory[row["platform"]]}',
            }
            for index, row in enumerate(matrix)
        ]
        if rid == '31' and slow:
            jobs[0]['completed_at'] = '2026-11-24T02:13:00Z'
        history['jobs'][rid] = [page('jobs', jobs)]
    if api_mutation == 'stale-id':
        history['runs']['31']['id'] = 32
    if api_mutation == 'wrong-head':
        history['runs']['31']['head_sha'] = 'd' * 40
    if api_mutation == 'partial-history':
        history['list'][0]['total_count'] += 1
    if api_mutation == 'moving-candidate':
        history['runs']['30']['created_at'] = '2026-11-21T01:00:00Z'
    (root / 'api.json').write_text(json.dumps(history))
    (root / 'workflow.yml').write_text(yaml.safe_dump(workflow))
    (root / 'system-time').mkdir()
    scripts = {
        'gh': r"""import json, os, sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
address = urlsplit(sys.argv[-1].split('/actions/', 1)[1])
history = json.loads(Path(os.environ['EVIDENCE_ROOT'], 'api.json').read_text())
page = int(parse_qs(address.query).get('page', ['1'])[0]) - 1
parts = address.path.split('/')
if parts[0] == 'workflows':
    assert address.path == 'workflows/ci.yml/runs', 'The collector requires the primary workflow'
    item = history['list'][page]
elif parts[-1] == 'jobs':
    item = history['jobs'][parts[1]][page]
else:
    item = history['runs'][parts[1]]
print(json.dumps(item))
""",
        'git': """import os,sys
from pathlib import Path
if sys.argv[1]=='show': print(Path(os.environ['EVIDENCE_ROOT'], 'workflow.yml').read_text())
elif sys.argv[1]!='fetch': sys.exit(2)
""",
        'pixi': """import os,sys
assert sys.argv[1:3] == ['run','python'], 'Only the real timing command is transported'
os.execv(sys.executable,[sys.executable,*sys.argv[3:]])
""",
    }
    binary = root / 'bin'
    binary.mkdir(exist_ok=True)
    for name, content in scripts.items():
        path = binary / name
        path.write_text('#!' + sys.executable + '\n' + content)
        path.chmod(0o755)
    producer = Path(__file__).resolve().parents[3] / 'tools/ci/system_shard_time.py'
    gate = root / 'tools/ci/system_shard_time.py'
    gate.parent.mkdir(parents=True, exist_ok=True)
    gate.symlink_to(producer)
    env = {
        **os.environ,
        'PATH': str(binary) + os.pathsep + os.environ['PATH'],
        'RUNNER_TEMP': str(root),
        'EVIDENCE_ROOT': str(root),
        'GITHUB_REPOSITORY': 'example/edi',
        'GITHUB_RUN_ID': '31',
        'GITHUB_SHA': 'a' * 40,
    }
    steps = [
        step for step in job['steps'] if 'tools/ci/system_shard_time.py' in step.get('run', '')
    ]
    assert len(steps) == 2, 'Nightly collection and replay have distinct workflow steps'
    completed = []
    for step in steps:
        reachable(step, workflow['jobs'], {}, event='schedule')
        command = step['run'].replace('${{ github.sha }}', 'a' * 40)
        shell = workflow_shell(workflow, job, step)
        shell = (
            'bash --noprofile --norc -e -o pipefail {0}'
            if shell == 'bash'
            else shell or 'bash -e {0}'
        )
        script = root / f'step-{len(completed)}.sh'
        script.write_text(command)
        result = subprocess.run(
            [str(script) if word == '{0}' else word for word in shlex.split(shell)],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
        completed.append(result)
        if result.returncode:
            break
    if api_mutation:
        assert len(completed) == 1 and completed[0].returncode == 2, (
            'An unproved API read fails closed in the collector before comparison'
        )
        assert not (root / 'system-time/history.json').exists(), (
            'The collector never writes replay evidence for a refused history'
        )
        return
    receipt = root / 'system-time/history.json'
    assert receipt.is_file(), 'The nightly comparator must receive the actual history.json'
    actual = json.loads(receipt.read_text())
    assert actual['runs']['31']['head_sha'] == 'a' * 40 and '30' in actual['runs'], (
        'Live collection records this exact nightly and the independently newest earlier run'
    )
    assert not (root / 'system-time/record.json').exists(), (
        'An admitted earlier run never emits a no-baseline verdict'
    )
    expected = 1 if slow else 0
    assert len(completed) == 2 and completed[1].returncode == expected, (
        'The nightly replay enforces the original comparison evidence after live collection'
    )
    assert 'baseline is run 30' in completed[1].stdout, (
        'The workflow compares the most recent earlier baseline by absolute timestamp'
    )
