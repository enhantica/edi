"""unit 8: execute CI run/uses source consumers against real Git history."""

from __future__ import annotations

import re
import runpy
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from tests.integration.py.test_e09_t75_sdk_consumer import SHA, consumer
from tests.system.py.test_e09_t75_native_execution import assert_restored, restore

ROOT = Path(__file__).resolve().parents[3]
WIRING = runpy.run_path(str(ROOT / 'tests/unit/py/test_e09_t74_ci_source_wiring.py'))
CONSUMERS = WIRING['CONSUMERS']
source_edges = WIRING['source_edges']


def _source_transport(root, build):
    protocol = root / 'bin/git-protocol'
    (root / 'bin/git').rename(protocol)
    transport = root / 'bin/git'
    transport.write_text(
        f'#!{sys.executable}\n'
        'import os,sys,subprocess\nfrom pathlib import Path\na=sys.argv[1:]\n'
        'if a == ["clone","-q","https://github.com/enhantica/c' + 'rysta","dependency"]:\n'
        f' sys.exit(subprocess.run([{build.git!r},"clone","-q",'
        f'{str(build.sibling)!r},"dependency"]).returncode)\n'
        f'if a == ["-C","dependency","checkout","-q","--detach",{build.second!r}]:\n'
        f' sys.exit(subprocess.run([{build.git!r},*a]).returncode)\n'
        f'os.execv({str(protocol)!r},[{str(protocol)!r},*a])\n'
    )
    transport.chmod(0o755)


