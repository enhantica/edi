"""notebook-gate rejection proof ( re-tier).

Moved from tests/integration/py/test_c09_t16_verification_notebooks.py with the assertions
unchanged: it executes a real notebook through the configured gate to prove rejection — an
end-to-end subprocess pipeline, which is system work by the tier rationale.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _run(
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


def _task_config(name: str) -> tuple[list[str], set[str]]:
    tasks = tomllib.loads((ROOT / 'pixi.toml').read_text())['tasks']
    assert name in tasks, f'missing pixi task: {name}'
    task = tasks[name]
    if isinstance(task, str):
        return shlex.split(task), set()

    command = task.get('cmd', [])
    tokens = (
        [str(token) for token in command] if isinstance(command, list) else shlex.split(command)
    )
    dependencies = task.get('depends-on', [])
    if isinstance(dependencies, str):
        dependencies = [dependencies]
    return tokens, set(dependencies)


def test_configured_notebook_gate_rejects_a_broken_assertion(tmp_path: Path) -> None:
    command, _ = _task_config('notebook-tests')
    assert command, 'notebook-tests must have an executable command'

    notebook_dir = tmp_path / 'docs/dev/verification'
    notebook_dir.mkdir(parents=True)
    marker = ' deliberately broken notebook assertion'
    notebook = {
        'cells': [
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [f'raise AssertionError({marker!r})\n'],
            }
        ],
        'metadata': {
            'kernelspec': {
                'display_name': 'Python 3',
                'language': 'python',
                'name': 'python3',
            },
            'language_info': {'name': 'python', 'version': '3'},
        },
        'nbformat': 4,
        'nbformat_minor': 5,
    }
    (notebook_dir / 'counterfactual.ipynb').write_text(json.dumps(notebook))

    isolated = tmp_path / 'jupyter'
    isolated.mkdir()
    env = {
        **os.environ,
        'IPYTHONDIR': str(isolated / 'ipython'),
        'JUPYTER_CONFIG_DIR': str(isolated / 'config'),
        'JUPYTER_DATA_DIR': str(isolated / 'data'),
        'XDG_CACHE_HOME': str(isolated / 'cache'),
    }
    result = _run(*command, cwd=tmp_path, env=env)
    output = result.stdout + result.stderr
    assert result.returncode != 0, 'the configured notebook gate accepted a failing assertion'
    assert marker in output, f'the gate failed without executing the injected assertion:\n{output}'
