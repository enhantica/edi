# SPDX-License-Identifier: BSD-3-Clause
"""Run a crysta pixi task's dependencies one at a time, then its pytest, so one red hides nothing.

    python3 tools/ci/crysta_tasks.py --root DIR --findings DIR --record PATH [--skip DEP] ENV TASK

pixi stops at the first dependency that fails, and every test after it goes unseen. Here each
dependency runs alone, in pixi's order, as a crysta_findings.py check with its time printed; the
task's pytest runs after them whatever they did, and the exit is the first failure's code. --skip
leaves out a dependency the tests of this part do not read.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

FINDINGS = Path(__file__).with_name('crysta_findings.py')


def graph(listing: list[dict]) -> dict[tuple[str, str], list[tuple[str | None, str]]]:
    """Each (environment, task) and the tasks it depends on, from `pixi task list --json`."""
    found = {}
    for environment in listing:
        name = environment['environment']
        tasks = list(environment.get('tasks') or [])
        for feature in environment.get('features') or []:
            tasks += feature.get('tasks') or []
        for task in tasks:
            found[name, task['name']] = [
                (dep.get('environment'), dep['task_name']) for dep in task.get('depends_on') or []
            ]
    return found


def order(tasks: dict, environment: str, task: str) -> list[tuple[str, str]]:
    """The dependencies of a task in the order pixi runs them: depth first, each once."""
    if (environment, task) not in tasks:
        raise SystemExit(f'crysta_tasks: no task {task} in environment {environment}')
    done: list[tuple[str, str]] = []

    def visit(env: str, name: str) -> None:
        for dep_env, dep in tasks[env, name]:
            key = (dep_env or env, dep)
            if key not in done:
                if key not in tasks:
                    raise SystemExit(f'crysta_tasks: no task {dep} in environment {key[0]}')
                visit(*key)
                done.append(key)

    visit(environment, task)
    return done


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--findings', required=True, type=Path)
    parser.add_argument('--record', required=True, type=Path)
    parser.add_argument('--skip', action='append', default=[])
    parser.add_argument('environment')
    parser.add_argument('task')
    args = parser.parse_args(argv)
    listing = json.loads(
        subprocess.run(
            ['pixi', 'task', 'list', '--json'],
            cwd=args.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    status = 0
    steps = [
        (f'dependency {name} ({env})', 'check', args.findings / f'{name}.log', env, name)
        for env, name in order(graph(listing), args.environment, args.task)
        if name not in args.skip
    ]
    steps.append((f'task {args.task}', 'pytest', args.record, args.environment, args.task))
    for label, kind, report, env, name in steps:
        root = ['--root', str(args.root)] if kind != 'pytest' else []
        command = [sys.executable, str(FINDINGS), *root, 'run', kind, str(report), '--']
        command += ['pixi', 'run', '-e', env, '--skip-deps', name]
        started = time.monotonic()
        code = subprocess.run(command, cwd=args.root, check=False).returncode
        print(
            f'crysta_tasks: {label}: exit {code}, {(time.monotonic() - started) / 60:.1f} min',
            flush=True,
        )
        status = status or code
    return status


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
