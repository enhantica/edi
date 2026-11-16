"""Retiering genuine configure work preserves its original pull-request core execution."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.native_process import fixture_shell, python_program

ROOT = Path(__file__).resolve().parents[3]
SUBJECT = 'tests/system/py/test_runtime_publication_reuse.py'


def assert_selection(argv):
    assert argv[:4] == ['-m', 'pytest', 'tests/unit', 'tests/integration'], (
        'The original core job retains both complete unit and integration selections'
    )
    assert argv.count(SUBJECT) == 1, (
        'Retiered real runtime-publication checks still execute exactly once in the PR core job'
    )


def test_core_entrypoint_retains_the_actual_publication_workflows_after_retiering(tmp_path):
    checkout = tmp_path / 'entrypoint with spaces'
    (checkout / 'tests').mkdir(parents=True)
    (checkout / 'tests/test-groups.json').write_bytes(
        (ROOT / 'tests/test-groups.json').read_bytes()
    )
    binary = tmp_path / 'spy bin'
    binary.mkdir()
    python_program(
        binary / 'python',
        """import json, subprocess, sys
if sys.argv[1:2] == ['-c']:
    raise SystemExit(subprocess.call([sys.executable, *sys.argv[1:]]))
print('PYTEST_ARGV ' + json.dumps(sys.argv[1:]))
""",
    )
    observed = []
    for name, source in [
        ('current', (ROOT / 'tools/ci/core-tests.sh').read_text()),
        (
            'comment-only',
            (ROOT / 'tools/ci/core-tests.sh').read_text().replace(' ' + SUBJECT, '')
            + '\n# '
            + SUBJECT
            + '\n',
        ),
    ]:
        script = checkout / (name + '.sh')
        script.write_text(source, encoding='utf-8', newline='\n')
        result = subprocess.run(
            fixture_shell(binary, 'core_subject="$1"; shift; . "$core_subject"')
            + [script.as_posix()],
            cwd=checkout,
            env={**os.environ, 'EDI_RUN_NIGHTLY_ONLY': 'false', 'EDI_RUN_WEEKLY_ONLY': 'false'},
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        assert result.returncode == 0, (
            'The actual finite core entrypoint reaches the original Python runner: '
            + result.stderr
        )
        records = [
            line.removeprefix('PYTEST_ARGV ')
            for line in result.stdout.splitlines()
            if line.startswith('PYTEST_ARGV ')
        ]
        assert len(records) == 1, (
            'The real core entrypoint executes one selected pytest invocation'
        )
        observed.append(json.loads(records[0]))
    assert_selection(observed[0])
    with pytest.raises(AssertionError, match='PR core job'):
        assert_selection(observed[1])