def _execute_consumer(root, document, job_name, edge, *, actions_root=ROOT):  # noqa: PLR0915
    """Execute workflow shell/env and local composites against two real commits.

    Remote main is A while the common needs output is B. Compilation is doubled;
    production build-crysta still chooses, fetches, checks out and installs source.
    Pixi task dependencies are read from the real manifest (not a job-name list).
    """

    support = runpy.run_path(str(ROOT / 'tests/system/py/test_e09_t74_ci_crysta_resolution.py'))
    build = support['harness'](root, lookup='none')
    build._git('checkout', '-q', '--detach', build.first)
    # Retain executable hypothetical source consumers. The currency fixture's
    # narrower protocol did not declare these unrelated clone/checkout commands.
    _source_transport(root, build)
    shutil.copy2(ROOT / 'pixi.toml', build.edi / 'pixi.toml')
    manifest = tomllib.loads((ROOT / 'pixi.toml').read_text())
    tasks = dict(manifest['tasks'])
    for feature in manifest.get('feature', {}).values():
        tasks.update(feature.get('tasks', {}))

    def needs_source(name, seen=(), *, include_dependencies=True):
        assert name not in seen, ' unit 8: cyclic task graph cannot prove consumption'
        task = tasks.get(name, {})
        if isinstance(task, str):
            command, dependencies = task, []
        else:
            command, dependencies = task.get('cmd', ''), task.get('depends-on', [])
        command = shlex.join(command) if isinstance(command, list) else command
        # Follow actual shell-script references transitively, including future tasks.
        pending, visited = [command], set()
        while pending:
            text = pending.pop()
            if 'build-crysta.sh' in text:
                return True
            for file in re.findall(r'tools/[\w./-]+\.sh', text):
                if file not in visited:
                    visited.add(file)
                    pending.append((ROOT / file).read_text())
        return include_dependencies and any(
            needs_source(d if isinstance(d, str) else d['task'], (*seen, name))
            for d in dependencies
        )

    consuming_tasks = {name for name in tasks if needs_source(name)}
    direct_tasks = {name for name in tasks if needs_source(name, include_dependencies=False)}
    pixi = root / 'bin/pixi'
    pixi.write_text(
        f'#!{sys.executable}\n'
        f"""
import os,sys,subprocess
from pathlib import Path
args=sys.argv[1:]
args=args[1:] if args and args[0]=='run' else args
while args and args[0] in ('-e','--environment'): args=args[2:]
skip='--skip-deps' in args
args=[a for a in args if a!='--skip-deps']
if args and args[0] in {consuming_tasks!r} and (not skip or args[0] in {direct_tasks!r}):
    result=subprocess.run(['bash','tools/ci/build-crysta.sh'],check=False)
    if result.returncode: sys.exit(result.returncode)
    with Path({str(root / 'consumed')!r}).open('a') as out:
        out.write(Path('build/crysta-prefix/.crysta-sha').read_text().strip()+'\\n')
"""
    )
    pixi.chmod(0o755)
    home = root / 'home'
    home.mkdir()
    environment = {
        **build.env,
        'HOME': str(home),
        'GITHUB_ENV': str(root / 'github-env'),
        'GITHUB_OUTPUT': str(root / 'github-output'),
    }
    expected = build.second

    def render(value, inputs=None):
        def replace(match):
            expression = match[1].strip()
            if expression == f'needs.{edge[0]}.outputs.{edge[1]}':
                return expected
            if expression.startswith('inputs.'):
                key = expression.removeprefix('inputs.')
                assert key in (inputs or {}), ' unit 8: composite input must be supplied'
                return str(inputs[key])
            context = {
                'github.event_name': 'pull_request',
                'runner.temp': str(root),
                'matrix.platform': 'Linux',
                'vars.ENHANTICA_APP_ID': 'fixture-installation-id',
                'secrets.ENHANTICA_APP_KEY': 'fixture-installation-key',
            }
            if expression in context:
                return context[expression]
            if expression.endswith('.outputs.token') or expression == 'github.token':
                return 'fixture-token-not-a-secret'
            raise AssertionError(f' unit 8: unproven workflow expression {expression}')

        return re.sub(r'\$\{\{(.*?)\}\}', replace, str(value))

    def env_values(values, inputs=None):
        return {key: render(value, inputs) for key, value in (values or {}).items()}

    environment.update(env_values(document.get('env')))
    job = document['jobs'][job_name]
    environment.update(env_values(job.get('env')))
    repositories = set()

    def steps(items, inherited, inputs=None, chain=()):
        for step in items:
            # Exercise conditional consumers too: path filters must not hide a source edge.
            active = {**inherited, **env_values(step.get('env'), inputs)}
            if 'run' in step:
                outcome = subprocess.run(
                    ['bash', '-e', '-o', 'pipefail', '-c', render(step['run'], inputs)],
                    cwd=build.edi,
                    env=active,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                assert outcome.returncode == 0, (
                    f' unit 8: {job_name} source-consuming command failed: {outcome.stderr}'
                )
                values = root / 'github-env'
                if values.exists():
                    for line in values.read_text().splitlines():
                        key, separator, value = line.partition('=')
                        assert separator, (
                            ' unit 8: workflow environment propagation must be parseable'
                        )
                        inherited[key] = value
                # A direct fetch/clone is observed independently of job/step names.
                repositories.update(gitdir.parent for gitdir in build.edi.rglob('.git'))
            elif 'uses' in step:
                action = step['uses']
                supplied = env_values(step.get('with'), inputs)
                if action.startswith('./'):
                    assert action not in chain, (
                        ' unit 8: recursive composite cannot prove consumption'
                    )
                    folder = actions_root / action
                    path = next(
                        (
                            folder / n
                            for n in ('action.yml', 'action.yaml')
                            if (folder / n).exists()
                        ),
                        None,
                    )
                    assert path, f' unit 8: unknown local action {action}'
                    definition = yaml.safe_load(path.read_text())
                    assert definition['runs']['using'] == 'composite', (
                        ' unit 8: executable actions need an explicit consumption exercise'
                    )
                    steps(definition['runs']['steps'], active, supplied, (*chain, action))
                elif action.startswith('actions/checkout@'):
                    if supplied.get('repository', 'enhantica/edi') == 'enhantica/crysta':
                        assert supplied.get('ref') == expected, (
                            f' unit 8: {job_name} checkout must consume the shared SHA'
                        )
                        repositories.add(build.sibling)
                        build._git('checkout', '-q', '--detach', supplied['ref'])
                else:
                    # Only specific non-source infrastructure actions are opaque.
                    assert action.split('@')[0] in {
                        'prefix-dev/setup-pixi',
                        'actions/create-github-app-token',
                        'actions/upload-artifact',
                        'dorny/paths-filter',
                    }, f' unit 8: {job_name} unexamined uses consumer {action}'

    steps(job.get('steps', []), environment)
    consumed = root / 'consumed'
    witnesses = consumed.read_text().splitlines() if consumed.exists() else []
    for repository in repositories:
        witnesses.append(
            subprocess.check_output(
                [build.git, '-C', str(repository), 'rev-parse', 'HEAD'], text=True
            ).strip()
        )
    assert all(sha == expected for sha in witnesses), (
        f' unit 8: {job_name} used main or another source instead of the common SHA'
    )
    return bool(witnesses)


@pytest.mark.parametrize(
    'job_name',
    sorted(
        source_edges(yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())).keys()
        - {'cli-native'}
    ),
)
def test_actual_workflow_consumes_its_common_output_at_fetch_or_build(tmp_path, job_name):
    document = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    links = source_edges(document)
    # Before: each job built crysta from a shared source SHA. After ADR-0017/I34:
    # native builds edi against the pin; every executing consumer restores those
    # native bytes and the same pinned SDK. Use the independent transport fixture,
    # whose SHA/packaged bytes are prescribed separately from the reader.
    assert job_name in links, '/ each executing consumer retains the shared source edge'
    from tests.integration.py.test_e09_t75_native_workflow import (  # noqa: PLC0415 - defer cross-module test wiring
        public_build_boundary,
        public_profile,
    )

    public = public_profile(document['jobs'])
    if public:
        public_build_boundary(document['jobs'], job_name)
    if job_name == 'native' or public:
        native = tmp_path / 'native'
        native.mkdir()
        acquired, _ = consumer(native, platform='linux-64')
        assert acquired.returncode == 0, (
            '/ the native producer acquires its independently pinned SDK'
        )
        assert (
            native / 'edi/build/crysta-consumer-prefix/.crysta-sha'
        ).read_text().strip() == SHA, '/ native acquisition installs the common pinned commit'
    else:
        result = restore(tmp_path / job_name, job_name, 'linux-64')
        assert_restored(result)
        repo = tmp_path / job_name / 'edi'
        assert (repo / 'build/crysta-prefix/.crysta-sha').read_text().strip() == SHA, (
            f'/ {job_name} restores against the common pinned SDK commit'
        )
        assert (repo / 'build/ci/.crysta-linked-sha').read_text().strip() == SHA, (
            f'/ {job_name} native bytes remain linked to the same SDK commit'
        )


