"""No-build task dispatcher for note 20 shell tests; never calls real pixi.

Interpret the declared dependency order once per invocation, as pixi does. Only
app sequencing and core-build commands execute; unrelated verify gates are
outside this witness. Build scripts and terminal tools are replaced by spies.
"""

import os
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

root = Path.cwd()


def invoke(command, env):
    """Keep each authored tool spy behind its explicit native interpreter."""
    target = Path(command[0])
    if not target.is_file() and (root / 'bin' / command[0]).is_file():
        target = root / 'bin' / command[0]
    if target.is_file():
        with target.open('rb') as stream:
            scripted = stream.read(2) == b'#!'
    else:
        scripted = False
    if scripted:
        command = [env['FIXTURE_NATIVE_BASH'], target.as_posix(), *command[1:]]
    return subprocess.run(command, env=env, check=True)


manifest = tomllib.loads((root / 'pixi.toml').read_text())
tasks = dict(manifest['tasks'])
for feature in manifest.get('feature', {}).values():
    tasks.update(feature.get('tasks', {}))
args = sys.argv[1:]
if args[:1] == ['run']:
    args.pop(0)
environment = None
skip_deps = False
while args and args[0].startswith('-'):
    option = args.pop(0)
    if option in {'-e', '--environment'}:
        environment = args.pop(0)
    elif option == '--skip-deps':
        skip_deps = True
    else:
        raise SystemExit(f'unsupported pixi run option: {option}')
seen = set()


def run(name, extra=(), environment=None, inherited=None):
    # Review-7's real Pixi run distinguished an inherited reference from an
    # explicitly environment-qualified one, even when both select app.
    identity = (name, environment)
    if identity in seen:
        return
    seen.add(identity)
    if name not in tasks:
        invoke([name, *extra], os.environ)
        return
    if not (
        name.startswith(('app-', 'verify')) or name in {'group-app', 'core-build', 'merge-tasks'}
    ):
        return
    spec = tasks[name]
    if isinstance(spec, str):
        spec = {'cmd': spec}
    selected = environment or inherited or os.environ.get('PIXI_ENVIRONMENT_NAME', 'default')
    if not skip_deps:
        for dependency in spec.get('depends-on', []):
            dep = {'task': dependency} if isinstance(dependency, str) else dependency
            run(dep['task'], environment=dep.get('environment'), inherited=selected)
    env = {**os.environ, 'PIXI_ENVIRONMENT_NAME': selected, **spec.get('env', {})}
    cmd = spec.get('cmd', '')
    if name.startswith('app-test-scan-') and isinstance(cmd, str) and 'cmake' in cmd:
        with Path(env['E04_CALLS']).open('a', encoding='utf-8') as stream:
            stream.write('check:' + name + '\n')
        return
    if cmd:
        if isinstance(cmd, list):
            invoke(
                [env['FIXTURE_NATIVE_BASH'] if cmd[0] == 'bash' else cmd[0], *cmd[1:], *extra], env
            )
        else:
            subprocess.run(
                [env['FIXTURE_NATIVE_BASH'], '-c', cmd + ' ' + shlex.join(extra)],
                env=env,
                check=True,
            )


run(args[0], args[1:], environment=environment)
