"""Acceptance gates for 's monorepo scaffold contracts."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from tests.fixtures.e09_t75_workflow import active
from tests.integration.py.ci_runner_contract import self_hosted_runners

ROOT = Path(__file__).resolve().parents[3]


def run(
    *args: str, cwd: Path = ROOT, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )


def assert_ok(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr


def test_surface_tree_matches_adr_0002() -> None:
    expected = {'core', 'lib', 'app', 'shared', 'cli', 'docs', 'tests'}
    missing = sorted(name for name in expected if not (ROOT / name).is_dir())
    assert not missing, f'missing ADR-0002 surfaces: {missing}'
    assert (ROOT / 'tests/hidden-surface.txt').is_file()
    assert any(path.is_file() for path in (ROOT / 'tests/unit').rglob('*'))
    assert not list((ROOT / 'tests').rglob('*_hidden.py'))
    assert (ROOT / 'tests/fixtures').is_dir()


def test_checkout_imports_edi_without_path_injection() -> None:
    result = run(sys.executable, '-c', 'import edi')
    assert_ok(result)


@pytest.mark.parametrize('surface', ['core', 'lib'])
def test_core_and_lib_are_qt_free(surface: str) -> None:
    forbidden = re.compile(r'PySide|\bimport\s+Qt\b|#\s*include\s*[<\"]Qt')
    offenders = [
        str(path.relative_to(ROOT))
        for path in (ROOT / surface).rglob('*')
        if path.is_file() and forbidden.search(path.read_text(errors='ignore'))
    ]
    assert not offenders, f'Qt leaked into {surface}: {offenders}'


def test_verify_requires_core_build() -> None:
    config = tomllib.loads((ROOT / 'pixi.toml').read_text())
    # : `verify` IS the merge-time full chain (`verify-full`); no wall-clock wrapper.
    assert config['tasks']['verify']['depends-on'] == ['verify-full'], (
        'the canonical verification task must delegate to the full entry point'
    )
    dependencies = config['tasks']['verify-full']['depends-on']
    assert 'core-build' in dependencies, (
        'the full verification chain must build the core before running gates'
    )


def test_app_is_one_option_gated_cpp_qml_host() -> None:
    root_cmake = (ROOT / 'CMakeLists.txt').read_text()
    app_cmake = (ROOT / 'app/CMakeLists.txt').read_text()
    assert re.search(
        r'option\s*\(\s*EDI_BUILD_APP\s+[^)]*\bOFF\b',
        root_cmake,
        re.IGNORECASE | re.DOTALL,
    )
    assert re.search(r'if\s*\(\s*EDI_BUILD_APP\s*\)', root_cmake, re.IGNORECASE)
    assert root_cmake.count('add_subdirectory(app)') == 1
    assert len(re.findall(r'\bqt_add_qml_module\s*\(', app_cmake)) == 1

    qml_files = list((ROOT / 'app').rglob('*.qml'))
    assert qml_files, 'the app host must declare one QML source tree'
    # Before: every QML file was host source.  P6 adds exactly one
    # separately built benchmark resource; all product QML keeps its one root.
    benchmark = ROOT / 'app/tools/ChartBench.qml'
    assert all(path.is_relative_to(ROOT / 'app/qml') or path == benchmark for path in qml_files), (
        'ADR-0002/0015  P6: product QML stays in app/qml; the named benchmark is tooling'
    )
    assert benchmark.is_file() and re.search(
        r'qt_add_resources\s*\(\s*edi_app_chart_bench\b[^)]*\bFILES\s+tools/ChartBench\.qml\b',
        app_cmake,
        re.DOTALL,
    ), ' P6: the benchmark QML must be an explicit resource of its separate executable'

    forbidden = re.compile(r'PySide|pyside', re.IGNORECASE)
    offenders = [
        str(path.relative_to(ROOT))
        for path in (ROOT / 'app').rglob('*')
        if path.is_file() and forbidden.search(path.read_text(errors='ignore'))
    ]
    assert not offenders, f'PySide app path found: {offenders}'


def test_product_checkout_has_no_embedded_process_plane() -> None:
    tracked = set(run('git', 'ls-files').stdout.splitlines())
    forbidden_prefixes = (
        '.claude/',
        '.codex/',
        '.agents/',
        'tools/agent-os/',
        'knowledge/roadmap/',
        'knowledge/issues/',
        'knowledge/milestones/',
        'knowledge/process/',
        'knowledge/reviews-internal/',
        'knowledge/reviews-external/',
        'knowledge/_repo/',
    )
    forbidden_files = {
        'AGENTS.md',
        'CLAUDE.md',
        'TURN.md',
        'COORDINATION.md',
        'CHECKLIST.md',
        '.copier-answers.agent-os.yml',
        'tools/checks/roadmap-consistency.py',
        'knowledge/book/adrs/0004-shared-agent-os-and-sync.md',
    }
    offenders = sorted(
        path for path in tracked if path in forbidden_files or path.startswith(forbidden_prefixes)
    )
    assert not offenders, f'process-plane paths remain in product checkout: {offenders}'


def test_ci_routes_surfaces_and_uses_strict_self_hosted_jobs() -> None:
    workflow = (ROOT / '.github/workflows/ci.yml').read_text()

    def job_body(name: str) -> str:
        match = re.search(
            rf'^  {re.escape(name)}:\n(?P<body>.*?)(?=^  \S|\Z)',
            workflow,
            re.MULTILINE | re.DOTALL,
        )
        assert match, f'missing CI job: {name}'
        return match.group('body')

    def condition_outputs(name: str) -> set[str]:
        condition = re.search(r'^\s*if:\s*(.+)$', job_body(name), re.MULTILINE)
        assert condition, f'missing condition for CI job: {name}'
        return set(re.findall(r'needs\.changes\.outputs\.(\w+)', condition.group(1)))

    jobs = yaml.safe_load(workflow)['jobs']
    assert jobs, 'E01: CI has concrete jobs whose runners can be checked'
    runners = [runner for job in jobs.values() for runner in self_hosted_runners(job)]
    from tests.integration.py.test_e09_t75_native_workflow import (  # noqa: PLC0415 - defer cross-module test wiring
        public_build_boundary,
        public_profile,
    )

    public = public_profile(jobs)
    family = 'github-hosted' if public else 'self-hosted'
    assert [family, 'Linux', 'X64'] in runners, 'E01: Linux runner remains scheduled'
    assert [family, 'macOS', 'ARM64'] in runners, 'E01: macOS runner remains scheduled'

    # Before: path-filtered core/lib/cli jobs. After  I1: all required jobs
    # execute; only the non-gate app recovery remains change-scoped.
    filters = workflow.split('filters: |', 1)[1].split('\n\n', 1)[0]
    assert "app_build: ['tools/ci/app-build.sh']" in filters, (
        'E01/ only the app recovery exercise retains its script filter'
    )
    for name in ('native', 'core', 'app', 'audit', 'notebooks', 'docs', 'cli-python'):
        if public:
            public_build_boundary(jobs, name)
        else:
            for event in ('push', 'pull_request', 'workflow_dispatch'):
                assert active(jobs[name], event), (
                    f'required {name} runs on every changed surface in full CI'
                )
                assert active(jobs[name], event, core_only=True) == (name in {'native', 'core'}), (
                    f'only explicit core-only repair skips downstream {name}'
                )
    assert 'pixi run core-build' in job_body('native'), (
        'E01/ the native matrix produces the core once'
    )
    if not public:
        assert 'native' in jobs['core']['needs'], (
            'E01/ private core consumes the native producer rather than rebuilding'
        )
    assert 'pixi run crysta-pin-check' not in workflow, (
        'E01/ the retired source-pin policing remains absent'
    )
    assert 'pixi run crysta-consumer' in job_body('core'), (
        'E01/ the installed crysta consumer proof remains required'
    )

    app_wasm = job_body('app-wasm')
    assert all(
        active(jobs['app-wasm'], event, states={'changes': 'success', 'core': 'success'})
        for event in ('push', 'pull_request', 'workflow_dispatch')
    ), 'the WebAssembly job runs on every full CI event'
    assert 'wasm-build' in app_wasm and 'wasm-check' in app_wasm, (
        'the WebAssembly job builds and checks the real site'
    )
    assert 'agent-os-drift' not in workflow
    assert 'tools/agent-os/' not in json.dumps(jobs), (
        'E01/ executable passenger jobs must not run re\x6cay-owned machinery'
    )
    assert 'roadmap-consistency.py' not in workflow
