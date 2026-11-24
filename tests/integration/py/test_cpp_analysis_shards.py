"""Replay PR analyzer shards over compile databases with an independent legacy inventory."""

import json
import os
import shlex
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pytest
import yaml

from tests.fixtures.native_process import environment_bash
from tests.system.py.ci_execution_contract import (
    contexts,
    prerequisites_ready,
    render,
    run_settings,
    task_commands,
    value,
)

ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(os.name == 'nt', reason='The analyzer jobs use POSIX shell tools')
DESKTOP_JOBS = {'app', 'app-macos', 'app-windows'}
ANALYZERS = ('cpp-tidy', 'cpp-cppcheck')
PLATFORM_SOURCES = {'linux-64': 'app/src/linux.cpp', 'osx-arm64': 'app/src/macos.cpp'}

# The old app compile database supplied native code and the old core database
# supplied Python bindings. The excluded rows below present the same spellings
# in the wrong database and outside the source tree.
LEGACY_APP_FILES = {
    'app/main.cpp',
    'app/src/session.cpp',
    'app/tests/probe.cpp',
    'assistant/native/main.cpp',
    'cli/src/main.cpp',
    'core/src/io.cpp',
    'core/src/model/phase.cpp',
}
LEGACY_CORE_FILES = {'lib/src/bindings.cpp', 'lib/src/project.cpp'}
EXCLUDED_APP_FILES = {
    'lib/src/wrong-build.cpp',
    'core/tests/wrong-directory.cpp',
    'assistant/service/not-native.cpp',
    'build/app/app_autogen/mocs_compilation.cpp',
    'vendor/sdk/engine.cpp',
}
EXCLUDED_CORE_FILES = {'core/src/not-a-binding.cpp', 'app/src/wrong-build.cpp'}


def source_corpus(*directories):
    return {
        file.relative_to(ROOT).as_posix()
        for directory in directories
        for file in (ROOT / directory).rglob('*.cpp')
    }


def compile_database(root, build, paths):
    directory = root / 'build' / build
    directory.mkdir(parents=True)
    rows = []
    for relative in sorted(paths, reverse=True):
        source = root / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('// Independent translation unit.\n')
        rows.append({
            'directory': str(directory),
            'file': str(source),
            'command': shlex.join(['c++', '-c', str(source), '-o', source.stem + '.o']),
        })
    (directory / 'compile_commands.json').write_text(json.dumps(rows))


def analyzer_steps(workflow, tool, platform):
    found = []
    for name, job, ctx, sdk in contexts(workflow, 'pull_request'):
        if sdk != platform:
            continue
        for step in job.get('steps', []):
            body = step.get('run', '')
            if tool not in body.split():
                continue
            assert ctx['github.job'] not in DESKTOP_JOBS, (
                'C++ analysis runs in separate jobs from the desktop app on every platform'
            )
            shell, env = run_settings(workflow, job, step, ctx)
            ctx.update({f'env.{key}': item for key, item in env.items()})
            assert (
                value(job.get('if'), ctx)
                and prerequisites_ready(workflow, job, ctx)
                and value(step.get('if'), ctx)
            ), f'{name} actually runs {tool} on trusted pull requests'
            assert not job.get('continue-on-error') and not step.get('continue-on-error'), (
                'Any analysis finding must fail its responsible PR shard'
            )
            found.append((name, render(body, ctx), env, shell))
    assert len(found) > 1 and len({name for name, *_ in found}) == len(found), (
        f'{tool} has multiple individually named PR shards on {platform}'
    )
    return found


def execute_analyzer(root, tool, step, tasks, bin_dir):
    name, body, env, _shell = step
    argv = shlex.split(body)
    assert argv[:2] == ['pixi', 'run'] and tool in argv, (
        'The workflow reaches the actual Pixi analysis task with its shard arguments'
    )
    (task,) = tasks[tool]
    assert task[0] == tool, 'The analysis task delegates only its declared analysis command'
    record = root / 'analysis.jsonl'
    record.unlink(missing_ok=True)
    result = subprocess.run(
        [
            environment_bash(),
            '-e',
            '-o',
            'pipefail',
            '-c',
            task[1] + ' ' + shlex.join(argv[argv.index(tool) + 1 :]),
        ],
        cwd=root,
        env={
            **os.environ,
            **env,
            **task[2],
            'PATH': str(bin_dir) + os.pathsep + os.environ['PATH'],
            'EDI_TEST_ANALYSIS_RECORD': str(record),
            'EDI_TEST_ANALYSIS_ROOT': str(root),
        },
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0 and record.is_file(), (
        f'{name} executes {tool} against the synthetic compile databases: {result.stderr}'
    )
    return [json.loads(line) for line in record.read_text().splitlines()]


@pytest.mark.parametrize('platform', PLATFORM_SOURCES)
@pytest.mark.parametrize('tool', ANALYZERS)
def test_pr_analysis_shards_cover_exactly_the_legacy_files(tmp_path, platform, tool):
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    tasks = task_commands((ROOT / 'pixi.toml').read_text(), 'cpp-lint')
    steps = analyzer_steps(workflow, tool, platform)
    shutil.copytree(ROOT / 'tools/ci', tmp_path / 'tools/ci')
    app = source_corpus('app', 'assistant/native', 'cli', 'core/src') | LEGACY_APP_FILES
    app.add(PLATFORM_SOURCES[platform])
    bindings = source_corpus('lib/src') | LEGACY_CORE_FILES
    compile_database(tmp_path, 'app', app | EXCLUDED_APP_FILES | {'lib/src/bindings.cpp'})
    compile_database(tmp_path, 'ci', bindings | EXCLUDED_CORE_FILES | {'core/src/io.cpp'})
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    instrument = ROOT / 'tests/fixtures/cpp_analysis/analyzer.py'
    for cmd in ('run-clang-tidy', 'cppcheck'):
        destination = bin_dir / cmd
        destination.write_text(
            f'#!{sys.executable}\n'
            f'import runpy\nrunpy.run_path({str(instrument)!r}, run_name="__main__")\n'
        )
        destination.chmod(0o755)
    owners = defaultdict(set)
    for step in steps:
        observations = execute_analyzer(tmp_path, tool, step, tasks, bin_dir)
        assert any(observation['files'] for observation in observations), (
            'Each PR shard processes part of the original compiler inventory'
        )
        for observation in observations:
            assert observation['tool'] == tool, 'The task launches its declared analyzer'
            assert observation['fatal'], 'The analyzer treats every finding as an error'
            for include in observation['files']:
                assert step[0] not in owners[include], (
                    f'{step[0]} analyzes {include} only once across its compile databases'
                )
                owners[include].add(step[0])
    expected = app | bindings
    assert set(owners) == expected, (
        'The shard union equals the original analysis file set on this platform, '
        f'missing {sorted(expected - owners.keys())}, extra {sorted(owners.keys() - expected)}'
    )
    assert all(len(shards) == 1 for shards in owners.values()), (
        'Every original analysis file is owned by exactly one shard on this platform'
    )
