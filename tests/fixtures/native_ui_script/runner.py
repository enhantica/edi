"""Execute original wiring vectors on the actual Qt owner after native migration.

Acorn identifies syntax and exposes lexical fixture bindings. It supplies no
ApplicationInfo behavior. Only a job lacking both artifact and Qt build capability
can skip; an app-capable job must supply its real matching runner.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def require_runner(runner: Path) -> None:
    if not runner.is_file() or not os.access(runner, os.X_OK):
        qt_config = 'lib/cmake/Qt6QuickTest/Qt6QuickTestConfig.cmake'
        can_build = any(
            (Path(sys.prefix) / base / qt_config).is_file() for base in ('', 'Library')
        )
        absent = not runner.exists() and not runner.is_symlink()
        if absent and 'EDI_APP_TEST_RUNNER' not in os.environ and not can_build:
            reason = (
                'Native UI wiring requires edi_app_tests; this Pixi job has neither the '
                'artifact nor Qt6QuickTest to build it. Run this case in the app environment '
                'after app-build. Pure JavaScript checks still run in the core job.'
            )
            # The ordinary core task is quiet: expose the prerequisite in its
            # warning summary as well as every skipped test's stored reason.
            warnings.warn(reason, pytest.PytestWarning, stacklevel=2)
            pytest.skip(reason)
        raise AssertionError(
            'Native UI wiring requires the real edi_app_tests runner. The app-capable job '
            'must run app-build, and an explicit EDI_APP_TEST_RUNNER must name an executable.'
        )


def run_javascript(program: str, *, timeout: float = 5) -> subprocess.CompletedProcess[str]:
    node = Path(sys.prefix) / 'bin/node'
    if not node.is_file():
        raise AssertionError('The declared test interpreter must provide its pinned Node parser')
    prepared = subprocess.run(
        [str(node), str(HERE / 'prepare_script.cjs'), '--inspect'],
        input=program,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if prepared.returncode:
        return prepared
    description = json.loads(prepared.stdout)
    if not description['native']:
        return subprocess.run(
            [str(node)],
            input=program,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    require_runner(runner)
    storage = ROOT / 'build/native-ui-wiring'
    storage.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='case-', dir=storage))
    source = work / 'program.js'
    result = work / 'result.json'
    source.write_text(description['program'])
    (work / 'original.js').write_text(program)
    env = os.environ.copy()
    env.update(
        QT_QPA_PLATFORM='offscreen',
        QT_QUICK_BACKEND='software',
        EDI_NATIVE_SCRIPT_INPUT=str(source),
        EDI_NATIVE_SCRIPT_RESULT=str(result),
    )
    command = [str(runner), '-input', str(HERE / 'tst_native_script.qml')]
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
        env=env,
    )
    (work / 'runner.log').write_text(completed.stdout + completed.stderr)
    if not result.is_file():
        return subprocess.CompletedProcess(
            command,
            completed.returncode or 1,
            '',
            'The actual Qt witness published no result: ' + completed.stdout + completed.stderr,
        )
    observation = json.loads(result.read_text())
    valid = (
        observation.get('version') == 2
        and observation.get('ok')
        and isinstance(observation.get('nativeCalls'), int)
        and observation['nativeCalls'] >= 0
        and observation.get('outputCount') == 1
    )
    if not valid or completed.returncode:
        return subprocess.CompletedProcess(
            command,
            completed.returncode or 1,
            '',
            'The real native witness refused or failed: '
            + json.dumps(observation)
            + '\n'
            + str(work),
        )
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        expected = os.environ.get('GITHUB_SHA', '')
        if not expected or 'built at ' + expected + '\n' not in completed.stdout:
            return subprocess.CompletedProcess(
                command, 1, '', 'CI requires the actual same-head clean Qt runner'
            )
    return subprocess.CompletedProcess(command, 0, observation['output'], '')
