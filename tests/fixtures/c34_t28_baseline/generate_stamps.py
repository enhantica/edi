"""Generate stamps.tsv using the exact pre-move source and its existing native build.

Only the visible route vehicle is compiled. The production library is reused,
with the compiler, ABI flags and libraries recorded by that same build.
"""

import argparse
import json
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

if __package__:
    from .closure import require_baseline_closure
else:
    from closure import require_baseline_closure

BASE = 'f3ea7afea400639f2a66d6acb8d922163f1ef128'
TARGET = 'core/edi_tests'
FIXTURE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    root, build = args.source_root.resolve(), args.build.resolve()
    git, ninja = shutil.which('git'), shutil.which('ninja')
    if not git or not ninja:
        parser.error('the producer toolchain must provide Git and Ninja')
    require_baseline_closure(root)
    records = json.loads(subprocess.check_output([ninja, '-C', str(build), '-t', 'compdb']))
    entry = next(
        x
        for x in records
        if '/test_' in x.get('file', '')
        and x.get('output', '').endswith('.o')
        and TARGET.rsplit('/', maxsplit=1)[-1] + '.dir' in x['output']
    )
    arguments, flags = iter(shlex.split(entry['command'])), []
    for arg in arguments:
        if arg in {'-c', '-o', '-MF', '-MT'}:
            next(arguments)
        elif arg not in {'-MD', '-MMD'}:
            flags.append(arg)
    with tempfile.TemporaryDirectory() as temporary:
        obj, exe = Path(temporary) / 'vehicle.o', Path(temporary) / 'vehicle'
        subprocess.run(
            [*flags, '-O0', '-c', str(FIXTURE / 'generate_stamps.cpp'), '-o', str(obj)],
            cwd=build,
            check=True,
        )
        entry = next(x for x in records if x.get('output') == TARGET and x['command'])
        arguments = shlex.split(entry['command'])
        start = arguments.index('&&') + 1
        arguments = iter(arguments[start : arguments.index('&&', start)])
        link = []
        for arg in arguments:
            if arg == '-o':
                next(arguments)
            elif not (arg.endswith('.o') or arg.startswith('-Wl,--dependency-file=')):
                link.append(arg)
        subprocess.run([link[0], str(obj), *link[1:], '-o', str(exe)], cwd=build, check=True)
        observed = subprocess.check_output([str(exe)], cwd=root)
    (FIXTURE / 'stamps.tsv').write_bytes(observed)
    print('captured native stamp flags from', BASE, 'with', build, flush=True)


if __name__ == '__main__':
    main()
