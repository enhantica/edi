"""Exercise helper traversal, harmless compiler use and enforcing PR workflow routes."""

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.fixtures.fast_ci.policy import app_build_sites
from tests.fixtures.fast_ci.processes import process_guard, stop_observer_tree
from tests.fixtures.fast_ci.selection import shard_selection
from tests.fixtures.fast_ci.workflow import artifact_routes, timing_evidence, timing_route


def probe(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.mark.parametrize(
    'route', ['imported', 'multi-hop', 'local-hop', 'browser', 'browser-alias', 'browser-argv']
)
def test_pr_fixture_build_policy_follows_each_actual_helper_boundary(tmp_path, route):
    fixture = probe(tmp_path, 'tests/system/py/test_use.py', 'pass\n')
    if route == 'imported':
        probe(
            tmp_path,
            'tools/builder.py',
            'import subprocess\ndef build(): subprocess.run(["cmake","--build","app"])\n',
        )
        fixture.write_text('from tools.builder import build\ndef test_use(): build()\n')
    elif route == 'multi-hop':
        probe(
            tmp_path,
            'tools/first.py',
            'import subprocess\nsubprocess.Popen(["python","tools/second.py"])\n',
        )
        probe(
            tmp_path,
            'tools/second.py',
            'import subprocess\nsubprocess.run(["cmake","--build","app"])\n',
        )
        fixture.write_text('import subprocess\nsubprocess.run(["python","tools/first.py"])\n')
    elif route == 'local-hop':
        probe(
            tmp_path,
            'tools/builder.py',
            'import subprocess\ndef build(): execute()\n'
            'def execute(): subprocess.run(["cmake","--build","app"])\n',
        )
        fixture.write_text('from tools.builder import build\ndef test_use(): build()\n')
    else:
        scripts = {
            'browser': 'import {spawnSync} from "node:child_process";\n'
            'spawnSync("cmake",["--build","app"]);\n',
            'browser-alias': 'import {spawnSync as launch} from "node:child_process";\n'
            'launch("cmake",["--build","app"]);\n',
            'browser-argv': 'import {spawnSync} from "node:child_process";\n'
            'const command=["cmake","--build","app"];\n'
            'spawnSync(command[0],command.slice(1));\n',
        }
        probe(tmp_path, 'tools/browser.mjs', scripts[route])
        fixture.write_text('import subprocess\nsubprocess.Popen(["node","tools/browser.mjs"])\n')
    assert app_build_sites(tmp_path), 'Every exercised PR helper route must reach its app build'


@pytest.mark.parametrize(
    'command',
    [
        '["cmake","--version"]',
        '["echo","cmake","--build","app"]',
        '["cmake","--build","native-core-probe"]',
        '["clang++","-fsyntax-only","app/src/project_view_model.hpp"]',
        '["c++","probe.cpp","-o","core-probe"]',
    ],
)
def test_harmless_compiler_commands_in_an_app_related_module_remain_allowed(tmp_path, command):
    probe(
        tmp_path,
        'tests/system/py/test_native.py',
        '# app/src edi_app_module EDI_BUILD_APP=ON\nimport subprocess\n'
        'subprocess.run(' + command + ')\n',
    )
    probe(
        tmp_path,
        'tests/system/py/CMakeLists.txt',
        'target_link_libraries(unrelated_app PRIVATE edi_app_module)\n',
    )
    assert not app_build_sites(tmp_path), (
        'Compiler queries, header layout readers and native probes do not build the app'
    )


def test_an_imported_harmless_function_does_not_execute_an_unused_build_function(tmp_path):
    probe(
        tmp_path,
        'tools/helper.py',
        'import subprocess\ndef version(): subprocess.run(["cmake","--version"])\n'
        'def build(): subprocess.run(["cmake","--build","app"])\n',
    )
    probe(
        tmp_path,
        'tests/system/py/test_use.py',
        'from tools.helper import version\ndef test_use(): version()\n',
    )
    assert not app_build_sites(tmp_path), (
        'Imported dependencies must follow the function actually used'
    )


def test_only_an_actual_off_pr_group_can_exempt_a_separate_app_build(tmp_path):
    path = 'tests/system/py/test_host.py'
    probe(tmp_path, path, 'import subprocess\nsubprocess.run(["cmake","--build","app"])\n')
    manifest = probe(
        tmp_path,
        'tests/test-groups.json',
        json.dumps({'groups': {'quick': {'tiers': ['system']}, 'nightly': {'paths': [path]}}}),
    )
    assert app_build_sites(tmp_path), 'The old nightly group still runs on Linux PRs'
    manifest.write_text(
        json.dumps({'groups': {'quick': {'tiers': ['system']}, 'nightly-only': {'paths': [path]}}})
    )
    assert not app_build_sites(tmp_path), (
        'An independently gated off-PR selection permits a private host'
    )


def workflow_control():
    return {
        'on': {'pull_request': {}},
        'defaults': {'run': {'shell': 'bash'}},
        'jobs': {
            'app': {
                'steps': [
                    {'run': 'pixi run -e app app-build'},
                    {
                        'uses': 'actions/upload-artifact@v4',
                        'with': {'name': 'normal-app', 'path': 'build/app/app/edi_app'},
                    },
                ]
            },
            'system': {
                'strategy': {'matrix': {'include': [{'platform': 'Linux', 'part': 1}]}},
                'needs': 'app',
                'steps': [
                    {
                        'uses': 'actions/download-artifact@v4',
                        'with': {'name': 'normal-app', 'path': 'build/app/app'},
                    },
                    {'run': 'pixi run system-tests-part 1 3'},
                ],
            },
            'system-time': {
                'needs': 'system',
                'steps': [
                    {
                        'run': next(
                            step['run']
                            for step in yaml.safe_load(
                                (
                                    Path(__file__).resolve().parents[3]
                                    / '.github/workflows/ci.yml'
                                ).read_text()
                            )['jobs']['system-time']['steps']
                            if 'record()' in step.get('run', '')
                        )
                    },
                    {
                        'run': (
                            'python3 tools/ci/system_shard_time.py '
                            '--current current.json --main main.json '
                            '--run-id 111 --head-sha cccccccccccccccccccccccccccccccccccccccc'
                        )
                    },
                ],
            },
        },
    }


@pytest.mark.parametrize(
    'mutation',
    [
        'missing-pr-trigger',
        'producer-job-disabled',
        'producer-step-disabled',
        'upload-disabled',
        'download-disabled',
        'consumer-job-disabled',
        'consumer-step-disabled',
        'missing-producer-dependency',
        'download-continue',
        'producer-echo',
        'producer-continue',
        'upload-continue',
        'producer-or-true',
    ],
)
def test_artifact_route_oracle_rejects_each_exercised_pr_bypass(tmp_path, mutation):
    workflow = workflow_control()
    artifact_routes(workflow, tmp_path / 'positive')
    broken = copy.deepcopy(workflow)
    jobs = broken['jobs']
    if mutation == 'missing-pr-trigger':
        broken['on'] = {'push': {}}
    elif mutation == 'missing-producer-dependency':
        jobs['system']['needs'] = []
    elif mutation == 'producer-echo':
        jobs['app']['steps'][0]['run'] = 'echo pixi run app-build'
    elif mutation == 'producer-or-true':
        jobs['app']['steps'][0]['run'] += ' || true'
    else:
        mapping = {
            'producer-job-disabled': jobs['app'],
            'producer-step-disabled': jobs['app']['steps'][0],
            'upload-disabled': jobs['app']['steps'][1],
            'download-disabled': jobs['system']['steps'][0],
            'consumer-job-disabled': jobs['system'],
            'consumer-step-disabled': jobs['system']['steps'][1],
            'download-continue': jobs['system']['steps'][0],
            'producer-continue': jobs['app'],
            'upload-continue': jobs['app']['steps'][1],
        }
        target = mapping[mutation]
        target['continue-on-error' if mutation.endswith('continue') else 'if'] = (
            True if mutation.endswith('continue') else "github.event_name != 'pull_request'"
        )
    with pytest.raises(AssertionError, match=r'PR|workflow|process|producer'):
        artifact_routes(broken, tmp_path / 'negative')


@pytest.mark.parametrize(
    'mutation',
    [
        'job-excludes-pr',
        'step-disabled',
        'missing-system-dependency',
        'echo',
        'or-true',
        'trailing-success',
        'pipeline-without-pipefail',
        'job-continue',
        'step-continue',
        'shell-branch-disabled',
        'custom-shell-swallows',
    ],
)
def test_timing_route_oracle_executes_and_enforces_each_exercised_pr_boundary(tmp_path, mutation):
    workflow = workflow_control()
    timing_route(workflow, tmp_path / 'positive')
    broken = copy.deepcopy(workflow)
    job = broken['jobs']['system-time']
    step = next(
        step for step in job['steps'] if 'tools/ci/system_shard_time.py' in step.get('run', '')
    )
    if mutation == 'job-excludes-pr':
        job['if'] = "github.event_name != 'pull_request'"
    elif mutation == 'step-disabled':
        step['if'] = '${{ false }}'
    elif mutation == 'missing-system-dependency':
        job['needs'] = []
    elif mutation == 'echo':
        step['run'] = 'echo ' + step['run']
    elif mutation == 'or-true':
        step['run'] += ' || true'
    elif mutation == 'trailing-success':
        step['run'] = 'set +e; ' + step['run'] + '; true'
    elif mutation == 'pipeline-without-pipefail':
        step['run'] = 'set +o pipefail; ' + step['run'] + ' | cat'
    elif mutation == 'custom-shell-swallows':
        step['shell'] = 'bash {0}'
        step['run'] += '; true'
    elif mutation == 'shell-branch-disabled':
        step['run'] = 'if false; then ' + step['run'] + '; fi'
    else:
        (job if mutation == 'job-continue' else step)['continue-on-error'] = True
    with pytest.raises(AssertionError, match=r'PR|workflow|process|comparator'):
        timing_route(broken, tmp_path / 'negative')


@pytest.mark.parametrize(
    'launcher', ['run', 'Popen', 'check_call', 'check_output', 'system', 'spawn']
)
def test_real_process_guard_refuses_each_app_compiler_entry_before_execution(tmp_path, launcher):
    command = [shutil.which('cmake'), '--build', 'app']
    with process_guard(tmp_path) as state:
        actions = {
            'system': lambda: getattr(os, launcher)('cmake --build app'),
            'spawn': lambda: os.posix_spawn(command[0], command, os.environ),
        }
        launch = actions.get(launcher, lambda: getattr(subprocess, launcher)(command))
        with pytest.raises(RuntimeError, match='private app build'):
            launch()
        positive = subprocess.run(
            [sys.executable, '-c', 'print(42)'],
            capture_output=True,
            text=True,
            check=False,
            timeout=1,
        )
        assert positive.returncode == 0, 'The process guard must allow an unrelated executable'
    assert state['blocked'], 'Every named process channel must reach the pre-execution guard'


@pytest.mark.parametrize('event', ['pull_request', 'push', 'schedule'])
@pytest.mark.parametrize('platform', ['Linux', 'macOS'])
def test_nightly_only_observers_are_absent_from_actual_pr_shards_and_retained_nightly(
    tmp_path, event, platform
):
    root = Path(__file__).resolve().parents[3]
    groups = json.loads((root / 'tests/test-groups.json').read_text())['groups']
    paths = groups['nightly-only']['paths']
    required = {
        'tests/system/py/test_c34_t28_value_storage.py',
        'tests/system/py/test_cwl_live_parameter_count.py',
        'tests/system/py/test_plain_data_app.py',
        'tests/system/py/test_web_parallel_build.py',
        'tests/system/py/test_scan_app_execution.py',
        'tests/system/py/test_scan_accident_paths.py',
        'tests/system/py/test_thread_selector.py',
    }
    assert required <= set(paths), 'Every assigned separate-build observer must be declared off PR'
    workflow = yaml.safe_load((root / '.github/workflows/ci.yml').read_text())
    arguments = shard_selection(root, tmp_path, event, platform, workflow)
    ignored = {
        argument.partition('=')[2] for argument in arguments if argument.startswith('--ignore=')
    }
    if event == 'schedule':
        assert not required & ignored, 'Nightly must retain every separate-build observer'
    else:
        assert set(paths) <= ignored, 'Both platforms must exclude these hosts on PR/main'


def test_observer_timeout_terminates_a_child_that_started_its_own_session(tmp_path):
    child_pid = tmp_path / 'child.pid'
    child = 'import time; time.sleep(20)'
    launcher = (
        'import pathlib, subprocess, sys; '
        'child=subprocess.Popen([sys.executable,"-c",sys.argv[2]],start_new_session=True); '
        'pathlib.Path(sys.argv[1]).write_text(str(child.pid)); '
        'child.wait()'
    )
    process = subprocess.Popen(
        [sys.executable, '-c', launcher, str(child_pid), child],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            process.communicate(timeout=0.2)
        assert child_pid.is_file(), 'The timeout control must actually start its detached child'
        pid = int(child_pid.read_text())
        family = stop_observer_tree(process)
        assert pid in family, 'The cleanup must discover descendants outside the launcher session'
        inventory = subprocess.run(
            [shutil.which('ps'), '-p', str(pid), '-o', 'stat='],
            capture_output=True,
            text=True,
            check=False,
            timeout=1,
        )
        assert not inventory.stdout.strip() or inventory.stdout.strip().startswith('Z'), (
            'No active observer child may survive the launcher timeout'
        )
    finally:
        if process.poll() is None:
            stop_observer_tree(process)


def test_only_declared_nightly_builder_files_may_compile_the_app():
    root = Path(__file__).resolve().parents[3]
    group = json.loads((root / 'tests/test-groups.json').read_text())['groups']['nightly-only']
    builders = set(group['app_builders'])
    assert builders, 'The nightly group must declare its actual app-builder inventory'
    assert all((root / name).is_file() for name in builders), (
        'Every declared app builder must identify an existing source file'
    )
    sites = app_build_sites(root, [root / name for name in group['paths']])
    actual = {site.rsplit(':', 1)[0] for site in sites}
    assert actual <= builders, 'Only declared nightly-only builder files may compile a private app'


# Ordinary accident paths: ordinary shared setup, requested fixture setup,
# import-time preparation, documented backend targets, shell cwd setup and a
# Python helper that uses a compiler after its parent has launched it.
@pytest.mark.parametrize(
    'route', ['autouse', 'requested', 'import-init', 'ninja', 'make', 'compound', 'child']
)
def test_no_build_policy_covers_ordinary_accidental_execution_routes(tmp_path, route):
    fixture = probe(tmp_path, 'tests/system/py/test_use.py', 'def test_use(): pass\n')
    if route in {'autouse', 'requested'}:
        probe(
            tmp_path,
            'tests/conftest.py',
            'import pytest, subprocess\n@pytest.fixture('
            + ('autouse=True' if route == 'autouse' else '')
            + ')\n'
            'def app(): subprocess.run(["ninja","edi_app"])\n',
        )
        if route == 'requested':
            fixture.write_text('def test_use(app): pass\n')
    elif route == 'import-init':
        probe(
            tmp_path,
            'tools/helper.py',
            'import subprocess\nsubprocess.run(["make","edi_app"])\ndef value(): return 1\n',
        )
        fixture.write_text('from tools.helper import value\ndef test_use(): assert value() == 1\n')
    elif route == 'child':
        probe(
            tmp_path, 'tools/helper.py', 'import subprocess\nsubprocess.run(["ninja","edi_app"])\n'
        )
        fixture.write_text(
            'import subprocess\ndef test_use(): subprocess.Popen(["python","tools/helper.py"])\n'
        )
    else:
        command = 'cd build/app && ninja edi_app' if route == 'compound' else route + ' edi_app'
        fixture.write_text(
            'import subprocess\ndef test_use(): subprocess.run('
            + repr(command)
            + ', shell=True)\n'
        )
    assert app_build_sites(tmp_path), (
        'The stated ordinary pytest/process accident must reach its compiler boundary'
    )


def test_child_python_guard_observes_the_actual_child_compiler_and_normal_process(tmp_path):
    root = Path(__file__).resolve().parents[3]
    helper = probe(
        tmp_path,
        'helper.py',
        'import subprocess\nsubprocess.run(["ninja","edi_app"],check=True)\n',
    )
    with process_guard(root) as state:
        result = subprocess.run(
            [sys.executable, str(helper)], capture_output=True, text=True, check=False, timeout=2
        )
        positive = subprocess.run(
            [sys.executable, '-c', 'import subprocess; subprocess.run(["/bin/echo","normal"])'],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    assert result.returncode != 0 and 'private app build' in result.stderr, (
        'The compiler must refuse in the child before running Ninja'
    )
    assert positive.returncode == 0, 'An ordinary child process remains permitted'
    assert any('ninja' in words for words in state['blocked']), (
        'The parent observation must retain its actual child refusal'
    )
    assert any('/bin/echo' in words for words in state['launched']), (
        'The observation must also retain permitted child launches'
    )


@pytest.mark.parametrize('mutation', ['current-is-main', 'swap', 'stale-id', 'wrong-head'])
def test_actual_timing_collection_refuses_aliased_swapped_or_stale_run_evidence(
    tmp_path, mutation
):
    root = Path(__file__).resolve().parents[3]
    workflow = yaml.safe_load((root / '.github/workflows/ci.yml').read_text())
    if mutation in {'stale-id', 'wrong-head'}:
        timing_evidence(workflow, tmp_path, api_mutation=mutation)
        return
    step = next(
        step
        for step in workflow['jobs']['system-time']['steps']
        if 'tools/ci/system_shard_time.py' in step.get('run', '')
    )
    if mutation == 'current-is-main':
        step['run'] = step['run'].replace('current.json', 'main.json')
    else:
        step['run'] = (
            step['run']
            .replace('current.json', 'swapped.json')
            .replace('main.json', 'current.json')
            .replace('swapped.json', 'main.json')
        )
    with pytest.raises(AssertionError, match=r'PR|comparator|evidence'):
        timing_evidence(workflow, tmp_path, slow=True)
