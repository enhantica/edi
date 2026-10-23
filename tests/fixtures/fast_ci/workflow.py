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


FULL_EVENTS = ('push', 'schedule', 'workflow_dispatch')


def reachable(node, jobs, matrix, event='push'):
    node = copy.deepcopy(node)
    if 'if' in node:
        condition = str(node['if']) if not isinstance(node['if'], bool) else node['if']
        if isinstance(condition, str):
            for key, item in matrix.items():
                condition = condition.replace('matrix.' + key, repr(item))
        node['if'] = condition
    assert active(node, event, states=dict.fromkeys(jobs, 'success')), (
        f'The required workflow artifact or time-gate path must execute on {event}'
    )
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
    require_events(workflow, ('pull_request', *FULL_EVENTS))
    for event in FULL_EVENTS:
        _artifact_routes(workflow, root / event, event)


def _artifact_routes(workflow, root, event):
    jobs = workflow['jobs']
    producers = {
        name: job
        for name, job in jobs.items()
        if any('app-build' in s.get('run', '') for s in job.get('steps', []))
    }
    assert producers, 'System shards require a normal-app artifact producer'
    uploads = {}
    for name, job in producers.items():
        for matrix in matrix_cases(job):
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
                    assert options.get('path') == 'build/app/app/edi_app', (
                        'The app cache must transfer exactly the normal executable'
                    )
                    assert (
                        options.get('key') == 'edi-app-${{ matrix.platform }}-${{ github.run_id }}'
                    ), 'The app cache identity must bind the platform and this exact workflow run'
                identity = options['key' if cached else 'name']
                uploads[cached, resolve(identity, matrix)] = name
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
                    assert options.get('path') == 'build/app/app/edi_app', (
                        'System app reuse must restore exactly the delivered normal executable'
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
                    assert set(compatible) & dependencies(jobs, name), (
                        'Each system consumer must wait for its actual artifact producer'
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
    require_events(workflow, ('pull_request', 'push'))
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
            'The push comparator must depend on every completed system job'
        )
        reachable(job, jobs, {})
        for step in steps:
            reachable(step, jobs, {})
            for code in (0, 1, 2):
                run_boundary(
                    step['run'], root / name, 'timing', code, workflow_shell(workflow, job, step)
                )
        found = True
    assert found, 'Push CI must invoke and enforce the same tested shard comparator'
    for slow in (False, True):
        timing_evidence(workflow, root / ('slow' if slow else 'green'), slow=slow)


def timing_evidence(workflow, root, *, slow=False, api_mutation=None):  # noqa: PLR0914, PLR0915 - one collection-to-comparison transport
    """Carry distinct real evidence from the workflow collector into its real comparator."""
    import collections  # noqa: PLC0415 - isolated evidence transport
    import json  # noqa: PLC0415 - isolated evidence transport
    from pathlib import Path  # noqa: PLC0415 - isolated evidence transport

    import yaml  # noqa: PLC0415 - serialize the workflow the run actually used

    from tests.fixtures.fast_ci.generate import run_record  # noqa: PLC0415

    root.mkdir(parents=True, exist_ok=True)
    job = workflow['jobs']['system-time']
    inventory = dict(
        collections.Counter(
            row['platform'] for row in workflow['jobs']['system']['strategy']['matrix']['include']
        )
    )
    documents = {}
    for current in (True, False):
        document = run_record('feature' if current else 'main', [2400], current=current)
        document['expected_system_shards'] = inventory
        if current:
            document['event'] = 'push'
            document['head_branch'] = 'main'
            document['head_sha'] = 'd' * 40
        template = document['jobs'][0]
        document['jobs'] = []
        for platform, count in inventory.items():
            for part in range(1, count + 1):
                item = {
                    **template,
                    'id': len(document['jobs']) + 1,
                    'name': f'system · {platform} · {part}/{count}',
                }
                item['completed_at'] = (
                    '2026-10-12T10:50:00+00:00'
                    if current and slow and not document['jobs']
                    else '2026-10-12T10:40:00+00:00'
                )
                document['jobs'].append(item)
        documents[str(document['id'])] = document
    if api_mutation == 'stale-id':
        documents['111']['id'] = 110
    if api_mutation == 'wrong-head':
        documents['111']['head_sha'] = 'a' * 40
    (root / 'runs.json').write_text(json.dumps(documents))
    (root / 'workflow.yml').write_text(yaml.safe_dump(workflow))
    (root / 'event.json').write_text(json.dumps({'pull_request': {'head': {'sha': 'c' * 40}}}))
    binary = root / 'bin'
    binary.mkdir(exist_ok=True)
    scripts = {
        'gh': r"""import json,os,re,sys
from pathlib import Path
args=sys.argv[1:]; endpoint=next(x for x in args if x.startswith('repos/'))
documents=json.loads(Path(os.environ['EVIDENCE_ROOT']+'/runs.json').read_text())
if '/workflows/' in endpoint: print('222')
else:
 run=re.search(r'/runs/(\d+)',endpoint).group(1); record=documents[run]
 if '/jobs' in endpoint:
  for job in record['jobs']: print(json.dumps(job))
 else: print(json.dumps({k:v for k,v in record.items() if k!='jobs'}))
""",
        'git': """import os,sys
from pathlib import Path
if sys.argv[1]=='show': print(Path(os.environ['EVIDENCE_ROOT']+'/workflow.yml').read_text())
elif sys.argv[1]!='fetch': sys.exit(2)
""",
        'pixi': """import os,sys
assert sys.argv[1:3]==['run','python'], 'Only the real inventory counter is transported'
os.execv(sys.executable,[sys.executable,*sys.argv[3:]])
""",
    }
    for name, body in scripts.items():
        path = binary / name
        path.write_text('#!' + sys.executable + '\n' + body)
        path.chmod(0o755)
    producer = Path(__file__).resolve().parents[3] / 'tools/ci/system_shard_time.py'
    gate = root / 'tools/ci/system_shard_time.py'
    gate.parent.mkdir(parents=True, exist_ok=True)
    # Observe the actual compared operands, then call the unchanged production comparator.
    gate.write_text(
        'import importlib.util,json,os,pathlib,sys\n'
        f'spec=importlib.util.spec_from_file_location("actual_time_gate",{str(producer)!r})\n'
        'module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)\n'
        'original=module.compare\n'
        'def observed(current,main):\n'
        ' output=pathlib.Path(os.environ["EVIDENCE_ROOT"]+"/compared.json")\n'
        ' output.write_text(json.dumps([current,main]))\n'
        ' return original(current,main)\n'
        'module.compare=observed\nsys.exit(module.main())\n'
    )
    env = {
        **os.environ,
        'PATH': str(binary) + ':' + os.environ['PATH'],
        'RUNNER_TEMP': str(root),
        'EVIDENCE_ROOT': str(root),
        'GITHUB_REPOSITORY': 'enhantica/edi',
        'GITHUB_RUN_ID': '111',
        'GITHUB_SHA': 'd' * 40,
        'GITHUB_EVENT_PATH': str(root / 'event.json'),
    }
    steps = [step for step in job['steps'] if 'run' in step]
    completed = []
    for step in steps:
        reachable(step, workflow['jobs'], {})
        command = (
            step['run']
            .replace('${{ github.event.pull_request.head.sha }}', 'c' * 40)
            .replace('${{ github.sha }}', 'd' * 40)
        )
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
        assert completed[-1].returncode != 0, (
            'Stale run id or push head evidence must refuse before a green timing verdict'
        )
        return
    compared = root / 'compared.json'
    assert compared.is_file(), (
        'The actual collection must reach the real comparator with its evidence files'
    )
    current, main = json.loads(compared.read_text())
    assert (
        current['id'] == 111 and current['head_sha'] == 'd' * 40 and current['event'] == 'push'
    ), 'The comparator must consume this push run id and pushed head, not main or stale evidence'
    assert main['id'] == 222 and main['head_sha'] == 'b' * 40 and main['event'] == 'push', (
        'The baseline must be the selected main run id and head'
    )
    assert (completed[-1].returncode == 0) == (not slow), (
        'The real comparator must enforce this push versus main after collection'
    )