@pytest.mark.parametrize(
    'shape',
    [
        'known-unused-env',
        'unused-build-env',
        'future-run',
        'composite',
        'checkout',
        'unknown-action',
    ],
)
def test_source_use_counterfactuals_reject_unused_common_values(tmp_path, shape):
    job = {
        'needs': ['source'],
        'env': {'UNUSED_SHA': '${{ needs.source.outputs.sha }}'},
        'steps': [{'run': 'git clone -q https://github.com/enhantica/c' + 'rysta dependency'}],
    }
    if shape == 'unused-build-env':
        job['steps'] = [{'run': 'pixi run core-build'}]
    elif shape == 'composite':
        folder = tmp_path / 'actions/fetch'
        folder.mkdir(parents=True)
        (folder / 'action.yml').write_text(
            yaml.safe_dump({'runs': {'using': 'composite', 'steps': job['steps']}})
        )
        job['steps'] = [{'uses': './actions/fetch'}]
    elif shape == 'checkout':
        job['steps'] = [
            {
                'uses': 'actions/checkout@v5',
                'with': {'repository': 'enhantica/crysta', 'ref': 'main'},
            }
        ]
    elif shape == 'unknown-action':
        job['steps'] = [{'uses': 'other-org/fetch-crysta@v1'}]
    name = 'core' if shape == 'known-unused-env' else 'future-consumer'
    with pytest.raises(AssertionError, match=' unit 8:.*' + name):
        _execute_consumer(
            tmp_path / 'run', {'jobs': {name: job}}, name, ('source', 'sha'), actions_root=tmp_path
        )


@pytest.mark.parametrize('shape', ['run', 'composite', 'checkout'])
def test_new_consumers_really_consuming_the_shared_sha_are_admitted(tmp_path, shape):
    steps = [
        {
            'run': (
                'git clone -q https://github.com/enhantica/c' + 'rysta dependency\n'
                'git -C dependency checkout -q --detach "$SELECTED"'
            )
        }
    ]
    job = {
        'needs': ['source'],
        'env': {'SELECTED': '${{ needs.source.outputs.sha }}'},
        'steps': steps,
    }
    if shape == 'composite':
        folder = tmp_path / 'actions/fetch'
        folder.mkdir(parents=True)
        (folder / 'action.yml').write_text(
            yaml.safe_dump({
                'runs': {
                    'using': 'composite',
                    'steps': [
                        {'run': steps[0]['run'], 'env': {'SELECTED': '${{ inputs.source }}'}}
                    ],
                }
            })
        )
        job['env'] = {}
        job['steps'] = [
            {'uses': './actions/fetch', 'with': {'source': '${{ needs.source.outputs.sha }}'}}
        ]
    elif shape == 'checkout':
        job['steps'] = [
            {
                'uses': 'actions/checkout@v5',
                'with': {
                    'repository': 'enhantica/crysta',
                    'ref': '${{ needs.source.outputs.sha }}',
                },
            }
        ]
    assert _execute_consumer(
        tmp_path / 'run',
        {'jobs': {'future-consumer': job}},
        'future-consumer',
        ('source', 'sha'),
        actions_root=tmp_path,
    ), ' unit 8: a new run/composite/checkout consumer requires an observed exact-SHA use'
