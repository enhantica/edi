"""Exercise the actual parent-option boundary with fresh nested pytest processes."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def hook_source():
    source = (ROOT / 'tests/conftest.py').read_text()
    function = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == 'pytest_configure'
    )
    return ast.get_source_segment(source, function)


def run_parent(tmp_path, option, escape):
    parent = tmp_path / ('escaped' if escape else 'control')
    parent.mkdir()
    hook = hook_source()
    if escape:
        hook = hook.replace("os.environ.pop('PYTEST_ADDOPTS', None)", 'pass')
    (parent / 'conftest.py').write_text('import os\n' + hook + '\n')
    (parent / 'test_parent.py').write_text(
        'import subprocess, sys, pytest\n'
        '@pytest.mark.parent_worker\n'
        'def test_parent_worker(tmp_path):\n'
        "    child = tmp_path / 'child'\n"
        '    child.mkdir()\n'
        "    test = child / 'test_child.py'\n"
        '    test.write_text("def test_child_witness(): print(\'child-witness-ran\')\\n")\n'
        "    result = subprocess.run([sys.executable, '-m', 'pytest', '-s', '-q', str(test)], "
        'cwd=child, capture_output=True, text=True, check=False)\n'
        "    assert result.returncode == 0, 'Nested pytest: the child oracle must execute'\n"
        "    assert 'child-witness-ran' in result.stdout, "
        "'Nested pytest: parent selectors must not suppress the child witness'\n"
        "    assert tmp_path.exists(), 'Nested pytest: the parent scratch must survive'\n"
    )
    options = {
        'basetemp': '--basetemp=' + str(parent / 'scratch'),
        'keyword': '-k parent_worker',
        'marker': '-m parent_worker',
    }
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith('PYTEST_')
    }
    environment['PYTEST_ADDOPTS'] = options[option]
    return subprocess.run(
        [
            sys.executable,
            '-m',
            'pytest',
            '-q',
            '-s',
            '-p',
            'no:cacheprovider',
            '-o',
            'markers=parent_worker: parent option control',
            str(parent / 'test_parent.py'),
        ],
        cwd=parent,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )


@pytest.fixture(scope='module')
def parent_runs(tmp_path_factory):
    # Fresh-process qualification is shared setup, recorded once as a module cost.
    return {
        option: (
            run_parent(tmp_path_factory.mktemp(option + '-control'), option, False),
            run_parent(tmp_path_factory.mktemp(option + '-escape'), option, True),
        )
        for option in ['basetemp', 'keyword', 'marker']
    }


@pytest.mark.parametrize('option', ['basetemp', 'keyword', 'marker'])
def test_parent_options_do_not_reach_nested_pytest(parent_runs, option):
    control, escaped = parent_runs[option]
    assert control.returncode == 0, (
        'Nested pytest: the actual configuration hook must preserve the parent scratch and '
        'execute the child witness under each parent option\n' + control.stdout + control.stderr
    )
    assert escaped.returncode != 0, (
        'Nested pytest: removing the actual option boundary must expose each inherited '
        'basetemp or selector escape'
    )
